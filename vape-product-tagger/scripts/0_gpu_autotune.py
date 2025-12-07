#!/usr/bin/env python3
"""
GPU Auto-Tuning Script for Vape Product Tagger

Monitors GPU utilization via nvidia-smi and dynamically adjusts worker count
to achieve target utilization (default 80%). Outputs baseline metrics at end.

Usage:
    python gpu_autotune.py --input input/products.csv --target-gpu 80
    python gpu_autotune.py --input input/products.csv --target-gpu 85 --max-workers 32
"""

import subprocess
import threading
import time
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv

from modules.ollama_utils import normalize_ollama_host


@dataclass
class GPUStats:
    """GPU statistics snapshot"""
    timestamp: float
    gpu_util: float  # GPU utilization %
    mem_util: float  # Memory utilization %
    mem_used: int    # Memory used MB
    mem_total: int   # Memory total MB
    temperature: int # Temperature C
    power_draw: float # Power draw W


@dataclass
class TuningResult:
    """Results from tuning run"""
    workers: int
    avg_gpu_util: float
    avg_mem_util: float
    products_per_min: float
    avg_latency_ms: float
    samples: int


class GPUMonitor:
    """Monitor GPU stats using nvidia-smi"""
    
    def __init__(self, gpu_ids: List[int] = None):
        self.gpu_ids = gpu_ids or [0, 1]  # Default to 2 GPUs
        self._running = False
        self._thread = None
        self._stats_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        
    def start(self):
        """Start background monitoring"""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            
    def _monitor_loop(self):
        """Background loop to collect GPU stats"""
        while self._running:
            try:
                stats = self._get_gpu_stats()
                with self._lock:
                    for stat in stats:
                        self._stats_history.append(stat)
            except Exception as e:
                print(f"GPU monitor error: {e}")
            time.sleep(0.5)  # Sample every 500ms
            
    def _get_gpu_stats(self) -> List[GPUStats]:
        """Query nvidia-smi for GPU stats"""
        cmd = [
            'nvidia-smi',
            '--query-gpu=index,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw',
            '--format=csv,noheader,nounits'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise RuntimeError(f"nvidia-smi failed: {result.stderr}")
            
        stats = []
        now = time.time()
        for line in result.stdout.strip().split('\n'):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 7:
                gpu_idx = int(parts[0])
                if gpu_idx in self.gpu_ids:
                    stats.append(GPUStats(
                        timestamp=now,
                        gpu_util=float(parts[1]),
                        mem_util=float(parts[2]),
                        mem_used=int(parts[3]),
                        mem_total=int(parts[4]),
                        temperature=int(parts[5]),
                        power_draw=float(parts[6]) if parts[6] != '[N/A]' else 0.0
                    ))
        return stats
    
    def get_current_avg(self, window_secs: float = 5.0) -> Dict:
        """Get average stats over recent window"""
        cutoff = time.time() - window_secs
        with self._lock:
            recent = [s for s in self._stats_history if s.timestamp > cutoff]
            
        if not recent:
            return {'gpu_util': 0, 'mem_util': 0, 'samples': 0}
            
        return {
            'gpu_util': sum(s.gpu_util for s in recent) / len(recent),
            'mem_util': sum(s.mem_util for s in recent) / len(recent),
            'mem_used': sum(s.mem_used for s in recent) / len(recent),
            'temperature': max(s.temperature for s in recent),
            'power_draw': sum(s.power_draw for s in recent) / len(recent),
            'samples': len(recent)
        }


class AutoTuner:
    """Auto-tune worker count based on GPU utilization"""
    
    def __init__(self, 
                 input_file: str,
                 target_gpu_util: float = 80.0,
                 min_workers: int = 4,
                 max_workers: int = 32,
                 ramp_step: int = 4,
                 stabilize_secs: float = 10.0,
                 ollama_model: str = 'llama3.1:8b',
                 ollama_num_parallel: int = None):
        
        self.input_file = input_file
        self.target_gpu_util = target_gpu_util
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.ramp_step = ramp_step
        self.stabilize_secs = stabilize_secs
        self.ollama_model = ollama_model
        
        # Load config
        config_path = Path('config.env')
        if config_path.exists():
            load_dotenv(config_path)
            
        raw_host = os.getenv('OLLAMA_HOST') or os.getenv('OLLAMA_BASE_URL')
        self.ollama_host = normalize_ollama_host(raw_host)
        
        # OLLAMA_NUM_PARALLEL - set if provided, otherwise read from env
        self.ollama_num_parallel = ollama_num_parallel or int(os.getenv('OLLAMA_NUM_PARALLEL', 8))
        
        # HTTP session with connection pooling
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=max_workers,
            pool_maxsize=max_workers * 2,
            max_retries=3
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        
        # GPU monitor
        self.gpu_monitor = GPUMonitor()
        
        # Results tracking
        self.tuning_results: List[TuningResult] = []
        self._request_latencies: deque = deque(maxlen=1000)
        self._products_processed = 0
        self._lock = threading.Lock()
        
        # Load products
        self.products = self._load_products()
        
    def _load_products(self) -> List[Dict]:
        """Load products from CSV"""
        products = []
        with open(self.input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(row)
        print(f"Loaded {len(products)} products from {self.input_file}")
        return products
        
    def _make_ollama_request(self, product: Dict) -> float:
        """Make single Ollama request, return latency in ms"""
        prompt = f"""Analyze this product and suggest category tags.
Product: {product.get('Handle', '')}
Title: {product.get('Title', '')}
Return JSON: {{"tags": ["tag1"], "confidence": 0.8}}"""

        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        start = time.time()
        try:
            response = self._session.post(url, json=payload, timeout=120)
            response.raise_for_status()
            latency = (time.time() - start) * 1000
            
            with self._lock:
                self._request_latencies.append(latency)
                self._products_processed += 1
                
            return latency
        except Exception as e:
            print(f"Request error: {e}")
            return -1
            
    def _run_with_workers(self, num_workers: int, duration_secs: float) -> TuningResult:
        """Run workload with specific worker count for duration"""
        print(f"\n{'='*60}")
        print(f"Testing with {num_workers} workers for {duration_secs:.0f}s...")
        print(f"{'='*60}")
        
        # Reset counters
        with self._lock:
            self._request_latencies.clear()
            self._products_processed = 0
            
        start_time = time.time()
        product_idx = 0
        futures = []
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Keep submitting work until duration elapsed
            while time.time() - start_time < duration_secs:
                # Submit batch of work
                while len([f for f in futures if not f.done()]) < num_workers * 2:
                    product = self.products[product_idx % len(self.products)]
                    futures.append(executor.submit(self._make_ollama_request, product))
                    product_idx += 1
                    
                # Brief sleep to avoid tight loop
                time.sleep(0.1)
                
                # Print progress
                stats = self.gpu_monitor.get_current_avg(window_secs=3.0)
                with self._lock:
                    processed = self._products_processed
                elapsed = time.time() - start_time
                rate = (processed / elapsed * 60) if elapsed > 0 else 0
                print(f"\r  Workers: {num_workers} | GPU: {stats['gpu_util']:.1f}% | "
                      f"Processed: {processed} | Rate: {rate:.1f}/min", end='', flush=True)
                
        print()  # Newline after progress
        
        # Wait for remaining futures
        for f in futures:
            try:
                f.result(timeout=30)
            except:
                pass
                
        # Calculate results
        elapsed = time.time() - start_time
        stats = self.gpu_monitor.get_current_avg(window_secs=duration_secs)
        
        with self._lock:
            latencies = list(self._request_latencies)
            processed = self._products_processed
            
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        products_per_min = (processed / elapsed * 60) if elapsed > 0 else 0
        
        result = TuningResult(
            workers=num_workers,
            avg_gpu_util=stats['gpu_util'],
            avg_mem_util=stats['mem_util'],
            products_per_min=products_per_min,
            avg_latency_ms=avg_latency,
            samples=stats['samples']
        )
        
        self.tuning_results.append(result)
        
        print(f"  Result: GPU={result.avg_gpu_util:.1f}%, Rate={result.products_per_min:.1f}/min, "
              f"Latency={result.avg_latency_ms:.0f}ms")
        
        return result
        
    def _set_ollama_num_parallel(self, num_parallel: int):
        """Set OLLAMA_NUM_PARALLEL by restarting Ollama with new value"""
        print(f"\n  Setting OLLAMA_NUM_PARALLEL={num_parallel}...")
        try:
            # Set env var for current process (Ollama reads on start)
            os.environ['OLLAMA_NUM_PARALLEL'] = str(num_parallel)
            
            # Kill existing Ollama
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True, timeout=5)
            time.sleep(1)
            
            # Start Ollama with new setting
            env = os.environ.copy()
            env['OLLAMA_NUM_PARALLEL'] = str(num_parallel)
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env
            )
            
            # Wait for Ollama to be ready
            for _ in range(30):
                try:
                    resp = self._session.get(f"{self.ollama_host}/api/tags", timeout=2)
                    if resp.status_code == 200:
                        print(f"  ✓ Ollama restarted with NUM_PARALLEL={num_parallel}")
                        return True
                except:
                    pass
                time.sleep(0.5)
                
            print(f"  ⚠ Ollama restart timeout")
            return False
        except Exception as e:
            print(f"  ⚠ Failed to set OLLAMA_NUM_PARALLEL: {e}")
            return False
    
    def run_auto_tune(self) -> Dict:
        """Run auto-tuning process"""
        print("\n" + "="*70)
        print("GPU AUTO-TUNING - Ramping up workers to target utilization")
        print("="*70)
        print(f"Target GPU Utilization: {self.target_gpu_util}%")
        print(f"Worker Range: {self.min_workers} - {self.max_workers} (step: {self.ramp_step})")
        print(f"Stabilization Time: {self.stabilize_secs}s per step")
        print(f"Ollama Model: {self.ollama_model}")
        print(f"Ollama Host: {self.ollama_host}")
        print(f"Ollama Parallel: {self.ollama_num_parallel}")
        
        # Set initial OLLAMA_NUM_PARALLEL
        self._set_ollama_num_parallel(self.ollama_num_parallel)
        
        # Start GPU monitoring
        self.gpu_monitor.start()
        time.sleep(1)  # Let monitor collect initial samples
        
        # Get baseline (idle) stats
        print("\nCollecting baseline (idle) GPU stats...")
        time.sleep(3)
        baseline = self.gpu_monitor.get_current_avg(window_secs=3.0)
        print(f"Baseline - GPU: {baseline['gpu_util']:.1f}%, Mem: {baseline['mem_util']:.1f}%")
        
        optimal_workers = self.min_workers
        optimal_result = None
        plateau_count = 0
        
        try:
            # Ramp up workers - test ALL values in range
            current_workers = self.min_workers
            
            while current_workers <= self.max_workers:
                # Adjust OLLAMA_NUM_PARALLEL to match workers (keep slightly lower)
                target_parallel = max(current_workers - 2, 4)
                if target_parallel != self.ollama_num_parallel:
                    self.ollama_num_parallel = target_parallel
                    self._set_ollama_num_parallel(target_parallel)
                    time.sleep(2)  # Let Ollama stabilize
                
                result = self._run_with_workers(current_workers, self.stabilize_secs)
                
                # Track best result by throughput
                if optimal_result is None or result.products_per_min > optimal_result.products_per_min:
                    optimal_result = result
                    optimal_workers = current_workers
                
                # Check if we've hit target GPU util
                if result.avg_gpu_util >= self.target_gpu_util:
                    print(f"\n✓ Target GPU utilization ({self.target_gpu_util}%) reached at {current_workers} workers!")
                    # Continue testing to find true optimal
                    
                # Check for plateau (3 consecutive non-improvements)
                if len(self.tuning_results) >= 3:
                    recent = self.tuning_results[-3:]
                    if all(r.products_per_min <= optimal_result.products_per_min * 1.02 for r in recent[-2:]):
                        plateau_count += 1
                        if plateau_count >= 2:
                            print(f"\n⚠ Throughput plateaued - stopping early")
                            break
                    else:
                        plateau_count = 0
                        
                # Ramp up
                current_workers += self.ramp_step
                
            if optimal_result is None and self.tuning_results:
                # Didn't reach target, use best result
                optimal_result = max(self.tuning_results, key=lambda r: r.products_per_min)
                optimal_workers = optimal_result.workers
                
        finally:
            self.gpu_monitor.stop()
            
        # Output results
        return self._generate_report(baseline, optimal_workers, optimal_result)
        
    def _generate_report(self, baseline: Dict, optimal_workers: int, optimal_result: TuningResult) -> Dict:
        """Generate and print final report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'target_gpu_util': self.target_gpu_util,
            'baseline': baseline,
            'optimal_workers': optimal_workers,
            'optimal_result': {
                'workers': optimal_result.workers if optimal_result else 0,
                'avg_gpu_util': optimal_result.avg_gpu_util if optimal_result else 0,
                'avg_mem_util': optimal_result.avg_mem_util if optimal_result else 0,
                'products_per_min': optimal_result.products_per_min if optimal_result else 0,
                'avg_latency_ms': optimal_result.avg_latency_ms if optimal_result else 0,
            },
            'all_results': [
                {
                    'workers': r.workers,
                    'avg_gpu_util': r.avg_gpu_util,
                    'products_per_min': r.products_per_min,
                    'avg_latency_ms': r.avg_latency_ms
                }
                for r in self.tuning_results
            ]
        }
        
        print("\n" + "="*70)
        print("AUTO-TUNING COMPLETE - BASELINE METRICS")
        print("="*70)
        
        print(f"\n{'BASELINE (Idle)':^40}")
        print("-"*40)
        print(f"  GPU Utilization:  {baseline['gpu_util']:.1f}%")
        print(f"  Memory Utilization: {baseline['mem_util']:.1f}%")
        
        print(f"\n{'OPTIMAL CONFIGURATION':^40}")
        print("-"*40)
        print(f"  Recommended Workers: {optimal_workers}")
        if optimal_result:
            print(f"  GPU Utilization:     {optimal_result.avg_gpu_util:.1f}%")
            print(f"  Memory Utilization:  {optimal_result.avg_mem_util:.1f}%")
            print(f"  Throughput:          {optimal_result.products_per_min:.1f} products/min")
            print(f"  Avg Latency:         {optimal_result.avg_latency_ms:.0f}ms")
            
        print(f"\n{'ALL TEST RESULTS':^40}")
        print("-"*40)
        print(f"{'Workers':>8} {'GPU%':>8} {'Rate/min':>10} {'Latency':>10}")
        print("-"*40)
        for r in self.tuning_results:
            print(f"{r.workers:>8} {r.avg_gpu_util:>7.1f}% {r.products_per_min:>10.1f} {r.avg_latency_ms:>9.0f}ms")
            
        print(f"\n{'RECOMMENDED CONFIG.ENV SETTINGS':^40}")
        print("-"*40)
        print(f"  MAX_WORKERS={optimal_workers}")
        print(f"  OLLAMA_NUM_PARALLEL={max(optimal_workers - 4, 8)}")
        
        # Save report to file
        report_path = Path('output/autotune_report.json')
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_path}")
        
        return report


def main():
    parser = argparse.ArgumentParser(description='GPU Auto-Tuning for Vape Product Tagger')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    parser.add_argument('--target-gpu', type=float, default=80.0, help='Target GPU utilization %% (default: 80)')
    parser.add_argument('--min-workers', type=int, default=8, help='Minimum workers to start (default: 8)')
    parser.add_argument('--max-workers', type=int, default=32, help='Maximum workers to test (default: 32)')
    parser.add_argument('--ramp-step', type=int, default=4, help='Workers to add each step (default: 4)')
    parser.add_argument('--stabilize', type=float, default=15.0, help='Seconds to run each test (default: 15)')
    parser.add_argument('--model', default='llama3.1:8b', help='Ollama model (default: llama3.1:8b)')
    parser.add_argument('--ollama-parallel', type=int, default=None, help='Initial OLLAMA_NUM_PARALLEL (default: auto)')
    
    args = parser.parse_args()
    
    print(f"Args received: min={args.min_workers}, max={args.max_workers}, step={args.ramp_step}")
    
    tuner = AutoTuner(
        input_file=args.input,
        target_gpu_util=args.target_gpu,
        min_workers=args.min_workers,
        max_workers=args.max_workers,
        ramp_step=args.ramp_step,
        stabilize_secs=args.stabilize,
        ollama_model=args.model,
        ollama_num_parallel=args.ollama_parallel
    )
    
    report = tuner.run_auto_tune()
    
    print("\n✓ Auto-tuning complete!")
    print(f"  Use: python main.py --input {args.input} --workers {report['optimal_workers']}")
    

if __name__ == '__main__':
    main()
