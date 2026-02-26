#!/usr/bin/env python3
"""
Script to extract federated learning papers from major Computer Vision conferences.
Supports CVPR, ICCV, ECCV, and MICCAI across multiple years.
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
    'cvpr': {
        'name': 'CVPR',
        'base_url': 'https://openaccess.thecvf.com',
        'url_template': {
            2025: 'https://openaccess.thecvf.com/CVPR2025?day=all',
            2024: 'https://openaccess.thecvf.com/CVPR2024?day=all',
            2023: 'https://openaccess.thecvf.com/CVPR2023?day=all',
        },
        'paper_link_pattern': 'CVPR'
    },
    'iccv': {
        'name': 'ICCV',
        'base_url': 'https://openaccess.thecvf.com',
        'url_template': {
            2025: 'https://openaccess.thecvf.com/ICCV2025?day=all',  # May not exist yet
            2024: None,  # ICCV is biennial (odd years only)
            2023: 'https://openaccess.thecvf.com/ICCV2023?day=all',
        },
        'paper_link_pattern': 'ICCV'
    },
    'eccv': {
        'name': 'ECCV',
        'base_url': 'https://eccv.ecva.net',
        'url_template': {
            2025: None,  # ECCV is biennial (even years only)
            2024: 'https://eccv.ecva.net/virtual/2024/papers.html',
            2023: None,
            2022: 'https://eccv.ecva.net/virtual/2022/papers.html',
        },
        'paper_link_pattern': '/virtual/{year}/poster/'
    },
    'miccai': {
        'name': 'MICCAI',
        'base_url': 'https://papers.miccai.org',
        'url_template': {
            2025: 'https://papers.miccai.org/miccai-2025/',
            2024: 'https://papers.miccai.org/miccai-2024/',
            2023: 'https://conferences.miccai.org/2023/papers/',
        },
        'paper_link_pattern': 'paper',
        'base_url_2023': 'https://conferences.miccai.org'
    }
}


def count_papers_only_miccai(url, base_url, search_term="federated", year=2023):
    """
    Scrape papers from MICCAI website.
    
    Args:
        url: The URL to scrape
        base_url: The base URL for constructing absolute links
        search_term: The search term to filter papers by
        year: Conference year (affects parsing logic)
    
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
    
    total_count = 0
    print(f"Filtering by search term: '{search_term}'")
    
    if year == 2023:
        # MICCAI 2023: bullet points with direct links to paper pages
        paper_items = soup.find_all('li')
        print(f"Found {len(paper_items)} list items")
        
        for li in paper_items:
            link_elem = li.find('a')
            if not link_elem:
                continue
                
            title = link_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                continue
                
            total_count += 1
            
            if search_term.lower() in title.lower():
                paper_url = urljoin(base_url, link_elem.get('href'))
                papers.append({
                    'title': title,
                    'link': paper_url
                })
    else:
        # MICCAI 2024+: titles in <b> tags, need "Paper Information and Reviews" link
        title_elems = soup.find_all('b')
        print(f"Found {len(title_elems)} bold elements (titles)")
        
        for title_elem in title_elems:
            title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                continue
            
            total_count += 1
            
            if search_term.lower() in title.lower():
                # Find the "Paper Information and Reviews" link in the same list item
                li_parent = title_elem.find_parent('li')
                if li_parent:
                    info_link = li_parent.find('a', string='Paper Information and Reviews')
                    if info_link:
                        paper_url = urljoin(base_url, info_link.get('href'))
                        papers.append({
                            'title': title,
                            'link': paper_url
                        })
    
    print(f"Total valid paper titles: {total_count}")
    filtered_count = len(papers)
    return papers, total_count, filtered_count


def get_paper_abstract_miccai(paper_url, headers):
    """
    Fetch the abstract from a MICCAI paper page.
    
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
        
        # MICCAI 2023: Abstract is in the page text after "Abstract" heading
        # Method 1: Try to extract from text by finding Abstract section
        page_text = soup.get_text()
        
        # Look for "Abstract" heading followed by content
        import re
        # Pattern: Find "Abstract" (case insensitive) followed by text until next section
        abstract_match = re.search(r'Abstract\s+(.*?)(?=\n\s*\n\s*[A-Z]|\Z)', page_text, re.IGNORECASE | re.DOTALL)
        
        if abstract_match:
            abstract_text = abstract_match.group(1).strip()
            # Clean up excessive whitespace
            abstract_text = ' '.join(abstract_text.split())
            if len(abstract_text) > 50:  # Reasonable abstract length
                return abstract_text
        
        # Method 2: Try standard HTML elements
        abstract_elem = soup.find('div', class_=lambda x: x and 'abstract' in str(x).lower())
        
        if not abstract_elem:
            abstract_elem = soup.find('p', class_=lambda x: x and 'abstract' in str(x).lower())
        
        if abstract_elem:
            abstract_text = abstract_elem.get_text(strip=True)
            if abstract_text.startswith("Abstract"):
                abstract_text = abstract_text[8:].strip()
            return abstract_text
        
        return "Abstract not found"
            
    except Exception as e:
        print(f"Error fetching abstract from {paper_url}: {e}")
        return "Error fetching abstract"


def count_papers_only_eccv(url, base_url, search_term="federated"):
    """
    Scrape papers from ECCV website.
    
    Args:
        url: The URL to scrape
        base_url: The base URL for constructing absolute links
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
    
    # ECCV uses dt tags with class ptitle
    paper_titles = soup.find_all('dt', class_='ptitle')
    
    total_count = len(paper_titles)
    print(f"Found {total_count} total papers")
    print(f"Filtering by search term: '{search_term}'")
    
    for dt in paper_titles:
        # Get the title link
        link_elem = dt.find('a')
        if not link_elem:
            continue
            
        title = link_elem.get_text(strip=True)
        
        # Filter by search term (case-insensitive)
        if title and search_term.lower() in title.lower():
            paper_url = urljoin(base_url, link_elem.get('href'))
            papers.append({
                'title': title,
                'link': paper_url
            })
    
    filtered_count = len(papers)
    return papers, total_count, filtered_count


def get_paper_abstract_eccv(paper_url, headers):
    """
    Fetch the abstract from an ECCV paper page.
    
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
        
        # ECCV abstract is in a div with id="abstract"
        abstract_elem = soup.find('div', id='abstract')
        
        if abstract_elem:
            abstract_text = abstract_elem.get_text(strip=True)
            # Remove "Abstract" prefix if present
            if abstract_text.startswith("Abstract"):
                abstract_text = abstract_text[8:].strip()
            return abstract_text
        else:
            return "Abstract not found"
            
    except Exception as e:
        print(f"Error fetching abstract from {paper_url}: {e}")
        return "Error fetching abstract"


def count_papers_only_cvf(url, base_url, conference_name, search_term="federated"):
    """
    Scrape papers from CVF (CVPR/ICCV) open access website.
    
    Args:
        url: The URL to scrape
        base_url: The base URL for constructing absolute links
        conference_name: Conference name pattern
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
    
    # CVF uses dt tags for paper titles
    paper_titles = soup.find_all('dt', class_='ptitle')
    
    total_count = len(paper_titles)
    print(f"Found {total_count} total papers")
    print(f"Filtering by search term: '{search_term}'")
    
    for dt in paper_titles:
        # Get the title link
        link_elem = dt.find('a')
        if not link_elem:
            continue
            
        title = link_elem.get_text(strip=True)
        
        # Filter by search term (case-insensitive)
        if title and search_term.lower() in title.lower():
            paper_url = urljoin(base_url, link_elem.get('href'))
            papers.append({
                'title': title,
                'link': paper_url
            })
    
    filtered_count = len(papers)
    return papers, total_count, filtered_count


def get_paper_abstract_cvf(paper_url, headers):
    """
    Fetch the abstract from a CVF paper page.
    
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
        
        # CVF uses div with id="abstract"
        abstract_elem = soup.find('div', id='abstract')
        
        if abstract_elem:
            abstract_text = abstract_elem.get_text(strip=True)
            # Remove "Abstract" prefix if present
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
        conference: Conference name (lowercase: 'cvpr', 'iccv', 'eccv', 'miccai')
        year: Conference year
    
    Returns:
        Number of papers found
    """
    if conference not in CONFERENCE_CONFIGS:
        print(f"Error: Unknown conference '{conference}'")
        return 0
    
    config = CONFERENCE_CONFIGS[conference]
    
    if year not in config['url_template'] or config['url_template'][year] is None:
        print(f"Skipping: {config['name']} {year} not available")
        return 0
    
    url = config['url_template'][year]
    
    print("=" * 80)
    print(f"{config['name']} {year} - Federated Learning Papers")
    print("=" * 80)
    print()
    
    # Step 1: Count papers without fetching abstracts
    print("Step 1: Counting papers...")
    
    if conference in ['cvpr', 'iccv', 'eccv']:
        paper_list, total_papers, federated_papers = count_papers_only_cvf(
            url, config['base_url'], config['paper_link_pattern']
        )
    elif conference == 'miccai':
        # MICCAI 2023 uses a different base URL
        if year == 2023:
            base_url_to_use = config.get('base_url_2023', config['base_url'])
        else:
            base_url_to_use = config['base_url']
        
        paper_list, total_papers, federated_papers = count_papers_only_miccai(
            url, base_url_to_use, year=year
        )
    else:
        print(f"Warning: Scraping for {conference} not fully implemented yet")
        return 0
    
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
        
        if conference in ['cvpr', 'iccv', 'eccv']:
            abstract = get_paper_abstract_cvf(paper_info['link'], headers)
        elif conference == 'miccai':
            abstract = get_paper_abstract_miccai(paper_info['link'], headers)
        else:
            abstract = "Abstract fetching not implemented"
        
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
        ('cvpr', [2023, 2024, 2025]),
        ('iccv', [2023, 2025]),  # ICCV is biennial (odd years)
        ('miccai', [2023, 2024, 2025]),
    ]
    
    total_papers_scraped = 0
    summary = []
    
    print("\n" + "=" * 80)
    print("Computer Vision Conference Federated Learning Papers Scraper")
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
    
    if total_papers_scraped == 0:
        print("\nNote: CV conferences may use different platforms or require different scraping approaches.")
        print("You may need to check the conference websites manually and adjust the scraper.")


if __name__ == "__main__":
    main()

