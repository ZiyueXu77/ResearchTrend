#!/usr/bin/env python3
"""
Script to analyze federated learning research trends across ML and CV conferences.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re
from pathlib import Path
import numpy as np
import argparse

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11

# Conference groupings
ML_CONFERENCES = ['neurips', 'icml', 'iclr']
CV_CONFERENCES = ['cvpr', 'iccv', 'miccai', 'eccv']
YEARS = [2023, 2024, 2025, 2026]

CATEGORY_NAMES = [
    'Personalization', 'Heterogeneity/Generalization', 'DataProcessing',
    'LLM/Agents', 'Privacy/Attack', 'Fairness/Incentives', 'FoundationModel',
    'Vertical', 'Unlearning', 'Efficiency/Compression', 'Benchmark',
    'ClientSelection', 'Graph', 'Other'
]

# Consistent color mapping for categories
CATEGORY_COLORS = {
    'Personalization': '#FF6B6B',
    'Heterogeneity/Generalization': '#4ECDC4',
    'DataProcessing': '#45B7D1',
    'LLM/Agents': '#FFA07A',
    'Privacy/Attack': '#98D8C8',
    'Fairness/Incentives': '#F7B731',
    'FoundationModel': '#5F27CD',
    'Vertical': '#00D2D3',
    'Unlearning': '#FF9FF3',
    'Efficiency/Compression': '#54A0FF',
    'Benchmark': '#48DBFB',
    'ClientSelection': '#1DD1A1',
    'Graph': '#FD79A8',
    'Other': '#A4B0BE',
    'Other Categories': '#95A5A6'
}


def parse_filename(filename):
    """
    Parse conference CSV filename to extract metadata.
    
    Filename format: conference_year_federated_learning_totalpapers_federatedpapers.csv
    Example: neurips_2023_federated_learning_3585_59.csv
    
    Returns:
        dict with conference, year, total_papers, federated_papers
    """
    match = re.match(r'(\w+)_(\d{4})_federated_learning_(\d+)_(\d+)', Path(filename).stem)
    if match:
        return {
            'conference': match.group(1),
            'year': int(match.group(2)),
            'total_papers': int(match.group(3)),
            'federated_papers': int(match.group(4))
        }
    return None


def load_all_categorized_data(input_dir='Categorized_32B'):
    """
    Load all categorized CSV files and aggregate metadata.
    
    Args:
        input_dir: Directory containing categorized CSV files
    
    Returns:
        tuple of (metadata_df, category_data)
    """
    csv_files = glob.glob(f'{input_dir}/*_federated_learning_*_categorized_llm.csv')
    
    if not csv_files:
        print(f"Error: No categorized CSV files found in '{input_dir}'!")
        print("Please run categorization first: python categorize_papers_llm.py --all")
        return None, None
    
    metadata = []
    all_categories = []
    
    for csv_file in csv_files:
        # Parse filename
        info = parse_filename(csv_file)
        if not info:
            print(f"Warning: Could not parse filename: {csv_file}")
            continue
        
        # Determine conference type
        if info['conference'] in ML_CONFERENCES:
            info['type'] = 'ML'
        elif info['conference'] in CV_CONFERENCES:
            info['type'] = 'CV'
        else:
            info['type'] = 'Other'
        
        metadata.append(info)
        
        # Load category data
        try:
            df = pd.read_csv(csv_file)
            
            # Count papers in each category
            category_counts = {}
            for cat in CATEGORY_NAMES:
                if cat in df.columns:
                    category_counts[cat] = df[cat].sum()
                else:
                    category_counts[cat] = 0
            
            category_counts.update(info)
            all_categories.append(category_counts)
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    
    metadata_df = pd.DataFrame(metadata)
    category_df = pd.DataFrame(all_categories)
    
    return metadata_df, category_df


def plot_papers_over_years(metadata_df, output_dir='plots', suffix=''):
    """
    Plot 1: Number of federated learning papers across years for ML vs CV.
    
    Args:
        metadata_df: DataFrame with metadata
        output_dir: Directory to save plots
        suffix: Suffix to add to filename (e.g., '_32B')
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    # Aggregate by type and year
    agg_data = metadata_df.groupby(['type', 'year'])['federated_papers'].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for conf_type in ['ML', 'CV']:
        data = agg_data[agg_data['type'] == conf_type]
        ax.plot(data['year'], data['federated_papers'], 
                marker='o', linewidth=2.5, markersize=10, 
                label=f'{conf_type} Conferences')
        
        # Add value labels
        for _, row in data.iterrows():
            ax.text(row['year'], row['federated_papers'] + 5, 
                   str(int(row['federated_papers'])), 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Federated Learning Papers', fontsize=13, fontweight='bold')
    ax.set_title(f'Federated Learning Papers: ML vs CV Conferences ({YEARS[0]}-{YEARS[-1]})', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(YEARS)
    
    plt.tight_layout()
    filename = f'{output_dir}/papers_over_years{suffix}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {filename}")
    plt.close()


def plot_federated_ratio(metadata_df, output_dir='plots', suffix=''):
    """
    Plot 2: Federated papers / All papers ratio bar plot.
    
    Args:
        metadata_df: DataFrame with metadata
        output_dir: Directory to save plots
        suffix: Suffix to add to filename (e.g., '_32B')
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    # Aggregate by type and year
    agg_data = metadata_df.groupby(['type', 'year']).agg({
        'total_papers': 'sum',
        'federated_papers': 'sum'
    }).reset_index()
    
    agg_data['ratio'] = (agg_data['federated_papers'] / agg_data['total_papers']) * 100
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(YEARS))
    width = 0.35
    
    ml_ratios = [agg_data[(agg_data['type']=='ML') & (agg_data['year']==y)]['ratio'].values[0] 
                 if len(agg_data[(agg_data['type']=='ML') & (agg_data['year']==y)]) > 0 else 0 
                 for y in YEARS]
    cv_ratios = [agg_data[(agg_data['type']=='CV') & (agg_data['year']==y)]['ratio'].values[0] 
                 if len(agg_data[(agg_data['type']=='CV') & (agg_data['year']==y)]) > 0 else 0 
                 for y in YEARS]
    
    bars1 = ax.bar(x - width/2, ml_ratios, width, label='ML Conferences', 
                   color='#3498db', edgecolor='black', linewidth=1.2)
    bars2 = ax.bar(x + width/2, cv_ratios, width, label='CV Conferences', 
                   color='#e74c3c', edgecolor='black', linewidth=1.2)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}%',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Federated Papers / All Papers (%)', fontsize=13, fontweight='bold')
    ax.set_title('Percentage of Federated Learning Papers in ML vs CV Conferences',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(YEARS)
    ax.legend(fontsize=12)
    ax.grid(True, axis='y', alpha=0.3)
    
    plt.tight_layout()
    filename = f'{output_dir}/federated_ratio{suffix}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {filename}")
    plt.close()


def plot_category_distribution(category_df, output_dir='plots', suffix=''):
    """
    Plot 3: Pie charts of research categories for each year (ML vs CV).
    
    Args:
        category_df: DataFrame with category data
        output_dir: Directory to save plots
        suffix: Suffix to add to filename (e.g., '_32B')
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    n_years = len(YEARS)
    
    for conf_type in ['ML', 'CV']:
        fig, axes = plt.subplots(1, n_years, figsize=(6 * n_years, 6))
        if n_years == 1:
            axes = [axes]
        fig.suptitle(f'{conf_type} Conferences: Research Category Distribution by Year', 
                     fontsize=16, fontweight='bold', y=1.02)
        
        for idx, year in enumerate(YEARS):
            ax = axes[idx]
            
            # Filter data for this type and year
            data = category_df[(category_df['type'] == conf_type) & 
                              (category_df['year'] == year)]
            
            if len(data) == 0:
                ax.text(0.5, 0.5, f'No data\nfor {year}', 
                       ha='center', va='center', fontsize=14)
                ax.set_title(f'{year}', fontsize=14, fontweight='bold')
                continue
            
            # Sum categories across all conferences of this type in this year
            category_sums = {}
            for cat in CATEGORY_NAMES:
                if cat in data.columns:
                    total = data[cat].sum()
                    if total > 0:
                        category_sums[cat] = total
            
            if not category_sums:
                ax.text(0.5, 0.5, f'No categories\nfor {year}', 
                       ha='center', va='center', fontsize=14)
                ax.set_title(f'{year}', fontsize=14, fontweight='bold')
                continue
            
            # Sort by value and take top categories
            sorted_cats = sorted(category_sums.items(), key=lambda x: x[1], reverse=True)
            
            # Group small categories into "Other" if there are too many
            if len(sorted_cats) > 8:
                top_cats = sorted_cats[:7]
                other_sum = sum([v for _, v in sorted_cats[7:]])
                if other_sum > 0:
                    top_cats.append(('Other Categories', other_sum))
                sorted_cats = top_cats
            
            labels = [cat for cat, _ in sorted_cats]
            sizes = [val for _, val in sorted_cats]
            
            # Create pie chart with consistent colors
            colors = [CATEGORY_COLORS.get(cat, '#95A5A6') for cat in labels]
            wedges, texts, autotexts = ax.pie(sizes, labels=None, autopct='%1.1f%%',
                                               colors=colors, startangle=90,
                                               textprops={'fontsize': 9, 'fontweight': 'bold'})
            
            # Add legend
            ax.legend(wedges, labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1),
                     fontsize=9)
            
            total_papers = data['federated_papers'].sum()
            ax.set_title(f'{year}\n({int(total_papers)} papers)', 
                        fontsize=13, fontweight='bold')
        
        plt.tight_layout()
        filename = f'{output_dir}/categories_{conf_type.lower()}{suffix}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filename}")
        plt.close()


def generate_summary_statistics(metadata_df, category_df):
    """
    Generate and print summary statistics.
    """
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    # Overall statistics
    print("\n📊 Overall Statistics:")
    print(f"  Total papers analyzed: {metadata_df['federated_papers'].sum()}")
    print(f"  ML conferences: {metadata_df[metadata_df['type']=='ML']['federated_papers'].sum()} papers")
    print(f"  CV conferences: {metadata_df[metadata_df['type']=='CV']['federated_papers'].sum()} papers")
    
    # Year-by-year breakdown
    print("\n📈 Year-by-Year Breakdown:")
    for year in YEARS:
        ml_papers = metadata_df[(metadata_df['type']=='ML') & (metadata_df['year']==year)]['federated_papers'].sum()
        cv_papers = metadata_df[(metadata_df['type']=='CV') & (metadata_df['year']==year)]['federated_papers'].sum()
        total = ml_papers + cv_papers
        print(f"  {year}: {total:3d} papers (ML: {ml_papers:3d}, CV: {cv_papers:3d})")
    
    # Top categories overall
    print("\n🏆 Top Research Categories (Overall):")
    category_totals = {}
    for cat in CATEGORY_NAMES:
        if cat in category_df.columns:
            category_totals[cat] = category_df[cat].sum()
    
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    for idx, (cat, count) in enumerate(sorted_cats[:10], 1):
        if count > 0:
            percentage = (count / metadata_df['federated_papers'].sum()) * 100
            print(f"  {idx:2d}. {cat:30s}: {int(count):3d} papers ({percentage:5.1f}%)")
    
    # Growth trends
    print("\n📊 Growth Trends:")
    first_year, last_year = YEARS[0], YEARS[-1]
    for conf_type in ['ML', 'CV']:
        papers_first = metadata_df[(metadata_df['type']==conf_type) & (metadata_df['year']==first_year)]['federated_papers'].sum()
        papers_last = metadata_df[(metadata_df['type']==conf_type) & (metadata_df['year']==last_year)]['federated_papers'].sum()
        if papers_first > 0:
            growth = ((papers_last - papers_first) / papers_first) * 100
            print(f"  {conf_type} conferences: {growth:+.1f}% ({first_year}→{last_year})")


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(
        description='Analyze federated learning research trends from categorized papers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze default 7B model output (from Categorized/)
  python3 analyze_research_trends.py
  
  # Analyze 32B model output with _32B suffix
  python3 analyze_research_trends.py --input-dir Categorized_32B --suffix _32B
  
  # Compare different models by using different suffixes
  python3 analyze_research_trends.py --input-dir Categorized_7B --suffix _7B
  python3 analyze_research_trends.py --input-dir Categorized_32B --suffix _32B
        """
    )
    parser.add_argument('--input-dir', default='Categorized_32B',
                       help='Directory containing categorized CSV files (default: Categorized)')
    parser.add_argument('--suffix', default='',
                       help='Suffix to add to output filenames, e.g., "_32B" (default: none)')
    parser.add_argument('--output-dir', default='plots',
                       help='Directory to save output plots (default: plots)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("Federated Learning Research Trend Analysis")
    print("="*80)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Filename suffix: {args.suffix if args.suffix else '(none)'}")
    print("="*80)
    
    # Load data
    print("\n📂 Loading categorized data...")
    metadata_df, category_df = load_all_categorized_data(args.input_dir)
    
    if metadata_df is None:
        return
    
    print(f"✓ Loaded {len(metadata_df)} conference-year combinations")
    
    # Generate summary statistics
    generate_summary_statistics(metadata_df, category_df)
    
    # Create output directory
    Path(args.output_dir).mkdir(exist_ok=True)
    print(f"\n📊 Generating visualizations in '{args.output_dir}/' directory...")
    
    # Generate plots
    print("\n1. Plotting papers over years...")
    plot_papers_over_years(metadata_df, args.output_dir, args.suffix)
    
    print("2. Plotting federated paper ratio...")
    plot_federated_ratio(metadata_df, args.output_dir, args.suffix)
    
    print("3. Plotting category distributions...")
    plot_category_distribution(category_df, args.output_dir, args.suffix)
    
    print("\n" + "="*80)
    print("✅ Analysis complete!")
    print(f"📁 All plots saved in '{args.output_dir}/' directory")
    if args.suffix:
        print(f"📝 Filenames include suffix: {args.suffix}")
    print("="*80)


if __name__ == "__main__":
    main()

