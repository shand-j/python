#!/usr/bin/env python3
"""
Unit tests for CBD strength range handling and numeric tag mapping
"""
import csv
import subprocess
import sys
from pathlib import Path


def write_input(path):
    rows = [
        {
            'Handle': 'cbd-0mg-product',
            'Variant SKU': 'CBD000',
            'Title': 'CBD balm 0mg',
            'Body (HTML)': 'Test product explicitly listing CBD 0mg'
        },
        {
            'Handle': 'cbd-3000mg-product',
            'Variant SKU': 'CBD3000',
            'Title': 'CBD oil 3000mg',
            'Body (HTML)': 'High potency CBD oil 3000mg'
        },
        {
            'Handle': 'cbd-60000mg-product',
            'Variant SKU': 'CBD60000',
            'Title': 'CBD syrup 60000mg',
            'Body (HTML)': 'Out-of-range CBD value 60000mg should not be accepted'
        }
    ]

    fieldnames = ['Handle', 'Variant SKU', 'Title', 'Body (HTML)']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_tagger(input_file, output_file):
    cmd = [sys.executable, 'main.py', '--input', str(input_file), '--output', str(output_file), '--no-ai']
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result.returncode == 0, result.stdout, result.stderr


def main():
    repo_test_dir = Path(__file__).parent
    input_file = repo_test_dir / 'test_cbd_input.csv'
    output_file = repo_test_dir / 'test_cbd_output.csv'

    write_input(input_file)

    ok, out, err = run_tagger(input_file, output_file)
    if not ok:
        print('Tagger run failed', err)
        return 1

    # Read tagged output
    tags_by_handle = {}
    if Path(output_file).exists():
        import csv
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                tags_by_handle[r['Handle']] = r['Tags']

    # Read untagged output
    untagged_file = Path(output_file).parent / 'controlled_untagged_products.csv'
    untagged_handles = set()
    if untagged_file.exists():
        with open(untagged_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                untagged_handles.add(r['Handle'])

    # Assertions
    # 0mg and 3000mg should be accepted and appear in tagged output
    if 'cbd-0mg-product' not in tags_by_handle or '0mg' not in tags_by_handle['cbd-0mg-product']:
        print('Failed: expected cbd-0mg-product to be tagged with 0mg')
        return 1

    if 'cbd-3000mg-product' not in tags_by_handle or '3000mg' not in tags_by_handle['cbd-3000mg-product']:
        print('Failed: expected cbd-3000mg-product to be tagged with 3000mg')
        return 1

    # 60000mg should be out of range and therefore untagged
    if 'cbd-60000mg-product' in tags_by_handle:
        print('Failed: expected cbd-60000mg-product to NOT be in tagged output')
        return 1

    if 'cbd-60000mg-product' not in untagged_handles:
        print('Failed: expected cbd-60000mg-product to be present in untagged file')
        return 1

    print('PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
