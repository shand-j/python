#!/usr/bin/env python3
"""Local full-stack validation suite for vape-product-tagger.

This script exercises the core tooling (tagger, audit DB, AI review plumbing,
GPU autotune harness, and training export) using only local resources.
Each check is lightweight and avoids real GPU/AI calls by using the
built-in flags or mocks.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_cmd(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a subprocess and raise with helpful output on failure."""
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def copy_sample_input(temp_dir: Path) -> Path:
    """Copy the sample test CSV into the temp directory."""
    source = PROJECT_ROOT / 'test' / 'test_products.csv'
    if not source.exists():
        raise FileNotFoundError(f"Sample input missing: {source}")
    target = temp_dir / 'sample_products.csv'
    target.write_text(source.read_text(), encoding='utf-8')
    return target


def validate_tagger(temp_dir: Path) -> Dict[str, Path]:
    """Run the tagger in no-AI mode and ensure outputs + audit DB exist."""
    input_csv = copy_sample_input(temp_dir)
    output_csv = temp_dir / 'tagged_output.csv'
    audit_db = temp_dir / 'local_audit.sqlite3'

    args = [
        PYTHON,
        'main.py',
        '--input', str(input_csv),
        '--output', str(output_csv),
        '--audit-db', str(audit_db),
        '--no-ai',
        '--no-parallel',
        '--limit', '5'
    ]
    run_cmd(args, PROJECT_ROOT)

    if not output_csv.exists():
        raise AssertionError('Tagger did not produce an output CSV')
    if not audit_db.exists():
        raise AssertionError('Audit DB not created')

    with sqlite3.connect(audit_db) as conn:
        run_count = conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
        product_count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    if run_count == 0 or product_count == 0:
        raise AssertionError('Audit DB missing run/product rows')

    return {
        'input': input_csv,
        'output': output_csv,
        'audit_db': audit_db,
    }


def validate_ai_review(audit_db: Path) -> Dict[str, int]:
    """Mock the AI reviewer to ensure the workflow updates records."""
    from tag_audit_db import TagAuditDB

    db = TagAuditDB(db_path=str(audit_db))

    responses = (
        {'decision': 'approve', 'confidence': 0.9, 'reasoning': 'synthetic approval'},
        {'decision': 'flag', 'confidence': 0.6, 'reasoning': 'synthetic flag'},
    )
    response_cycle = iter(responses)

    def fake_ai_review(self, product, model='mock-model'):
        try:
            return next(response_cycle)
        except StopIteration:
            return {'decision': 'flag', 'confidence': 0.5, 'reasoning': 'fallback'}

    with mock.patch.object(TagAuditDB, 'ai_review_product', fake_ai_review):
        stats = db.ai_review_session(model='mock-model', auto_approve_threshold=0.8, batch_size=2)

    if stats['reviewed'] == 0:
        raise AssertionError('AI review mock did not process any products')
    return stats


def validate_tag_auditor(audit_db: Path, temp_dir: Path) -> Path:
    """Run the CLI auditor to ensure reporting + CSV export works."""
    output_csv = temp_dir / 'audit_report.csv'
    args = [
        PYTHON,
        'tag_auditor.py',
        '--audit-db', str(audit_db),
        '--output', str(output_csv)
    ]
    run_cmd(args, PROJECT_ROOT)
    if not output_csv.exists() or output_csv.stat().st_size == 0:
        raise AssertionError('Audit report not generated')
    return output_csv


def validate_training_export(temp_dir: Path) -> Path:
    """Use the public audit dataset to ensure JSONL export works."""
    sample_training_csv = PROJECT_ROOT / 'audit_training_dataset.csv'
    if not sample_training_csv.exists():
        raise FileNotFoundError('audit_training_dataset.csv not found')

    output_jsonl = temp_dir / 'training_export.jsonl'
    args = [
        PYTHON,
        'train_tag_model.py',
        '--export',
        '--input', str(sample_training_csv),
        '--output', str(output_jsonl)
    ]
    run_cmd(args, PROJECT_ROOT)
    if not output_jsonl.exists() or output_jsonl.stat().st_size == 0:
        raise AssertionError('Training JSONL export failed')
    return output_jsonl


def validate_autotune(sample_input: Path) -> Dict[str, float]:
    """Exercise the autotune logic with mocked GPU + Ollama calls."""
    from gpu_autotune import AutoTuner, GPUMonitor, GPUStats

    def fake_get_gpu_stats(self):
        now = time.time()
        return [GPUStats(timestamp=now, gpu_util=60.0, mem_util=50.0, mem_used=8192, mem_total=24576, temperature=60, power_draw=180.0)]

    def fake_make_request(self, product):
        time.sleep(0.01)
        return 120.0

    with mock.patch.object(GPUMonitor, '_get_gpu_stats', fake_get_gpu_stats), \
            mock.patch.object(AutoTuner, '_set_ollama_num_parallel', return_value=True), \
            mock.patch.object(AutoTuner, '_make_ollama_request', fake_make_request):
        tuner = AutoTuner(
            input_file=str(sample_input),
            target_gpu_util=50.0,
            min_workers=2,
            max_workers=4,
            ramp_step=2,
            stabilize_secs=2.0,
            ollama_model='mock-model',
            ollama_num_parallel=4,
        )
        report = tuner.run_auto_tune()

    if not report.get('all_results'):
        raise AssertionError('Autotune report missing results')
    return {
        'workers_tested': len(report['all_results']),
        'recommended_workers': report['optimal_workers']
    }


def main():
    print('🔬 Running local full-stack validation...')
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        temp_dir = Path(tmp_dir_str)
        artifacts = {}

        # 1. Tagger pipeline (rule-only)
        print(' - Validating tagger pipeline (no AI)...')
        tagger_result = validate_tagger(temp_dir)
        artifacts.update(tagger_result)

        # 2. Training export
        print(' - Validating training export...')
        training_output = validate_training_export(temp_dir)
        artifacts['training_jsonl'] = training_output

        # 3. Autotune harness (mocked)
        print(' - Validating GPU autotune harness...')
        autotune_stats = validate_autotune(tagger_result['input'])

        # 4. AI review flow with mocks
        print(' - Validating AI review session (mocked responses)...')
        ai_review_stats = validate_ai_review(tagger_result['audit_db'])

        # 5. Audit reporting export
        print(' - Validating audit reporting CLI...')
        audit_report = validate_tag_auditor(tagger_result['audit_db'], temp_dir)
        artifacts['audit_report'] = audit_report

        print('\n✅ LOCAL VALIDATION COMPLETE')
        print(f"   Tagged output: {tagger_result['output']}")
        print(f"   Audit DB:      {tagger_result['audit_db']}")
        print(f"   Audit report:  {audit_report}")
        print(f"   Training JSONL:{training_output}")
        print(f"   Autotune runs: {autotune_stats['workers_tested']} worker configs tested")
        print(f"   AI review:     {ai_review_stats['reviewed']} reviewed, {ai_review_stats['approved']} auto-approved")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f"\n❌ Local validation failed: {exc}")
        sys.exit(1)
