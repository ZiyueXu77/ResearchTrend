#!/usr/bin/env python3
"""
Analyze author information to find top publishing groups and other statistics.
Supports reading from fl_summary.csv (with categories) or Authors_Analyzed/ directory.
"""

import csv
from collections import Counter, defaultdict
import argparse


CATEGORY_COLUMNS = [
    'Personalization', 'Heterogeneity/Generalization', 'DataProcessing',
    'LLM/Agents', 'Privacy/Attack', 'Fairness/Incentives',
    'FoundationModel', 'Vertical', 'Unlearning',
    'Efficiency/Compression', 'Benchmark', 'ClientSelection',
    'Graph', 'Other'
]


def load_from_summary(filepath='fl_summary.csv'):
    """Load from combined FL summary CSV (includes categories)."""
    papers = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper = {
                'title': row.get('title', ''),
                'last_author': row.get('last_author', '').strip(),
                'institution': row.get('institution', '').strip(),
                'conference': row.get('conference', 'Unknown').upper(),
                'year': int(row.get('year', 0)),
                'categories': {}
            }
            for col in CATEGORY_COLUMNS:
                val = row.get(col, '')
                if val == '':
                    val = row.get(col.split('/')[0], '')
                try:
                    paper['categories'][col] = int(val)
                except (ValueError, TypeError):
                    paper['categories'][col] = 0
            papers.append(paper)
    return papers


def has_categories(papers):
    """Check if any paper has non-zero category values."""
    return any(
        any(v == 1 for v in p['categories'].values())
        for p in papers
    )


def analyze_institutions(papers):
    """Analyze publication statistics by institution."""
    institution_counter = Counter()
    institution_by_year = defaultdict(lambda: defaultdict(int))
    institution_by_conference = defaultdict(lambda: defaultdict(int))
    institution_by_category = defaultdict(lambda: defaultdict(int))

    for paper in papers:
        inst = paper['institution']
        if inst:
            institution_counter[inst] += 1
            institution_by_year[inst][paper['year']] += 1
            institution_by_conference[inst][paper['conference']] += 1
            for cat, val in paper['categories'].items():
                if val == 1:
                    institution_by_category[inst][cat] += 1

    return {
        'overall': institution_counter,
        'by_year': institution_by_year,
        'by_conference': institution_by_conference,
        'by_category': institution_by_category
    }


def analyze_authors(papers):
    """Analyze publication statistics by author."""
    author_counter = Counter()
    author_institution = {}
    author_papers = defaultdict(list)
    author_by_category = defaultdict(lambda: defaultdict(int))

    for paper in papers:
        author = paper['last_author']
        if author:
            author_counter[author] += 1
            author_institution[author] = paper['institution']
            author_papers[author].append(paper['title'][:60])
            for cat, val in paper['categories'].items():
                if val == 1:
                    author_by_category[author][cat] += 1

    return {
        'counter': author_counter,
        'institution': author_institution,
        'papers': author_papers,
        'by_category': author_by_category
    }


def print_top_institutions(inst_stats, top_n=10, show_categories=False):
    """Print top N institutions."""
    print("\n" + "="*100)
    print(f"TOP {top_n} INSTITUTIONS BY NUMBER OF PAPERS")
    print("="*100)

    for i, (inst, count) in enumerate(inst_stats['overall'].most_common(top_n), 1):
        print(f"\n{i:2d}. {inst:50s} : {count:3d} papers")

        years = sorted(inst_stats['by_year'][inst].items())
        year_str = " | ".join([f"{year}: {cnt}" for year, cnt in years])
        print(f"    Years: {year_str}")

        confs = sorted(inst_stats['by_conference'][inst].items(),
                      key=lambda x: x[1], reverse=True)
        conf_str = " | ".join([f"{conf}: {cnt}" for conf, cnt in confs[:5]])
        print(f"    Conferences: {conf_str}")

        if show_categories and inst in inst_stats['by_category']:
            cats = sorted(inst_stats['by_category'][inst].items(),
                         key=lambda x: x[1], reverse=True)
            cat_str = " | ".join([f"{cat}: {cnt}" for cat, cnt in cats[:3]])
            if cat_str:
                print(f"    Top Categories: {cat_str}")


def print_top_authors(author_stats, top_n=10, min_papers=3, show_categories=False):
    """Print top N prolific authors."""
    print("\n" + "="*100)
    print(f"TOP {top_n} MOST PROLIFIC LAST AUTHORS (minimum {min_papers} papers)")
    print("="*100)

    prolific = [(author, count) for author, count in author_stats['counter'].most_common()
                if count >= min_papers]

    if not prolific:
        print(f"\n  (No authors with {min_papers}+ papers)")
        return

    for i, (author, count) in enumerate(prolific[:top_n], 1):
        inst = author_stats['institution'].get(author, 'Unknown')
        print(f"\n{i:2d}. {author:40s} : {count:2d} papers | {inst}")

        papers = author_stats['papers'][author]
        for j, title in enumerate(papers[:3], 1):
            print(f"    {j}. {title}...")
        if len(papers) > 3:
            print(f"    ... and {len(papers) - 3} more")

        if show_categories and author in author_stats['by_category']:
            cats = sorted(author_stats['by_category'][author].items(),
                         key=lambda x: x[1], reverse=True)
            cat_str = " | ".join([f"{cat}: {cnt}" for cat, cnt in cats[:3]])
            if cat_str:
                print(f"    Top Categories: {cat_str}")


def print_institution_trends(inst_stats, top_n=5):
    """Print publication trends for top institutions."""
    print("\n" + "="*100)
    print(f"PUBLICATION TRENDS FOR TOP {top_n} INSTITUTIONS")
    print("="*100)

    years = sorted(set(year for inst_years in inst_stats['by_year'].values()
                      for year in inst_years.keys()))

    print(f"\n{'Institution':<30s} | " + " | ".join([f"{year}" for year in years]))
    print("-" * 100)

    for inst, _ in inst_stats['overall'].most_common(top_n):
        year_counts = [str(inst_stats['by_year'][inst].get(year, 0)) for year in years]
        print(f"{inst:<30s} | " + " | ".join([f"{cnt:>4s}" for cnt in year_counts]))


def print_conference_breakdown(papers):
    """Print breakdown by conference type."""
    print("\n" + "="*100)
    print("CONFERENCE TYPE BREAKDOWN")
    print("="*100)

    ml_confs = ['ICLR', 'ICML', 'NEURIPS']
    cv_confs = ['CVPR', 'ICCV', 'ECCV', 'MICCAI']

    ml_papers = [p for p in papers if p['conference'] in ml_confs]
    cv_papers = [p for p in papers if p['conference'] in cv_confs]

    print(f"\nML Conferences (ICLR, ICML, NeurIPS): {len(ml_papers)} papers")
    print(f"CV Conferences (CVPR, ICCV, ECCV, MICCAI): {len(cv_papers)} papers")

    ml_insts = Counter([p['institution'] for p in ml_papers if p['institution']])
    cv_insts = Counter([p['institution'] for p in cv_papers if p['institution']])

    print("\nTop 5 ML Conference Publishers:")
    for i, (inst, count) in enumerate(ml_insts.most_common(5), 1):
        print(f"  {i}. {inst:40s} : {count:3d} papers")

    print("\nTop 5 CV Conference Publishers:")
    for i, (inst, count) in enumerate(cv_insts.most_common(5), 1):
        print(f"  {i}. {inst:40s} : {count:3d} papers")


def print_category_breakdown(papers):
    """Print breakdown by research category."""
    print("\n" + "="*100)
    print("RESEARCH CATEGORY BREAKDOWN")
    print("="*100)

    category_counts = defaultdict(int)
    for paper in papers:
        for cat, val in paper['categories'].items():
            if val == 1:
                category_counts[cat] += 1

    print("\nPapers by Category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:25s}: {count:3d} papers")


def generate_summary(papers):
    """Generate overall summary statistics."""
    print("\n" + "="*100)
    print("OVERALL STATISTICS")
    print("="*100)

    total_papers = len(papers)
    papers_with_author = sum(1 for p in papers if p['last_author'])
    papers_with_inst = sum(1 for p in papers if p['institution'])

    unique_authors = len(set(p['last_author'] for p in papers if p['last_author']))
    unique_institutions = len(set(p['institution'] for p in papers if p['institution']))

    print(f"\nTotal papers analyzed: {total_papers}")
    print(f"Papers with last author: {papers_with_author} ({papers_with_author/total_papers*100:.1f}%)")
    print(f"Papers with institution: {papers_with_inst} ({papers_with_inst/total_papers*100:.1f}%)")
    print(f"\nUnique last authors: {unique_authors}")
    print(f"Unique institutions: {unique_institutions}")

    year_dist = Counter([p['year'] for p in papers if p['year']])
    print(f"\nPapers by year:")
    for year in sorted(year_dist.keys()):
        print(f"  {year}: {year_dist[year]} papers")

    conf_dist = Counter([p['conference'] for p in papers if p['conference']])
    print(f"\nPapers by conference:")
    for conf in sorted(conf_dist.keys()):
        print(f"  {conf}: {conf_dist[conf]} papers")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze author and institution statistics from federated learning papers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 8_analyze_author_stats.py
  python3 8_analyze_author_stats.py --top 15 --min-papers 2
  python3 8_analyze_author_stats.py --input my_summary.csv
        """
    )
    parser.add_argument(
        '--input',
        type=str,
        default='fl_summary.csv',
        help='Path to FL summary CSV file (default: fl_summary.csv)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Number of top institutions/authors to show (default: 10)'
    )
    parser.add_argument(
        '--min-papers',
        type=int,
        default=3,
        help='Minimum papers for author to be listed (default: 3)'
    )

    args = parser.parse_args()

    print("="*100)
    print("FEDERATED LEARNING RESEARCH - AUTHOR & INSTITUTION ANALYSIS")
    print("="*100)

    print(f"\nLoading data from {args.input}...")
    papers = load_from_summary(args.input)

    if not papers:
        return

    print(f"Loaded {len(papers)} papers")

    show_cats = has_categories(papers)

    generate_summary(papers)

    inst_stats = analyze_institutions(papers)
    print_top_institutions(inst_stats, args.top, show_categories=show_cats)
    print_institution_trends(inst_stats, min(5, args.top))

    author_stats = analyze_authors(papers)
    print_top_authors(author_stats, args.top, args.min_papers, show_categories=show_cats)

    print_conference_breakdown(papers)

    if show_cats:
        print_category_breakdown(papers)

    print("\n" + "="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
