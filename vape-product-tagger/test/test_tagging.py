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
    cmd = [sys.executable, 'main.py', '--input', input_file, '--output', output_file, '--no-ai']
    if limit:
        cmd.extend(['--limit', str(limit)])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
    return result.returncode == 0, result.stdout, result.stderr

def load_expected_tags():
    """Load expected tags for test products (placeholder for now)."""
    # This could be a dict mapping handle to expected tags
    return {
        'test-e-liquid-50vg': ['10ml', '50/50', 'nic_salt', 'fruity', 'mouth-to-lung'],
        'test-pod-refillable': ['refillable_pod'],
        'test-device-pod-system': ['battery'],
        'test-coil-0-5ohm': ['0.5ohm'],
        'test-accessory-battery': ['battery'],
        # Add more as needed
    }

def validate_output(output_file, expected_tags):
    """Validate the tagging output."""
    with open(output_file, 'r') as f:
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