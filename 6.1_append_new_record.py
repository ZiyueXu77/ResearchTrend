#!/usr/bin/env python3
"""
Append new platform usage records from Analyzed/ CSVs to platform_details_manual_checked.csv.
Run this after adding new conference data, then manually review before plotting with 6.2.
"""

import pandas as pd
import glob
import re
import os
from pathlib import Path

CHECKED_CSV = 'platform_details_manual_checked.csv'

ML_CONFERENCES = ['neurips', 'icml', 'iclr']
CV_CONFERENCES = ['cvpr', 'iccv', 'miccai', 'eccv']


def parse_filename(filename):
    """Parse conference CSV filename to extract metadata."""
    match = re.match(r'(\w+)_(\d{4})_federated_learning_(\d+)_(\d+)', Path(filename).stem)
    if match:
        return {
            'conference': match.group(1),
            'year': int(match.group(2)),
            'total_papers': int(match.group(3)),
            'federated_papers': int(match.group(4))
        }
    return None


def get_existing_conferences(checked_csv):
    """Get set of conference strings already present in the checked CSV."""
    if not os.path.exists(checked_csv):
        return set()
    df = pd.read_csv(checked_csv)
    existing = set()
    for conf_str in df['conference'].unique():
        match = re.match(r'(\w+)_(\d{4})_', conf_str)
        if match:
            existing.add((match.group(1).lower(), int(match.group(2))))
    return existing


def extract_platform_records(skip_conferences):
    """Extract platform USED records from Analyzed/ CSVs, skipping already-reviewed conferences."""
    csv_files = sorted(glob.glob('Analyzed/*_analyzed.csv'))

    if not csv_files:
        print("Error: No analyzed CSV files found in Analyzed/")
        return pd.DataFrame()

    all_records = []
    skipped = []

    for csv_file in csv_files:
        info = parse_filename(csv_file)
        if not info:
            continue

        conf_key = (info['conference'], info['year'])
        if conf_key in skip_conferences:
            skipped.append(f"{info['conference'].upper()} {info['year']}")
            continue

        df = pd.read_csv(csv_file)
        conf_str = (f"{info['conference'].upper()}_{info['year']}"
                    f"_FEDERATED_LEARNING {info['total_papers']}")

        for _, row in df.iterrows():
            platform_used = row.get('platform_used')
            if pd.isna(platform_used) or str(platform_used).strip() == '':
                continue

            platforms = [p.strip() for p in str(platform_used).split(',')]
            mention_text = str(row.get('platform_mentions', ''))

            for platform in platforms:
                if not platform:
                    continue
                all_records.append({
                    'platform': platform,
                    'conference': conf_str,
                    'title': row['title'],
                    'mention_text': mention_text
                })

    if skipped:
        print(f"  Skipping already-reviewed conferences: {', '.join(sorted(set(skipped)))}")

    return pd.DataFrame(all_records)


def main():
    print("=" * 80)
    print("Append New Platform Records to Manual Checked CSV")
    print("=" * 80)

    file_exists = os.path.exists(CHECKED_CSV)
    if file_exists:
        existing_df = pd.read_csv(CHECKED_CSV)
        print(f"\n  Existing records in {CHECKED_CSV}: {len(existing_df)}")
    else:
        print(f"\n  {CHECKED_CSV} not found, will create new file")
        existing_df = pd.DataFrame(columns=['platform', 'conference', 'title', 'mention_text'])

    reviewed_conferences = get_existing_conferences(CHECKED_CSV)

    print(f"\n📂 Extracting platform records from new conferences in Analyzed/ ...")
    to_append = extract_platform_records(reviewed_conferences)

    if to_append.empty:
        print("\n✅ No new records to append. All conferences already reviewed.")
        return

    to_append = to_append.sort_values(['platform', 'conference', 'title'])

    to_append.to_csv(CHECKED_CSV, mode='a', header=not file_exists, index=False)

    print(f"\n✅ Appended {len(to_append)} new records to {CHECKED_CSV}")

    print(f"\nNew records by conference:")
    for conf, count in to_append['conference'].value_counts().sort_index().items():
        print(f"  {conf}: {count}")

    print(f"\nNew records by platform:")
    for plat, count in to_append['platform'].value_counts().items():
        print(f"  {plat}: {count}")

    print(f"\nNew records detail:")
    print("-" * 80)
    for _, row in to_append.iterrows():
        print(f"  [{row['platform']}] {row['conference']}")
        print(f"    {row['title']}")
        print()

    print(f"⚠️  Please manually review the new records in {CHECKED_CSV}")
    print(f"   Then run 6.2_plot_platform_trends.py to generate plots.")


if __name__ == "__main__":
    main()
