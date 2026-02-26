#!/usr/bin/env python3
"""
Scrape ICLR 2026 federated learning papers and save to Raw/ directory.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
from urllib.parse import urljoin
import os
import sys

BASE_URL = "https://iclr.cc"
SEARCH_URL = "https://iclr.cc/virtual/2026/papers.html?search=federated"
PAPER_LINK_PATTERN = "/virtual/2026/poster/"
SEARCH_TERM = "federated"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Raw")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def fetch_paper_list():
    """Fetch the list of federated papers from the search results page."""
    print(f"Fetching: {SEARCH_URL}")
    resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, 'html.parser')
    all_links = soup.find_all('a', href=lambda x: x and PAPER_LINK_PATTERN in str(x))
    total_count = len(all_links)
    print(f"Total paper links on page: {total_count}")

    federated_papers = []
    for link in all_links:
        title = link.get_text(strip=True)
        if title and SEARCH_TERM.lower() in title.lower():
            paper_url = urljoin(BASE_URL, link.get('href'))
            federated_papers.append({'title': title, 'link': paper_url})

    print(f"Federated learning papers found: {len(federated_papers)}")
    return federated_papers, total_count


def fetch_abstract(paper_url):
    """Fetch the abstract from an individual paper page."""
    try:
        resp = requests.get(paper_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Try class-based abstract element
        abstract_elem = soup.find('div', class_=lambda x: x and 'abstract' in str(x).lower())
        if not abstract_elem:
            abstract_elem = soup.find('p', class_=lambda x: x and 'abstract' in str(x).lower())
        if not abstract_elem:
            for header in soup.find_all(['h2', 'h3', 'h4', 'strong'],
                                        string=lambda x: x and 'abstract' in x.lower()):
                next_elem = header.find_next_sibling(['p', 'div'])
                if next_elem:
                    abstract_elem = next_elem
                    break

        if abstract_elem:
            text = abstract_elem.get_text(strip=True)
            if text.startswith("Abstract"):
                text = text[8:].strip()
            return text
        return "Abstract not found"
    except Exception as e:
        print(f"  Error: {e}")
        return "Error fetching abstract"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Get paper list
    paper_list, total_count = fetch_paper_list()
    fl_count = len(paper_list)

    if not paper_list:
        print("No federated learning papers found. Exiting.")
        sys.exit(1)

    # Step 2: Fetch abstracts
    print(f"\nFetching abstracts for {fl_count} papers...")
    papers = []
    for idx, info in enumerate(paper_list, 1):
        print(f"[{idx}/{fl_count}] {info['title'][:70]}...")
        abstract = fetch_abstract(info['link'])
        papers.append({'title': info['title'], 'link': info['link'], 'abstract': abstract})
        time.sleep(0.5)

    # Step 3: Save CSV
    filename = f"iclr_2026_federated_learning_{total_count}_{fl_count}.csv"
    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'link', 'abstract'])
        writer.writeheader()
        writer.writerows(papers)

    print(f"\nSaved {fl_count} papers to {output_path}")
    print(f"Filename: total={total_count}, federated={fl_count}")


if __name__ == "__main__":
    main()
