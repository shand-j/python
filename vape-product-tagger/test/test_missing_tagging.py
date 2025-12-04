#!/usr/bin/env python3
"""
Integration test to ensure tags detected by rules (like 5ml and battery) are kept for kit/device products
"""
import csv
import subprocess
import sys
from pathlib import Path


def write_input(path):
    rows = [
        {
            'Handle': 'ezee-e-cigarette-starter-kit',
            'Variant SKU': 'EC0329X0493',
            'Title': 'Ezee e-cigarette starter kit',
            'Body (HTML)': 'Starter kit with battery and 5ml sample'
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
    input_file = repo_test_dir / 'test_missing_input.csv'
    output_file = repo_test_dir / 'test_missing_out.csv'

    write_input(input_file)

    ok, out, err = run_tagger(input_file, output_file)
    if not ok:
        print('Tagger failed', err)
        return 1

    tags = None
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['Handle'] == 'ezee-e-cigarette-starter-kit':
                    tags = r['Tags']
                    break

    if not tags:
        print('Failed: expected tags for ezee-e-cigarette-starter-kit')
        return 1

    # Expect to see the detected 5ml and battery tags retained
    if '5ml' not in tags:
        print(f"Failed: expected '5ml' in tags but got: {tags}")
        return 1

    if 'battery' not in tags and 'accessory' not in tags:
        print(f"Failed: expected 'battery' or 'accessory' in tags but got: {tags}")
        return 1

    print('PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
