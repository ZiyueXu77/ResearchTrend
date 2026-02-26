#!/usr/bin/env python3
"""
Script to categorize federated learning papers using LLM.
More accurate than keyword matching.
"""

import csv
import pandas as pd
import json
import time
from typing import Dict, List
import os

# You can choose different LLM backends
LLM_BACKEND = "gemini"  # Options: "gemini", "openai", "anthropic", "ollama"

# Category definitions with clear descriptions
CATEGORY_DEFINITIONS = """
You are an expert in federated learning research. Categorize the given paper into one or more of the following categories based on its abstract and title. A paper can belong to multiple categories.

**Categories:**

1. **Personalization**: Papers focused on creating personalized models for individual clients or groups, adapting global models to local preferences, or learning client-specific parameters.

2. **Heterogeneity/Generalization**: Papers addressing data heterogeneity (non-IID data), system heterogeneity, or improving model generalization across diverse data distributions. Focus is on handling differences between clients.

3. **DataProcessing**: Papers about data quality, data selection, data augmentation, synthetic data generation, handling noisy labels, missing data, or data valuation in FL.

4. **LLM/Agents**: Papers specifically about federated learning with Large Language Models, instruction tuning, prompt learning, or multi-agent systems in FL context.

5. **Privacy/Attack**: Papers focused on privacy preservation (differential privacy, secure aggregation), or studying attacks (poisoning, backdoor, inference attacks, byzantine attacks) and defenses.

6. **Fairness/Incentives**: Papers about fairness across clients, bias mitigation, incentive mechanisms, game theory, contribution evaluation, or equitable resource allocation.

7. **FoundationModel**: Papers about using foundation models (CLIP, Vision Transformers, pretrained models) in federated settings, or federated fine-tuning of foundation models.

8. **Vertical**: Papers specifically about vertical federated learning where features are split across parties, or split learning architectures.

9. **Unlearning**: Papers about machine unlearning, data deletion, or the right to be forgotten in federated settings.

10. **Efficiency/Compression**: Papers with PRIMARY focus on reducing communication costs, model compression, quantization, pruning, or computational efficiency. Note: merely mentioning efficiency improvements is not enough - it should be a core contribution.

11. **Benchmark**: Papers that primarily introduce NEW benchmarks, datasets, or evaluation frameworks for FL. Note: papers that simply use existing benchmarks for evaluation should NOT be categorized here.

12. **ClientSelection**: Papers focused on client selection strategies, participant sampling, device scheduling, or active client management.

13. **Graph**: Papers about federated learning on graph data, graph neural networks in FL, or subgraph learning.

14. **Other**: Papers that don't fit well into the above categories. Extract 3-5 key technical terms or concepts for these papers.

**Important guidelines:**
- Be conservative: only mark a category if it's a PRIMARY focus of the paper, not just mentioned in passing
- Multiple categories are allowed if the paper has multiple main contributions
- For "Other", provide specific keywords describing the main focus
"""


def categorize_with_openai(title: str, abstract: str, api_key: str = None) -> Dict:
    """Categorize using OpenAI API."""
    import openai
    
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""{CATEGORY_DEFINITIONS}

**Paper to categorize:**

Title: {title}

Abstract: {abstract}

**Task:** Return a JSON object with category names as keys and values as follows:
- 1 if the paper belongs to this category (PRIMARY focus)
- 0 if not
For "Other", also include "Other_keywords" as a string with comma-separated keywords if Other=1.

Example format:
{{
  "Personalization": 0,
  "Heterogeneity/Generalization": 1,
  "DataProcessing": 0,
  "LLM/Agents": 0,
  "Privacy/Attack": 0,
  "Fairness/Incentives": 0,
  "FoundationModel": 0,
  "Vertical": 0,
  "Unlearning": 0,
  "Efficiency/Compression": 0,
  "Benchmark": 0,
  "ClientSelection": 0,
  "Graph": 0,
  "Other": 0,
  "Other_keywords": ""
}}

Return ONLY the JSON object, no other text.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" for better quality
        messages=[
            {"role": "system", "content": "You are an expert in federated learning research. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result


def categorize_with_anthropic(title: str, abstract: str, api_key: str = None) -> Dict:
    """Categorize using Anthropic Claude API."""
    import anthropic
    
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""{CATEGORY_DEFINITIONS}

**Paper to categorize:**

Title: {title}

Abstract: {abstract}

**Task:** Return a JSON object with category names as keys and values as follows:
- 1 if the paper belongs to this category (PRIMARY focus)
- 0 if not
For "Other", also include "Other_keywords" as a string with comma-separated keywords if Other=1.

Return ONLY the JSON object, no other text.
"""
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract JSON from response
    content = response.content[0].text
    # Try to parse JSON
    result = json.loads(content)
    return result


def categorize_with_gemini(title: str, abstract: str, api_key: str = None) -> Dict:
    """Categorize using Google Gemini API."""
    import google.generativeai as genai
    
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
    
    genai.configure(api_key=api_key)
    
    prompt = f"""{CATEGORY_DEFINITIONS}

**Paper to categorize:**

Title: {title}

Abstract: {abstract}

**Task:** Return a JSON object with category names as keys and values as follows:
- 1 if the paper belongs to this category (PRIMARY focus)
- 0 if not
For "Other", also include "Other_keywords" as a string with comma-separated keywords if Other=1.

Example format:
{{
  "Personalization": 0,
  "Heterogeneity/Generalization": 1,
  "DataProcessing": 0,
  "LLM/Agents": 0,
  "Privacy/Attack": 0,
  "Fairness/Incentives": 0,
  "FoundationModel": 0,
  "Vertical": 0,
  "Unlearning": 0,
  "Efficiency/Compression": 0,
  "Benchmark": 0,
  "ClientSelection": 0,
  "Graph": 0,
  "Other": 0,
  "Other_keywords": ""
}}

Return ONLY the JSON object, no other text.
"""
    
    model = genai.GenerativeModel('gemini-2.5-flash')  # Free tier model
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            response_mime_type="application/json"
        )
    )
    
    result = json.loads(response.text)
    return result


def categorize_with_ollama(title: str, abstract: str, model: str = "qwen2.5:7b") -> Dict:
    """Categorize using local Ollama."""
    import requests
    
    prompt = f"""{CATEGORY_DEFINITIONS}

**Paper to categorize:**

Title: {title}

Abstract: {abstract}

**Task:** Return a JSON object with category names as keys and values as follows:
- 1 if the paper belongs to this category (PRIMARY focus)
- 0 if not
For "Other", also include "Other_keywords" as a string with comma-separated keywords if Other=1.

Example format:
{{
  "Personalization": 0,
  "Heterogeneity/Generalization": 1,
  "DataProcessing": 0,
  "LLM/Agents": 0,
  "Privacy/Attack": 0,
  "Fairness/Incentives": 0,
  "FoundationModel": 0,
  "Vertical": 0,
  "Unlearning": 0,
  "Efficiency/Compression": 0,
  "Benchmark": 0,
  "ClientSelection": 0,
  "Graph": 0,
  "Other": 0,
  "Other_keywords": ""
}}

Return ONLY the JSON object, no other text.
"""
    
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            'model': model,
            'prompt': prompt,
            'stream': False,
            'format': 'json'
        },
        timeout=120
    )
    
    result = json.loads(response.json()['response'])
    return result


def categorize_paper_llm(title: str, abstract: str, backend: str = "openai", model: str = None) -> Dict:
    """
    Categorize a paper using LLM.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        backend: LLM backend to use
        model: Model name (for ollama: qwen2.5:7b, qwen2.5:32b, etc.)
    
    Returns:
        Dictionary with category names as keys and 1/0 as values
    """
    # Define all categories
    all_categories = [
        'Personalization', 'Heterogeneity/Generalization', 'DataProcessing',
        'LLM/Agents', 'Privacy/Attack', 'Fairness/Incentives', 'FoundationModel',
        'Vertical', 'Unlearning', 'Efficiency/Compression', 'Benchmark',
        'ClientSelection', 'Graph', 'Other', 'Other_keywords'
    ]
    
    try:
        if backend == "gemini":
            result = categorize_with_gemini(title, abstract)
        elif backend == "openai":
            result = categorize_with_openai(title, abstract)
        elif backend == "anthropic":
            result = categorize_with_anthropic(title, abstract)
        elif backend == "ollama":
            ollama_model = model if model else "qwen2.5:7b"
            result = categorize_with_ollama(title, abstract, model=ollama_model)
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        # Ensure all categories are present
        for cat in all_categories:
            if cat not in result:
                result[cat] = 0 if cat != 'Other_keywords' else ''
        
        return result
        
    except Exception as e:
        print(f"Error in LLM categorization: {e}")
        # Return empty categorization on error
        return {cat: 0 if cat != 'Other_keywords' else '' for cat in all_categories}


def test_single_paper(csv_file: str, row_index: int = 0, backend: str = "openai"):
    """
    Test categorization on a single paper.
    
    Args:
        csv_file: Path to CSV file
        row_index: Index of the paper to test (0-based, excluding header)
        backend: LLM backend to use
    """
    print("=" * 80)
    print(f"Testing LLM Categorization on Paper from: {csv_file}")
    print(f"Using backend: {backend}")
    print("=" * 80)
    
    df = pd.read_csv(csv_file)
    
    if row_index >= len(df):
        print(f"Error: Row index {row_index} out of range (file has {len(df)} papers)")
        return
    
    paper = df.iloc[row_index]
    title = paper['title']
    abstract = paper['abstract']
    
    print(f"\nPaper #{row_index + 1}:")
    print(f"Title: {title}")
    print(f"\nAbstract: {abstract[:300]}...")
    
    # Categorize
    print("\nCategorizing with LLM...")
    categories = categorize_paper_llm(title, abstract, backend=backend)
    
    print("\n" + "-" * 80)
    print("Categorization Results:")
    print("-" * 80)
    
    matched_cats = []
    for cat, value in categories.items():
        if cat == 'Other_keywords':
            continue
        if value == 1:
            matched_cats.append(cat)
            if cat == 'Other' and categories.get('Other_keywords'):
                print(f"✓ {cat}: {categories['Other_keywords']}")
            else:
                print(f"✓ {cat}")
    
    if not matched_cats:
        print("(No categories matched)")
    
    print("\n" + "=" * 80)


def categorize_csv_file_llm(input_csv: str, output_csv: str = None, backend: str = "openai", 
                            model: str = None, output_dir: str = None):
    """
    Categorize all papers in a CSV file using LLM and save results.
    
    Args:
        input_csv: Input CSV file path
        output_csv: Output CSV file path (if None, will auto-generate)
        backend: LLM backend to use
        model: Model name (for ollama: qwen2.5:7b, qwen2.5:32b, etc.)
        output_dir: Output directory (if specified, saves to this folder)
    """
    if output_csv is None:
        filename = os.path.basename(input_csv)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_csv = os.path.join(output_dir, filename.replace('.csv', '_categorized_llm.csv'))
        else:
            output_csv = input_csv.replace('.csv', '_categorized_llm.csv')
    
    print(f"\nProcessing: {input_csv}")
    print(f"Using LLM backend: {backend}")
    if model:
        print(f"Using model: {model}")
    
    df = pd.read_csv(input_csv)
    
    # Add category columns
    category_cols = [
        'Personalization', 'Heterogeneity/Generalization', 'DataProcessing',
        'LLM/Agents', 'Privacy/Attack', 'Fairness/Incentives', 'FoundationModel',
        'Vertical', 'Unlearning', 'Efficiency/Compression', 'Benchmark',
        'ClientSelection', 'Graph', 'Other', 'Other_keywords'
    ]
    
    for col in category_cols:
        df[col] = 0 if col != 'Other_keywords' else ''
    
    # Categorize each paper
    for idx, row in df.iterrows():
        print(f"\n[{idx + 1}/{len(df)}] {row['title'][:60]}...")
        
        categories = categorize_paper_llm(row['title'], row['abstract'], backend=backend, model=model)
        
        for cat, value in categories.items():
            df.at[idx, cat] = value
        
        # Show results
        matched = [cat for cat in category_cols if cat != 'Other_keywords' and categories.get(cat) == 1]
        print(f"  Categories: {', '.join(matched) if matched else 'None'}")
        
        # Rate limiting
        time.sleep(1)  # Be respectful to API
    
    # Save results
    df.to_csv(output_csv, index=False)
    print(f"\n✓ Saved categorized results to: {output_csv}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("Category Summary:")
    print("=" * 80)
    for col in category_cols:
        if col != 'Other_keywords':
            count = df[col].sum()
            percentage = (count / len(df) * 100) if len(df) > 0 else 0
            print(f"  {col:30s}: {int(count):3d} papers ({percentage:5.1f}%)")
    
    return output_csv


def main():
    """Main function."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM-based Paper Categorization Tool')
    parser.add_argument('--test', action='store_true', help='Test mode on specific paper')
    parser.add_argument('--all', action='store_true', help='Process all CSV files')
    parser.add_argument('--file', type=str, help='Process specific CSV file')
    parser.add_argument('--backend', type=str, default=os.environ.get("LLM_BACKEND", "ollama"),
                       help='LLM backend (gemini/openai/anthropic/ollama)')
    parser.add_argument('--model', type=str, default=None,
                       help='Model name (for ollama: qwen2.5:7b, qwen2.5:32b, etc.)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for categorized results')
    parser.add_argument('--input-dir', type=str, default='Raw',
                       help='Input directory containing CSV files (default: Raw)')
    parser.add_argument('--force', action='store_true',
                       help='Force re-processing even if output file already exists')
    parser.add_argument('--row-index', type=int, default=0,
                       help='Row index for test mode')
    
    args = parser.parse_args()
    
    # Default test file
    test_csv = 'icml_2024_federated_learning_2635_60.csv'
    
    if args.test:
        # Test mode
        test_single_paper(test_csv, row_index=args.row_index, backend=args.backend)
    elif args.all:
        # Categorize all CSV files
        import glob
        csv_pattern = os.path.join(args.input_dir, '*_federated_learning_*.csv')
        csv_files = glob.glob(csv_pattern)
        csv_files = [f for f in csv_files if '_categorized' not in f]
        
        if not csv_files:
            print(f"No CSV files found in {args.input_dir}/")
            return
        
        print(f"\nFound {len(csv_files)} CSV files in {args.input_dir}/")
        if args.output_dir:
            print(f"Output directory: {args.output_dir}/")
        if args.model:
            print(f"Using model: {args.model}")
        print()
        
        skipped = 0
        for csv_file in sorted(csv_files):
            if args.output_dir:
                out_name = os.path.basename(csv_file).replace('.csv', '_categorized_llm.csv')
                out_path = os.path.join(args.output_dir, out_name)
                if os.path.exists(out_path) and not args.force:
                    print(f"Skipping (already exists): {out_path}")
                    skipped += 1
                    continue
            categorize_csv_file_llm(csv_file, backend=args.backend, model=args.model, 
                                   output_dir=args.output_dir)
            print()
        
        if skipped:
            print(f"\nSkipped {skipped} already-categorized file(s). Use --force to re-process.")
    elif args.file:
        # Process specific file
        categorize_csv_file_llm(args.file, backend=args.backend, model=args.model,
                               output_dir=args.output_dir)
    else:
        parser.print_help()
        print("\nEnvironment variables:")
        print("  GEMINI_API_KEY    - For Google Gemini backend (default, free tier available)")
        print("  OPENAI_API_KEY    - For OpenAI backend")
        print("  ANTHROPIC_API_KEY - For Anthropic Claude backend")
        print("  LLM_BACKEND       - Backend to use (gemini/openai/anthropic/ollama)")
        print("\nExamples:")
        print("  # Test with default model (qwen2.5:7b)")
        print("  python categorize_papers_llm.py --test --row-index 0")
        print()
        print("  # Categorize all files with 7B model to default location")
        print("  python categorize_papers_llm.py --all --backend ollama")
        print()
        print("  # Categorize all files with 32B model to Categorized_32B folder")
        print("  python categorize_papers_llm.py --all --backend ollama --model qwen2.5:32b --output-dir Categorized_32B")
        print()
        print("  # Categorize specific file")
        print("  python categorize_papers_llm.py --file Raw/icml_2024_federated_learning.csv --model qwen2.5:32b")
        print()
        print("\nTo get a free Gemini API key:")
        print("  Visit: https://makersuite.google.com/app/apikey")
        print()


if __name__ == "__main__":
    main()

