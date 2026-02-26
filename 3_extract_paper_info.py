#!/usr/bin/env python3
"""
Extract author blocks and FL platform mentions from PDFs in one pass.
Combines the functionality of add_author_info.py and add_platform_mentions.py.
"""

import fitz  # PyMuPDF
import re
import csv
import glob
from pathlib import Path
from collections import defaultdict
import argparse
import os

# FL platforms to search for
FL_PLATFORMS = {
    'Flower': [r'\bFlower\b', r'\bflwr\b'],
    'NVIDIA FLARE': [r'\bNVIDIA\s+FLARE\b', r'\bNVFLARE\b', r'\bNvFlare\b', r'\bnvflare\b'],
    'PySyft': [r'\bPySyft\b', r'\bSyft\b'],
    'TensorFlow Federated': [r'\bTensorFlow\s+Federated\b', r'\bTFF\b'],
    'FedML': [r'\bFedML\b'],
    'FATE': [r'\bFATE\b(?!\s+\()', r'\bFederated\s+AI\s+Technology\s+Enabler\b'],
    'PaddleFL': [r'\bPaddleFL\b', r'\bPaddle\s+Federated\s+Learning\b'],
    'OpenFL': [r'\bOpenFL\b', r'\bOpen\s+Federated\s+Learning\b'],
    'FederatedScope': [r'\bFederatedScope\b'],
    'FedScale': [r'\bFedScale\b'],
    'LEAF': [r'\bLEAF\b(?=\s+benchmark|\s+dataset|\s+framework)'],
}

# ─── PDF text extraction ────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path):
    """Extract full text from PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"  Error reading PDF: {e}")
        return ""


def extract_first_page_text(pdf_path):
    """Extract text from first page of PDF."""
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            text = doc[0].get_text()
            doc.close()
            return text
        doc.close()
        return ""
    except Exception as e:
        print(f"  Error reading PDF first page: {e}")
        return ""

# ─── Author extraction ──────────────────────────────────────────────────────

def clean_text(text):
    """Clean extracted text."""
    text = ' '.join(text.split())
    text = re.sub(r'\S+@\S+', '', text)
    return text


def extract_author_block(text):
    """
    Extract the entire author block including affiliations.
    Returns the author block as a string.
    """
    if not text:
        return ""

    abstract_patterns = [
        r'\bAbstract\b',
        r'\bA\s*B\s*S\s*T\s*R\s*A\s*C\s*T\b',
    ]

    abstract_match = None
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if abstract_match is None or match.start() < abstract_match.start():
                abstract_match = match

    if not abstract_match:
        return clean_text(text[:1500])

    before_abstract = text[:abstract_match.start()]

    has_affiliations_before = bool(re.search(
        r'\d+\s*(University|Institute|College|Lab|Corporation|Inc\.|Company)', before_abstract))

    if has_affiliations_before:
        return clean_text(before_abstract)

    after_abstract = text[abstract_match.end():]
    affiliation_pattern_numbered = r'(\d+[^\d].*?[;.])'
    affiliation_matches = re.findall(affiliation_pattern_numbered, after_abstract[:2000], re.DOTALL)

    page_bottom = text[-800:]
    symbol_pattern = r'([∗†‡§¶∥•])\s*([^\n]+)'
    symbol_matches_raw = re.findall(symbol_pattern, page_bottom, re.MULTILINE)

    institution_keywords = [
        'University', 'Institute', 'College', 'Laboratory', 'Lab', 'Corp',
        'Inc.', 'Company', 'Academy', 'Center', 'School', 'RIKEN', 'MIT',
        'Google', 'Meta', 'Microsoft', 'Amazon', 'Apple', 'IBM', 'Facebook',
        'NVIDIA', 'Intel', 'Adobe', 'Huawei', 'Tencent', 'Alibaba', 'ByteDance',
        'Baidu', 'DeepMind', 'OpenAI', 'Anthropic', 'Tesla', 'Samsung', 'LG',
        'Stanford', 'Berkeley', 'CMU', 'Harvard', 'Yale', 'Princeton', 'Oxford',
        'Cambridge', 'ETH', 'EPFL', 'Caltech', 'UCLA', 'USC', 'NYU'
    ]
    symbol_matches = []
    for symbol, inst_text in symbol_matches_raw:
        if '@' not in inst_text and 'Corresponding author' not in inst_text:
            if any(kw in inst_text for kw in institution_keywords):
                symbol_matches.append((symbol, inst_text))

    affiliation_lines = []
    for match_text in affiliation_matches:
        if any(kw in match_text for kw in
               ['University', 'Institute', 'College', 'Laboratory', 'Lab', 'Corp',
                'Inc.', 'Company', 'Academy', 'Center', 'School', 'RIKEN', 'MIT',
                'China', 'Japan', 'USA', 'UK', 'France', 'Germany']):
            affiliation_lines.append(' '.join(match_text.split()))

    for symbol, inst_text in symbol_matches:
        affiliation_lines.append(' '.join(inst_text.split()))

    if affiliation_lines:
        affiliation_section = ' | '.join(affiliation_lines)
        combined = before_abstract + ' --- Affiliations from footer --- ' + affiliation_section
    else:
        combined = before_abstract

    return clean_text(combined)

# ─── Platform mention extraction ────────────────────────────────────────────

def split_into_sentences(text):
    """Split text into sentences."""
    text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|vs|i\.e|e\.g|et al|Fig|Tab|Eq)\.\s', r'\1<PERIOD> ', text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    sentences = [s.replace('<PERIOD>', '.') for s in sentences]
    return sentences


def find_platform_mentions(text):
    """Find all platform mentions in text and extract the sentences."""
    sentences = split_into_sentences(text)
    mentions = defaultdict(list)

    for platform, patterns in FL_PLATFORMS.items():
        for sentence in sentences:
            for pattern in patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    clean_sentence = ' '.join(sentence.split())
                    if clean_sentence and clean_sentence not in mentions[platform]:
                        mentions[platform].append(clean_sentence)
                    break
    return dict(mentions)


def format_mentions_for_csv(mentions):
    """Format platform mentions for CSV storage."""
    if not mentions:
        return ""
    parts = []
    for platform, sentences in mentions.items():
        platform_text = f"{platform}: {' | '.join(sentences)}"
        parts.append(platform_text)
    return ' || '.join(parts)

# ─── PDF path resolution ────────────────────────────────────────────────────

def find_pdf_path(conference, year, title):
    """Find the PDF file path for a given paper."""
    conf_lower = conference.lower()
    normalized_title = title.replace(':', '').replace('?', '').replace('"', '').replace('\\', '')
    normalized_title = ' '.join(normalized_title.split())

    possible_paths = [
        Path(f"PDFs/{conf_lower}/{year}/{title}.pdf"),
        Path(f"PDFs/{conf_lower}/{year}/{normalized_title}.pdf"),
    ]
    for pdf_path in possible_paths:
        if pdf_path.exists():
            return str(pdf_path)
    return None

# ─── Main processing ────────────────────────────────────────────────────────

def process_csv_file(csv_file, output_dir='Enriched'):
    """Process a single CSV file: extract both authors and platform mentions."""
    print(f"\nProcessing: {csv_file}")

    Path(output_dir).mkdir(exist_ok=True)

    filename = Path(csv_file).stem
    match = re.match(r'(\w+)_(\d{4})_federated_learning_(\d+)_(\d+)', filename)
    if not match:
        print(f"  Could not parse filename: {csv_file}")
        return None

    conference = match.group(1)
    year = match.group(2)

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        return None

    if not rows:
        print(f"  Empty CSV file")
        return None

    print(f"  Found {len(rows)} papers")

    processed_rows = []
    author_found = 0
    platform_found = 0

    for i, row in enumerate(rows, 1):
        title = row.get('title', '')

        pdf_path = find_pdf_path(conference, year, title)

        if not pdf_path:
            print(f"  [{i}/{len(rows)}] PDF not found: {title[:50]}...")
            row['authors'] = ""
            row['platform_mentions'] = ""
            processed_rows.append(row)
            continue

        # Read PDF once, use for both extractions
        first_page_text = extract_first_page_text(pdf_path)
        full_text = extract_text_from_pdf(pdf_path)

        # --- Author extraction ---
        author_text = first_page_text if first_page_text else ""
        author_block = extract_author_block(author_text) if author_text else ""
        row['authors'] = author_block

        # --- Platform mention extraction ---
        mentions = find_platform_mentions(full_text) if full_text else {}
        mentions_text = format_mentions_for_csv(mentions)
        row['platform_mentions'] = mentions_text

        # --- Logging ---
        parts = []
        if author_block:
            author_found += 1
            parts.append(f"authors")
        if mentions:
            platform_found += 1
            platforms_str = ', '.join(mentions.keys())
            parts.append(platforms_str)

        status = ' + '.join(parts) if parts else "no info"
        print(f"  [{i}/{len(rows)}] {title[:40]}... -> {status}")

        processed_rows.append(row)

    # Write output CSV
    output_filename = Path(csv_file).name.replace('.csv', '_enriched.csv')
    output_path = Path(output_dir) / output_filename

    original_fields = list(rows[0].keys())
    fieldnames = []
    for field in original_fields:
        fieldnames.append(field)
        if field == 'abstract':
            if 'authors' not in original_fields:
                fieldnames.append('authors')
            if 'platform_mentions' not in original_fields:
                fieldnames.append('platform_mentions')

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed_rows)

        print(f"\n  Saved to: {output_path}")
        print(f"  Authors extracted: {author_found}/{len(rows)}")
        print(f"  Platform mentions: {platform_found}/{len(rows)}")
        return output_path
    except Exception as e:
        print(f"  Error writing output: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Extract author blocks and platform mentions from PDFs (combined step)')
    parser.add_argument('--csv', type=str, help='Process a single CSV file')
    parser.add_argument('--all', action='store_true', help='Process all CSV files in input directory')
    parser.add_argument('--input-dir', type=str, default='Raw',
                        help='Directory containing raw CSV files (default: Raw)')
    parser.add_argument('--output-dir', type=str, default='Enriched',
                        help='Output directory (default: Enriched)')
    parser.add_argument('--force', action='store_true',
                        help='Force re-processing even if output file already exists')

    args = parser.parse_args()

    print("=" * 80)
    print("Paper Info Extraction (Authors + Platform Mentions)")
    print("=" * 80)
    print(f"\nSearching for platforms: {', '.join(FL_PLATFORMS.keys())}")

    if args.csv:
        process_csv_file(args.csv, args.output_dir)
    elif args.all:
        print(f"\nMode: Process all CSV files in {args.input_dir}/")
        csv_files = glob.glob(f'{args.input_dir}/*_federated_learning_*.csv')

        if not csv_files:
            print(f"\nNo CSV files found in {args.input_dir}/")
            return

        print(f"Found {len(csv_files)} CSV files\n")

        results = []
        skipped = 0
        for csv_file in sorted(csv_files):
            out_name = Path(csv_file).name.replace('.csv', '_enriched.csv')
            out_path = Path(args.output_dir) / out_name
            if out_path.exists() and not args.force:
                print(f"Skipping (already exists): {out_path}")
                skipped += 1
                continue
            result = process_csv_file(csv_file, args.output_dir)
            if result:
                results.append(result)

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Processed: {len(results)}/{len(csv_files)} files")
        if skipped:
            print(f"Skipped: {skipped} already-processed file(s). Use --force to re-process.")
        print(f"Output directory: {args.output_dir}/")
    else:
        print("\nPlease specify --csv <file> or --all")
        parser.print_help()


if __name__ == "__main__":
    main()
