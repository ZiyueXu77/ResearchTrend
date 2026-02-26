#!/usr/bin/env python3
"""
Script to add OpenReview PDF links to missing_papers.csv for NeurIPS 2025 papers.
"""

import csv
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus


def setup_driver():
    """Setup Selenium WebDriver."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    return driver


def search_openreview_for_paper(driver, title):
    """Search OpenReview for a paper and return the PDF link."""
    try:
        # Search OpenReview
        search_query = quote_plus(title)
        search_url = f"https://openreview.net/search?term={search_query}&group=NeurIPS/2025/Conference"
        
        driver.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        # Look for the first search result
        results = driver.find_elements(By.CSS_SELECTOR, "li.note")
        
        if results:
            # Get the first result's link
            link_element = results[0].find_element(By.CSS_SELECTOR, "h4 a")
            paper_url = link_element.get_attribute('href')
            
            # Extract paper ID from URL (e.g., https://openreview.net/forum?id=XXXXX)
            if 'id=' in paper_url:
                paper_id = paper_url.split('id=')[1].split('&')[0]
                pdf_url = f"https://openreview.net/pdf?id={paper_id}"
                return pdf_url, paper_id
        
        return None, None
    
    except Exception as e:
        print(f"    Error: {e}")
        return None, None


def add_openreview_links():
    """Add OpenReview PDF links to missing_papers.csv for NeurIPS 2025 papers."""
    
    # Read missing papers
    missing_file = Path('missing_papers.csv')
    if not missing_file.exists():
        print("Error: missing_papers.csv not found")
        return
    
    papers = []
    with open(missing_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            papers.append(row)
    
    # Filter NeurIPS 2025 papers
    neurips_papers = [p for p in papers if p.get('conference') == 'NEURIPS' and p.get('year') == '2025']
    
    print(f"Found {len(neurips_papers)} NeurIPS 2025 papers to process")
    print("=" * 80)
    
    # Setup Selenium
    driver = setup_driver()
    
    # Process each paper
    updated_count = 0
    for idx, paper in enumerate(papers, 1):
        if paper.get('conference') == 'NEURIPS' and paper.get('year') == '2025':
            title = paper['title']
            print(f"\n[{idx}] {title[:70]}...")
            
            # Add delay to avoid rate limiting
            if updated_count > 0:
                print("    Waiting 3 seconds...")
                time.sleep(3)
            
            pdf_url, paper_id = search_openreview_for_paper(driver, title)
            
            if pdf_url:
                paper['pdf_link'] = pdf_url
                print(f"    ✓ Found: {pdf_url}")
                updated_count += 1
            else:
                paper['pdf_link'] = 'NOT_FOUND'
                print(f"    ✗ Not found")
    
    driver.quit()
    
    # Write back to CSV
    fieldnames = ['conference', 'year', 'title', 'link', 'pdf_link']
    with open(missing_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            # Add pdf_link column if it doesn't exist
            if 'pdf_link' not in paper:
                paper['pdf_link'] = ''
            writer.writerow(paper)
    
    print()
    print("=" * 80)
    print(f"✓ Updated {updated_count} NeurIPS 2025 papers with OpenReview PDF links")
    print(f"✓ Saved to missing_papers.csv")


if __name__ == '__main__':
    print("Adding OpenReview PDF Links")
    print("=" * 80)
    add_openreview_links()


