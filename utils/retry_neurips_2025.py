#!/usr/bin/env python3
"""
Script to retry downloading NeurIPS 2025 papers from OpenReview with rate limiting.
"""

import csv
import time
import sys
from pathlib import Path

# Import from existing download script
from download_pdfs import setup_driver, process_paper


def retry_neurips_2025():
    """Retry downloading all missing NeurIPS 2025 papers with delays."""
    
    # Read missing papers
    missing_file = Path('missing_papers.csv')
    if not missing_file.exists():
        print("Error: missing_papers.csv not found")
        return
    
    # Filter for NeurIPS 2025
    neurips_2025_papers = []
    with open(missing_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('conference') == 'NEURIPS' and row.get('year') == '2025':
                neurips_2025_papers.append({
                    'title': row['title'],
                    'link': row['link'],
                    'abstract': 'N/A'
                })
    
    total = len(neurips_2025_papers)
    print(f"Found {total} NeurIPS 2025 papers to retry")
    print("=" * 80)
    print()
    
    # Setup Selenium driver
    driver = setup_driver()
    
    # Track results
    success_count = 0
    failed_papers = []
    
    try:
        for idx, paper in enumerate(neurips_2025_papers, 1):
            print(f"\n[{idx}/{total}] Attempting: {paper['title'][:80]}...")
            
            # Add delay between requests (10 seconds to be more conservative)
            if idx > 1:  # No delay for first paper
                print(f"  ⏳ Waiting 10 seconds to avoid rate limiting...")
                time.sleep(10)
            
            # Attempt download with retry on connection error
            max_retries = 3
            retry_delay = 30  # 30 seconds on connection error
            success = False
            
            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"  ⚠️  Retry attempt {attempt}/{max_retries-1} after {retry_delay}s delay...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
                try:
                    success = process_paper(paper, 'neurips', 2025, 'papers_pdf', driver)
                    if success:
                        break  # Success, no need to retry
                    elif attempt < max_retries - 1:
                        # Failed but not connection error, might be worth retrying
                        print(f"  ⚠️  Download failed, will retry...")
                except Exception as e:
                    if "ERR_CONNECTION_REFUSED" in str(e):
                        print(f"  ⚠️  Connection refused, will retry with longer delay...")
                        if attempt == max_retries - 1:
                            print(f"  ✗ Max retries reached, skipping...")
                    else:
                        print(f"  ⚠️  Error: {e}")
                        if attempt == max_retries - 1:
                            break
            
            if success:
                success_count += 1
                print(f"  ✓ Success ({success_count}/{idx})")
            else:
                failed_papers.append(paper)
                print(f"  ✗ Failed")
            
            # Progress summary
            if idx % 10 == 0:
                print()
                print("-" * 80)
                print(f"Progress: {idx}/{total} papers processed")
                print(f"Success rate: {success_count}/{idx} ({100*success_count/idx:.1f}%)")
                print("-" * 80)
                print()
    
    finally:
        driver.quit()
    
    # Final summary
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total attempted: {total}")
    print(f"✓ Successfully downloaded: {success_count}")
    print(f"✗ Failed: {len(failed_papers)}")
    print(f"Success rate: {100*success_count/total:.1f}%")
    
    if failed_papers:
        print()
        print("Still failed papers:")
        for paper in failed_papers:
            print(f"  - {paper['title'][:70]}...")
    
    print()
    print(f"Total PDFs now in papers_pdf/neurips/2025/:")
    neurips_2025_dir = Path('papers_pdf/neurips/2025')
    if neurips_2025_dir.exists():
        pdf_count = len(list(neurips_2025_dir.glob('*.pdf')))
        print(f"  {pdf_count} PDFs")


if __name__ == '__main__':
    print("NeurIPS 2025 PDF Retry Script")
    print("=" * 80)
    print("This will attempt to download all missing NeurIPS 2025 papers")
    print("with 5-second delays between requests to avoid rate limiting.")
    print()
    
    retry_neurips_2025()

