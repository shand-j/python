#!/usr/bin/env python3
"""
Controlled AI Product Tagger
===========================
AI-powered product tagging with strict vocabulary control.
Only approved tags from approved_tags.json can be applied.
"""

import json
import requests
import sqlite3
import csv
import re
import logging
import argparse
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os

# Ensure the project root is importable so local modules resolve when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tag_audit_db import TagAuditDB

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Controlled AI Product Tagger - Strict vocabulary tagging for vaping products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag products from default input directory
  python controlled_tagger.py
  
  # Tag specific file
  python controlled_tagger.py --input products.csv
  
  # Tag with custom output and limit
  python controlled_tagger.py --input products.csv --output tagged.csv --limit 10
  
  # Disable AI (rule-based only)
  python controlled_tagger.py --no-ai
  
  # Verbose logging
  python controlled_tagger.py --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input CSV file path (default: auto-detect from input/)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output CSV file path (default: output/controlled_tagged_products.csv)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (config.env)'
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI-powered tagging (use only rule-based tagging)'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit processing to first N products (useful for testing)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--type', '-t',
        type=str,
        help='Optional override for product Type (e.g. "Vaping/Smoking Products" or "CBD products")'
    )

    parser.add_argument(
        '--audit-db',
        type=str,
        help='Path to sqlite audit DB file (enables audit logging). If omitted, auditing is disabled.'
    )

    parser.add_argument(
        '--run-id',
        type=str,
        help='Resume a specific run by ID. If omitted, starts a new run.'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        help='Number of parallel workers (overrides MAX_WORKERS env var)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing (sequential mode)'
    )
    
    return parser.parse_args()

# Simple logger setup
def setup_simple_logger():
    logger = logging.getLogger('controlled-tagger')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class ControlledTagger:
    def __init__(self, config_file=None, no_ai=False, verbose=False, default_product_type=None, audit_db_path=None, run_id=None, max_workers=None, no_parallel=False):
        # Load config
        if config_file:
            load_dotenv(config_file)
        else:
            # Try default config.env
            config_path = Path('config.env')
            if config_path.exists():
                load_dotenv(config_path)
        
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.model_backend = os.getenv('MODEL_BACKEND', 'ollama')  # 'ollama' or 'huggingface'
        self.hf_repo_id = os.getenv('HF_REPO_ID')
        self.hf_token = os.getenv('HF_TOKEN')
        self.base_model = os.getenv('BASE_MODEL', 'meta-llama/Meta-Llama-3.1-8B-Instruct')
        self.ollama_host = os.getenv('OLLAMA_HOST') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', 60))
        self.ollama_num_parallel = int(os.getenv('OLLAMA_NUM_PARALLEL', os.getenv('MAX_WORKERS', 4)))
        self.secondary_ollama_model = os.getenv('OLLAMA_SECONDARY_MODEL', '')
        self.tertiary_ollama_model = os.getenv('OLLAMA_TERTIARY_MODEL', '')
        self.ai_confidence_threshold = float(os.getenv('AI_CONFIDENCE_THRESHOLD', 0.7))
        self.enable_ai_cascade = os.getenv('ENABLE_AI_CASCADE', 'true').lower() == 'true'
        self.progress_rate_window = max(5, int(os.getenv('PROGRESS_RATE_WINDOW_SECONDS', 30)))
        
        self.no_ai = no_ai
        # Allow CLI override or env var to force a product type for the run
        self.default_product_type = default_product_type or os.getenv('DEFAULT_PRODUCT_TYPE')
        
        # Setup logging
        self.logger = self._setup_logger(verbose)
        
        # HF model (lazy loaded)
        self._hf_model = None
        self._hf_tokenizer = None
        
        # Optional audit DB for persisting decisions (thread-safe for parallel processing)
        self.audit_db = TagAuditDB(audit_db_path, thread_safe=True) if audit_db_path else None
        # Handle run_id: if provided, resume; else start new
        self.run_id = run_id
        if self.audit_db:
            if run_id:
                status = self.audit_db.get_run_status(run_id)
                if not status:
                    raise ValueError(f"Run ID {run_id} not found in audit DB")
                if status == 'completed':
                    raise ValueError(f"Run ID {run_id} is already completed")
                self.logger.info(f"Resuming run {run_id}")
            else:
                config_dict = {
                    'no_ai': no_ai,
                    'verbose': verbose,
                    'default_product_type': default_product_type,
                    'audit_db_path': audit_db_path
                }
                self.run_id = self.audit_db.start_run(config=config_dict)
                self.logger.info(f"Started new run {self.run_id}")
        
        self.approved_tags = self._load_approved_tags()
        self.all_approved_tags = self._flatten_approved_tags()
        self.tag_to_category = self._build_tag_to_category()
        
        # Category priority for more specific categorization
        # Higher number = higher priority (more specific categories should have higher priority)
        self.category_priority = {
            'CBD': 15,           # CBD always highest priority
            'e-liquid': 14,      # E-liquid before disposable (explicit liquid products)
            'coil': 13,          # Coils explicitly mentioned are coil products
            'pod': 12,           # Replacement pods
            'tank': 11,          # Tanks before device
            'disposable': 10,    # Disposables
            'pod_system': 9,     # Pod systems (kits)
            'box_mod': 8,        # Box mods
            'device': 7,         # Generic device (lowest priority for hardware)
            'nicotine_pouches': 6,
            'accessory': 5,
            'supplement': 4,
            'terpene': 3,
            'extraction_equipment': 2,
        }
        self.category_tags = set(self.approved_tags.get('category', []))
        
        # Parallel processing config (CLI args override env vars)
        if no_parallel:
            self.parallel_processing = False
        else:
            self.parallel_processing = os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
        
        if max_workers:
            self.max_workers = max_workers
        else:
            self.max_workers = int(os.getenv('MAX_WORKERS', 4))
        
        self.batch_size = int(os.getenv('BATCH_SIZE', 10))
        if self.parallel_processing and self.max_workers > self.ollama_num_parallel:
            self.logger.warning(
                "MAX_WORKERS (%s) exceeds OLLAMA_NUM_PARALLEL (%s); Ollama may queue requests",
                self.max_workers,
                self.ollama_num_parallel,
            )
        
        # HTTP adapter reused per-thread for Ollama API calls
        self._http_adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers * 2,
            max_retries=3
        )
        self._http_thread_local = threading.local()
        
        # Performance tracking
        self._processed_count = 0
        self._ai_skipped_count = 0
        self._start_time = None
        self._lock = None  # Will be set when parallel processing starts
        self._progress_history = deque()
        self._metrics_lock = threading.Lock()
        self._ai_call_count = 0
        self._ai_total_latency = 0.0
        self._ai_inflight = 0
        self._ai_max_inflight = 0
        
    def _setup_logger(self, verbose):
        """Setup logger with appropriate level"""
        logger = logging.getLogger('controlled-tagger')
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def _format_eta(seconds):
        """Format ETA seconds into a human-friendly label."""
        if seconds is None or seconds <= 0:
            return "~00:00"
        minutes, secs = divmod(int(round(seconds)), 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
            return f"~{hours}h {minutes:02d}m"
        return f"~{minutes:02d}:{secs:02d}"

    def _get_http_session(self):
        """Return a thread-local HTTP session for Ollama calls."""
        if not hasattr(self._http_thread_local, 'session'):
            session = requests.Session()
            session.mount('http://', self._http_adapter)
            session.mount('https://', self._http_adapter)
            self._http_thread_local.session = session
        return self._http_thread_local.session

    def _is_ollama_model_available(self, model_name):
        """Check whether the requested Ollama model is installed locally."""
        if self.model_backend != 'ollama' or not model_name:
            return False
        url = f"{self.ollama_host}/api/show"
        session = self._get_http_session()
        try:
            response = session.post(url, json={'name': model_name}, timeout=self.ollama_timeout)
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False
    
    def _load_hf_model(self):
        """Lazy load HuggingFace model with LoRA adapters from HF Hub"""
        if self._hf_model is not None:
            return self._hf_model, self._hf_tokenizer
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel
        except ImportError:
            self.logger.error("HuggingFace backend requires: pip install torch transformers peft bitsandbytes")
            raise
        
        self.logger.info(f"Loading HF model: {self.base_model} + LoRA from {self.hf_repo_id}")
        
        # 4-bit quantization for inference
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            token=self.hf_token,
        )
        
        # Load LoRA adapters from HF Hub
        if self.hf_repo_id:
            self._hf_model = PeftModel.from_pretrained(base_model, self.hf_repo_id, token=self.hf_token)
        else:
            self._hf_model = base_model
        
        self._hf_tokenizer = AutoTokenizer.from_pretrained(self.base_model, token=self.hf_token)
        self._hf_model.eval()
        
        self.logger.info("HF model loaded successfully")
        return self._hf_model, self._hf_tokenizer
    
    def _get_ai_tags_hf(self, prompt: str) -> tuple:
        """Get AI tags using HuggingFace model"""
        import torch
        
        model, tokenizer = self._load_hf_model()
        
        # Format for chat model
        input_text = f"<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response_text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return response_text.strip()
        
    def _load_approved_tags(self):
        """Load approved tags structure"""
        tags_file = Path('approved_tags.json')
        if not tags_file.exists():
            raise FileNotFoundError("approved_tags.json not found. Run cleanup first.")
        
        with open(tags_file) as f:
            data = json.load(f)
            self.rules = data.pop('rules', {})
            return data
    
    def _flatten_approved_tags(self):
        """Create flat list of all approved tags"""
        tags = []
        for cat_data in self.approved_tags.values():
            if isinstance(cat_data, dict):
                tags.extend(cat_data.get('tags', []))
            else:
                tags.extend(cat_data)
        return tags
    
    def _build_tag_to_category(self):
        """Build mapping from tag to category"""
        tag_to_cat = {}
        for cat, cat_data in self.approved_tags.items():
            if isinstance(cat_data, dict):
                for tag in cat_data.get('tags', []):
                    tag_to_cat[tag] = cat
            else:
                for tag in cat_data:
                    tag_to_cat[tag] = cat
        return tag_to_cat
    
    def _create_ai_prompt(self, handle, title, description="", option1_name="", option1_value="", option2_name="", option2_value="", option3_name="", option3_value="", category=None):
        """Create category-aware AI prompt for tag suggestion with confidence scoring"""
        
        rules_text = "\n".join(f"- {rule}" for rule in self.rules.values())
        
        # Truncate description to save tokens
        desc_truncated = (description or 'Not provided')[:300]
        if len(description or '') > 300:
            desc_truncated += "..."
        
        # Compact approved tags - only include relevant categories
        relevant_tags = {}
        if category:
            # Only include category-relevant tags + always-needed ones
            always_include = ['category', 'brand']
            category_map = {
                'CBD': ['cbd_form', 'cbd_spectrum', 'cbd_strength'],
                'e-liquid': ['nicotine_type', 'nicotine_strength', 'vg_ratio', 'flavour_profile', 'bottle_size'],
                'pod': ['pod_type', 'capacity', 'resistance'],
                'coil': ['resistance', 'coil_type'],
                'disposable': ['nicotine_strength', 'puff_count', 'flavour_profile'],
                'device': ['device_type', 'battery_capacity'],
                'accessory': ['accessory_type'],
            }
            for key in always_include + category_map.get(category, []):
                if key in self.approved_tags:
                    relevant_tags[key] = self.approved_tags[key]
        else:
            # Unknown category - send only category tags to help identify
            relevant_tags = {'category': self.approved_tags.get('category', [])}
        
        # Further compress: only send tag names, not full config
        compressed_tags = {}
        for cat_name, cat_data in relevant_tags.items():
            if isinstance(cat_data, dict):
                compressed_tags[cat_name] = cat_data.get('tags', [])
            else:
                compressed_tags[cat_name] = cat_data
        
        # Base prompt - shortened
        base_prompt = f"""Analyze this vaping/CBD product and suggest tags from the approved list.

PRODUCT: {handle}
TITLE: {title}
DESC: {desc_truncated}
OPTIONS: {option1_name}:{option1_value} | {option2_name}:{option2_value} | {option3_name}:{option3_value}

APPROVED TAGS:
{json.dumps(compressed_tags)}

RULES:
{rules_text}

Return JSON only:
{{"tags": ["tag1", "tag2"], "confidence": 0.0-1.0, "reasoning": "brief"}}

Confidence: 0.95+=explicit in title, 0.80-0.94=strong evidence, 0.60-0.79=inference, <0.60=uncertain"""

        # Shorter category-specific hints
        if category == 'CBD':
            base_prompt += """

CBD HINTS: tincture=drops/oil/sublingual, capsule=pills/softgels, gummy=bears/candies, topical=cream/balm, patch=transdermal, paste=concentrate/wax"""
            
        elif category == 'e-liquid':
            base_prompt += """

E-LIQUID HINTS: Look for VG/PG ratio (50/50, 70/30), nic type (salt vs freebase), bottle size (10ml, 100ml shortfill)"""
            
        elif category == 'pod':
            base_prompt += """

POD HINTS: prefilled_pod=comes with juice, replacement_pod=empty pods for refilling"""

        return base_prompt
    
    def _get_ai_tags_ollama_http(self, prompt):
        """Call Ollama via HTTP API for better parallel performance"""
        url = f"{self.ollama_host}/api/chat"
        session = self._get_http_session()

        payload = {
            "model": self.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json"  # Force JSON output to prevent markdown wrapping
        }

        with self._metrics_lock:
            self._ai_inflight += 1
            if self._ai_inflight > self._ai_max_inflight:
                self._ai_max_inflight = self._ai_inflight
        start_time = time.time()

        try:
            response = session.post(url, json=payload, timeout=self.ollama_timeout)
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', '').strip()
        except requests.Timeout as exc:
            raise RuntimeError(
                f"Ollama response timed out after {self.ollama_timeout}s. "
                "Ensure `OLLAMA_NUM_PARALLEL` matches MAX_WORKERS and the model is loaded."
            ) from exc
        except requests.ConnectionError as exc:
            raise RuntimeError(
                f"Unable to reach Ollama at {self.ollama_host}. Verify the daemon is running."
            ) from exc
        finally:
            duration = time.time() - start_time
            with self._metrics_lock:
                self._ai_inflight = max(0, self._ai_inflight - 1)
                self._ai_call_count += 1
                self._ai_total_latency += duration
    
    def get_ai_tags(self, product_or_handle, title=None, description="", category=None):
        """Get AI tag suggestions using controlled vocabulary with category-aware prompting and confidence scoring.
        Returns tuple: (valid_tags, ai_metadata) where ai_metadata contains prompt, response, confidence, reasoning."""
        
        if isinstance(product_or_handle, dict):
            product = product_or_handle
            handle = product['handle']
            title = product['title']
            description = product['description']
            option1_name = product.get('option1_name', '')
            option1_value = product.get('option1_value', '')
            option2_name = product.get('option2_name', '')
            option2_value = product.get('option2_value', '')
            option3_name = product.get('option3_name', '')
            option3_value = product.get('option3_value', '')
        else:
            handle = product_or_handle
            option1_name = option1_value = option2_name = option2_value = option3_name = option3_value = ""
        
        ai_metadata = {
            'prompt': None,
            'model_output': None,
            'confidence': None,
            'reasoning': None
        }
        
        if self.no_ai:
            return [], ai_metadata
        
        try:
            prompt = self._create_ai_prompt(handle, title, description, option1_name, option1_value, option2_name, option2_value, option3_name, option3_value, category)
            ai_metadata['prompt'] = prompt
            
            # Route to appropriate backend
            if self.model_backend == 'huggingface':
                response_text = self._get_ai_tags_hf(prompt)
            else:
                # Default: Ollama via HTTP (faster than ollama library for parallel calls)
                response_text = self._get_ai_tags_ollama_http(prompt)
            
            ai_metadata['model_output'] = response_text
            
            # Clean markdown code blocks before JSON extraction
            cleaned_response = re.sub(r'```json\s*', '', response_text)
            cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
            cleaned_response = cleaned_response.strip()
            
            # Extract JSON object from response - use non-greedy match for nested objects
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_response, re.DOTALL)
            if not json_match:
                # Fallback to simple pattern for flat JSON
                json_match = re.search(r'\{.*?\}', cleaned_response, re.DOTALL)
            if json_match:
                try:
                    ai_response = json.loads(json_match.group())
                    suggested_tags = ai_response.get('tags', [])
                    confidence = ai_response.get('confidence', 0.5)
                    reasoning = ai_response.get('reasoning', '')
                    
                    ai_metadata['confidence'] = confidence
                    ai_metadata['reasoning'] = reasoning
                    
                    # Only use high-confidence suggestions (threshold configurable)
                    if confidence >= self.ai_confidence_threshold:
                        valid_tags = [tag for tag in suggested_tags if tag in self.all_approved_tags]
                        self.logger.info(f"AI suggested {len(suggested_tags)} tags (confidence: {confidence:.2f}), {len(valid_tags)} valid: {valid_tags}")
                        if reasoning:
                            self.logger.debug(f"AI reasoning: {reasoning}")
                        ai_metadata['model_used'] = self.ollama_model
                        return valid_tags, ai_metadata
                    else:
                        # Low confidence - try cascade to secondary/tertiary models
                        self.logger.info(f"Primary AI confidence too low ({confidence:.2f}), attempting cascade...")
                        ai_metadata['primary_confidence'] = confidence
                        ai_metadata['primary_tags'] = suggested_tags
                        
                        cascade_result = self._try_cascade_models(prompt, ai_metadata)
                        if cascade_result:
                            return cascade_result
                        
                        # All cascade attempts failed - return primary result anyway if it had some tags
                        valid_tags = [tag for tag in suggested_tags if tag in self.all_approved_tags]
                        if valid_tags:
                            self.logger.info(f"Cascade failed, using low-confidence primary result: {valid_tags}")
                            ai_metadata['model_used'] = self.ollama_model
                            ai_metadata['needs_manual_review'] = True
                            return valid_tags, ai_metadata
                        return [], ai_metadata
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse AI JSON response: {response_text[:200]}...")
                    return [], ai_metadata
            else:
                self.logger.warning(f"No JSON found in AI response: {response_text[:200]}...")
                return [], ai_metadata
            
        except Exception as e:
            self.logger.error(f"AI tagging error: {e}")
            return [], ai_metadata
    
    def _try_cascade_models(self, prompt, ai_metadata):
        """Try secondary and tertiary models for better confidence.
        Returns (valid_tags, ai_metadata) if successful, None if all fail."""
        
        if not self.enable_ai_cascade:
            return None
        
        models_to_try = []
        if self.secondary_ollama_model and self._is_ollama_model_available(self.secondary_ollama_model):
            models_to_try.append(('secondary', self.secondary_ollama_model))
        if self.tertiary_ollama_model and self._is_ollama_model_available(self.tertiary_ollama_model):
            models_to_try.append(('tertiary', self.tertiary_ollama_model))
        
        for model_name, model_id in models_to_try:
            try:
                self.logger.info(f"Trying {model_name} model: {model_id}")
                response_text = self._call_ollama_model_direct(model_id, prompt)
                
                if not response_text:
                    continue
                
                # Parse response
                cleaned = re.sub(r'```json\s*', '', response_text)
                cleaned = re.sub(r'```\s*$', '', cleaned).strip()
                
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\{[^\}]*\}', cleaned, re.DOTALL)
                
                if json_match:
                    ai_response = json.loads(json_match.group())
                    suggested_tags = ai_response.get('tags', [])
                    confidence = ai_response.get('confidence', 0.5)
                    reasoning = ai_response.get('reasoning', '')
                    
                    if confidence >= self.ai_confidence_threshold:
                        valid_tags = [tag for tag in suggested_tags if tag in self.all_approved_tags]
                        self.logger.info(f"{model_name.capitalize()} model succeeded: {len(valid_tags)} tags, confidence {confidence:.2f}")
                        ai_metadata['confidence'] = confidence
                        ai_metadata['reasoning'] = reasoning
                        ai_metadata['model_used'] = model_id
                        ai_metadata['cascade_level'] = model_name
                        return valid_tags, ai_metadata
                    else:
                        self.logger.info(f"{model_name.capitalize()} model confidence too low: {confidence:.2f}")
                        ai_metadata[f'{model_name}_confidence'] = confidence
                        
            except Exception as e:
                self.logger.warning(f"{model_name.capitalize()} model failed: {e}")
        
        return None
    
    def _call_ollama_model_direct(self, model_id, prompt):
        """Call a specific Ollama model directly (for cascade)."""
        url = f"{self.ollama_host}/api/chat"
        session = self._get_http_session()
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json"
        }
        
        try:
            response = session.post(url, json=payload, timeout=self.ollama_timeout)
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', '').strip()
        except Exception as e:
            self.logger.warning(f"Ollama direct call to {model_id} failed: {e}")
            return None
    
    def _normalize_tag(self, tag: str) -> str:
        """Normalize AI-suggested tag to standard format
        
        Args:
            tag: Tag string from AI (e.g. 'Pen Style', '20 mg', 'Ice')
        
        Returns:
            str: Normalized tag (e.g. 'pen_style', '20mg', 'ice')
        """
        if not tag:
            return ""
        
        # Convert to lowercase
        normalized = tag.lower().strip()
        
        # Remove spaces around mg/ml units FIRST (before replacing spaces with underscores)
        normalized = re.sub(r'(\d+(?:\.\d+)?)\s*(mg|ml|ohm)', r'\1\2', normalized)
        
        # Remove extra spaces and replace with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Store in normalized_map if not already present
        if not hasattr(self, 'normalized_map'):
            self.normalized_map = {}
        self.normalized_map[normalized] = normalized
        
        return normalized
    
    def _filter_and_map_ai_tags(self, suggested_tags, forced_category=None, device_evidence=False):
        """Filter and map AI-suggested tags to approved vocabulary
        
        Args:
            suggested_tags: List of AI-suggested tags
            forced_category: Forced category from rule-based detection
            device_evidence: Whether there's explicit device evidence in text
        
        Returns:
            list: Filtered and mapped tags
        """
        mapped_tags = []
        
        for tag in suggested_tags:
            # Normalize the tag
            normalized = self._normalize_tag(tag)
            
            # Check if normalized tag is in approved tags OR is a valid range-based tag
            is_valid = normalized in self.all_approved_tags
            
            # For range-based tags (nicotine_strength, cbd_strength, capacity, bottle_size)
            # validate against their ranges
            if not is_valid:
                # Check mg tags - could be nicotine (0-20mg) OR CBD (0-50000mg)
                if re.match(r'^\d+(\.\d+)?mg$', normalized):
                    try:
                        value = float(normalized[:-2])  # Remove 'mg'
                        
                        # Try nicotine strength first (0-20mg)
                        nicotine_config = self.approved_tags.get('nicotine_strength', {})
                        range_config = nicotine_config.get('range', {})
                        if range_config:
                            min_val = range_config.get('min', 0)
                            max_val = range_config.get('max', 20)
                            if min_val <= value <= max_val:
                                is_valid = True
                        
                        # If not valid for nicotine, try CBD strength (0-50000mg)
                        if not is_valid:
                            cbd_config = self.approved_tags.get('cbd_strength', {})
                            range_config = cbd_config.get('range', {})
                            if range_config:
                                min_val = range_config.get('min', 0)
                                max_val = range_config.get('max', 50000)
                                if min_val <= value <= max_val:
                                    is_valid = True
                    except ValueError:
                        pass
                
                # Check capacity (ml)
                if not is_valid and re.match(r'^\d+(\.\d+)?ml$', normalized):
                    try:
                        value = float(normalized[:-2])
                        capacity_config = self.approved_tags.get('capacity', {})
                        range_config = capacity_config.get('range', {})
                        if range_config:
                            min_val = range_config.get('min', 0)
                            max_val = range_config.get('max', 10)
                            if min_val <= value <= max_val:
                                is_valid = True
                    except ValueError:
                        pass
                
                # Check bottle_size (ml)
                if not is_valid and re.match(r'^\d+(\.\d+)?ml$', normalized):
                    try:
                        value = float(normalized[:-2])
                        bottle_config = self.approved_tags.get('bottle_size', {})
                        range_config = bottle_config.get('range', {})
                        if range_config:
                            min_val = range_config.get('min', 0)
                            max_val = range_config.get('max', 120)
                            if min_val <= value <= max_val:
                                is_valid = True
                    except ValueError:
                        pass
            
            if is_valid:
                # Filter device-related tags for CBD products unless there's evidence
                if forced_category == 'CBD' and not device_evidence:
                    # Device style/form tags should not be applied to CBD products
                    device_tags = ['pen_style', 'pod_style', 'box_style', 'stick_style', 'device', 
                                  'disposable', 'pod_system', 'box_mod']
                    if normalized in device_tags:
                        continue
                
                mapped_tags.append(normalized)
        
        return mapped_tags
    
    def get_rule_based_tags(self, handle, title, description="", product_type=None):
        """Extract obvious tags using rules
        
        Args:
            handle: Product handle/slug
            title: Product title
            description: Product description
            product_type: Optional Type column hint (e.g. 'CBD', 'Vaping Products')
        
        Returns:
            tuple: (rule_tags, forced_category)
        """
        
        text = f"{handle} {title} {description}".lower()
        handle_title = f"{handle} {title}".lower()
        rule_tags = []
        
        # Use product_type hint if provided
        if product_type:
            product_type_lower = product_type.lower()
            # If Type column says 'CBD', force CBD category
            if 'cbd' in product_type_lower:
                if 'CBD' not in rule_tags:
                    rule_tags.append('CBD')
                # Early detection of CBD allows strength extraction later
            # If Type says Vaping/Smoking, allow device style detection even without 'style' keyword
        
        # Prioritize handle/title for category determination
        # USB/Charging cable detection - check first (before generic 'charger')
        if any(pattern in handle_title for pattern in ['usb cable', 'charging cable', 'data cable', 'usb-c cable', 'micro usb', 'type-c cable']):
            rule_tags.append('charging_cable')
            forced_category = 'accessory'
        elif 'cable' in handle_title and any(word in handle_title for word in ['usb', 'charge', 'charging', 'data', 'phone', 'iphone', 'android', 'type-c', 'micro']):
            rule_tags.append('charging_cable')
            forced_category = 'accessory'
        elif 'charger' in handle_title:
            rule_tags.append('charger')
            forced_category = 'accessory'
        elif 'battery' in handle_title:
            rule_tags.append('battery')
            forced_category = 'accessory'
        # Atomizer detection
        elif 'atomizer' in handle_title or 'atomiser' in handle_title:
            if '510' in handle_title:
                rule_tags.append('510_atomizer')
            else:
                rule_tags.append('atomizer')
            forced_category = 'accessory'
        # NEW: Terpene detection
        elif 'terpene' in handle_title or 'terpenes' in handle_title:
            rule_tags.append('terpene')
            forced_category = 'terpene'
            # Detect terpene type
            if 'indica' in handle_title:
                rule_tags.append('indica')
            elif 'sativa' in handle_title:
                rule_tags.append('sativa')
            elif 'balanced' in handle_title or 'hybrid' in handle_title:
                rule_tags.append('balanced')
            else:
                rule_tags.append('strain_specific')
        # NEW: Extraction equipment detection
        elif any(term in handle_title for term in ['rosin press', 'rosin-press', 'pollen press', 'extractor', 'concentrate extractor', 'hex press', 'hex-press']):
            rule_tags.append('extraction_equipment')
            forced_category = 'extraction_equipment'
            if 'rosin' in handle_title or 'pollen' in handle_title:
                rule_tags.append('rosin_press')
            elif 'extractor' in handle_title:
                rule_tags.append('extractor')
        # NEW: Non-CBD Supplement detection (vitamins, nootropics, etc.)
        elif any(term in handle_title for term in ['vitamin', 'mineral', 'nootropic', 'mushroom', 'probiotic']) and 'cbd' not in handle_title and 'cbg' not in handle_title:
            rule_tags.append('supplement')
            forced_category = 'supplement'
            if 'vitamin' in handle_title:
                rule_tags.append('vitamin')
            elif 'nootropic' in handle_title or 'neuro' in handle_title:
                rule_tags.append('nootropic')
            elif 'mushroom' in handle_title or 'agaricus' in handle_title or 'lions mane' in handle_title or 'reishi' in handle_title:
                rule_tags.append('mushroom')
            elif 'probiotic' in handle_title:
                rule_tags.append('probiotic')
        # NEW: Vape cleaning/accessory detection
        elif any(term in handle_title for term in ['cleaning swab', 'cleaning wipe', 'cleaning kit', 'vape clean', 'pipe cleaner']):
            rule_tags.append('accessory')
            rule_tags.append('tool_kit')
            forced_category = 'accessory'
        # NEW: Empty bottle detection
        elif 'empty' in handle_title and 'bottle' in handle_title:
            rule_tags.append('accessory')
            forced_category = 'accessory'
        # NEW: 510 thread vape pen detection
        elif '510' in handle_title and any(term in handle_title for term in ['pen', 'battery', 'thread', 'vape']):
            rule_tags.append('device')
            rule_tags.append('pen_style')
            forced_category = 'device'
        elif 'coil' in handle_title:
            rule_tags.append('coil')
            forced_category = 'coil'
        elif 'tank' in handle_title:
            rule_tags.append('tank')
            forced_category = 'tank'
        elif 'cbd' in handle_title or 'cbg' in handle_title or ('hemp' in handle_title and ('oil' in handle_title or 'seed' in handle_title or 'extract' in handle_title)):
            rule_tags.append('CBD')
            forced_category = 'CBD'
        elif 'e-liquid' in handle_title or 'liquid' in handle_title or ('nic' in handle_title and 'salt' in handle_title) or 'salt' in handle_title:
            # Note: removed 'mg' as standalone indicator - too ambiguous (CBD products have mg too)
            rule_tags.append('e-liquid')
            forced_category = 'e-liquid'
        # Check case BEFORE pod to avoid "airpod case" matching as pod
        elif 'case' in handle_title:
            rule_tags.append('case')
            forced_category = 'accessory'
        # Pod detection - use word boundary to avoid "airpod" matching
        elif re.search(r'\bpod\b', handle_title):
            # "pod kit" or "pod system" should be pod_system
            if 'kit' in handle_title or 'system' in handle_title:
                rule_tags.append('pod_system')
                forced_category = 'pod_system'
            else:
                rule_tags.append('pod')
                forced_category = 'pod'
        elif 'disposable' in handle_title or 'puff' in handle_title or 'puffs' in handle_title:
            rule_tags.append('disposable')
            forced_category = 'disposable'
        # Common disposable brand patterns
        elif any(brand in handle_title for brand in ['elf bar', 'elfbar', 'crystal bar', 'lost mary', 
                                                       'ske crystal', 'geek bar', 'geekbar', 'hayati',
                                                       'elux', 'ivg bar', 'oxbar', 'waka']):
            rule_tags.append('disposable')
            forced_category = 'disposable'
        elif 'pouch' in handle_title:
            rule_tags.append('pouch')
            forced_category = 'accessory'
        elif 'mouthpiece' in handle_title:
            rule_tags.append('mouthpiece')
            forced_category = 'accessory'
        else:
            forced_category = None
        
        # If no category from handle/title, fall back to full text
        if not any(tag in self.category_tags for tag in rule_tags):
            if 'charger' in text and 'charger' not in rule_tags:
                rule_tags.append('charger')
            elif 'battery' in text and 'battery' not in rule_tags:
                rule_tags.append('battery')
            elif 'glass' in text and 'replacement' in text:
                rule_tags.append('replacement_glass')
            # Add more as needed
        
        # Nicotine strength detection (range-based)
        # First check for explicit zero nicotine indicators (use word boundaries for accuracy)
        zero_nic_detected = False
        if any(phrase in text for phrase in ['zero nicotine', 'zero nic', 'nicotine free', 'nicotine-free', 'nic free', 'nic-free']):
            if 'cbd' not in text and 'cbg' not in text:  # Skip for CBD products
                rule_tags.append('0mg')
                zero_nic_detected = True
        # Check for explicit 0mg with word boundary (not part of 20mg, 5000, etc.)
        elif re.search(r'\b0\s*mg\b', text, re.IGNORECASE):
            if 'cbd' not in text and 'cbg' not in text:
                rule_tags.append('0mg')
                zero_nic_detected = True
        
        # Then check for numeric mg values (only if not already detected as zero)
        if not zero_nic_detected:
            mg_matches = re.findall(r'(\d+(?:\.\d+)?)mg', text)
            if mg_matches:
                # Skip if CBD/CBG
                if 'cbd' in text or 'cbg' in text:
                    pass
                else:
                    nicotine_config = self.approved_tags.get('nicotine_strength', {})
                    range_config = nicotine_config.get('range')
                    if range_config:
                        min_val = range_config.get('min', 0)
                        max_val = range_config.get('max', 20)
                        unit = range_config.get('unit', 'mg')
                        for mg in mg_matches:
                            try:
                                mg_value = float(mg)
                                if min_val <= mg_value <= max_val:
                                    rule_tags.append(f"{mg}{unit}")
                                    break
                            except ValueError:
                                continue
                    else:
                        # Fallback to tag-based validation (legacy)
                        strengths = [f"{m}mg" for m in mg_matches if f"{m}mg" in self.approved_tags.get('nicotine_strength', {}).get('tags', [])]
                        if strengths:
                            rule_tags.append(strengths[0])  # Take first valid strength
        
        # Nicotine type detection
        if 'nic' in text and 'salt' in text:
            rule_tags.append('nic_salt')
        
        # Detect if this is a nic shot (for shortfill exclusion logic later)
        # Check handle/title primarily - avoid false positives from "add nic shots" in description
        is_nic_shot = ('nic' in handle_title and 'shot' in handle_title) or 'nicshot' in handle_title or 'nic-shot' in handle_title
        
        # CBD strength detection - include hemp products (hemp oil = CBD product)
        is_cbd_product = 'cbd' in text or 'cbg' in text or ('hemp' in text and ('oil' in text or 'seed' in text or 'extract' in text))
        if is_cbd_product:
            # CBD form detection - ordered by specificity, NO default fallback
            # Check handle/title FIRST (more reliable), then fall back to description
            # This prevents description text like "can be rubbed on skin" from overriding "oil" in title
            cbd_form_detected = False
            
            # Priority 1: Check handle/title only first
            if any(word in handle_title for word in ['capsule', 'cap', 'softgel', 'soft gel', 'soft-gel', 'gel cap', 'gelcap']):
                rule_tags.append('capsule')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['gummy', 'gummies', 'bear', 'candy', 'chew', 'jelly', 'sweets']):
                rule_tags.append('gummy')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['topical', 'cream', 'balm', 'salve', 'lotion', 'roll-on', 'roller']):
                rule_tags.append('topical')
                cbd_form_detected = True
            # Check for oil in handle/title specifically (common CBD form)
            # Oil should come BEFORE tincture check since "oil" is more specific
            elif 'oil' in handle_title:
                rule_tags.append('oil')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['tincture', 'drop', 'drops', 'sublingual', 'extract']):
                rule_tags.append('tincture')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['crumble']):
                rule_tags.append('crumble')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['shatter']):
                rule_tags.append('shatter')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['wax', 'dab']):
                rule_tags.append('wax')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['paste', 'concentrate', 'raw paste']):
                rule_tags.append('paste')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['shot', 'beverage', 'drink', 'sparkling', 'energy drink', 'soda', 'tea', 'coffee', 'infusion']):
                rule_tags.append('beverage')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['edible', 'cookie', 'brownie', 'chocolate', 'bar', 'snack']):
                rule_tags.append('edible')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['patch', 'transdermal', 'skin patch']):
                rule_tags.append('patch')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['vape', 'cartridge', 'cart', 'disposable', 'e-liquid', 'eliquid']):
                rule_tags.append('vape')
                cbd_form_detected = True
            elif any(word in handle_title for word in ['flower', 'bud', 'hemp flower', 'pre-roll', 'preroll']):
                rule_tags.append('flower')
                cbd_form_detected = True
            
            # Priority 2: If no form found in handle/title, check full text (including description)
            # But be more careful with short words that can cause false positives
            if not cbd_form_detected:
                # Use word-boundary matching for short words to avoid false positives
                # e.g., "rubbed" shouldn't match "rub" when it's incidental description text
                if any(word in text for word in ['topical', 'cream', 'balm', 'salve', 'lotion', 'roll-on', 'roller']):
                    rule_tags.append('topical')
                    cbd_form_detected = True
                elif any(word in text for word in ['tincture', 'drops', 'sublingual']):
                    rule_tags.append('tincture')
                    cbd_form_detected = True
                elif any(word in text for word in ['capsule', 'softgel', 'gelcap']):
                    rule_tags.append('capsule')
                    cbd_form_detected = True
                elif any(word in text for word in ['beverage', 'drink', 'sparkling', 'soda', 'tea', 'coffee']):
                    rule_tags.append('beverage')
                    cbd_form_detected = True
                # Final fallback: if still no form and 'oil' appears, assume tincture
                elif 'oil' in text:
                    rule_tags.append('tincture')
                    cbd_form_detected = True
            
            # CBD spectrum type detection - NO default fallback
            if 'full spectrum' in text or 'full-spectrum' in text or 'fullspectrum' in text:
                rule_tags.append('full_spectrum')
            elif 'broad spectrum' in text or 'broad-spectrum' in text or 'broadspectrum' in text:
                rule_tags.append('broad_spectrum')
            elif 'isolate' in text or 'pure cbd' in text:
                rule_tags.append('isolate')
            elif 'cbg' in text and 'cbd' not in text:
                rule_tags.append('cbg')
            elif 'cbda' in text:
                rule_tags.append('cbda')
            # NO default to full_spectrum - let AI determine if ambiguous
            
            mg_matches = re.findall(r'(\d+)mg', text)
            if mg_matches:
                cbd_strength_config = self.approved_tags.get('cbd_strength', {})
                range_config = cbd_strength_config.get('range')
                
                if range_config:
                    # Use range-based validation
                    min_val = range_config.get('min', 0)
                    max_val = range_config.get('max', 50000)
                    unit = range_config.get('unit', 'mg')
                    
                    for mg in mg_matches:
                        try:
                            mg_value = int(mg)
                            if min_val <= mg_value <= max_val:
                                rule_tags.append(f"{mg}{unit}")
                                break
                        except ValueError:
                            continue
                else:
                    # Fallback to tag-based validation (legacy)
                    for mg in mg_matches:
                        cbd_tag = f"{mg}mg"
                        if cbd_tag in cbd_strength_config.get('tags', []):
                            rule_tags.append(cbd_tag)
                            break
            
            # Check for unlimited
            if 'unlimited' in text.lower():
                if 'unlimited mg' in self.approved_tags.get('cbd_strength', {}).get('tags', []):
                    rule_tags.append('unlimited mg')
        
        # Bottle size detection - check for various formats
        bottle_size_match = re.search(r'(\d+)\s*ml\b', text, re.IGNORECASE)
        if bottle_size_match:
            detected_size = bottle_size_match.group(1)
            size_tag = f"{detected_size}ml"
            # Only add if it's a standard bottle size in approved tags or common sizes
            standard_sizes = ['2ml', '5ml', '10ml', '20ml', '30ml', '50ml', '100ml', '120ml']
            if size_tag in standard_sizes:
                rule_tags.append(size_tag)
        
        # VG/PG ratio detection - advanced patterns
        ratio_matches = re.findall(r'(\d+)\s*vg\s*[/-]\s*(\d+)\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try alternative format like "50/50 VG/PG"
            ratio_matches = re.findall(r'(\d+)[/-](\d+)\s*vg[/-]pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG/PG 50/50" format
            ratio_matches = re.findall(r'vg[/-]pg\s*(\d+)[/-](\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "50% VG / 50% PG" format
            ratio_matches = re.findall(r'(\d+)%?\s*vg\s*[/-]\s*(\d+)%?\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG:PG 50:50" format
            ratio_matches = re.findall(r'vg\s*:\s*pg\s*(\d+)\s*:\s*(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "50VG 50PG" format (no separator)
            ratio_matches = re.findall(r'(\d+)\s*vg\s+(\d+)\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try percentage format "50% VG 50% PG"
            percent_matches = re.findall(r'(\d+)%\s*vg.*?(\d+)%\s*pg', text, re.IGNORECASE)
            if percent_matches:
                ratio_matches = percent_matches
        if not ratio_matches:
            # Try "70VG30PG" format (no spaces)
            ratio_matches = re.findall(r'(\d+)vg(\d+)pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG 70 / PG 30" format
            ratio_matches = re.findall(r'vg\s+(\d+)[/-]\s*pg\s+(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70/30 VG PG" format
            ratio_matches = re.findall(r'(\d+)[/-](\d+)\s*vg\s*pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70VG/30PG" format
            ratio_matches = re.findall(r'(\d+)vg[/-](\d+)pg', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "VG70PG30" format (compact)
            ratio_matches = re.findall(r'vg(\d+)pg(\d+)', text, re.IGNORECASE)
        if not ratio_matches:
            # Try "70-30" with VG/PG context
            if 'vg' in text and 'pg' in text:
                dash_matches = re.findall(r'(\d+)[/-](\d+)', text)
                if dash_matches:
                    ratio_matches = dash_matches
        
        if ratio_matches:
            for vg, pg in ratio_matches:
                # Handle cases where VG/PG might be swapped
                try:
                    vg_val = int(vg)
                    pg_val = int(pg)
                    # Ensure VG >= PG (typical ratios)
                    if pg_val > vg_val:
                        vg, pg = pg, vg
                    ratio = f"{vg}/{pg}"
                    if ratio in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                        rule_tags.append(ratio)
                        break  # Take first valid ratio
                except ValueError:
                    continue
        
        # Pure VG detection
        if not ratio_matches and ('100% vg' in text.lower() or 'pure vg' in text.lower() or 'max vg' in text.lower()):
            rule_tags.append('100/0')
        elif not ratio_matches and 'vg' in text and 'pg' not in text:
            rule_tags.append('100/0')
        
        # Shortfill detection - EITHER explicit "shortfill" mention OR large (50ml+) zero-nicotine liquid
        # Shortfills are larger bottles (60ml, 120ml) filled with 50ml/100ml to allow room for nic shots
        # EXCLUDE nic shots even if they mention "shortfill" (they're added TO shortfills, not shortfills themselves)
        bottle_sizes = re.findall(r'(\d+)\s*ml', text, re.IGNORECASE)
        is_shortfill_size = any(int(size) >= 50 for size in bottle_sizes if size.isdigit())
        has_small_bottle = any(int(size) <= 20 for size in bottle_sizes if size.isdigit())
        
        # Case 1: Explicit "shortfill" mention
        if 'shortfill' in text and not is_nic_shot:
            if is_shortfill_size or (not bottle_sizes and not has_small_bottle):
                rule_tags.append('shortfill')
        # Case 2: Large bottle (50ml+) with zero nicotine (implicit shortfill)
        elif is_shortfill_size and zero_nic_detected and not is_nic_shot:
            rule_tags.append('shortfill')
        
        # Basic product type (skip if already have a category from handle/title)
        if forced_category is None:
            if any(word in text for word in ['disposable', 'puff']):
                rule_tags.append('disposable')
            elif any(word in text for word in ['e-liquid', 'liquid', 'juice']) or ('nic' in text and 'salt' in text):
                rule_tags.append('e-liquid')
            elif any(word in text for word in ['kit', 'device', 'mod']):
                rule_tags.append('device')
        
        # Specific type detection - only add if not already have a category
        # Don't add 'coil' just because description mentions it
        has_category = forced_category is not None or any(t in self.category_tags for t in rule_tags)
        if 'coil' in text and not has_category:
            rule_tags.append('coil')
        # Tank detection - but not for coils (which are "for tank" but aren't tanks)
        if ('tank' in text or ('replacement' in text and 'glass' in text)) and forced_category not in ('coil', 'tank') and 'tank' not in rule_tags:
            rule_tags.append('tank')
        # Pod subtype detection - even if already categorized as pod
        if re.search(r'\bpod\b', text) and forced_category != 'accessory':
            if 'prefilled' in text or 'pre-filled' in text or 'pre_filled' in text:
                rule_tags.append('prefilled_pod')
            elif 'refillable' in text or 'replacement' in text:
                rule_tags.append('replacement_pod')
            # Only add 'pod' category tag if not already present
            if forced_category not in ('pod', 'pod_system') and 'pod' not in rule_tags and 'pod_system' not in rule_tags:
                rule_tags.append('pod')
            # Pod capacity detection
            capacity_matches = re.findall(r'(\d+(?:\.\d+)?)\s*ml', text, re.IGNORECASE)
            if capacity_matches:
                capacity_config = self.approved_tags.get('capacity', {})
                for cap in capacity_matches:
                    cap_tag = f"{cap}ml"
                    if cap_tag in capacity_config.get('tags', []):
                        rule_tags.append(cap_tag)
                        break
        if 'box' in text and 'mod' in text:
            rule_tags.append('box_mod')
        
        # Battery detection
        if any(word in text for word in ['battery', 'batteries']):
            rule_tags.append('accessory')
            rule_tags.append('battery')
        
        # Charger detection
        if 'charger' in text:
            rule_tags.append('accessory')
            rule_tags.append('charger')
        
        # Device style detection
        # For vaping products, allow device form detection even without 'style' keyword
        is_vaping_product = (product_type and 'vaping' in product_type.lower()) or \
                           forced_category in ('device', 'disposable', 'pod_system', 'box_mod', 'pod')
        
        # CBD products should NOT get device style tags unless explicit evidence
        is_cbd_product_type = (product_type and 'cbd' in product_type.lower()) or \
                             'CBD' in rule_tags or forced_category == 'CBD'
        
        if not is_cbd_product_type or is_vaping_product:
            if 'pen' in text and ('style' in text or is_vaping_product):
                rule_tags.append('pen_style')
            elif 'pod' in text and ('style' in text or is_vaping_product):
                rule_tags.append('pod_style')
            elif 'box' in text and ('style' in text or is_vaping_product):
                rule_tags.append('box_style')
            elif 'stick' in text:
                rule_tags.append('stick_style')
            elif 'compact' in text:
                rule_tags.append('compact')
            elif 'mini' in text:
                rule_tags.append('mini')
        
        # Coil ohm detection
        ohm_matches = re.findall(r'(\d+)[-\.]?(\d*)\s*[ωo]h?m?', text)
        if ohm_matches:
            for match in ohm_matches:
                ohm = f"{match[0]}.{match[1]}" if match[1] else match[0]
                ohm_tag = f"{ohm}ohm"
                if ohm_tag in self.approved_tags.get('coil_ohm', {}).get('tags', []):
                    rule_tags.append(ohm_tag)
                    break
        
        # Flavour type detection - check ALL applicable flavors (not elif chain)
        # A product like "Strawberry Ice" should get BOTH fruity AND ice tags
        if any(word in text for word in ['e-liquid', 'liquid', 'juice', 'pod', 'disposable', 'pouch', 'mg']):
            # Fruity detection - primary keywords AND specific fruit names
            fruity_keywords = [
                'fruit', 'fruity', 'berry', 'citrus',
                # Specific fruits
                'strawberry', 'raspberry', 'blueberry', 'blackberry', 'cranberry',
                'apple', 'pear', 'orange', 'lemon', 'lime', 'grapefruit', 'tangerine',
                'mango', 'pineapple', 'coconut', 'papaya', 'guava', 'passion fruit', 'lychee',
                'peach', 'plum', 'apricot', 'nectarine', 'cherry',
                'grape', 'watermelon', 'melon', 'kiwi', 'banana'
            ]
            if any(word in text for word in fruity_keywords):
                rule_tags.append('fruity')
            
            # Ice/menthol detection - use word boundary to avoid matching 'ice' in 'device'
            # Also exclude 'ice cream' which is a dessert, not a cooling flavor
            ice_keywords = ['iced', 'icy', 'cool', 'cooling', 'menthol', 'mint', 
                           'freeze', 'frozen', 'arctic', 'peppermint', 'spearmint', 'wintergreen']
            # 'ice' needs special handling - must be standalone word, not part of 'device' or 'ice cream'
            has_ice = re.search(r'\bice\b', text) is not None and 'ice cream' not in text
            if has_ice or any(word in text for word in ice_keywords):
                rule_tags.append('ice')
            
            # Tobacco detection
            if 'tobacco' in text:
                rule_tags.append('tobacco')
            
            # Desserts/bakery detection
            dessert_keywords = ['dessert', 'bakery', 'cake', 'cookie', 'custard', 'cream',
                               'donut', 'waffle', 'pastry', 'pudding', 'ice cream']
            if any(word in text for word in dessert_keywords):
                rule_tags.append('desserts/bakery')
            
            # Beverages detection
            beverage_keywords = ['beverage', 'drink', 'cola', 'coffee', 'tea', 'soda', 
                                'lemonade', 'energy drink', 'cocktail', 'mojito']
            if any(word in text for word in beverage_keywords):
                rule_tags.append('beverages')
            
            # Candy/sweets detection
            candy_keywords = ['candy', 'sweets', 'gummy', 'gummies', 'sour', 'bubblegum',
                             'bubble gum', 'cotton candy', 'lollipop', 'blue razz', 'razz',
                             'skittles', 'starburst', 'sherbet', 'rainbow', 'toffee', 'caramel']
            if any(word in text for word in candy_keywords):
                rule_tags.append('candy/sweets')
            
            # Nuts detection
            nut_keywords = ['nut', 'nuts', 'nutty', 'almond', 'hazelnut', 'peanut', 'walnut', 'pistachio']
            if any(word in text for word in nut_keywords):
                rule_tags.append('nuts')
            
            # Spices & herbs detection
            spice_keywords = ['spice', 'spices', 'herb', 'herbs', 'cinnamon', 'vanilla', 
                             'anise', 'licorice', 'ginger', 'clove']
            if any(word in text for word in spice_keywords):
                rule_tags.append('spices_&_herbs')
            
            # Cereal detection
            if 'cereal' in text:
                rule_tags.append('cereal')
            
            # Unflavoured detection
            if 'unflavoured' in text or 'unflavored' in text or 'plain' in text:
                rule_tags.append('unflavoured')
        
        # Validate rule tags and deduplicate (preserve order)
        seen = set()
        valid_tags = []
        for tag in rule_tags:
            if tag in seen:
                continue
            # Accept approved tags from flat list
            if tag in self.all_approved_tags:
                valid_tags.append(tag)
                seen.add(tag)
            # Accept nicotine strength (range-based, not in flat list)
            elif re.match(r'^\d+(?:\.\d+)?mg$', tag):
                # Validate against nicotine or CBD range
                range_config = self.approved_tags.get('nicotine_strength', {}).get('range')
                if range_config and forced_category != 'CBD':
                    try:
                        mg_value = float(tag.replace('mg', ''))
                        if range_config['min'] <= mg_value <= range_config['max']:
                            valid_tags.append(tag)
                            seen.add(tag)
                    except ValueError:
                        pass
                elif forced_category == 'CBD':
                    # CBD has its own range - already validated when added
                    valid_tags.append(tag)
                    seen.add(tag)
        return valid_tags, forced_category
    
    def _process_single_product(self, product, index, total):
        """Process a single product and return result dict. Thread-safe."""
        handle = product.get('Handle', '')
        
        product_dict = {
            'handle': handle,
            'title': product.get('Title', ''),
            'description': product.get('Body (HTML)', ''),
            'option1_name': product.get('Option1 Name', ''),
            'option1_value': product.get('Option1 Value', ''),
            'option2_name': product.get('Option2 Name', ''),
            'option2_value': product.get('Option2 Value', ''),
            'option3_name': product.get('Option3 Name', ''),
            'option3_value': product.get('Option3 Value', ''),
        }
        
        # Get rule-based tags first to determine category
        rule_tags, forced_category = self.get_rule_based_tags(
            product_dict['handle'], product_dict['title'], product_dict['description']
        )
        
        # Determine preliminary product category for AI prompting
        preliminary_category = None
        max_priority = -1
        for tag in rule_tags:
            if tag in self.category_tags:
                priority = self.category_priority.get(tag, 0)
                if priority > max_priority:
                    max_priority = priority
                    preliminary_category = tag
        
        # Override with forced category from handle
        if forced_category:
            preliminary_category = forced_category
        
        # AI-FIRST WORKFLOW: Always call AI unless explicitly disabled
        # AI provides semantic understanding, rules supplement with precise extraction
        ai_tags = []
        ai_metadata = {
            'prompt': None,
            'model_output': None,
            'confidence': None,
            'reasoning': None,
            'skipped_ai': False
        }
        
        if self.no_ai:
            # AI explicitly disabled - use rule-based only
            ai_metadata['skipped_ai'] = True
            ai_metadata['confidence'] = 0.0
            ai_metadata['reasoning'] = "AI tagging disabled via --no-ai flag"
            # Track skip count (thread-safe)
            if self._lock:
                with self._lock:
                    self._ai_skipped_count += 1
            else:
                self._ai_skipped_count += 1
        else:
            # AI-FIRST: Get AI suggestions with category-aware prompting
            # AI provides semantic tagging, rules will supplement with precise values
            ai_tags, ai_metadata = self.get_ai_tags(product_dict, category=preliminary_category)
        
        # Combine and deduplicate
        all_tags = list(set(ai_tags + rule_tags))
        
        # Determine product category with priority
        product_category = None
        max_priority = -1
        for tag in all_tags:
            if tag in self.category_tags:
                priority = self.category_priority.get(tag, 0)
                if priority > max_priority:
                    max_priority = priority
                    product_category = tag
        
        # Override with forced category from handle
        if forced_category:
            product_category = forced_category
        
        # Infer vaping style from VG/PG ratio for e-liquids
        inferred_tags = []
        if product_category == 'e-liquid':
            for tag in all_tags:
                if '/' in tag and tag in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                    try:
                        vg, pg = map(int, tag.split('/'))
                        if pg >= 50:
                            inferred_tags.append('mouth-to-lung')
                        elif 60 <= vg <= 70:
                            inferred_tags.append('restricted-direct-to-lung')
                        elif vg >= 70:
                            inferred_tags.append('direct-to-lung')
                    except ValueError:
                        pass
        all_tags.extend(inferred_tags)
        all_tags = list(set(all_tags))
        
        # Filter tags based on applies_to and enforce category limits
        tag_by_cat = defaultdict(list)
        for tag in all_tags:
            cat = self.tag_to_category.get(tag)
            
            # Special handling for range-based categories
            if not cat:
                if re.match(r'^\d+mg$', tag):
                    cbd_config = self.approved_tags.get('cbd_strength', {})
                    if cbd_config.get('range') and product_category == 'CBD':
                        cat = 'cbd_strength'
            
            # Skip category tags from all_tags - category will be added separately
            if cat == 'category':
                continue
            
            cat_data = self.approved_tags.get(cat, {})
            applies_to = cat_data.get('applies_to', ['all']) if isinstance(cat_data, dict) else ['all']
            if 'all' in applies_to or product_category in applies_to:
                tag_by_cat[cat].append(tag)
        
        # Sort tags within each category
        for cat in tag_by_cat:
            if cat == 'accessory_type':
                tag_by_cat[cat].sort(key=lambda t: (0 if t == 'charger' else 1 if t == 'battery' else 2, -len(t)))
            else:
                tag_by_cat[cat].sort(key=len, reverse=True)
        
        # Build final tags list: [category, ...other tags]
        final_tags = []
        
        # Add category first (required)
        if product_category:
            final_tags.append(product_category)
        
        # Add one tag per category (limit enforced)
        for cat, tags in tag_by_cat.items():
            final_tags.extend(tags[:1])  # Keep at most one per category
        
        now = time.time()
        if self._lock:
            with self._lock:
                self._processed_count += 1
                count = self._processed_count
                self._progress_history.append((now, count))
                while self._progress_history and (now - self._progress_history[0][0]) > self.progress_rate_window:
                    self._progress_history.popleft()
                window_start_time, window_start_count = self._progress_history[0]
        else:
            self._processed_count += 1
            count = self._processed_count
            self._progress_history.append((now, count))
            while self._progress_history and (now - self._progress_history[0][0]) > self.progress_rate_window:
                self._progress_history.popleft()
            window_start_time, window_start_count = self._progress_history[0]

        with self._metrics_lock:
            ai_inflight = self._ai_inflight
        
        if count % 10 == 0 or count == total:
            overall_elapsed = max(now - self._start_time, 1e-6)
            window_elapsed = max(now - window_start_time, float(self.progress_rate_window))
            window_delta = max(count - window_start_count, 0)
            window_rate = window_delta / (window_elapsed / 60)
            avg_rate = count / (overall_elapsed / 60)
            remaining = total - count
            eta_seconds = (remaining / avg_rate) * 60 if avg_rate > 0 and remaining > 0 else 0
            eta_label = self._format_eta(eta_seconds) if remaining else "~00:00"
            self.logger.info(
                "Progress: %d/%d (%.1f%%) | Rate: %.1f/min (avg %.1f/min) | ETA %s | AI inflight: %d",
                count,
                total,
                count / total * 100,
                window_rate,
                avg_rate,
            eta_label,
            ai_inflight,
        )
        
        # Insert into audit DB immediately (before returning, to ensure all products are saved)
        if self.audit_db and self.run_id:
            try:
                # Ensure all metadata values are correct types
                model_output = ai_metadata.get('model_output')
                if isinstance(model_output, (dict, list)):
                    model_output = json.dumps(model_output)
                
                confidence = ai_metadata.get('confidence')
                if isinstance(confidence, (dict, list)):
                    confidence = json.dumps(confidence) if confidence else None
                
                reasoning = ai_metadata.get('reasoning')
                if isinstance(reasoning, (dict, list)):
                    reasoning = json.dumps(reasoning) if reasoning else None
                
                with self._lock:
                    self.audit_db.insert_product(
                        run_id=self.run_id,
                        handle=handle,
                        title=product_dict['title'],
                        csv_type=self.default_product_type or '',
                        effective_type=product_category or '',
                        description=product_dict['description'],
                        rule_tags=rule_tags,
                        ai_tags=ai_tags,
                        final_tags=final_tags,
                        forced_category=forced_category,
                        device_evidence=bool('device' in final_tags),
                        skipped=0,
                        ai_prompt=ai_metadata.get('prompt'),
                        ai_model_output=model_output,
                        ai_confidence=confidence,
                        ai_reasoning=reasoning
                    )
            except Exception as e:
                self.logger.error(f"Failed to insert {handle} into audit DB: {e}")
        
        return {
            'handle': handle,
            'product': product,
            'product_dict': product_dict,
            'rule_tags': rule_tags,
            'ai_tags': ai_tags,
            'final_tags': final_tags,
            'forced_category': forced_category,
            'product_category': product_category,
            'ai_metadata': ai_metadata,
            'tag_by_cat': dict(tag_by_cat),
        }
    
    def _log_performance_summary(self, total, start_time, ai_skipped=0):
        """Log final performance statistics"""
        elapsed = time.time() - start_time
        smoothed_elapsed = max(elapsed, 5)
        rate = total / (smoothed_elapsed / 60)
        ai_calls = total - ai_skipped
        skip_pct = (ai_skipped / total * 100) if total > 0 else 0
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info("PERFORMANCE SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"  Total products processed: {total}")
        self.logger.info(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.2f} minutes)")
        self.logger.info(f"  Average rate: {rate:.1f} products/minute")
        self.logger.info(f"  Workers: {self.max_workers if self.parallel_processing else 1}")
        self.logger.info(f"  Parallel processing: {'enabled' if self.parallel_processing else 'disabled'}")
        self.logger.info(f"{'─'*60}")
        self.logger.info(f"  AI calls made: {ai_calls}")
        self.logger.info(f"  AI calls skipped: {ai_skipped} ({skip_pct:.1f}%)")

        with self._metrics_lock:
            ai_call_count = self._ai_call_count
            ai_total_latency = self._ai_total_latency
            ai_max_inflight = self._ai_max_inflight

        if ai_call_count:
            avg_latency = ai_total_latency / ai_call_count
            self.logger.info(f"  Avg AI latency: {avg_latency:.1f} seconds")
            self.logger.info(f"  Peak concurrent AI calls: {ai_max_inflight}/{self.ollama_num_parallel}")
            if (
                self.parallel_processing
                and self.max_workers > 1
                and ai_call_count > 1
                and ai_max_inflight <= 1
                and self.ollama_num_parallel > 1
            ):
                self.logger.warning(
                    "Ollama processed AI requests serially (max concurrency %s). "
                    "Restart the daemon with `ollama serve --num-parallel %s` to unlock parallel AI tagging.",
                    ai_max_inflight,
                    self.ollama_num_parallel,
                )
        else:
            self.logger.info("  No AI latency data (all products resolved via rules)")
        self.logger.info(f"{'='*60}\n")
    
    def tag_products(self, input_file, output_file=None, limit=None):
        """Tag products from input CSV with optional parallel processing"""
        
        self.logger.info(f"Starting controlled tagging from {input_file}")
        
        if not Path(input_file).exists():
            self.logger.error(f"Input file not found: {input_file}")
            return
        
        # Read input products
        products = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            products = list(reader)
        
        if limit:
            products = products[:limit]
            self.logger.info(f"Limited to first {limit} products")
        
        self.logger.info(f"Processing {len(products)} products")
        
        # Load already processed products (check ALL runs to prevent duplicates)
        processed_handles = set()
        if self.audit_db:
            conn = self.audit_db._get_connection()
            cur = conn.cursor()
            # Query all handles in DB, not just current run (prevents duplicates across runs)
            cur.execute('SELECT DISTINCT handle FROM products')
            processed_handles = {row[0] for row in cur.fetchall()}
            self.logger.info(f"Found {len(processed_handles)} already processed products in audit DB")
        
        # Filter out already processed
        products_to_process = [p for p in products if p.get('Handle', '') not in processed_handles]
        skipped_count = len(products) - len(products_to_process)
        if skipped_count > 0:
            self.logger.info(f"Skipping {skipped_count} already processed products")
        
        total = len(products_to_process)
        if total == 0:
            self.logger.info("No products to process")
            return
        
        # Initialize performance tracking
        self._processed_count = 0
        self._ai_skipped_count = 0
        self._start_time = time.time()
        self._lock = threading.Lock()
        self._progress_history.clear()
        self._progress_history.append((self._start_time, 0))
        with self._metrics_lock:
            self._ai_call_count = 0
            self._ai_total_latency = 0.0
            self._ai_inflight = 0
            self._ai_max_inflight = 0
        
        self.logger.info(f"Processing {total} products with {'parallel' if self.parallel_processing else 'sequential'} mode")
        if self.parallel_processing:
            self.logger.info(f"Using {self.max_workers} workers")
        
        # Process products
        results = []
        
        if self.parallel_processing and total > 1:
            # Parallel processing with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._process_single_product, product, i, total): (i, product)
                    for i, product in enumerate(products_to_process, 1)
                }
                
                for future in as_completed(futures):
                    i, product = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        handle = product.get('Handle', 'unknown')
                        self.logger.error(f"Error processing {handle}: {e}")
        else:
            # Sequential processing
            for i, product in enumerate(products_to_process, 1):
                try:
                    result = self._process_single_product(product, i, total)
                    results.append(result)
                except Exception as e:
                    handle = product.get('Handle', 'unknown')
                    self.logger.error(f"Error processing {handle}: {e}")
        
        # Log performance summary
        self._log_performance_summary(len(results), self._start_time, self._ai_skipped_count)
        
        # Collect tagged and untagged products
        tagged_products = []
        untagged_products = []
        untagged_originals = []
        
        for result in results:
            handle = result['handle']
            product = result['product']
            product_dict = result['product_dict']
            rule_tags = result['rule_tags']
            ai_tags = result['ai_tags']
            final_tags = result['final_tags']
            forced_category = result['forced_category']
            product_category = result['product_category']
            ai_metadata = result['ai_metadata']
            
            # Note: Database insertion now happens inside _process_single_product
            
            # Create output product
            product_output = {
                'Handle': product.get('Handle', ''),
                'Variant SKU': product.get('Variant SKU', ''),
                'Tags': ', '.join(final_tags)
            }
            
            if product_output['Tags'].strip():
                tagged_products.append(product_output)
            else:
                untagged_products.append(product_output)
                untagged_originals.append(product)
        
        # Complete the run if audit DB is used
        if self.audit_db and self.run_id:
            self.audit_db.complete_run(self.run_id)
            self.logger.info(f"Completed run {self.run_id}")
        
        # Save tagged products
        if not output_file:
            output_file = Path('output/controlled_tagged_products.csv')
        else:
            output_file = Path(output_file)
        
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if tagged_products:
                fieldnames = tagged_products[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tagged_products)
        
        self.logger.info(f"Tagged products saved to {output_file}")
        self.logger.info(f"  Tagged: {len(tagged_products)}, Untagged: {len(untagged_products)}")
        
        # Save untagged products
        untagged_file = output_file.parent / 'controlled_untagged_products.csv'
        with open(untagged_file, 'w', newline='', encoding='utf-8') as f:
            if untagged_products:
                fieldnames = untagged_products[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(untagged_products)
                self.logger.info(f"Untagged products saved to {untagged_file} ({len(untagged_products)} products)")
            else:
                # Write header even if empty
                writer = csv.DictWriter(f, fieldnames=['Handle', 'Variant SKU', 'Tags'])
                writer.writeheader()
                self.logger.info("No untagged products found")
        
        # Secondary AI pass for untagged products
        if untagged_originals and not self.no_ai:
            secondary_model = self.secondary_ollama_model
            can_run_secondary = True
            if not secondary_model:
                self.logger.info("Skipping secondary AI tagging: OLLAMA_SECONDARY_MODEL not configured")
                can_run_secondary = False
            elif not self._is_ollama_model_available(secondary_model):
                self.logger.warning(
                    "Skipping secondary AI tagging: model '%s' is not installed on the Ollama daemon",
                    secondary_model,
                )
                can_run_secondary = False

            if can_run_secondary:
                self.logger.info(
                    f"Attempting secondary AI tagging for {len(untagged_originals)} untagged products using {secondary_model}"
                )
                original_model = self.ollama_model
                newly_tagged = []
                still_untagged = []
                try:
                    self.ollama_model = secondary_model
                    for orig_product in untagged_originals:
                        handle = orig_product.get('Handle', '')
                        title = orig_product.get('Title', '')
                        description = orig_product.get('Body (HTML)', '')
                        
                        # Get rule-based tags again (in case)
                        rule_tags_secondary, forced_category_secondary = self.get_rule_based_tags(handle, title, description)
                        
                        # Determine preliminary category for secondary AI
                        preliminary_category_secondary = None
                        max_priority_secondary = -1
                        for tag in rule_tags_secondary:
                            if tag in self.category_tags:
                                priority = self.category_priority.get(tag, 0)
                                if priority > max_priority_secondary:
                                    max_priority_secondary = priority
                                    preliminary_category_secondary = tag
                        
                        # Override with forced category
                        if forced_category_secondary:
                            preliminary_category_secondary = forced_category_secondary
                        
                        # Get secondary AI tags with category-aware prompting
                        ai_tags_secondary, _ = self.get_ai_tags(handle, title, description, category=preliminary_category_secondary)
                        
                        # Combine (use secondary results, not outer variables)
                        all_tags = list(set(ai_tags_secondary + rule_tags_secondary))
                        
                        # Determine product category with priority (using only rule_tags for secondary)
                        rule_tags_secondary, forced_category_secondary = self.get_rule_based_tags(handle, title, description)
                        product_category = None
                        max_priority = -1
                        for tag in rule_tags_secondary:
                            if tag in self.category_tags:
                                priority = self.category_priority.get(tag, 0)
                                if priority > max_priority:
                                    max_priority = priority
                                    product_category = tag
                        
                        # Override with forced category
                        if forced_category_secondary:
                            product_category = forced_category_secondary
                        
                        # Infer vaping style from VG/PG ratio for e-liquids
                        inferred_tags = []
                        if product_category == 'e-liquid':
                            for tag in all_tags:
                                if '/' in tag and tag in self.approved_tags.get('vg_ratio', {}).get('tags', []):
                                    try:
                                        vg, pg = map(int, tag.split('/'))
                                        if pg >= 50:
                                            inferred_tags.append('mouth-to-lung')
                                        elif 60 <= vg <= 70:
                                            inferred_tags.append('restricted-direct-to-lung')
                                        elif vg >= 70:
                                            inferred_tags.append('direct-to-lung')
                                    except ValueError:
                                        pass
                        all_tags.extend(inferred_tags)
                        all_tags = list(set(all_tags))
                        
                        # Filter tags based on applies_to and enforce category limits
                        tag_by_cat = defaultdict(list)
                        for tag in all_tags:
                            cat = self.tag_to_category.get(tag)
                            if cat == 'category':
                                continue
                            cat_data = self.approved_tags.get(cat, {})
                            applies_to = cat_data.get('applies_to', ['all']) if isinstance(cat_data, dict) else ['all']
                            if 'all' in applies_to or product_category in applies_to:
                                tag_by_cat[cat].append(tag)
                        
                        # Sort tags within each category by specificity (longer tags first)
                        for cat in tag_by_cat:
                            if cat == 'accessory_type':
                                # Prioritize charger over battery
                                tag_by_cat[cat].sort(key=lambda t: (0 if t == 'charger' else 1 if t == 'battery' else 2, -len(t)))
                            else:
                                tag_by_cat[cat].sort(key=len, reverse=True)
                        
                        final_tags = []
                        for cat, tags in tag_by_cat.items():
                            final_tags.extend(tags[:1])  # Keep at most one per category
                        
                        self.logger.info(f"Secondary AI for {handle} | Final tags: {final_tags}")
                        
                        product_output = {
                            'Handle': handle,
                            'Variant SKU': orig_product.get('Variant SKU', ''),
                            'Tags': ', '.join(final_tags)
                        }
                        
                        if final_tags:
                            newly_tagged.append(product_output)
                        else:
                            still_untagged.append(product_output)
                finally:
                    self.ollama_model = original_model

                # Update the lists once after processing
                tagged_products.extend(newly_tagged)
                untagged_products[:] = still_untagged

                # Re-save files
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if tagged_products:
                        fieldnames = tagged_products[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(tagged_products)
                
                with open(untagged_file, 'w', newline='', encoding='utf-8') as f:
                    if untagged_products:
                        fieldnames = untagged_products[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(untagged_products)
                        self.logger.info(f"After secondary AI: {len(newly_tagged)} newly tagged, {len(still_untagged)} still untagged")
                    else:
                        writer = csv.DictWriter(f, fieldnames=['Handle', 'Variant SKU', 'Tags'])
                        writer.writeheader()
                        self.logger.info("All products now tagged after secondary AI")
        
        return output_file

if __name__ == "__main__":
    args = parse_arguments()
    
    # Initialize tagger
    tagger = ControlledTagger(
        config_file=args.config,
        no_ai=args.no_ai,
        verbose=args.verbose,
        default_product_type=args.type,
        audit_db_path=args.audit_db,
        run_id=args.run_id,
        max_workers=args.workers,
        no_parallel=args.no_parallel
    )
    
    # Determine input file
    if args.input:
        input_file = args.input
    else:
        # Auto-detect from input/
        input_files = list(Path('input').glob('*.csv'))
        if not input_files:
            print("❌ No input CSV found in input/ directory")
            sys.exit(1)
        input_file = input_files[0]
    
    # Tag products
    result = tagger.tag_products(input_file, args.output, args.limit)
    if result:
        print(f"✅ Tagging complete: {result}")
    else:
        print("❌ Tagging failed")
        sys.exit(1)
