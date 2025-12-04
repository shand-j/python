#!/usr/bin/env python3
"""
Test Runner for Controlled AI Product Tagger
===========================================
Runs the tagging pipeline on a test dataset and validates results.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

def run_tagger(input_file, output_file, limit=None):
    """Run the tagger on the input file."""
    # Ensure input/output paths are full paths under the test directory
    repo_test_dir = Path(__file__).parent
    cmd = [
        sys.executable,
        'main.py',
        '--input', str(repo_test_dir / input_file),
        '--output', str(repo_test_dir / output_file),
        '--no-ai'
    ]
    if limit:
        cmd.extend(['--limit', str(limit)])
    # run from repo root
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result.returncode == 0, result.stdout, result.stderr

def load_expected_tags():
    """Load expected tags for test products (placeholder for now)."""
    # This could be a dict mapping handle to expected tags
    return {
        'test-e-liquid-50vg': ['10ml', '50/50', 'nic_salt', 'fruity', 'mouth-to-lung'],
        'test-pod-refillable': ['replacement_pod'],
        'test-device-pod-system': ['battery'],
        'test-coil-0-5ohm': ['0.5ohm'],
        'test-accessory-battery': ['battery'],
        # Add more as needed
    }

def validate_output(output_file, expected_tags):
    """Validate the tagging output."""
    repo_test_dir = Path(__file__).parent
    out_path = repo_test_dir / output_file
    with open(out_path, 'r') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    failures = []
    for row in results:
        handle = row['Handle']
        tags = row['Tags'].split(', ') if row['Tags'] else []
        
        if handle in expected_tags:
            expected = set(expected_tags[handle])
            actual = set(tags)
            if not expected.issubset(actual):
                failures.append(f"{handle}: Missing expected tags {expected - actual}")
        
        # Basic checks
        if not tags and (handle not in expected_tags or expected_tags.get(handle)):
            failures.append(f"{handle}: No tags applied")
        
        if not row['Variant SKU']:
            failures.append(f"{handle}: Missing Variant SKU")
    
    return failures

def main():
    input_file = 'test_products.csv'
    output_file = 'test_output.csv'
    
    print("Running tagger on test dataset...")
    success, stdout, stderr = run_tagger(input_file, output_file, limit=5)
    
    if not success:
        print("Tagger failed:")
        print(stderr)
        return 1
    
    print("Tagger completed successfully.")
    print(stdout)
    
    expected_tags = load_expected_tags()
    failures = validate_output(output_file, expected_tags)
    
    if failures:
        print("Validation failures:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    else:
        print("All validations passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())