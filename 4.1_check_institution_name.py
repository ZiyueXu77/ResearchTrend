#!/usr/bin/env python3
"""
Normalize institution names in Analyzed/ CSVs.
Expands abbreviations to full names, merges variants, and flags uncertain cases.
"""

import pandas as pd
import glob
import re
from pathlib import Path

# Canonical mapping: variant → full name
# Add new entries here as needed
INSTITUTION_MAP = {
    # --- Abbreviations → full names ---
    'CMU': 'Carnegie Mellon University',
    'HUST': 'Huazhong University of Science and Technology',
    'UIUC': 'University of Illinois Urbana-Champaign',
    'ECUST': 'East China University of Science and Technology',
    'UCAS': 'University of Chinese Academy of Sciences',
    'UESTC': 'University of Electronic Science and Technology of China',
    'HKUST(GZ)': 'The Hong Kong University of Science and Technology (Guangzhou)',
    'UNIST': 'Ulsan National Institute of Science and Technology',
    'IHPC': 'A*STAR',
    'Institute of High Performance Computing (IHPC)': 'A*STAR',
    'NC State University': 'North Carolina State University',
    'TU Berlin': 'Technische Universität Berlin',

    # --- "The" prefix inconsistencies ---
    'Pennsylvania State University': 'The Pennsylvania State University',
    'University of British Columbia': 'The University of British Columbia',
    'Chinese University of Hong Kong': 'The Chinese University of Hong Kong',
    'Hong Kong University of Science and Technology': 'The Hong Kong University of Science and Technology',
    'University of Sydney': 'The University of Sydney',
    'Johns Hopkins University': 'The Johns Hopkins University',
    'University of Texas at Austin': 'The University of Texas at Austin',

    # --- Variant spellings ---
    'Shanghai Jiaotong University': 'Shanghai Jiao Tong University',
    'National University of Defence Technology': 'National University of Defense Technology',
    'Universit`a della Svizzera italiana': 'Università della Svizzera italiana',
    'Ecole polytechnique': 'École Polytechnique',
    'École polytechnique': 'École Polytechnique',
    'Poly-technic University of Turin': 'Polytechnic University of Turin',
    'University of Sungkyunkwan': 'Sungkyunkwan University',
    'Webank': 'WeBank',

    # --- UC system normalization ---
    'UCLA': 'University of California, Los Angeles',
    'UC Berkeley': 'University of California, Berkeley',
    'UC San Diego': 'University of California, San Diego',
    'UC Santa Cruz': 'University of California, Santa Cruz',
    'University of California San Diego': 'University of California, San Diego',
    'University of California Irvine': 'University of California, Irvine',

    # --- UMass normalization ---
    'University of Massachusetts, Amherst': 'University of Massachusetts Amherst',
    'University of Massachusetts': 'University of Massachusetts Amherst',

    # --- UMD normalization ---
    'University of Maryland College Park': 'University of Maryland',

    # --- UB normalization ---
    'State University of New York at Buffalo': 'University at Buffalo',

    # --- Company normalization ---
    'Sony Reasearch': 'Sony AI',
    'Sony': 'Sony AI',
    'Alibaba Group': 'Alibaba',
    'AWS': 'Amazon',
    'The Wharton School': 'University of Pennsylvania',

    # --- CISPA normalization ---
    'CISPA': 'CISPA Helmholtz Center for Information Security',

    # --- Garbage ---
    '2': '',
}


def normalize_institutions(dry_run=True):
    """Normalize institution names across all Analyzed/ CSVs."""
    csv_files = sorted(glob.glob('Analyzed/*_analyzed.csv'))
    if not csv_files:
        print("Error: No analyzed CSV files found in Analyzed/")
        return

    all_names = {}
    changes = []

    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        if 'institution_extracted' not in df.columns:
            continue

        conf = Path(csv_file).stem.replace('_analyzed', '')
        modified = False

        for idx, row in df.iterrows():
            raw = row.get('institution_extracted')
            if pd.isna(raw) or str(raw).strip() == '':
                continue
            name = str(raw).strip()

            canonical = INSTITUTION_MAP.get(name)
            if canonical is not None:
                if canonical == '':
                    changes.append((conf, name, '(REMOVED)', row.get('title', '')[:60]))
                elif canonical != name:
                    changes.append((conf, name, canonical, row.get('title', '')[:60]))
                df.at[idx, 'institution_extracted'] = canonical
                modified = True
                name = canonical

            if name:
                all_names[name] = all_names.get(name, 0) + 1

        if modified and not dry_run:
            df.to_csv(csv_file, index=False)

    return all_names, changes


def find_uncertain(all_names):
    """Flag names that look like abbreviations or possible duplicates."""
    uncertain = []
    name_list = sorted(all_names.keys())

    for name in name_list:
        reasons = []
        if re.match(r'^[A-Z][A-Z0-9\s\-\*]*$', name) and len(name) <= 10:
            reasons.append('looks like abbreviation')
        if all_names[name] == 1 and not any(c.islower() for c in name[:3]):
            reasons.append('single occurrence + short/uppercase')
        if reasons:
            uncertain.append((name, all_names[name], ', '.join(reasons)))

    return uncertain


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Normalize institution names in Analyzed/ CSVs')
    parser.add_argument('--apply', action='store_true',
                        help='Actually write changes (default: dry run)')
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "APPLYING CHANGES"

    print("=" * 80)
    print(f"Institution Name Normalization ({mode})")
    print("=" * 80)

    all_names, changes = normalize_institutions(dry_run=dry_run)

    if changes:
        print(f"\n{'Applied' if not dry_run else 'Pending'} corrections ({len(changes)}):")
        print("-" * 80)
        for conf, old, new, title in changes:
            print(f"  {old:45s} → {new}")
            print(f"    [{conf}] {title}")
    else:
        print("\nNo corrections needed.")

    uncertain = find_uncertain(all_names)
    if uncertain:
        print(f"\n⚠️  Uncertain cases (may need manual review):")
        print("-" * 80)
        for name, count, reason in uncertain:
            print(f"  {count:3d}x  {name:40s}  ({reason})")

    print(f"\n📊 Final institution counts (top 30):")
    print("-" * 80)
    for name, count in sorted(all_names.items(), key=lambda x: (-x[1], x[0]))[:30]:
        print(f"  {count:3d}  {name}")

    total = sum(all_names.values())
    print(f"\n  Total: {total} records, {len(all_names)} unique institutions")

    if dry_run and changes:
        print(f"\n💡 Run with --apply to write changes to Analyzed/ CSVs")


if __name__ == "__main__":
    main()
