#!/usr/bin/env python3
"""
Plot FL platform usage trends from manually checked platform_details_manual_checked.csv.
Run after manual review of records appended by 6.1_append_new_record.py.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11

ML_CONFERENCES = ['neurips', 'icml', 'iclr']
CV_CONFERENCES = ['cvpr', 'iccv', 'miccai', 'eccv']

PLATFORM_COLORS = {
    'Flower': '#FF6B6B',
    'FederatedScope': '#4ECDC4',
    'FedML': '#45B7D1',
    'TensorFlow Federated': '#FFA07A',
    'FedScale': '#54A0FF',
    'NVIDIA FLARE': '#5F27CD',
    'LEAF': '#1DD1A1',
    'FATE': '#FD79A8',
    'PySyft': '#00D2D3',
    'PaddleFL': '#48DBFB',
    'OpenFL': '#F7B731',
}

CHECKED_CSV = 'platform_details_manual_checked.csv'


def load_data():
    """Load and parse platform data from manually checked CSV."""
    df = pd.read_csv(CHECKED_CSV)

    records = []
    for _, row in df.iterrows():
        conf_str = str(row['conference'])

        year = None
        conference = None

        for y in range(2020, 2030):
            if str(y) in conf_str:
                year = y
                break

        for conf in ML_CONFERENCES + CV_CONFERENCES:
            if conf.upper() in conf_str.upper():
                conference = conf
                break

        if not year or not conference:
            continue

        conf_type = 'ML' if conference in ML_CONFERENCES else 'CV'
        records.append({
            'conference': conference,
            'year': year,
            'type': conf_type,
            'platform': row['platform'],
            'title': row['title'],
        })

    return pd.DataFrame(records)


def plot_platform_usage_over_years(df, years, output_dir='plots'):
    """Plot platform usage trends over years (ML vs CV)."""
    agg = df.groupby(['type', 'year']).size().reset_index(name='count')

    fig, ax = plt.subplots(figsize=(10, 6))

    for conf_type in ['ML', 'CV']:
        data = agg[agg['type'] == conf_type]
        if len(data) > 0:
            ax.plot(data['year'], data['count'],
                    marker='o', linewidth=2.5, markersize=10,
                    label=f'{conf_type} Conferences')
            for _, row in data.iterrows():
                ax.text(row['year'], row['count'] + 0.5,
                        str(int(row['count'])),
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Papers Using FL Platforms', fontsize=13, fontweight='bold')
    ax.set_title(f'FL Platform Usage Trends: ML vs CV Conferences ({years[0]}-{years[-1]})',
                 fontsize=15, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(years)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/platform_usage_over_years.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir}/platform_usage_over_years.png")
    plt.close()


def plot_top_platforms(df, years, output_dir='plots'):
    """Plot most used FL platforms."""
    platform_counts = df['platform'].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = [PLATFORM_COLORS.get(p, '#95A5A6') for p in platform_counts.index]
    bars = ax.barh(range(len(platform_counts)), platform_counts.values, color=colors,
                   edgecolor='black', linewidth=1.2)
    ax.set_yticks(range(len(platform_counts)))
    ax.set_yticklabels(platform_counts.index, fontsize=11)
    ax.invert_yaxis()

    for i, (bar, count) in enumerate(zip(bars, platform_counts.values)):
        ax.text(count + 0.3, i, str(count),
                va='center', fontsize=10, fontweight='bold')

    ax.set_xlabel('Number of Papers', fontsize=13, fontweight='bold')
    ax.set_title(f'Top FL Platforms Actually Used in Research ({years[0]}-{years[-1]})',
                 fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/top_platforms_used.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir}/top_platforms_used.png")
    plt.close()


def plot_platform_by_conference_type(df, years, output_dir='plots'):
    """Plot platform usage by ML vs CV conferences, with year breakdown."""
    platform_counts = df['platform'].value_counts()
    priority_order = [
        'Flower', 'FederatedScope', 'FedML', 'NVIDIA FLARE',
        'TensorFlow Federated', 'FedScale', 'LEAF'
    ]
    top_platforms = [p for p in priority_order if p in platform_counts.index][:6]

    usage_data = []
    for platform in top_platforms:
        for conf_type in ['ML', 'CV']:
            for year in years:
                count = len(df[(df['platform'] == platform) &
                               (df['type'] == conf_type) &
                               (df['year'] == year)])
                usage_data.append({
                    'platform': platform,
                    'conference_type': conf_type,
                    'year': year,
                    'count': count
                })

    usage_df = pd.DataFrame(usage_data)

    fig, ax = plt.subplots(figsize=(14, 7))
    platforms = list(top_platforms)
    x = range(len(platforms))
    width = 0.35

    palette = ['#95a5a6', '#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12']
    year_colors = {y: palette[i % len(palette)] for i, y in enumerate(years)}

    for conf_idx, conf_type in enumerate(['ML', 'CV']):
        x_positions = [i + (conf_idx - 0.5) * width for i in x]

        bottom = [0] * len(platforms)
        for year in years:
            counts = []
            for platform in platforms:
                vals = usage_df[(usage_df['platform'] == platform) &
                                (usage_df['conference_type'] == conf_type) &
                                (usage_df['year'] == year)]['count'].values
                counts.append(vals[0] if len(vals) > 0 else 0)

            label = f'{year}' if conf_idx == 0 else None
            bars = ax.bar(x_positions, counts, width, bottom=bottom,
                          label=label, color=year_colors[year],
                          edgecolor='white', linewidth=1.5)

            for i, (bar, count) in enumerate(zip(bars, counts)):
                if count > 0:
                    y_pos = bottom[i] + count / 2
                    ax.text(bar.get_x() + bar.get_width() / 2., y_pos,
                            str(count), ha='center', va='center',
                            fontsize=8, fontweight='bold', color='white')

            bottom = [b + c for b, c in zip(bottom, counts)]

        for i in range(len(platforms)):
            total = bottom[i]
            if total > 0:
                ax.text(x_positions[i], total + 0.3, conf_type,
                        ha='center', va='bottom', fontsize=9, fontweight='bold',
                        color='#3498db' if conf_type == 'ML' else '#e67e22')

    ax.set_xlabel('Platform', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Papers', fontsize=13, fontweight='bold')
    ax.set_title('Top FL Platforms: ML vs CV Conference Adoption by Year',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, rotation=45, ha='right', fontsize=10)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=year_colors[y], edgecolor='white', label=str(y))
        for y in years
    ]
    ax.legend(handles=legend_elements, fontsize=11, title='Year', title_fontsize=12)
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/platform_by_conference_type.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir}/platform_by_conference_type.png")
    plt.close()


def print_summary(df, years):
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("PLATFORM USAGE SUMMARY STATISTICS")
    print("=" * 80)

    print(f"\nTotal platform-paper records: {len(df)}")
    print(f"Unique papers using platforms: {df['title'].nunique()}")
    print(f"Unique platforms: {df['platform'].nunique()}")

    print(f"\n📊 Top Platforms (by paper count):")
    for i, (platform, count) in enumerate(df['platform'].value_counts().head(10).items(), 1):
        pct = count / len(df) * 100
        print(f"  {i:2d}. {platform:25s}: {count:3d} papers ({pct:5.1f}%)")

    print(f"\n📈 Usage by Conference Type:")
    for conf_type in ['ML', 'CV']:
        count = len(df[df['type'] == conf_type])
        print(f"  {conf_type}: {count} records")

    print(f"\n📅 Usage by Year:")
    for year in years:
        count = len(df[df['year'] == year])
        print(f"  {year}: {count} records")


def main():
    print("=" * 80)
    print("FL Platform Usage Trend Analysis")
    print(f"Source: {CHECKED_CSV}")
    print("=" * 80)

    print(f"\n📂 Loading data from {CHECKED_CSV}...")
    df = load_data()

    if df.empty:
        print("Error: No valid records found.")
        return

    years = sorted(df['year'].unique())

    print_summary(df, years)

    output_dir = 'plots'
    Path(output_dir).mkdir(exist_ok=True)
    print(f"\n📊 Generating visualizations in '{output_dir}/'...")

    print("\n1. Platform usage over years (ML vs CV)...")
    plot_platform_usage_over_years(df, years, output_dir)

    print("2. Top platforms...")
    plot_top_platforms(df, years, output_dir)

    print("3. Platform by conference type with year breakdown...")
    plot_platform_by_conference_type(df, years, output_dir)

    print(f"\n{'=' * 80}")
    print(f"✅ Analysis complete! Plots saved in '{output_dir}/'")
    print("=" * 80)


if __name__ == "__main__":
    main()
