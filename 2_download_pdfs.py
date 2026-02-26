#!/usr/bin/env python3
"""
Script to download PDFs of federated learning papers.
"""

import os
import re
import time
import random
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse


def setup_driver():
    """Set up Selenium Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def sanitize_filename(filename):
    """Sanitize filename to be filesystem-safe."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Trim to reasonable length (leaving room for .pdf)
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()


def search_openreview_by_title(driver, title, venue="NeurIPS.cc/2025/Conference"):
    """Search OpenReview for a paper by title and return PDF link.
    Uses the OpenReview API directly (no Selenium) to avoid being blocked.
    Tries api2 (v2) first, then falls back to api (v1), with retries.
    """
    search_title = title.replace(':', '').replace('?', '').strip()
    search_words = ' '.join(search_title.split()[:10])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    api_endpoints = [
        ("https://api2.openreview.net/notes/search",
         {'query': search_words, 'source': 'forum', 'group': venue, 'limit': 5}),
        ("https://api.openreview.net/notes/search",
         {'query': search_words, 'source': 'forum', 'group': venue, 'limit': 5}),
    ]

    max_retries = 3
    for api_url, params in api_endpoints:
        for attempt in range(max_retries):
            try:
                print(f"  → Searching OpenReview API ({api_url.split('//')[1].split('/')[0]}, attempt {attempt + 1})...")
                resp = requests.get(api_url, params=params, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                notes = data.get('notes', [])
                if notes:
                    paper_id = notes[0]['id']
                    pdf_url = f"https://openreview.net/pdf?id={paper_id}"
                    print(f"  → Found OpenReview paper ID: {paper_id}")
                    return pdf_url

                print(f"  ✗ No results found on OpenReview")
                return None
            except Exception as e:
                wait = 5 * (attempt + 1)
                print(f"  ⚠ API error: {e}")
                if attempt < max_retries - 1:
                    print(f"    Retrying in {wait}s...")
                    time.sleep(wait)
        print(f"  ⚠ All retries failed for {api_url.split('//')[1].split('/')[0]}, trying next endpoint...")

    print(f"  ✗ Could not reach OpenReview API")
    return None


def find_pdf_link_neurips(driver, paper_url, year=None, title=None):
    """Find PDF link for NeurIPS papers (year-specific logic)."""
    try:
        # Step 1: Load the paper page
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # NeurIPS 2025: Search OpenReview by title
        if year and year >= 2025:
            if not title:
                # Try to extract title from page
                title_elem = soup.find('h1') or soup.find('h2', class_='card-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if title:
                return search_openreview_by_title(driver, title, venue="NeurIPS.cc/2025/Conference")
            else:
                print(f"  ✗ Could not extract title for OpenReview search")
                return None
        
        # NeurIPS 2023-2024: Two-hop navigation through proceedings
        # Step 2: Find the first "Paper" link (leads to intermediate page)
        paper_link = None
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            if link_text == 'paper':
                paper_link = urljoin(paper_url, link['href'])
                print(f"  → Found Paper link: {paper_link}")
                break
        
        if not paper_link:
            print(f"  ✗ Could not find 'Paper' link on first page")
            return None
        
        # Step 3: Load the intermediate page
        driver.get(paper_link)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Step 4: Find the second "Paper" link (leads to PDF)
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link['href']
            if link_text == 'paper' or '.pdf' in href.lower():
                pdf_url = urljoin(paper_link, href)
                if '.pdf' in pdf_url.lower():
                    return pdf_url
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def find_pdf_link_icml(driver, paper_url, year=None):
    """Find PDF link for ICML papers (year-specific logic)."""
    try:
        # Step 1: Load the paper page
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # ICML 2025: Use OpenReview OR JMLR/PMLR
        if year and year >= 2025:
            # First try OpenReview link
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'openreview.net/forum' in href or 'openreview.net/pdf' in href:
                    openreview_link = href
                    print(f"  → Found OpenReview link: {openreview_link}")
                    
                    # If it's already a PDF link, return it
                    if '/pdf?' in openreview_link:
                        return openreview_link
                    
                    # Otherwise, load the forum page
                    driver.get(openreview_link)
                    time.sleep(2)
                    
                    soup2 = BeautifulSoup(driver.page_source, 'html.parser')
                    for link2 in soup2.find_all('a', href=True):
                        if '/pdf?' in link2['href']:
                            return urljoin('https://openreview.net', link2['href'])
            
            # If no OpenReview, try JMLR/PMLR link
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text(strip=True)
                
                if 'jmlr.org' in href or 'proceedings.mlr.press' in href:
                    print(f"  → Found JMLR/PMLR link: {href}")
                    
                    # Load the JMLR page
                    driver.get(href)
                    time.sleep(2)
                    
                    soup2 = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Look for PDF link on JMLR page
                    for link2 in soup2.find_all('a', href=True):
                        href2 = link2['href']
                        link_text2 = link2.get_text(strip=True)
                        
                        if '.pdf' in href2 or link_text2.upper() == 'PDF':
                            pdf_url = urljoin(href, href2)
                            if '.pdf' in pdf_url.lower():
                                return pdf_url
                    
                    break
            
            print(f"  ✗ Could not find OpenReview or JMLR link for ICML {year}")
            return None
        
        # ICML 2024: "Paper PDF" → "Download PDF"
        if year and year == 2024:
            # Find "Paper PDF" link
            paper_pdf_link = None
            for link in soup.find_all('a', href=True):
                link_text = link.get_text(strip=True)
                if 'paper pdf' in link_text.lower():
                    paper_pdf_link = urljoin(paper_url, link['href'])
                    print(f"  → Found 'Paper PDF' link: {paper_pdf_link}")
                    break
            
            if not paper_pdf_link:
                print(f"  ✗ Could not find 'Paper PDF' link")
                return None
            
            # Load the Paper PDF page
            driver.get(paper_pdf_link)
            time.sleep(2)
            
            soup2 = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find "Download PDF" link
            for link in soup2.find_all('a', href=True):
                link_text = link.get_text(strip=True)
                href = link['href']
                if 'download pdf' in link_text.lower() or '.pdf' in href.lower():
                    pdf_url = urljoin(paper_pdf_link, href)
                    if '.pdf' in pdf_url.lower():
                        return pdf_url
            
            print(f"  ✗ Could not find 'Download PDF' link")
            return None
        
        # ICML 2023: Direct PDF link to proceedings.mlr.press OR JMLR
        # First try direct PDF link
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            href = link['href']
            
            # Look for "PDF" link or direct .pdf link
            if link_text == 'PDF' or '.pdf' in href.lower():
                pdf_url = urljoin(paper_url, href)
                if '.pdf' in pdf_url.lower():
                    return pdf_url
        
        # If no direct PDF, try JMLR link
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True)
            
            if 'jmlr.org' in href or 'proceedings.mlr.press' in href:
                # Skip generic proceedings homepage links
                if href == 'https://proceedings.mlr.press' or href == 'https://proceedings.mlr.press/':
                    continue
                    
                print(f"  → Found JMLR/PMLR link: {href}")
                
                # Load the JMLR page
                driver.get(href)
                time.sleep(2)
                
                soup2 = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Look for PDF link on JMLR page
                for link2 in soup2.find_all('a', href=True):
                    href2 = link2['href']
                    link_text2 = link2.get_text(strip=True)
                    
                    if '.pdf' in href2 or link_text2.upper() == 'PDF':
                        pdf_url = urljoin(href, href2)
                        if '.pdf' in pdf_url.lower():
                            return pdf_url
                
                break
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def find_pdf_link_iclr(driver, paper_url, year=None, title=None):
    """Find PDF link for ICLR papers (uses OpenReview)."""
    try:
        # ICLR 2026+: Try API first, fall back to iclr.cc virtual page
        if year and year >= 2026:
            if title:
                result = search_openreview_by_title(driver, title, venue=f"ICLR.cc/{year}/Conference")
                if result:
                    return result
                print(f"  → API failed, falling back to iclr.cc virtual page...")

        # Step 1: Load the paper page
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Step 2: Find OpenReview link
        openreview_link = None
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            href = link['href']
            
            if 'openreview.net/forum' in href:
                openreview_link = href
                print(f"  → Found OpenReview link: {openreview_link}")
                break
        
        if not openreview_link:
            print(f"  ✗ Could not find OpenReview link")
            return None
        
        # Step 3: Load OpenReview page
        driver.get(openreview_link)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Step 4: Find PDF link on OpenReview (format: /pdf?id=...)
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            if '/pdf?' in href:
                pdf_url = urljoin('https://openreview.net', href)
                return pdf_url
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def find_pdf_link_cvpr_iccv(driver, paper_url):
    """Find PDF link for CVPR/ICCV papers (CVF Open Access)."""
    try:
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # CVF: Direct PDF link in the page
        pdf_link = soup.find('a', string=re.compile('pdf', re.I))
        if pdf_link:
            return urljoin(paper_url, pdf_link['href'])
        
        # Look for links ending in .pdf
        for link in soup.find_all('a', href=True):
            if link['href'].endswith('.pdf'):
                return urljoin(paper_url, link['href'])
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def find_pdf_link_miccai(driver, paper_url, year=None):
    """Find PDF link for MICCAI papers (year-specific logic)."""
    try:
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # MICCAI 2023: Papers are behind Springer paywall (subscription required)
        if year and year == 2023:
            print(f"  ⚠ MICCAI 2023 papers require Springer subscription (skipping)")
            print(f"    Papers available at: https://link.springer.com/conference/miccai")
            return None
        
        # MICCAI 2024+: Direct PDF link
        pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            return urljoin(paper_url, pdf_link['href'])
        
        # Look for "Download" or "PDF" links
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if 'pdf' in text or 'download' in text:
                href = link['href']
                if '.pdf' in href:
                    return urljoin(paper_url, href)
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def find_pdf_link_eccv(driver, paper_url):
    """Find PDF link for ECCV papers."""
    try:
        driver.get(paper_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # ECCV: Look for PDF link in the virtual site
        pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            return urljoin(paper_url, pdf_link['href'])
        
        # Look for paper links
        for link in soup.find_all('a', href=True):
            if 'paper' in link.get('href', '').lower() and '.pdf' in link.get('href', '').lower():
                return urljoin(paper_url, link['href'])
        
        return None
    except Exception as e:
        print(f"  Error finding PDF link: {e}")
        return None


def download_pdf(pdf_url, output_path, timeout=30):
    """Download PDF from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(pdf_url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check if it's actually a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not pdf_url.endswith('.pdf'):
            print(f"  Warning: Content type is {content_type}, might not be a PDF")
        
        # Write to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file size
        file_size = os.path.getsize(output_path)
        if file_size < 1000:  # Less than 1KB, probably not a real PDF
            os.remove(output_path)
            return False
        
        return True
        
    except Exception as e:
        print(f"  Error downloading PDF: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def load_missing_papers(missing_csv='PDFs/missing_papers.csv'):
    """Load known missing papers to skip during download."""
    missing = set()
    if os.path.exists(missing_csv):
        df = pd.read_csv(missing_csv)
        for _, row in df.iterrows():
            missing.add((row['conference'].upper(), int(row['year']), row['title']))
    return missing


_MISSING_PAPERS = None

def is_known_missing(conference, year, title):
    """Check if a paper is in the known-missing list."""
    global _MISSING_PAPERS
    if _MISSING_PAPERS is None:
        _MISSING_PAPERS = load_missing_papers()
    return (conference.upper(), int(year), title) in _MISSING_PAPERS


def process_paper(paper, conference, year, output_base_dir, driver):
    """
    Process a single paper: find PDF link and download.
    
    Args:
        paper: Dictionary with title, link, abstract
        conference: Conference name (neurips, icml, etc.)
        year: Conference year (2023, 2024, 2025)
        output_base_dir: Base directory for PDFs
        driver: Selenium driver
    
    Returns:
        True if successful, False otherwise
    """
    title = paper['title']
    link = paper['link']
    
    if is_known_missing(conference, year, title):
        print(f"\n[{conference.upper()} {year}] {title[:60]}...")
        print(f"  ⚠ Skipping (known missing)")
        return False
    
    print(f"\n[{conference.upper()} {year}] {title[:60]}...")
    print(f"  Paper URL: {link}")
    
    # Create output directory (organized by conference and year)
    conf_year_dir = Path(output_base_dir) / conference / str(year)
    conf_year_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_filename = sanitize_filename(title) + '.pdf'
    output_path = conf_year_dir / safe_filename
    
    # Skip if already downloaded
    if output_path.exists():
        print(f"  ✓ Already exists: {output_path}")
        return True
    
    # Find PDF link based on conference and year
    print(f"  Finding PDF link...")
    pdf_url = None
    
    if 'neurips.cc' in link:
        pdf_url = find_pdf_link_neurips(driver, link, year=year, title=title)
    elif 'icml.cc' in link:
        pdf_url = find_pdf_link_icml(driver, link, year=year)
    elif 'iclr.cc' in link:
        pdf_url = find_pdf_link_iclr(driver, link, year=year, title=title)
    elif 'openaccess.thecvf.com' in link:
        pdf_url = find_pdf_link_cvpr_iccv(driver, link)
    elif 'miccai.org' in link or 'papers.miccai.org' in link:
        pdf_url = find_pdf_link_miccai(driver, link, year=year)
    elif 'eccv.ecva.net' in link:
        pdf_url = find_pdf_link_eccv(driver, link)
    else:
        print(f"  ⚠ Unknown conference site: {link}")
        return False
    
    if not pdf_url:
        print(f"  ✗ Could not find PDF link")
        return False
    
    print(f"  PDF URL: {pdf_url}")
    print(f"  Downloading to: {output_path}")
    
    # Download PDF
    success = download_pdf(pdf_url, output_path)
    
    if success:
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"  ✓ Downloaded successfully ({file_size:.2f} MB)")
        return True
    else:
        print(f"  ✗ Download failed")
        return False


def test_download_one_per_conference_year():
    """Test downloading one paper from each conference-year combination."""
    print("=" * 80)
    print("Testing PDF Download - One Paper Per Conference-Year")
    print("=" * 80)
    
    # Define test papers (first paper from each conference-year)
    test_papers = {
        'neurips_2023': 'Raw/neurips_2023_federated_learning_3585_59.csv',
        'neurips_2024': 'Raw/neurips_2024_federated_learning_4538_74.csv',
        'neurips_2025': 'Raw/neurips_2025_federated_learning_5858_83.csv',
        'icml_2023': 'Raw/icml_2023_federated_learning_1865_50.csv',
        'icml_2024': 'Raw/icml_2024_federated_learning_2635_60.csv',
        'icml_2025': 'Raw/icml_2025_federated_learning_3339_65.csv',
        'iclr_2023': 'Raw/iclr_2023_federated_learning_1585_41.csv',
        'iclr_2024': 'Raw/iclr_2024_federated_learning_2297_51.csv',
        'iclr_2025': 'Raw/iclr_2025_federated_learning_3827_41.csv',
        'cvpr_2023': 'Raw/cvpr_2023_federated_learning_2353_23.csv',
        'cvpr_2024': 'Raw/cvpr_2024_federated_learning_2716_32.csv',
        'cvpr_2025': 'Raw/cvpr_2025_federated_learning_2871_26.csv',
        'iccv_2023': 'Raw/iccv_2023_federated_learning_2156_30.csv',
        'iccv_2025': 'Raw/iccv_2025_federated_learning_2701_34.csv',
        'miccai_2023': 'Raw/miccai_2023_federated_learning_733_13.csv',
        'miccai_2024': 'Raw/miccai_2024_federated_learning_859_19.csv',
        'miccai_2025': 'Raw/miccai_2025_federated_learning_1030_16.csv',
        'eccv_2024': 'Raw/eccv_2024_federated_learning_2387_20.csv',
        'iclr_2026': 'Raw/iclr_2026_federated_learning_5416_48.csv',
    }
    
    output_dir = 'PDFs'
    driver = setup_driver()
    
    results = {}
    
    try:
        for conf_key, csv_file in test_papers.items():
            parts = conf_key.split('_')
            conference = parts[0]
            year = int(parts[1])
            
            if not os.path.exists(csv_file):
                print(f"\n⚠ Skipping {conf_key}: {csv_file} not found")
                results[conf_key] = 'not_found'
                continue
            
            # Load CSV and get first paper
            df = pd.read_csv(csv_file)
            if len(df) == 0:
                print(f"\n⚠ Skipping {conf_key}: No papers in {csv_file}")
                results[conf_key] = 'empty'
                continue
            
            paper = df.iloc[0].to_dict()
            
            # Skip if this test paper's PDF already exists
            conf_year_dir = Path(output_dir) / conference / str(year)
            safe_filename = sanitize_filename(paper['title']) + '.pdf'
            if (conf_year_dir / safe_filename).exists():
                print(f"\n✓ Skipping {conf_key}: test paper already downloaded")
                results[conf_key] = 'already_done'
                continue
            
            # Try to download
            success = process_paper(paper, conference, year, output_dir, driver)
            results[conf_key] = 'success' if success else 'failed'
            
            wait = random.uniform(60, 90)
            print(f"  Waiting {wait:.0f}s before next paper...")
            time.sleep(wait)
    
    finally:
        driver.quit()
    
    # Print summary
    print("\n" + "=" * 80)
    print("Download Test Summary")
    print("=" * 80)
    
    # Group by conference
    conferences = {}
    for conf_key, result in results.items():
        conf = conf_key.split('_')[0]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append((conf_key, result))
    
    for conf in sorted(conferences.keys()):
        print(f"\n{conf.upper()}:")
        for conf_key, result in conferences[conf]:
            status = "✓" if result == 'success' else "✗"
            print(f"  {status} {conf_key:20s}: {result}")
    print()


def download_all_papers():
    """Download PDFs for all papers in all CSV files."""
    import glob
    
    print("=" * 80)
    print("Downloading PDFs for All Papers")
    print("=" * 80)
    
    # Find all CSV files
    csv_files = glob.glob('Raw/*_federated_learning_*.csv')
    csv_files = [f for f in csv_files if '_categorized' not in f]
    csv_files = sorted(csv_files)
    
    output_dir = 'PDFs'
    driver = setup_driver()
    
    total_papers = 0
    successful_downloads = 0
    failed_downloads = 0
    skipped_downloads = 0
    
    try:
        for csv_file in csv_files:
            # Parse conference and year from filename
            # Format: conference_year_federated_learning_total_count.csv
            match = re.match(r'(\w+)_(\d{4})_federated_learning_', os.path.basename(csv_file))
            if not match:
                print(f"\n⚠ Skipping {csv_file}: Could not parse filename")
                continue
            
            conference = match.group(1)
            year = int(match.group(2))
            
            # Load CSV
            df = pd.read_csv(csv_file)
            total_papers += len(df)
            
            # Skip if conference-year folder already has all PDFs
            conf_year_dir = Path(output_dir) / conference / str(year)
            if conf_year_dir.exists():
                existing_pdfs = list(conf_year_dir.glob('*.pdf'))
                if len(existing_pdfs) >= len(df):
                    skipped_downloads += len(df)
                    print(f"\n✓ Skipping {conference.upper()} {year}: all {len(df)} papers already downloaded ({len(existing_pdfs)} PDFs found)")
                    continue
            
            print(f"\n{'='*80}")
            print(f"{conference.upper()} {year}")
            print(f"{'='*80}")
            print(f"Processing {len(df)} papers from {csv_file}")
            
            # Process each paper
            for idx, row in df.iterrows():
                paper = row.to_dict()
                
                # Check if already exists
                conf_year_dir = Path(output_dir) / conference / str(year)
                safe_filename = sanitize_filename(paper['title']) + '.pdf'
                output_path = conf_year_dir / safe_filename
                
                if output_path.exists():
                    skipped_downloads += 1
                    print(f"[{idx+1}/{len(df)}] ✓ Already exists: {paper['title'][:50]}...")
                    continue
                
                success = process_paper(paper, conference, year, output_dir, driver)
                
                if success:
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                
                wait = random.uniform(60, 90)
                print(f"  Waiting {wait:.0f}s before next paper...")
                time.sleep(wait)
    
    finally:
        driver.quit()
    
    # Print final summary
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE - Final Summary")
    print("=" * 80)
    print(f"Total papers:          {total_papers}")
    print(f"Successfully downloaded: {successful_downloads}")
    print(f"Failed downloads:       {failed_downloads}")
    print(f"Already existed:        {skipped_downloads}")
    print(f"Success rate:           {(successful_downloads/(successful_downloads+failed_downloads)*100 if (successful_downloads+failed_downloads) > 0 else 0):.1f}%")
    print()


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        download_all_papers()
    else:
        test_download_one_per_conference_year()


if __name__ == "__main__":
    main()

