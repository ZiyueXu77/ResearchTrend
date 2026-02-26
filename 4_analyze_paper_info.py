#!/usr/bin/env python3
"""
LLM analysis of enriched paper data: extract last author/institution AND
classify platform usage (USED vs MENTIONED) in one pass.
Combines the functionality of extract_last_author.py and platform_usage_llm.py.
"""

import csv
import json
import glob
import argparse
from pathlib import Path
import requests
import time

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# ─── LLM prompts ────────────────────────────────────────────────────────────

AUTHOR_PROMPT = """Extract the last author's name and their institution from the following author block.

Author Block:
{author_block}

Instructions:
1. Identify the LAST author listed (usually the corresponding author or senior author)
2. Extract their full name
3. Extract the FULL OFFICIAL institution name (university or company):
   - Remove departments, schools, colleges, centers, labs, cities, states, countries, addresses
   - Always use the FULL university name, NOT abbreviations or city names. Examples:
     * "Department of Computer Science, Stanford University, California, USA" → "Stanford University"
     * "School of Engineering, MIT" → "MIT"
     * "University of California, Los Angeles" → "UCLA"
     * "Carnegie Mellon University" → "Carnegie Mellon University"
     * "ETH Zurich" → "ETH Zurich"
     * "Tsinghua University, Beijing" → "Tsinghua University"
     * "Wuhan University, Wuhan, China" → "Wuhan University"
     * "National University of Singapore" → "National University of Singapore"
     * "Nanyang Technological University" → "Nanyang Technological University"
     * "University of Illinois at Urbana-Champaign" → "UIUC"
     * "Georgia Institute of Technology" → "Georgia Tech"
     * "East China Normal University" → "East China Normal University"
     * "Huazhong University of Science and Technology" → "HUST"
   - For companies: use short name only
     * "Google Research" → "Google"
     * "Meta AI" → "Meta"
     * "Microsoft Research" → "Microsoft"
   - Use the SAME name consistently for the same institution
   - If the last author has MULTIPLE affiliations, choose the one that MOST OTHER AUTHORS share
   - If you can't determine which is more common, pick the first one listed

Respond ONLY with a JSON object:
{{"last_author": "Full Name", "institution": "Short Name"}}

If you cannot find the information, use empty strings.

JSON Response:"""

PLATFORM_PROMPT = """You are analyzing federated learning research papers to determine FL platform usage.

Given the platform mentions extracted from a paper, determine for each FEDERATED LEARNING platform whether:
- "USED": The paper actually implemented/used this FL platform for experiments or implementation
- "MENTIONED": The paper only cited/referenced the platform, or mentioned it as related work, or used a dataset from the platform

IMPORTANT: Only analyze actual FL platforms (Flower, NVIDIA FLARE, PySyft, TensorFlow Federated, FedML, FATE, PaddleFL, OpenFL, FederatedScope, FedScale, LEAF).
IGNORE general ML frameworks like PyTorch, Scikit-learn, TensorFlow (non-federated), etc. Do not include them in your response.

Platform mentions from the paper:
{mentions}

Return your analysis as a JSON object with this structure:
{{
  "fl_platform_name": "USED" or "MENTIONED",
  ...
}}

Guidelines for "USED":
- "built on", "implemented using", "implemented in", "implemented with"
- "experiments conducted with", "evaluated on", "framework deployed"
- "code available at/in/on [platform]", "code released on [platform]"
- "using [platform]", "based on [platform]", "leveraging [platform]"

Guidelines for "MENTIONED":
- citations, references in related work (e.g., "Package name. arXiv:..., year" or "[Author et al., year]")
- bibliography-style references with arXiv numbers, DOIs, or publication venues
- "compared to", "unlike", "differs from"
- dataset names (e.g., "LEAF dataset" is just a dataset, not platform usage)
- survey/review mentions

IMPORTANT: If the text is ONLY a citation format, classify as MENTIONED.
Be conservative: when uncertain, classify as "MENTIONED"
Only analyze FL platforms, skip non-FL tools
Only return the JSON object, no additional text

JSON response:"""

# ─── Ollama helpers ──────────────────────────────────────────────────────────

def call_ollama(prompt, model="qwen2.5:7b", max_tokens=150):
    """Call Ollama API and return raw response text."""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.1, 'num_predict': max_tokens},
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
        else:
            print(f"    API error: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print(f"    Request timeout")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def parse_json_response(text):
    """Extract JSON object from LLM response text."""
    if not text:
        return None
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return None
    return None


def extract_last_author(author_block, model):
    """Use LLM to extract last author and institution from author block."""
    prompt = AUTHOR_PROMPT.format(author_block=author_block[:1500])
    resp = call_ollama(prompt, model, max_tokens=150)
    data = parse_json_response(resp)
    if data:
        return data.get('last_author', '').strip(), data.get('institution', '').strip()
    return "", ""


def classify_platform_usage(mentions_text, model):
    """Use LLM to classify platform mentions as USED or MENTIONED."""
    prompt = PLATFORM_PROMPT.format(mentions=mentions_text)
    resp = call_ollama(prompt, model, max_tokens=500)
    return parse_json_response(resp)

# ─── Main processing ────────────────────────────────────────────────────────

def process_csv_file(csv_file, model="qwen2.5:7b", output_dir='Analyzed'):
    """Process a single enriched CSV file with LLM analysis."""
    print(f"\nProcessing: {csv_file}")

    Path(output_dir).mkdir(exist_ok=True)

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames)
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        return None

    if not rows:
        print(f"  Empty CSV file")
        return None

    print(f"  Found {len(rows)} papers")

    # Add new columns if missing
    new_cols = ['last_author_extracted', 'institution_extracted', 'platform_used', 'platform_mentioned']
    for col in new_cols:
        if col not in fieldnames:
            if col.startswith('last_author') and 'authors' in fieldnames:
                idx = fieldnames.index('authors') + 1
                fieldnames.insert(idx, col)
            elif col.startswith('institution') and 'last_author_extracted' in fieldnames:
                idx = fieldnames.index('last_author_extracted') + 1
                fieldnames.insert(idx, col)
            elif col == 'platform_used' and 'platform_mentions' in fieldnames:
                idx = fieldnames.index('platform_mentions') + 1
                fieldnames.insert(idx, col)
            elif col == 'platform_mentioned' and 'platform_used' in fieldnames:
                idx = fieldnames.index('platform_used') + 1
                fieldnames.insert(idx, col)
            else:
                fieldnames.append(col)

    author_success = 0
    platform_analyzed = 0

    for i, row in enumerate(rows, 1):
        title = row.get('title', '')[:50]
        author_block = row.get('authors', '')
        mentions_str = str(row.get('platform_mentions', '')).strip()
        has_mentions = mentions_str and mentions_str != 'nan'

        needs_author = bool(author_block)
        needs_platform = has_mentions

        if not needs_author and not needs_platform:
            for col in new_cols:
                row.setdefault(col, '')
            continue

        print(f"  [{i}/{len(rows)}] {title}...")

        # --- Author LLM extraction ---
        if needs_author:
            last_author, institution = extract_last_author(author_block, model)
            row['last_author_extracted'] = last_author
            row['institution_extracted'] = institution
            if last_author:
                author_success += 1
                print(f"    Author: {last_author[:30]} | {institution}")
        else:
            row['last_author_extracted'] = ''
            row['institution_extracted'] = ''

        # --- Platform LLM classification ---
        if needs_platform:
            analysis = classify_platform_usage(mentions_str, model)
            if analysis:
                platform_analyzed += 1
                used = []
                mentioned = []
                for platform, status in analysis.items():
                    print(f"    Platform: {platform}: {status}")
                    if status == 'USED':
                        used.append(platform)
                    elif status == 'MENTIONED':
                        mentioned.append(platform)
                row['platform_used'] = ', '.join(used) if used else ''
                row['platform_mentioned'] = ', '.join(mentioned) if mentioned else ''
            else:
                row['platform_used'] = ''
                row['platform_mentioned'] = ''
                print(f"    Platform analysis failed")
        else:
            row['platform_used'] = ''
            row['platform_mentioned'] = ''

        time.sleep(0.3)

    # Write output
    output_filename = Path(csv_file).name.replace('_enriched.csv', '_analyzed.csv')
    output_path = Path(output_dir) / output_filename

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n  Saved to: {output_path}")
        print(f"  Authors extracted: {author_success}/{len(rows)}")
        print(f"  Platforms analyzed: {platform_analyzed}")
        return output_path
    except Exception as e:
        print(f"  Error writing output: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='LLM analysis: extract last author/institution + classify platform usage (combined step)')
    parser.add_argument('--csv', type=str, help='Process a single CSV file')
    parser.add_argument('--all', action='store_true', help='Process all CSV files in input directory')
    parser.add_argument('--input-dir', type=str, default='Enriched',
                        help='Directory containing enriched CSV files (default: Enriched)')
    parser.add_argument('--output-dir', type=str, default='Analyzed',
                        help='Output directory (default: Analyzed)')
    parser.add_argument('--model', type=str, default='qwen2.5:7b',
                        help='Ollama model to use (default: qwen2.5:7b)')
    parser.add_argument('--force', action='store_true',
                        help='Force re-processing even if output file already exists')

    args = parser.parse_args()

    print("=" * 80)
    print("Paper Info Analysis (Last Author + Platform Usage)")
    print("=" * 80)
    print(f"Model: {args.model}")

    # Check Ollama
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            print("Ollama is running")
        else:
            print("Ollama might not be running properly")
    except Exception:
        print("Cannot connect to Ollama. Please start Ollama first.")
        return

    if args.csv:
        process_csv_file(args.csv, args.model, args.output_dir)
    elif args.all:
        print(f"\nMode: Process all CSV files in {args.input_dir}/")
        csv_files = glob.glob(f'{args.input_dir}/*_enriched.csv')

        if not csv_files:
            print(f"\nNo enriched CSV files found in {args.input_dir}/")
            return

        print(f"Found {len(csv_files)} CSV files\n")

        results = []
        skipped = 0
        for csv_file in sorted(csv_files):
            out_name = Path(csv_file).name.replace('_enriched.csv', '_analyzed.csv')
            out_path = Path(args.output_dir) / out_name
            if out_path.exists() and not args.force:
                print(f"Skipping (already exists): {out_path}")
                skipped += 1
                continue
            result = process_csv_file(csv_file, args.model, args.output_dir)
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
