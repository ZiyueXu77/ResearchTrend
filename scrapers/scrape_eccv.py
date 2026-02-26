#!/usr/bin/env python3
"""
Script to scrape ECCV federated learning papers using Selenium for JavaScript rendering.
"""

import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re


def setup_driver():
    """Set up Selenium Chrome driver with headless options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrape_eccv_year(year, search_term="federated"):
    """
    Scrape ECCV papers for a given year using Selenium.
    
    Args:
        year: Conference year (2024, 2022, 2020, etc.)
        search_term: Search term to filter papers
    
    Returns:
        List of paper dictionaries with title, link, and abstract
    """
    print("=" * 80)
    print(f"ECCV {year} - Federated Learning Papers")
    print("=" * 80)
    
    # Use direct search URL to filter papers
    url = f"https://eccv.ecva.net/virtual/{year}/papers.html?search={search_term}"
    
    # Total paper counts for ECCV (hardcoded from conference statistics)
    TOTAL_PAPERS = {
        2024: 2387,
        2022: 1645,
        2020: 1360
    }
    total_papers = TOTAL_PAPERS.get(year, 0)
    
    print(f"\nStep 1: Loading filtered papers (search='{search_term}')...")
    print(f"URL: {url}")
    print(f"Total ECCV {year} papers: {total_papers}")
    
    driver = setup_driver()
    
    try:
        # Load the page with search filter
        driver.get(url)
        
        # Wait for content to load
        print("Waiting for filtered results to load...")
        time.sleep(5)  # Initial wait for JavaScript to execute
        
        # Wait for paper elements to appear
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
            )
            print("✓ Page loaded successfully")
        except:
            print("⚠ Timeout waiting for papers, trying anyway...")
        
        # Get page source after JavaScript rendering
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find all paper titles (already filtered by search)
        paper_titles = soup.find_all('h5', class_='card-title')
        federated_count = len(paper_titles)
        
        print(f"✓ Found {federated_count} federated learning papers out of {total_papers} total papers")
        
        # Extract paper information
        filtered_papers = []
        
        print(f"\nStep 2: Extracting paper information...")
        
        for title_elem in paper_titles:
            title = title_elem.get_text(strip=True)
            
            # Get paper link - look for link in the same card
            paper_link = ""
            card = title_elem.find_parent('div', class_=re.compile('card'))
            if card:
                link_elem = card.find('a', href=re.compile('/virtual/'))
                if link_elem:
                    href = link_elem.get('href')
                    if href.startswith('http'):
                        paper_link = href
                    else:
                        paper_link = f"https://eccv.ecva.net{href}"
            
            filtered_papers.append({
                'title': title,
                'link': paper_link,
                'abstract': 'N/A'  # Will fetch later
            })
        
        if len(filtered_papers) == 0:
            print("No papers found. Saving page source for debugging...")
            with open(f'eccv_{year}_debug.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"Saved debug HTML to eccv_{year}_debug.html")
            driver.quit()
            return []
        
        # Step 3: Fetch abstracts
        print(f"\nStep 3: Fetching abstracts for {federated_count} papers...")
        print("This may take a few minutes...\n")
        
        for idx, paper in enumerate(filtered_papers, 1):
            print(f"[{idx}/{len(filtered_papers)}] {paper['title'][:60]}...")
            
            if not paper['link']:
                paper['abstract'] = "Link not found"
                continue
            
            try:
                # Load paper page
                driver.get(paper['link'])
                time.sleep(2)  # Wait for page load
                
                # Get abstract
                paper_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Try different methods to find abstract
                abstract_text = "Abstract not found"
                
                # Method 1: Look for abstract in div/p with class containing 'abstract'
                abstract_elem = paper_soup.find(['div', 'p'], class_=re.compile('abstract', re.I))
                if abstract_elem:
                    abstract_text = abstract_elem.get_text(strip=True)
                    if abstract_text.lower().startswith('abstract'):
                        abstract_text = abstract_text[8:].strip()
                
                # Method 2: Look for abstract in text
                if abstract_text == "Abstract not found":
                    page_text = paper_soup.get_text()
                    abstract_match = re.search(r'Abstract[:\s]+(.*?)(?=\n\s*\n|$)', page_text, re.IGNORECASE | re.DOTALL)
                    if abstract_match:
                        abstract_text = abstract_match.group(1).strip()
                        abstract_text = ' '.join(abstract_text.split())
                        if len(abstract_text) > 50:
                            abstract_text = abstract_text[:1000]  # Limit length
                
                paper['abstract'] = abstract_text
                
            except Exception as e:
                print(f"  Error fetching abstract: {e}")
                paper['abstract'] = "Error fetching abstract"
        
        return filtered_papers, total_papers
        
    finally:
        driver.quit()


def save_to_csv(papers, year, total_papers):
    """Save papers to CSV file."""
    if not papers:
        print("No papers to save.")
        return None
    
    filename = f"eccv_{year}_federated_learning_{total_papers}_{len(papers)}.csv"
    
    print(f"\nSaving {len(papers)} papers to {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'link', 'abstract']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    
    print(f"Successfully saved papers to {filename}")
    print(f"Filename contains: Total papers={total_papers}, Federated papers={len(papers)}")
    
    return filename


def scrape_eccv_all_years():
    """Scrape ECCV for all available years."""
    # ECCV is biennial (every 2 years)
    years = [2024, 2022]  # 2020 might not have virtual site
    
    for year in years:
        try:
            papers, total_papers = scrape_eccv_year(year)
            
            if papers:
                save_to_csv(papers, year, total_papers)
            
            print(f"\n✓ Extraction complete for ECCV {year}!\n")
            
        except Exception as e:
            print(f"Error scraping ECCV {year}: {e}")
            continue


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1:
        # Scrape specific year
        year = int(sys.argv[1])
        papers, total_papers = scrape_eccv_year(year)
        
        if papers:
            save_to_csv(papers, year, total_papers)
    else:
        # Scrape all years
        scrape_eccv_all_years()


if __name__ == "__main__":
    main()

