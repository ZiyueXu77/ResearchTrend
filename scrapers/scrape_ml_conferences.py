#!/usr/bin/env python3
"""
Script to extract federated learning papers from multiple ML conferences.
Supports NeurIPS, ICML, and ICLR across multiple years.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
from urllib.parse import urljoin
import sys
import os

# Configuration for different conferences
CONFERENCE_CONFIGS = {
    'neurips': {
        'name': 'NeurIPS',
        'base_url': 'https://neurips.cc',
        'url_template': {
            2025: 'https://neurips.cc/virtual/2025/loc/san-diego/papers.html?search=federated&layout=detail',
            2024: 'https://neurips.cc/virtual/2024/papers.html?search=federated',
            2023: 'https://neurips.cc/virtual/2023/papers.html?search=federated',
        },
        'paper_link_pattern': '/virtual/{year}/poster/'
    },
    'icml': {
        'name': 'ICML',
        'base_url': 'https://icml.cc',
        'url_template': {
            2025: 'https://icml.cc/virtual/2025/papers.html?search=federated',
            2024: 'https://icml.cc/virtual/2024/papers.html?search=federated',
            2023: 'https://icml.cc/virtual/2023/papers.html?search=federated',
        },
        'paper_link_pattern': '/virtual/{year}/poster/'
    },
    'iclr': {
        'name': 'ICLR',
        'base_url': 'https://iclr.cc',
        'url_template': {
            2025: 'https://iclr.cc/virtual/2025/papers.html?search=federated',
            2024: 'https://iclr.cc/virtual/2024/papers.html?search=federated',
            2023: 'https://iclr.cc/virtual/2023/papers.html?search=federated',
        },
        'paper_link_pattern': '/virtual/{year}/poster/'
    }
}


def count_papers_only(url, base_url, paper_link_pattern, search_term="federated"):
    """
    Quick check to count how many papers are available without fetching abstracts.
    
    Args:
        url: The URL to scrape
        base_url: The base URL for constructing absolute links
        paper_link_pattern: Pattern to identify paper links
        search_term: The search term to filter papers by
    
    Returns:
        Tuple of (filtered_papers_list, total_count, filtered_count)
    """
    print(f"Fetching from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return [], 0, 0
    
    soup = BeautifulSoup(response.content, 'html.parser')
    papers = []
    
    # Try to find paper links using the pattern
    paper_links = soup.find_all('a', href=lambda x: x and paper_link_pattern in str(x))
    
    total_count = len(paper_links)
    print(f"Found {total_count} total paper links")
    print(f"Filtering by search term: '{search_term}'")
    
    for idx, link in enumerate(paper_links):
        paper_url = urljoin(base_url, link.get('href'))
        title = link.get_text(strip=True)
        
        # Filter by search term (case-insensitive)
        if title and search_term.lower() in title.lower():
            papers.append({
                'title': title,
                'link': paper_url
            })
    
    filtered_count = len(papers)
    return papers, total_count, filtered_count


def get_paper_abstract(paper_url, headers):
    """
    Fetch the abstract from an individual paper page.
    
    Args:
        paper_url: URL of the paper page
        headers: HTTP headers to use
    
    Returns:
        Abstract text or "N/A" if not found
    """
    try:
        response = requests.get(paper_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract abstract
        abstract_elem = soup.find('div', class_=lambda x: x and 'abstract' in str(x).lower())
        
        if not abstract_elem:
            abstract_elem = soup.find('p', class_=lambda x: x and 'abstract' in str(x).lower())
        
        if not abstract_elem:
            # Look for text containing "Abstract"
            abstract_headers = soup.find_all(['h2', 'h3', 'h4', 'strong'], 
                                            string=lambda x: x and 'abstract' in x.lower())
            if abstract_headers:
                # Get the next sibling or parent's next sibling
                for header in abstract_headers:
                    next_elem = header.find_next_sibling(['p', 'div'])
                    if next_elem:
                        abstract_elem = next_elem
                        break
        
        if abstract_elem:
            abstract_text = abstract_elem.get_text(strip=True)
            # Remove redundant "Abstract" prefix if present
            if abstract_text.startswith("Abstract"):
                abstract_text = abstract_text[8:].strip()
            return abstract_text
        else:
            return "Abstract not found"
            
    except Exception as e:
        print(f"Error fetching abstract from {paper_url}: {e}")
        return "Error fetching abstract"


def save_to_csv(papers, conference, year, total_papers=0, federated_papers=0):
    """
    Save papers to a CSV file.
    
    Args:
        papers: List of paper dictionaries
        conference: Conference name (lowercase)
        year: Conference year
        total_papers: Total number of papers on the page
        federated_papers: Number of federated learning papers
    """
    if not papers:
        print("No papers to save!")
        return
    
    # Generate filename with metadata
    filename = f'{conference}_{year}_federated_learning_{total_papers}_{federated_papers}.csv'
    
    print(f"\nSaving {len(papers)} papers to {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'link', 'abstract']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    
    print(f"Successfully saved papers to {filename}")
    print(f"Filename contains: Total papers={total_papers}, Federated papers={federated_papers}")


def scrape_conference_year(conference, year):
    """
    Scrape federated learning papers for a specific conference and year.
    
    Args:
        conference: Conference name (lowercase: 'neurips', 'icml', 'iclr')
        year: Conference year
    
    Returns:
        Number of papers found
    """
    if conference not in CONFERENCE_CONFIGS:
        print(f"Error: Unknown conference '{conference}'")
        return 0
    
    config = CONFERENCE_CONFIGS[conference]
    
    if year not in config['url_template']:
        print(f"Error: Year {year} not configured for {config['name']}")
        return 0
    
    url = config['url_template'][year]
    paper_link_pattern = config['paper_link_pattern'].format(year=year)
    
    print("=" * 80)
    print(f"{config['name']} {year} - Federated Learning Papers")
    print("=" * 80)
    print()
    
    # Step 1: Count papers without fetching abstracts
    print("Step 1: Counting papers...")
    paper_list, total_papers, federated_papers = count_papers_only(
        url, config['base_url'], paper_link_pattern
    )
    
    if not paper_list:
        print(f"\n✗ No federated papers found for {config['name']} {year}")
        return 0
    
    print(f"\n✓ Found {federated_papers} federated learning papers out of {total_papers} total papers")
    
    # Step 2: Fetch abstracts for all papers
    print(f"\nStep 2: Fetching abstracts for {federated_papers} papers...")
    print("This may take a few minutes...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    papers = []
    for idx, paper_info in enumerate(paper_list, 1):
        print(f"[{idx}/{federated_papers}] {paper_info['title'][:60]}...")
        abstract = get_paper_abstract(paper_info['link'], headers)
        
        papers.append({
            'title': paper_info['title'],
            'link': paper_info['link'],
            'abstract': abstract
        })
        
        # Be polite and don't overwhelm the server
        time.sleep(0.5)
    
    # Save to CSV
    if papers:
        save_to_csv(papers, conference, year, total_papers, federated_papers)
        print(f"\n✓ Extraction complete for {config['name']} {year}!")
        return len(papers)
    else:
        print(f"\n✗ No papers extracted for {config['name']} {year}")
        return 0


def main():
    """Main function to orchestrate the scraping process."""
    
    # Define which conferences and years to scrape
    conferences_to_scrape = [
        ('neurips', [2023, 2024, 2025]),
        ('icml', [2023, 2024, 2025]),
        ('iclr', [2023, 2024, 2025]),
    ]
    
    total_papers_scraped = 0
    summary = []
    
    print("\n" + "=" * 80)
    print("Multi-Conference Federated Learning Papers Scraper")
    print("=" * 80)
    print()
    
    for conference, years in conferences_to_scrape:
        for year in years:
            try:
                count = scrape_conference_year(conference, year)
                summary.append((conference.upper(), year, count))
                total_papers_scraped += count
                
                # Add a delay between conferences to be respectful
                if count > 0:
                    print("\nWaiting 2 seconds before next conference...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"\n✗ Error scraping {conference.upper()} {year}: {e}")
                summary.append((conference.upper(), year, 0))
    
    # Print summary
    print("\n" + "=" * 80)
    print("SCRAPING SUMMARY")
    print("=" * 80)
    for conf, yr, count in summary:
        status = "✓" if count > 0 else "✗"
        print(f"{status} {conf} {yr}: {count} papers")
    
    print(f"\nTotal papers scraped: {total_papers_scraped}")
    print("=" * 80)


if __name__ == "__main__":
    main()

