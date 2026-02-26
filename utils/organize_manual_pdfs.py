#!/usr/bin/env python3
"""
Organize manually downloaded PDFs from Manual_Download folder
- Extract title from PDF content
- Match to papers in missing_papers.csv using fuzzy matching
- Rename them to proper titles
- Move them to correct subfolders under PDFs/
"""

import os
import csv
import re
import shutil
from pathlib import Path
import fitz  # PyMuPDF
from rapidfuzz import fuzz, process

def sanitize_filename(title):
    """
    Sanitize title to be a valid filename
    """
    # Remove or replace invalid characters
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace multiple spaces with single space
    title = re.sub(r'\s+', ' ', title)
    # Trim and limit length
    title = title.strip()[:200]
    return title

def extract_title_from_pdf(pdf_path):
    """
    Extract the title from the first page of a PDF
    Usually the title is in the first few lines
    """
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None
        
        # Get first page
        first_page = doc[0]
        text = first_page.get_text()
        
        # Extract first few lines (title is usually at the top)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Try to find the title - usually one of the first few lines
        # Skip very short lines (likely headers) and look for substantial text
        potential_titles = []
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            # Skip page numbers, single words, URLs, etc.
            if len(line) > 20 and not line.startswith('http') and not line.isdigit():
                potential_titles.append(line)
        
        doc.close()
        
        # Return the first substantial line as the title
        if potential_titles:
            return potential_titles[0]
        
        return None
    except Exception as e:
        print(f"  Error extracting title from PDF: {e}")
        return None

def normalize_title(title):
    """
    Normalize title for better matching
    """
    # Convert to lowercase
    title = title.lower()
    # Replace special LaTeX/math characters
    title = title.replace('$', '')
    title = title.replace('^', '')
    title = title.replace('–', '-')  # en-dash
    title = title.replace('—', '-')  # em-dash
    # Remove special characters but keep spaces and basic punctuation
    title = re.sub(r'[^\w\s\-:]', ' ', title)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def main():
    # Paths
    manual_dir = Path("/media/ziyuexu/Research/Experiment/ResearchTrend/Manual_Download")
    pdfs_dir = Path("/media/ziyuexu/Research/Experiment/ResearchTrend/PDFs")
    missing_csv = Path("/media/ziyuexu/Research/Experiment/ResearchTrend/missing_papers.csv")
    
    # Read missing papers CSV
    papers = []
    with open(missing_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row['conference']:  # Skip empty rows
                continue
            papers.append({
                'conference': row['conference'],
                'year': row['year'],
                'title': row['title'],
                'normalized_title': normalize_title(row['title']),
                'link': row['link']
            })
    
    print(f"Loaded {len(papers)} papers from missing_papers.csv")
    
    # Process each PDF in Manual_Download
    pdf_files = sorted(manual_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in Manual_Download folder\n")
    
    moved_count = 0
    not_matched_count = 0
    
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
        
        # Extract title from PDF
        pdf_title = extract_title_from_pdf(str(pdf_file))
        if not pdf_title:
            print(f"  ⚠️  Could not extract title from PDF")
            not_matched_count += 1
            continue
        
        print(f"  Extracted title: {pdf_title[:80]}...")
        
        # Normalize and match
        normalized_pdf_title = normalize_title(pdf_title)
        
        # Find best match using fuzzy matching
        best_match = None
        best_score = 0
        
        for paper in papers:
            # Try multiple matching strategies
            score1 = fuzz.ratio(normalized_pdf_title, paper['normalized_title'])
            score2 = fuzz.partial_ratio(normalized_pdf_title, paper['normalized_title'])
            score3 = fuzz.token_sort_ratio(normalized_pdf_title, paper['normalized_title'])
            
            # Use the best score among different matching strategies
            score = max(score1, score2, score3)
            
            if score > best_score:
                best_score = score
                best_match = paper
        
        # Require at least 75% match (lowered from 80%)
        if best_score < 75:
            print(f"  ⚠️  No good match found (best score: {best_score}%)")
            print(f"     Extracted: {normalized_pdf_title[:80]}")
            if best_match:
                print(f"     Best was: {best_match['normalized_title'][:80]}")
            not_matched_count += 1
            continue
        
        print(f"  ✓ Matched to: {best_match['title'][:60]}... (score: {best_score}%)")
        
        # Create target directory
        target_dir = pdfs_dir / f"{best_match['conference']}_{best_match['year']}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize title and create new filename
        clean_title = sanitize_filename(best_match['title'])
        new_filename = f"{clean_title}.pdf"
        target_path = target_dir / new_filename
        
        # Move and rename
        try:
            shutil.move(str(pdf_file), str(target_path))
            print(f"  ✓ Moved to: {target_dir.name}/{new_filename}")
            moved_count += 1
        except Exception as e:
            print(f"  ✗ Error moving file: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Successfully moved: {moved_count}")
    print(f"  Not matched: {not_matched_count}")
    print(f"  Total processed: {len(pdf_files)}")
    
    # Check if Manual_Download is empty
    remaining = list(manual_dir.glob("*.pdf"))
    if not remaining:
        print(f"\n✓ Manual_Download folder is now empty!")
    else:
        print(f"\n⚠️  {len(remaining)} files remaining in Manual_Download")
        for f in remaining:
            print(f"    - {f.name}")

if __name__ == "__main__":
    main()
