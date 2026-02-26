# Federated Learning Research Trend Analysis

A comprehensive pipeline for scraping, categorizing, and analyzing federated learning research papers across major ML and CV conferences (2023-2025).

## Overview

This project provides tools to:
1. **Scrape** federated learning papers with abstracts and links from multiple conferences
2. **Categorize** papers using LLM-based semantic analysis
3. **Download PDFs** for each paper automatically
4. **Extract** FL platform mentions from paper PDFs
5. **Analyze** platform usage (USED vs MENTIONED) using LLM
6. **Visualize** research trends and platform adoption patterns

## Conferences Covered

### ML Conferences
- **NeurIPS** (2023, 2024, 2025)
- **ICML** (2023, 2024, 2025)
- **ICLR** (2023, 2024, 2025, 2026)

### CV Conferences
- **CVPR** (2023, 2024, 2025)
- **ICCV** (2023, 2025)
- **ECCV** (2024)
- **MICCAI** (2023, 2024, 2025)

## Project Structure

```
ResearchTrend/
├── Raw/                          # Raw scraped CSV files
│   └── {conf}_{year}_federated_learning_{total}_{fl_count}.csv
├── Categorized/                  # LLM-categorized CSV files (default with 7B model)
│   └── {conf}_{year}_federated_learning_{total}_{fl_count}_categorized_llm.csv
├── Categorized_32B/              # LLM-categorized with 32B model (optional)
│   └── {conf}_{year}_federated_learning_{total}_{fl_count}_categorized_llm.csv
├── Platform/                     # Platform mentions extracted from PDFs
│   └── {conf}_{year}_federated_learning_{total}_{fl_count}_platform.csv
├── Platform_Analyzed/            # LLM-analyzed platform usage (USED vs MENTIONED)
│   └── {conf}_{year}_federated_learning_{total}_{fl_count}_platform_analyzed.csv
├── PDFs/                         # Downloaded PDFs organized by conference/year
│   ├── neurips/
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   └── ...
├── plots/                        # Generated analysis plots
│   ├── papers_over_years.png
│   ├── federated_ratio.png
│   ├── categories_ml.png
│   ├── categories_cv.png
│   ├── platform_usage_over_years.png
│   ├── top_platforms_used.png
│   └── platform_by_conference_type.png
├── platform_details_manual_checked.csv          # Final cleaned list of USED platforms
├── fl_summary.csv                # Combined summary with categories (output of combine_all_data.py)
├── 1_categorize_papers_llm.py     # LLM-based categorization script
├── 2_download_pdfs.py            # Download PDFs from conference sites
├── 3_extract_paper_info.py       # Extract authors + platform mentions from PDFs
├── 4_analyze_paper_info.py       # LLM: last author/institution + platform USED/MENTIONED
├── 5_analyze_research_trends.py  # Trend analysis and visualization
├── 4.1_check_institution_name.py # Normalize institution names in Analyzed/
├── 6.1_append_new_record.py      # Append new platform records for manual review
├── 6.2_plot_platform_trends.py   # Plot platform trends from reviewed data
├── 7_combine_all_data.py          # Merge all data sources into one master CSV
└── 8_analyze_author_stats.py     # Author & institution statistics
```

## Installation

1. Create and activate conda environment:

```bash
conda create -n research python=3.12
conda activate research
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. For LLM categorization, set up Local Ollama:

```bash
# Install Ollama (https://ollama.ai)
ollama pull qwen2.5:32b  # Or qwen2:7b for faster processing
```

## Usage

### 1. Scrape Papers

The papers have already been scraped and saved in the `Raw/` directory. Each CSV contains:
- `title`: Paper title
- `link`: Direct link to paper
- `abstract`: Paper abstract

Filename format: `{conference}_{year}_federated_learning_{total_papers}_{federated_papers}.csv`

### 2. Categorize Papers

Categorize papers using LLM-based semantic analysis:

**Advanced Usage (32B model for better accuracy):**
```bash
python 1_categorize_papers_llm.py --all --backend ollama --model qwen2.5:32b --output-dir Categorized_32B
```

**Test Before Full Run:**
```bash
python 1_categorize_papers_llm.py --test --backend ollama --model qwen2.5:32b
```

**Backends available:**
- `ollama` (default) - Local, free, recommended
- `gemini` - Google Gemini API
- `openai` - OpenAI GPT-4
- `anthropic` - Anthropic Claude

**Command Line Options:**
- `--all`: Process all CSV files from input directory
- `--file FILE`: Process a specific CSV file
- `--backend BACKEND`: LLM backend to use (default: ollama)
- `--model MODEL`: Model name for Ollama (e.g., `qwen2.5:7b`, `qwen2.5:32b`, `gemma2:27b`)
- `--output-dir DIR`: Output directory for categorized results (default: same as input)
- `--input-dir DIR`: Input directory containing CSV files (default: `Raw`)
- `--test`: Test mode on a single paper
- `--row-index N`: Row index for test mode (default: 0)

**Categories:**
- Personalization
- Heterogeneity/Generalization
- DataProcessing
- LLM/Agents
- Privacy/Attack
- Fairness/Incentives
- FoundationModel
- Vertical
- Unlearning
- Efficiency/Compression
- Benchmark
- ClientSelection
- Graph
- Other

**Output Locations:**
- Default: `Categorized/{conference}_{year}_*.csv`
- With `--output-dir`: `{output-dir}/{conference}_{year}_*.csv`
- Example: `Categorized_32B/{conference}_{year}_*.csv`

**Model Comparison:**

| Model | Speed | Quality | Memory | Use Case |
|-------|-------|---------|--------|----------|
| qwen2.5:7b | Fast | Good | 8GB | Quick iteration, testing |
| qwen2.5:32b | Slower | Excellent | 20GB+ | Final analysis, publication |
| gemma2:27b | Medium | Very Good | 16GB | Alternative option |

### 3. Download PDFs

Download PDFs for all papers:

```bash
python 2_download_pdfs.py --all
```

**Options:**
- `--all`: Download PDFs for all papers
- `--retry-failed`: Retry only failed downloads

PDFs are organized in: `PDFs/{conference}/{year}/{title}.pdf`

**Note:** Some papers (MICCAI 2023, some NeurIPS papers) may require manual download due to access restrictions.

### 4. Extract Paper Info (Authors + Platform Mentions)

Extract author blocks and FL platform mentions from PDFs in one pass:

```bash
python 3_extract_paper_info.py --all
```

This reads each PDF once to:
- Extract the author block (between title and abstract, plus footnote affiliations)
- Search for FL platform keywords and extract the sentences they appear in

Output: `Enriched/{conference}_{year}_federated_learning_{total}_{fl}_enriched.csv`

**Supported platforms:**
- Flower, FederatedScope, FedML, TensorFlow Federated, FedScale, NVIDIA FLARE, LEAF, FATE, PySyft, PaddleFL, OpenFL

### 5. Analyze Paper Info (LLM: Authors + Platform Usage)

Use LLM to extract last author/institution AND classify platform usage in one pass:

```bash
python 4_analyze_paper_info.py --all --model qwen2.5:32b
```

For each paper the LLM:
- Extracts the **last author** name and **institution** (full official name, e.g., "Wuhan University" not "Wuhan") from the author block
- Classifies each platform mention as **USED** or **MENTIONED**

Output: `Analyzed/{conference}_{year}_federated_learning_{total}_{fl}_analyzed.csv`

**Post-processing:**
The analysis needs further manual review and filtering to remove false positives:
- Dataset mentions (e.g., "LEAF benchmark", "FedML dataset") → MENTIONED
- Citation-only references → MENTIONED
- Comparison tables → MENTIONED

Final cleaned results saved to:
- `platform_details_manual_checked.csv` - Papers that USED platforms

**Classification Accuracy:** 100% after manual review (0 false negatives, 4 false positives removed)

### 6. Normalize Institution Names

Standardize institution names in `Analyzed/` CSVs (expand abbreviations, merge variants):

```bash
# Preview changes (dry run)
python 4.1_check_institution_name.py

# Apply changes to Analyzed/ CSVs
python 4.1_check_institution_name.py --apply
```

- Expands abbreviations to full names (e.g., `HUST` → `Huazhong University of Science and Technology`)
- Merges variant spellings (e.g., `Pennsylvania State University` / `The Pennsylvania State University`)
- Normalizes UC system names (e.g., `UCLA` → `University of California, Los Angeles`)
- Flags remaining uncertain cases for manual review
- Add new mappings to `INSTITUTION_MAP` in the script as needed

### 7. Analyze Research Trends

Generate visualizations and statistics for research categories:

```bash
python 5_analyze_research_trends.py
```

**Generated plots:**
- `papers_over_years.png` - Number of FL papers across years (ML vs CV)
- `federated_ratio.png` - Percentage of FL papers in total submissions
- `categories_ml.png` - Research category distribution for ML conferences (2023-2025)
- `categories_cv.png` - Research category distribution for CV conferences (2023-2025)

### 7. Analyze Platform Trends (Two-Step with Manual Review)

Platform trend analysis is split into two steps to allow manual review of auto-extracted records:

**Step 7a: Append new platform records**
```bash
python 6.1_append_new_record.py
```
- Scans all `Analyzed/*_analyzed.csv` files for papers with `platform_used` set
- Compares against existing records in `platform_details_manual_checked.csv`
- Appends only **new** records and prints a summary of what was added
- **After running:** manually review and correct the new entries in `platform_details_manual_checked.csv`

**Step 7b: Plot platform trends (after manual review)**
```bash
python 6.2_plot_platform_trends.py
```
- Reads from the manually reviewed `platform_details_manual_checked.csv`
- Generates plots and prints summary statistics

**Generated plots:**
- `platform_usage_over_years.png` - Platform adoption trends over years (ML vs CV)
- `top_platforms_used.png` - Most used FL platforms
- `platform_by_conference_type.png` - Platform adoption by ML vs CV conferences with year breakdown



### Combine All Data

Merge per-conference data from `Raw/`, `Analyzed/`, and `Categorized_32B/` into a single master CSV:

```bash
python 7_combine_all_data.py
```

**Options:**
- `--raw-dir DIR`: Raw CSV directory (default: `Raw`)
- `--analyzed-dir DIR`: Analyzed CSV directory (default: `Analyzed`)
- `--categorized-dir DIR`: Categorized CSV directory (default: `Categorized_32B`)
- `--output FILE`: Output file name (default: `fl_summary.csv`)

Papers are matched by title across sources. The output includes data completeness statistics.

### Analyze Author & Institution Statistics

Generate console reports on top institutions, prolific last authors, publication trends, and conference breakdowns:

```bash
python 8_analyze_author_stats.py

# Show top 15 with minimum 2 papers
python 8_analyze_author_stats.py --top 15 --min-papers 2
```

**Options:**
- `--input FILE`: Path to summary CSV (default: `fl_summary.csv`)
- `--top N`: Number of top institutions/authors to show (default: 10)
- `--min-papers N`: Minimum papers for an author to be listed (default: 3)

## Technical Details

### Scraping Approach
- ML conferences: Direct scraping from virtual conference sites
- CV conferences: Mix of direct scraping and search-based filtering
- MICCAI: Two-hop navigation to paper pages for abstracts

### PDF Download Strategy
- Conference-specific logic for each venue
- Handles OpenReview, CVF Open Access, Springer, PMLR
- Retry mechanism with exponential backoff
- Rate limiting to respect server resources

### LLM Categorization
- **Model Options:** Support for multiple models (qwen2.5:7b, qwen2.5:32b, gemma2, etc.)
- **Conservative Approach:** Only assigns categories with high confidence
- **Structured Output:** JSON parsing for consistent results
- **Detailed Prompts:** Category descriptions with clear examples
- **Multi-Category:** Papers can belong to multiple categories
- **Flexible Backends:** Ollama (local), Gemini, OpenAI, Anthropic
- **Quality:** 32B model recommended for publication-quality results

### Platform Usage Analysis (LLM-based Classification)

**Two-Stage Analysis Pipeline:**

1. **Stage 1: PDF Extraction** (`3_extract_paper_info.py`)
   - Extracts author blocks and FL platform keyword mentions from PDFs
   - Uses PyMuPDF for text extraction
   - Single PDF read for both tasks

2. **Stage 2: LLM Analysis** (`4_analyze_paper_info.py`)
   - Extracts last author/institution from author blocks
   - Classifies platform mentions as USED vs MENTIONED
   - Uses Ollama (qwen2.5:32b recommended) for both tasks in one pass
   - Conservative classification: when uncertain → MENTIONED

**Classification Guidelines (LLM Prompt):**

USED indicators:
- "implemented using", "built on", "experiments conducted with"
- "we use [platform]", "our implementation uses"
- "code available at [platform]"

MENTIONED indicators:
- Citations with arXiv numbers, years, authors
- "compared to", "unlike", "differs from"
- Dataset names (e.g., "LEAF benchmark", "FedML dataset")
- Survey/review mentions without implementation

**Quality Assurance Process:**
1. LLM classification (qwen2.5:32b)
2. Manual review of all USED classifications
3. False positive identification and removal (3 papers)
4. False negative review of MENTIONED papers (0 found)
5. Final accuracy: 100% on 144 papers analyzed

**Key Challenges Addressed:**
- **Dataset vs Platform:** "LEAF benchmark" → MENTIONED (dataset, not platform)
- **Dataset vs Platform:** "Flowers102 dataset" → Not Flower platform
- **Utility vs Platform:** "TFF dataset preprocessing" → MENTIONED (data utility only)
- **Citation vs Usage:** Papers with only bibliography mentions → MENTIONED

## Workflow Examples

### Complete Analysis Pipeline

```bash
# 1. Activate environment
conda activate research

# 2. Categorize papers (choose model based on needs)
python 1_categorize_papers_llm.py --all --backend ollama --model qwen2.5:32b --output-dir Categorized_32B

# 3. Extract authors + platform mentions from PDFs
python 3_extract_paper_info.py --all

# 4. LLM analysis: last author/institution + platform USED/MENTIONED
python 4_analyze_paper_info.py --all --model qwen2.5:32b

# 5. Normalize institution names
python 4.1_check_institution_name.py --apply

# 6. Combine all data into a master CSV
python 7_combine_all_data.py

# 6. Generate research trend plots
python 5_analyze_research_trends.py

# 7a. Append new platform records, then manually review
python 6.1_append_new_record.py
# → Manually review platform_details_manual_checked.csv

# 7b. Generate platform trend plots (after manual review)
python 6.2_plot_platform_trends.py

# 8. Author & institution statistics
python 8_analyze_author_stats.py
```

### Comparing Different Models

To compare results between 7B and 32B models:

```bash
# Run with 7B model (faster)
python 1_categorize_papers_llm.py --all --model qwen2.5:7b --output-dir Categorized_7B

# Run with 32B model (more accurate)
python 1_categorize_papers_llm.py --all --model qwen2.5:32b --output-dir Categorized_32B

# Compare results
diff Categorized_7B/icml_2024_*.csv Categorized_32B/icml_2024_*.csv
```

### Processing Specific Conferences

```bash
# Process only ML conferences
python 1_categorize_papers_llm.py --file Raw/neurips_2025_*.csv --model qwen2.5:32b
python 1_categorize_papers_llm.py --file Raw/icml_2025_*.csv --model qwen2.5:32b
python 1_categorize_papers_llm.py --file Raw/iclr_2025_*.csv --model qwen2.5:32b

# Process only CV conferences
python 1_categorize_papers_llm.py --file Raw/cvpr_2025_*.csv --model qwen2.5:32b
python 1_categorize_papers_llm.py --file Raw/iccv_2025_*.csv --model qwen2.5:32b
```

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve

# Pull required model
ollama pull qwen2.5:32b
```

### PDF Extraction Errors

If platform extraction fails for some PDFs:
1. Check PDF is readable: `pdftotext PDFs/conference/year/title.pdf`
2. Verify PDF structure: Some scanned PDFs may need OCR
3. Manual review: Check `platform_mentioned.csv` for missed platforms

### Memory Issues with Large Models

If qwen2.5:32b runs out of memory:
1. Close other applications
2. Use smaller model: `--model qwen2.5:14b`
3. Process files one at a time: `--file` instead of `--all`
4. Consider using API backend: `--backend gemini`

### False Positive/Negative Review

To manually review platform classifications:
```bash
# Check all USED platforms
cat platform_details.csv | grep "PLATFORM_NAME"

# Check all MENTIONED platforms  
cat platform_mentioned.csv | grep "PLATFORM_NAME"

# Verify specific paper
grep "Paper Title" Platform_Analyzed/*.csv
```

## Data Quality & Validation

### Manual Review Process

All platform classifications underwent rigorous manual review:

1. **Initial LLM Classification:** qwen2.5:32b analyzed 144 papers with platform mentions
2. **False Positive Review:** 4 papers incorrectly classified as USED were corrected
   - 3 from initial systematic review
   - 1 from user feedback (citation in related work section)
3. **False Negative Review:** 111 MENTIONED papers checked for missed usage (0 found)
4. **Final Accuracy:** 100% on 144 papers (33 USED, 111 MENTIONED)
