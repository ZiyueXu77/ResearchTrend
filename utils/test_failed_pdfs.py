#!/usr/bin/env python3
"""
Test script to verify fixes for failed PDF downloads.
"""

import sys
sys.path.insert(0, '.')

from download_pdfs import setup_driver, process_paper
import pandas as pd
import time

def test_failed_cases():
    """Test only the previously failed cases."""
    print("=" * 80)
    print("Testing Failed PDF Downloads")
    print("=" * 80)
    
    # Define the failed cases
    test_cases = [
        ('neurips_2025_federated_learning_5858_83.csv', 'neurips', 2025),
        ('icml_2024_federated_learning_2635_60.csv', 'icml', 2024),
        ('icml_2025_federated_learning_3339_65.csv', 'icml', 2025),
        ('miccai_2023_federated_learning_733_13.csv', 'miccai', 2023),
    ]
    
    output_dir = 'papers_pdf'
    driver = setup_driver()
    
    results = {}
    
    try:
        for csv_file, conference, year in test_cases:
            print(f"\n{'='*80}")
            print(f"Testing: {conference.upper()} {year}")
            print(f"{'='*80}")
            
            # Load CSV and get first paper
            try:
                df = pd.read_csv(csv_file)
                if len(df) == 0:
                    print(f"⚠ No papers in {csv_file}")
                    results[f"{conference}_{year}"] = 'empty'
                    continue
                
                paper = df.iloc[0].to_dict()
                
                # Try to download
                success = process_paper(paper, conference, year, output_dir, driver)
                results[f"{conference}_{year}"] = 'success' if success else 'failed'
                
                time.sleep(2)  # Be respectful to servers
                
            except Exception as e:
                print(f"✗ Error: {e}")
                results[f"{conference}_{year}"] = 'error'
    
    finally:
        driver.quit()
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    for case, result in results.items():
        status = "✓" if result == 'success' else "✗"
        print(f"  {status} {case:20s}: {result}")
    
    # Overall result
    all_success = all(r == 'success' for r in results.values())
    print("\n" + ("🎉 All tests passed!" if all_success else "⚠ Some tests failed"))
    print()

if __name__ == "__main__":
    test_failed_cases()

