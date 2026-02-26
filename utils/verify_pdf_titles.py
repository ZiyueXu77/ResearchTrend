#!/usr/bin/env python3
"""
Script to verify that PDF filenames match the actual paper titles.
Identifies mismatches between filename and extracted title from PDF.
"""

import fitz  # PyMuPDF
import re
import csv
import glob
from pathlib import Path
from rapidfuzz import fuzz
import argparse


def extract_title_from_pdf(pdf_path, filename_title=None, max_chars=3000):
    """
    Extract the title from the first page of a PDF.
    Heuristic: Title is usually in the first few lines, larger font, centered.
    
    Args:
        pdf_path: Path to PDF file
        filename_title: Expected title from filename (for search matching)
        max_chars: Maximum characters to read from start of PDF
        
    Returns:
        str: Extracted title or None
    """
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None
        
        # Get first page text
        first_page = doc[0]
        full_text = first_page.get_text()
        
        # Special handling for ICLR-style papers: extract title between "Published as..." and "ABSTRACT"
        published_match = re.search(r'Published as a conference paper at [A-Z]+\s+\d{4}', full_text, re.IGNORECASE)
        abstract_match = re.search(r'\bABSTRACT\b', full_text, re.IGNORECASE)
        
        if published_match and abstract_match:
            # Extract text between these two markers
            start_idx = published_match.end()
            end_idx = abstract_match.start()
            
            if start_idx < end_idx:
                title_section = full_text[start_idx:end_idx].strip()
                
                # Clean up the title section
                # Remove hyphenation at line breaks
                title_section = re.sub(r'-\s*\n\s*', '', title_section)
                # Normalize whitespace
                title_section = ' '.join(title_section.split())
                
                # The title is usually at the beginning, before author names/affiliations
                # Stop at email addresses, affiliations, or numbered superscripts followed by names
                title_end_patterns = [
                    r'\s+\S+@',  # Email
                    r'\s+\d+\s+[A-Z][a-z]+',  # "1 Name" pattern (affiliation markers)
                    r'\s+[A-Z][a-z]+\s+[A-Z][a-z]+\d',  # "Name Surname1" pattern
                    r'\s+University\b',
                    r'\s+Institute\b',
                    r'\s+Laboratory\b',
                    r'\s+Center\b',
                    r'\s+School\b',
                ]
                
                min_end = len(title_section)
                for pattern in title_end_patterns:
                    end_match = re.search(pattern, title_section, re.IGNORECASE)
                    if end_match and end_match.start() > 20 and end_match.start() < min_end:  # Must be at least 20 chars in
                        min_end = end_match.start()
                
                extracted_title = title_section[:min_end].strip()
                
                # Remove trailing punctuation
                extracted_title = re.sub(r'[\s,;:]+$', '', extracted_title)
                
                if len(extracted_title) > 10:  # Reasonable title length
                    doc.close()
                    return extracted_title[:250]
        
        # If filename_title is provided, try to find it directly in the PDF
        if filename_title:
            # Normalize PDF text: remove hyphens at line breaks, normalize whitespace
            normalized_text = re.sub(r'-\s*\n\s*', '', full_text)  # Remove hyphenation
            # Also remove colons followed by newlines (common in title formatting)
            normalized_text = re.sub(r':\s*\n\s*', ': ', normalized_text)
            normalized_text = ' '.join(normalized_text.split())  # Normalize whitespace
            
            # Search for the title string in the PDF (case-insensitive, flexible whitespace)
            filename_words = filename_title.lower().split()
            if len(filename_words) >= 3:
                # Search for the first few significant words of the title (skip common words)
                significant_words = [w for w in filename_words if len(w) > 3]
                
                # Try with different word combinations (more flexible)
                # Prioritize matches in the first 500 characters (likely title area)
                match = None
                # Try first words, then skip first word and try next ones (in case first word is missing)
                word_combinations = [
                    significant_words[:3] if len(significant_words) >= 3 else significant_words[:2],  # First 3 or 2
                    significant_words[1:4] if len(significant_words) >= 4 else significant_words[1:3],  # Skip first, try next 3
                    significant_words[:2] if len(significant_words) >= 2 else None,  # First 2
                ]
                
                for words_to_search in word_combinations:
                    if not words_to_search or len(words_to_search) < 2:
                        continue
                    
                    # Build flexible pattern that allows for extra spaces and optional punctuation
                    # This handles cases like "FedInverse:" followed by "Evaluating"
                    pattern_parts = []
                    for i, word in enumerate(words_to_search):
                        if i > 0:
                            # Allow optional colon, comma, or just whitespace between words
                            pattern_parts.append(r'[\s:,]+')
                        pattern_parts.append(re.escape(word))
                    search_pattern = r'\b' + ''.join(pattern_parts) + r'\b'
                    
                    # Find all matches
                    matches = list(re.finditer(search_pattern, normalized_text, re.IGNORECASE))
                    
                    # Prioritize matches in first 500 chars (title area)
                    for m in matches:
                        if m.start() < 500:
                            match = m
                            break
                    
                    # If no match in title area, take first match
                    if not match and matches:
                        match = matches[0]
                    
                    if match:
                        break
                
                if match:
                        # Found the title! Extract reasonable title length from this position
                        start_idx = match.start()
                        # Get surrounding text (up to 500 chars to capture longer titles)
                        end_idx = min(len(normalized_text), start_idx + 500)
                        context = normalized_text[start_idx:end_idx]
                        
                        # Extract until we hit author names, emails, or abstract
                        # Title usually ends before:
                        # 1. Email addresses (@)
                        # 2. "Abstract" or "ABSTRACT"
                        # 3. Author affiliations (University, Institute, etc.)
                        # 4. Multiple lowercase names in sequence (likely authors)
                        
                        # Try to find where title ends
                        title_end_patterns = [
                            r'\s+\S+@',  # Email
                            r'\s+Abstract\b',
                            r'\s+ABSTRACT\b',
                            r'\s+\d+\s+[A-Z][a-z]+\s+[A-Z]',  # "1 Name Surname" pattern
                            r'\s+[A-Z][a-z]+\s+[A-Z][a-z]+\d',  # "Name Surname1" pattern (affiliations)
                            r'\s+University\b',
                            r'\s+Institute\b',
                            r'\s+Laboratory\b',
                        ]
                        
                        # Find the earliest match of any ending pattern
                        min_end = len(context)
                        for pattern in title_end_patterns:
                            end_match = re.search(pattern, context, re.IGNORECASE)
                            if end_match and end_match.start() < min_end:
                                min_end = end_match.start()
                        
                        title = context[:min_end].strip()
                        
                        # Clean up: remove trailing punctuation that's not part of title
                        title = re.sub(r'[\s,;]+$', '', title)
                        
                        doc.close()
                        return ' '.join(title.split())[:250]
        
        # Extract text with formatting information
        blocks = first_page.get_text("dict")["blocks"]
        
        # Try to find title using font size (title usually has larger font)
        potential_titles = []
        max_font_size = 0
        
        # Skip patterns (conference headers, etc.)
        skip_patterns = [
            r'^published as a conference paper',
            r'^preprint',
            r'^arxiv',
            r'^under review',
            r'^submitted to',
        ]
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_size = span.get("size", 0)
                        text_content = span.get("text", "").strip()
                        
                        # Skip very short text or common headers
                        if len(text_content) < 10:
                            continue
                        
                        # Skip common headers and patterns
                        text_lower = text_content.lower()
                        if text_lower in ['abstract', 'introduction', 'preprint']:
                            continue
                        if any(re.match(pattern, text_lower) for pattern in skip_patterns):
                            continue
                        
                        if font_size > max_font_size:
                            max_font_size = font_size
                            potential_titles = [text_content]
                        elif abs(font_size - max_font_size) < 0.5:  # Similar font size
                            potential_titles.append(text_content)
        
        doc.close()
        
        # Combine potential title spans (titles can be split across lines)
        if potential_titles:
            # Take the first few large-font text spans as title
            # Be more generous - titles can be long and split across multiple lines
            title = ' '.join(potential_titles[:10])  # Increased from 5 to 10
            # Clean up
            title = ' '.join(title.split())  # Remove extra whitespace
            # Remove common prefixes
            title = re.sub(r'^(Preprint\s*|arXiv:\S+\s*)', '', title, flags=re.IGNORECASE)
            
            # Stop at author names or emails
            # Usually after title comes author names (often with digits like "Name1")
            title_end_match = re.search(r'\s+\S+@|\s+[A-Z][a-z]+\s+[A-Z][a-z]+\d', title)
            if title_end_match:
                title = title[:title_end_match.start()]
            
            return title.strip()[:250]  # Limit length
        
        # Fallback: use first non-empty lines (simpler approach)
        lines = full_text.split('\n')
        title_lines = []
        for line in lines[:30]:  # Check first 30 lines
            line = line.strip()
            if len(line) < 10:
                continue
            
            # Skip common headers
            line_lower = line.lower()
            if any(re.match(pattern, line_lower) for pattern in skip_patterns):
                continue
            if line_lower.startswith(('abstract', 'preprint', 'arxiv')):
                continue
            
            title_lines.append(line)
            if len(' '.join(title_lines)) > 50:  # Got enough for a title
                break
        
        if title_lines:
            return ' '.join(title_lines)[:200]
        
        return None
        
    except Exception as e:
        print(f"  Error extracting title: {e}")
        return None


def normalize_title(title):
    """
    Normalize title for comparison.
    
    Args:
        title: Title string
        
    Returns:
        str: Normalized title
    """
    if not title:
        return ""
    
    # Convert to lowercase
    title = title.lower()
    
    # Remove special characters and extra spaces
    title = re.sub(r'[^\w\s]', ' ', title)
    title = ' '.join(title.split())
    
    return title


def compare_titles(filename_title, pdf_title, threshold=80):
    """
    Compare filename title with PDF title using fuzzy matching.
    
    Args:
        filename_title: Title from filename
        pdf_title: Title extracted from PDF
        threshold: Similarity threshold (0-100)
        
    Returns:
        tuple: (similarity_score, is_match)
    """
    if not pdf_title:
        return 0, False
    
    norm_filename = normalize_title(filename_title)
    norm_pdf = normalize_title(pdf_title)
    
    # Use partial ratio to handle cases where filename is truncated
    similarity = fuzz.partial_ratio(norm_filename, norm_pdf)
    
    is_match = similarity >= threshold
    
    return similarity, is_match


def verify_single_pdf(pdf_path, threshold=80):
    """
    Verify a single PDF file.
    
    Args:
        pdf_path: Path to PDF file
        threshold: Similarity threshold for matching
        
    Returns:
        dict: Verification result
    """
    pdf_path = Path(pdf_path)
    
    # Extract metadata from path
    parts = pdf_path.parts
    if 'PDFs' in parts or 'papers_pdf' in parts:
        idx = parts.index('PDFs') if 'PDFs' in parts else parts.index('papers_pdf')
        conference = parts[idx + 1] if idx + 1 < len(parts) else 'unknown'
        year = parts[idx + 2] if idx + 2 < len(parts) else 'unknown'
    else:
        conference = 'unknown'
        year = 'unknown'
    
    filename_title = pdf_path.stem
    
    # Extract title from PDF
    pdf_title = extract_title_from_pdf(pdf_path, filename_title)
    
    # Compare titles
    similarity, is_match = compare_titles(filename_title, pdf_title, threshold)
    
    return {
        'conference': conference,
        'year': year,
        'filename': pdf_path.name,
        'filename_title': filename_title,
        'pdf_title': pdf_title,
        'similarity': similarity,
        'is_match': is_match,
        'path': str(pdf_path)
    }


def verify_all_pdfs(pdf_dir='PDFs', threshold=80):
    """
    Verify all PDFs in the directory.
    
    Args:
        pdf_dir: Root directory containing PDFs
        threshold: Similarity threshold
        
    Returns:
        list: Verification results
    """
    pdf_files = glob.glob(f'{pdf_dir}/**/*.pdf', recursive=True)
    print(f"Found {len(pdf_files)} PDF files to verify\n")
    
    results = []
    mismatches = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Checking: {Path(pdf_path).name[:60]}...")
        
        result = verify_single_pdf(pdf_path, threshold)
        results.append(result)
        
        if not result['is_match']:
            mismatches.append(result)
            print(f"  ⚠️  MISMATCH (similarity: {result['similarity']}%)")
            print(f"      Filename: {result['filename_title'][:80]}")
            print(f"      PDF:      {result['pdf_title'][:80] if result['pdf_title'] else 'Could not extract'}")
        else:
            print(f"  ✓ Match (similarity: {result['similarity']}%)")
    
    return results, mismatches


def save_results(results, output_file='pdf_title_verification.csv'):
    """
    Save verification results to CSV.
    
    Args:
        results: List of verification results
        output_file: Output CSV filename
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Conference', 'Year', 'Filename', 'Filename Title', 
            'PDF Title', 'Similarity (%)', 'Match', 'Path'
        ])
        
        # Write results
        for result in results:
            writer.writerow([
                result['conference'],
                result['year'],
                result['filename'],
                result['filename_title'],
                result['pdf_title'] or 'N/A',
                result['similarity'],
                'Yes' if result['is_match'] else 'No',
                result['path']
            ])
    
    print(f"\n✓ Full results saved to: {output_file}")


def save_mismatches(mismatches, output_file='pdf_title_mismatches.csv'):
    """
    Save only mismatched PDFs to a separate CSV.
    
    Args:
        mismatches: List of mismatched results
        output_file: Output CSV filename
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Conference', 'Year', 'Filename Title', 'PDF Title', 
            'Similarity (%)', 'Path'
        ])
        
        # Write mismatches
        for result in sorted(mismatches, key=lambda x: x['similarity']):
            writer.writerow([
                result['conference'],
                result['year'],
                result['filename_title'],
                result['pdf_title'] or 'Could not extract title',
                result['similarity'],
                result['path']
            ])
    
    print(f"✓ Mismatches saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Verify PDF filenames match actual paper titles'
    )
    parser.add_argument(
        '--pdf',
        type=str,
        help='Verify a single PDF file (for testing)'
    )
    parser.add_argument(
        '--pdf-dir',
        type=str,
        default='PDFs',
        help='Directory containing PDFs (default: PDFs)'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        default=80,
        help='Similarity threshold for matching (0-100, default: 80)'
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("PDF Title Verification")
    print("="*80)
    print(f"Similarity threshold: {args.threshold}%\n")
    
    if args.pdf:
        # Verify single PDF
        print(f"Mode: Single PDF test\n")
        result = verify_single_pdf(args.pdf, args.threshold)
        
        print("\n" + "="*80)
        print("RESULT")
        print("="*80)
        print(f"Filename: {result['filename']}")
        print(f"Filename title: {result['filename_title']}")
        print(f"PDF title:      {result['pdf_title'] or 'Could not extract'}")
        print(f"Similarity:     {result['similarity']}%")
        print(f"Match:          {'✓ Yes' if result['is_match'] else '✗ No'}")
        
    else:
        # Verify all PDFs
        print(f"Mode: Verify all PDFs in {args.pdf_dir}/\n")
        results, mismatches = verify_all_pdfs(args.pdf_dir, args.threshold)
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total PDFs verified:  {len(results)}")
        print(f"Matching:             {len(results) - len(mismatches)}")
        print(f"Mismatches:           {len(mismatches)}")
        print(f"Match rate:           {((len(results) - len(mismatches)) / len(results) * 100):.1f}%")
        
        # Save results
        save_results(results, 'pdf_title_verification.csv')
        
        if mismatches:
            save_mismatches(mismatches, 'pdf_title_mismatches.csv')
            
            print("\n" + "="*80)
            print("TOP 10 MISMATCHES (by similarity)")
            print("="*80)
            for i, result in enumerate(sorted(mismatches, key=lambda x: x['similarity'])[:10], 1):
                print(f"\n{i}. [{result['conference'].upper()} {result['year']}] (Similarity: {result['similarity']}%)")
                print(f"   Filename: {result['filename_title'][:70]}")
                print(f"   PDF:      {(result['pdf_title'] or 'N/A')[:70]}")


if __name__ == "__main__":
    main()

