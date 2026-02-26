#!/usr/bin/env python3
"""
Script to retry failed PDF downloads with better rate limiting.
"""

import sys
sys.path.insert(0, '.')

from download_pdfs import setup_driver, sanitize_filename, process_paper
import pandas as pd
import glob
import re
from pathlib import Path
import time

def find_missing_papers():
    """Find all papers that don't have downloaded PDFs."""
    missing_papers = []
    
    # Find all CSV files
    csv_files = glob.glob('*_federated_learning_*.csv')
    csv_files = [f for f in csv_files if '_categorized' not in f]
    csv_files = sorted(csv_files)
    
    for csv_file in csv_files:
        # Parse conference and year
        match = re.match(r'(\w+)_(\d{4})_federated_learning_', csv_file)
        if not match:
            continue
        
        conference = match.group(1)
        year = int(match.group(2))
        
        # Skip MICCAI 2023 (subscription required)
        if conference == 'miccai' and year == 2023:
            continue
        
        # Load CSV
        df = pd.read_csv(csv_file)
        
        # Check each paper
        for idx, row in df.iterrows():
            paper = row.to_dict()
            
            # Check if PDF exists
            conf_year_dir = Path('papers_pdf') / conference / str(year)
            safe_filename = sanitize_filename(paper['title']) + '.pdf'
            output_path = conf_year_dir / safe_filename
            
            if not output_path.exists():
                missing_papers.append({
                    'conference': conference,
                    'year': year,
                    'paper': paper,
                    'csv_file': csv_file,
                    'idx': idx
                })
    
    return missing_papers


def retry_downloads_with_rate_limiting():
    """Retry failed downloads with better rate limiting."""
    print("=" * 80)
    print("Retrying Failed PDF Downloads")
    print("=" * 80)
    
    # Find missing papers
    print("\nScanning for missing papers...")
    missing_papers = find_missing_papers()
    
    if not missing_papers:
        print("✓ No missing papers found! All downloads complete.")
        return
    
    print(f"Found {len(missing_papers)} missing papers")
    
    # Group by conference
    by_conference = {}
    for item in missing_papers:
        conf_key = f"{item['conference']}_{item['year']}"
        if conf_key not in by_conference:
            by_conference[conf_key] = []
        by_conference[conf_key].append(item)
    
    print("\nMissing papers by conference:")
    for conf_key, items in sorted(by_conference.items()):
        print(f"  {conf_key:20s}: {len(items)} papers")
    
    # Proceed automatically
    print(f"\n{'='*80}")
    print(f"Starting retry of {len(missing_papers)} papers...")
    print("=" * 80)
    
    # Setup driver
    driver = setup_driver()
    
    successful = 0
    failed = 0
    
    try:
        for idx, item in enumerate(missing_papers, 1):
            conf_key = f"{item['conference'].upper()} {item['year']}"
            print(f"\n[{idx}/{len(missing_papers)}] {conf_key}: {item['paper']['title'][:50]}...")
            
            # Special handling for OpenReview-based conferences
            # Add extra delay to avoid rate limiting
            if item['conference'] in ['neurips', 'icml'] and item['year'] >= 2025:
                if idx > 1:  # Skip delay for first paper
                    print("  ⏱  Waiting 5 seconds to avoid rate limiting...")
                    time.sleep(5)
            
            # Retry with longer timeout
            success = False
            max_retries = 3
            
            for retry in range(max_retries):
                try:
                    success = process_paper(
                        item['paper'], 
                        item['conference'], 
                        item['year'], 
                        'papers_pdf', 
                        driver
                    )
                    
                    if success:
                        successful += 1
                        break
                    else:
                        if retry < max_retries - 1:
                            print(f"  ⟳ Retry {retry + 1}/{max_retries - 1}...")
                            time.sleep(3)
                        
                except Exception as e:
                    if "ERR_CONNECTION_REFUSED" in str(e) and retry < max_retries - 1:
                        print(f"  ⟳ Connection error, retry {retry + 1}/{max_retries - 1}...")
                        time.sleep(5)
                    else:
                        print(f"  ✗ Error: {e}")
                        break
            
            if not success:
                failed += 1
            
            # Regular delay between papers
            if idx < len(missing_papers):
                time.sleep(2)
    
    finally:
        driver.quit()
    
    # Final summary
    print("\n" + "=" * 80)
    print("RETRY COMPLETE - Summary")
    print("=" * 80)
    print(f"Total attempted:        {len(missing_papers)}")
    print(f"Successfully downloaded: {successful}")
    print(f"Still failed:            {failed}")
    print(f"Success rate:            {(successful/len(missing_papers)*100 if len(missing_papers) > 0 else 0):.1f}%")
    
    # Count total downloaded now
    total_pdfs = len(list(Path('papers_pdf').rglob('*.pdf')))
    print(f"\nTotal PDFs now:          {total_pdfs}")
    print("=" * 80)


if __name__ == "__main__":
    retry_downloads_with_rate_limiting()

