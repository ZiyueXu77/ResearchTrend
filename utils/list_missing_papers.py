#!/usr/bin/env python3
"""
Script to list all papers that are missing PDFs.
"""

import pandas as pd
import glob
import re
from pathlib import Path
import csv

def sanitize_filename(filename):
    """Sanitize filename to be filesystem-safe."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Trim to reasonable length
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()


def list_missing_papers():
    """List all papers without downloaded PDFs."""
    
    # Find all CSV files in Raw/ folder
    csv_files = glob.glob('Raw/*_federated_learning_*.csv')
    csv_files = [f for f in csv_files if '_categorized' not in f]
    csv_files = sorted(csv_files)
    
    missing_by_conf = {}
    missing_all = []
    
    for csv_file in csv_files:
        # Parse conference and year from filename
        basename = Path(csv_file).name
        match = re.match(r'(\w+)_(\d{4})_federated_learning_', basename)
        if not match:
            continue
        
        conference = match.group(1)
        year = int(match.group(2))
        conf_key = f"{conference}_{year}"
        
        # Load CSV
        df = pd.read_csv(csv_file)
        
        # Check each paper
        missing_papers = []
        for idx, row in df.iterrows():
            paper = row.to_dict()
            
            # Check if PDF exists - try multiple folder naming conventions
            # Try PDFs/conference/year/ (main structure)
            conf_year_dir1 = Path('PDFs') / conference / str(year)
            # Try PDFs/CONFERENCE_YEAR/ (for manually downloaded papers)
            conf_year_dir2 = Path('PDFs') / f"{conference.upper()}_{year}"
            # Try PDFs/conference_year/ (alternative)
            conf_year_dir3 = Path('PDFs') / f"{conference}_{year}"
            
            safe_filename = sanitize_filename(paper['title']) + '.pdf'
            output_path1 = conf_year_dir1 / safe_filename
            output_path2 = conf_year_dir2 / safe_filename
            output_path3 = conf_year_dir3 / safe_filename
            
            if not output_path1.exists() and not output_path2.exists() and not output_path3.exists():
                missing_papers.append({
                    'conference': conference.upper(),
                    'year': year,
                    'title': paper['title'],
                    'link': paper['link']
                })
        
        if missing_papers:
            missing_by_conf[conf_key] = missing_papers
            missing_all.extend(missing_papers)
    
    return missing_by_conf, missing_all


def main():
    print("=" * 80)
    print("Missing Papers Report")
    print("=" * 80)
    
    missing_by_conf, missing_all = list_missing_papers()
    
    # Print summary
    print(f"\nTotal missing papers: {len(missing_all)}")
    print("\nBreakdown by conference:")
    for conf_key in sorted(missing_by_conf.keys()):
        papers = missing_by_conf[conf_key]
        print(f"  {conf_key:20s}: {len(papers)} papers")
    
    # Save to CSV
    if missing_all:
        output_file = 'missing_papers.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['conference', 'year', 'title', 'link'])
            writer.writeheader()
            writer.writerows(missing_all)
        
        print(f"\n✓ Saved detailed list to: {output_file}")
        
        # Print first 10 for reference
        print("\n" + "=" * 80)
        print("First 10 Missing Papers:")
        print("=" * 80)
        for idx, paper in enumerate(missing_all[:10], 1):
            print(f"\n{idx}. [{paper['conference']} {paper['year']}]")
            print(f"   Title: {paper['title']}")
            print(f"   Link:  {paper['link']}")
    else:
        print("\n✓ No missing papers! All downloads complete.")
    
    # Print statistics
    print("\n" + "=" * 80)
    print("Download Statistics")
    print("=" * 80)
    
    total_pdfs = len(list(Path('PDFs').rglob('*.pdf')))
    total_expected = sum([
        59 + 74 + 83,  # NeurIPS 2023, 2024, 2025
        50 + 60 + 65,  # ICML 2023, 2024, 2025
        41 + 51 + 41,  # ICLR 2023, 2024, 2025
        23 + 32 + 26,  # CVPR 2023, 2024, 2025
        30 + 34,       # ICCV 2023, 2025
        19 + 16,       # MICCAI 2024, 2025 (2023 requires subscription)
        20             # ECCV 2024
    ])
    
    print(f"Total PDFs downloaded:  {total_pdfs}")
    print(f"Total papers expected:  {total_expected} (excluding MICCAI 2023)")
    print(f"Missing papers:         {len(missing_all)}")
    print(f"Success rate:           {(total_pdfs/total_expected*100):.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()

