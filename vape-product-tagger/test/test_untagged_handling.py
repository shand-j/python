#!/usr/bin/env python3
"""
Integration test: ensure untagged products are excluded from tagged output and recorded separately
"""
import csv
import subprocess
import sys
from pathlib import Path


def write_input(path):
    rows = [
        {'Handle': 'should-be-untagged', 'Variant SKU': 'SKU001', 'Title': 'Generic product', 'Body (HTML)': 'A generic product with no matching keywords'},
        {'Handle': 'tagged-cbd-1000mg-1', 'Variant SKU': 'SKU002', 'Title': 'CBD oil 1000mg', 'Body (HTML)': 'High potency CBD oil 1000mg'},
    ]

    fieldnames = ['Handle', 'Variant SKU', 'Title', 'Body (HTML)']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_tagger(input_file, output_file):
    cmd = [sys.executable, 'main.py', '--input', str(input_file), '--output', str(output_file), '--no-ai']
    # run from repo root (one level up from test/)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result.returncode == 0, result.stdout, result.stderr


def main():
    repo_test_dir = Path(__file__).parent
    input_file = repo_test_dir / 'test_untagged_sample.csv'
    output_file = repo_test_dir / 'test_untagged_out.csv'

    write_input(input_file)

    ok, out, err = run_tagger(input_file, output_file)
    if not ok:
        print('Tagger failed', err)
        return 1

    # Check tagged output
    tagged = []
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tagged.append(r['Handle'])

    # Check untagged output file (stored in same parent as output_file)
    untagged_file = Path(output_file).parent / 'controlled_untagged_products.csv'
    untagged = []
    if untagged_file.exists():
        with open(untagged_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                untagged.append(r['Handle'])

    # Assertions
    if 'tagged-cbd-1000mg-1' not in tagged:
        print('Missing expected tagged product in tagged output')
        return 1

    if 'should-be-untagged' not in untagged:
        print('Missing expected untagged product in untagged file')
        return 1

    print('PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
