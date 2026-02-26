#!/usr/bin/env python3
"""
Combine all CSV data sources into a single master dataset.
Merges: Raw data, Analyzed (authors + platforms), and Categorized.
"""

import csv
import glob
import re
from pathlib import Path
import argparse


def parse_filename(filename):
    """Parse conference and year from filename."""
    match = re.match(r'(\w+)_(\d{4})_federated_learning_(\d+)_(\d+)', Path(filename).stem)
    if match:
        return {
            'conference': match.group(1),
            'year': match.group(2),
            'total_papers': match.group(3),
            'federated_papers': match.group(4)
        }
    return None


def load_csv_dict(csv_file):
    """Load CSV file into a dictionary keyed by title."""
    data = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get('title', '').strip()
                if title:
                    data[title] = row
    except Exception as e:
        print(f"  Warning: Error reading {csv_file}: {e}")
    return data


def combine_all_data(raw_dir='Raw', analyzed_dir='Analyzed',
                     categorized_dir='Categorized_32B',
                     output_file='fl_summary.csv'):
    """Combine all data sources into one master CSV."""
    print("=" * 100)
    print("COMBINING ALL FEDERATED LEARNING DATA")
    print("=" * 100)

    raw_files = sorted(glob.glob(f'{raw_dir}/*_federated_learning_*.csv'))

    if not raw_files:
        print(f"\nNo raw CSV files found in {raw_dir}/")
        return

    print(f"\nFound {len(raw_files)} conference files")

    all_papers = []

    for raw_file in raw_files:
        file_info = parse_filename(raw_file)
        if not file_info:
            print(f"  Warning: Could not parse filename: {raw_file}")
            continue

        conf = file_info['conference']
        year = file_info['year']
        base = f"{conf}_{year}_federated_learning_{file_info['total_papers']}_{file_info['federated_papers']}"

        print(f"\nProcessing {conf.upper()} {year}...")

        raw_data = load_csv_dict(raw_file)
        print(f"  Raw: {len(raw_data)} papers")

        analyzed_file = f"{analyzed_dir}/{base}_analyzed.csv"
        analyzed_data = load_csv_dict(analyzed_file) if Path(analyzed_file).exists() else {}
        print(f"  Analyzed: {len(analyzed_data)} papers")

        categorized_file = f"{categorized_dir}/{base}_categorized_llm.csv"
        categorized_data = load_csv_dict(categorized_file) if Path(categorized_file).exists() else {}
        print(f"  Categories: {len(categorized_data)} papers")

        for title, raw_row in raw_data.items():
            combined_row = {
                'conference': conf.upper(),
                'year': year,
                'title': title,
                'link': raw_row.get('link', ''),
                'abstract': raw_row.get('abstract', ''),
            }

            if title in analyzed_data:
                row = analyzed_data[title]
                combined_row['authors'] = row.get('authors', '')
                combined_row['last_author'] = row.get('last_author_extracted', '')
                combined_row['institution'] = row.get('institution_extracted', '')
                combined_row['platform_mentions'] = row.get('platform_mentions', '')
                combined_row['platform_used'] = row.get('platform_used', '')
                combined_row['platform_mentioned'] = row.get('platform_mentioned', '')
            else:
                combined_row['authors'] = ''
                combined_row['last_author'] = ''
                combined_row['institution'] = ''
                combined_row['platform_mentions'] = ''
                combined_row['platform_used'] = ''
                combined_row['platform_mentioned'] = ''

            if title in categorized_data:
                for col in categorized_data[title].keys():
                    if col not in ['title', 'link', 'abstract']:
                        combined_row[col] = categorized_data[title].get(col, '')

            all_papers.append(combined_row)

    print(f"\nWriting combined dataset...")

    if not all_papers:
        print("No papers to write!")
        return

    all_columns = set()
    for paper in all_papers:
        all_columns.update(paper.keys())

    priority_columns = [
        'conference', 'year', 'title', 'link', 'abstract',
        'authors', 'last_author', 'institution',
        'platform_mentions', 'platform_used', 'platform_mentioned',
        'Personalization', 'Heterogeneity/Generalization', 'DataProcessing',
        'LLM/Agents', 'Privacy/Attack', 'Fairness/Incentives',
        'FoundationModel', 'Vertical', 'Unlearning',
        'Efficiency/Compression', 'Benchmark', 'ClientSelection',
        'Graph', 'Other'
    ]

    remaining_columns = sorted(all_columns - set(priority_columns))
    fieldnames = [col for col in priority_columns if col in all_columns] + remaining_columns

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_papers)

        print(f"Saved to: {output_file}")
        print(f"Total papers: {len(all_papers)}")
        print(f"Total columns: {len(fieldnames)}")

        print(f"\nData Completeness:")
        with_authors = sum(1 for p in all_papers if p.get('authors'))
        with_last_author = sum(1 for p in all_papers if p.get('last_author'))
        with_institution = sum(1 for p in all_papers if p.get('institution'))
        with_platform = sum(1 for p in all_papers if p.get('platform_mentions'))

        total = len(all_papers)
        print(f"  Authors: {with_authors}/{total} ({with_authors/total*100:.1f}%)")
        print(f"  Last Author: {with_last_author}/{total} ({with_last_author/total*100:.1f}%)")
        print(f"  Institution: {with_institution}/{total} ({with_institution/total*100:.1f}%)")
        print(f"  Platform Mentions: {with_platform}/{total} ({with_platform/total*100:.1f}%)")

    except Exception as e:
        print(f"Error writing output: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Combine all federated learning data sources into one master CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 7_combine_all_data.py
  python3 7_combine_all_data.py --output my_dataset.csv
  python3 7_combine_all_data.py --categorized-dir Categorized_7B
        """
    )
    parser.add_argument('--raw-dir', type=str, default='Raw',
                        help='Directory containing raw CSV files (default: Raw)')
    parser.add_argument('--analyzed-dir', type=str, default='Analyzed',
                        help='Directory containing analyzed CSV files (default: Analyzed)')
    parser.add_argument('--categorized-dir', type=str, default='Categorized_32B',
                        help='Directory containing categorized CSV files (default: Categorized_32B)')
    parser.add_argument('--output', type=str, default='fl_summary.csv',
                        help='Output CSV file name (default: fl_summary.csv)')

    args = parser.parse_args()

    combine_all_data(
        raw_dir=args.raw_dir,
        analyzed_dir=args.analyzed_dir,
        categorized_dir=args.categorized_dir,
        output_file=args.output
    )

    print("\n" + "=" * 100)
    print("DATASET COMBINATION COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
