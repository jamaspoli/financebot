"""
Complete workflow example: Normalize and categorize bank transactions.

This script demonstrates the full pipeline from raw bank CSV files
to categorized and analyzed transactions.
"""

from transaction_normalizer import TransactionNormalizer
from transaction_categorizer import TransactionCategorizer
from dotenv import load_dotenv
import sys
import os


def main():
    print("="*80)
    print("Complete Transaction Processing Workflow")
    print("="*80)

    # Load environment variables from .env file
    load_dotenv()

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("Or add it to a .env file")
        print("Or pass it directly: TransactionCategorizer(api_key='...')")
        sys.exit(1)

    # STEP 1: Normalize transactions
    print("\n" + "="*80)
    print("STEP 1: Normalize Bank CSV Files")
    print("="*80)

    normalizer = TransactionNormalizer()

    files = [
        ('Westpac Sample download Data_export_05022026 (1).csv', 'westpac'),
        ('Amex Sample Download - activity.csv', 'amex')
    ]

    print("\nProcessing files:")
    for file, bank in files:
        print(f"  - {file} ({bank})")

    df = normalizer.normalize_multiple(files)
    print(f"\n✓ Normalized {len(df)} transactions")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Accounts: {', '.join(df['account_name'].unique())}")

    # STEP 2: Initialize categorizer with overrides
    print("\n" + "="*80)
    print("STEP 2: Initialize Categorizer")
    print("="*80)

    categorizer = TransactionCategorizer(batch_size=75)
    print("\n✓ Categorizer initialized")
    print(f"  Batch size: 75 transactions per API call")
    print(f"  Cache file: {categorizer.cache_file}")
    print(f"  Overrides file: {categorizer.overrides_file}")

    # STEP 3: Add common merchant overrides
    print("\n" + "="*80)
    print("STEP 3: Add Manual Overrides")
    print("="*80)

    common_overrides = {
        # Groceries
        'WOOLWORTHS': 'Groceries',
        'COLES': 'Groceries',
        'ALDI': 'Groceries',
        'IGA': 'Groceries',

        # Dining
        'CHARLOTTE AND ARMANDO': 'Dining',

        # Transport
        'TRANSLINK': 'Transport',
        'CELLPARK': 'Transport',
        'CELLOPARK': 'Transport',

        # Entertainment
        'NETFLIX': 'Entertainment',
        'SPOTIFY': 'Entertainment',
        'APPLE.COM/BILL': 'Entertainment',
        'STAN.COM.AU': 'Entertainment',
        'PRIME VIDE': 'Entertainment',
        'NYTIMES': 'Entertainment',

        # Utilities
        'TELSTRA': 'Utilities',
        'ALINTA ENERGY': 'Utilities',
        'QUEENSLAND URBAN UTI': 'Utilities',

        # Health
        'TAL LIFE': 'Health',
        'HCFLIFE': 'Health',
        'HCFHEALTHANDLIFE': 'Health',

        # Shopping
        'AMAZON': 'Shopping',
        'TESLA': 'Shopping',
    }

    print(f"\nAdding {len(common_overrides)} common merchant overrides...")
    for merchant, category in common_overrides.items():
        categorizer.add_override(merchant, category, save=False)

    # Save all at once
    categorizer._save_json(categorizer.overrides, categorizer.overrides_file)
    print("✓ Overrides saved")

    # STEP 4: Categorize transactions
    print("\n" + "="*80)
    print("STEP 4: Categorize Transactions")
    print("="*80)

    print("\nCategorizing transactions...")
    print("(This will use Claude API for merchants not in cache or overrides)")
    categorized_df = categorizer.categorize(df)

    print("\n✓ Categorization complete!")
    print(f"  Total transactions: {len(categorized_df)}")
    print(f"  Cached merchants: {len(categorizer.cache)}")
    print(f"  Manual overrides: {len(categorizer.overrides)}")

    # STEP 5: Analyze results
    print("\n" + "="*80)
    print("STEP 5: Analyze Results")
    print("="*80)

    summary = categorizer.get_category_summary(categorized_df)

    print("\nCategory Summary:")
    print(summary)

    print("\n\nTop 10 Expenses by Category:")
    expenses = categorized_df[categorized_df['amount'] < 0].copy()
    expenses['abs_amount'] = expenses['amount'].abs()
    top_expenses = expenses.nlargest(10, 'abs_amount')

    for _, row in top_expenses.iterrows():
        print(f"  {row['date'].strftime('%Y-%m-%d')} | "
              f"{row['category']:15s} | "
              f"${row['amount']:8.2f} | "
              f"{row['description'][:50]}")

    print("\n\nTop 10 Income Transactions:")
    income = categorized_df[categorized_df['amount'] > 0].copy()
    top_income = income.nlargest(10, 'amount')

    for _, row in top_income.iterrows():
        print(f"  {row['date'].strftime('%Y-%m-%d')} | "
              f"{row['category']:15s} | "
              f"${row['amount']:8.2f} | "
              f"{row['description'][:50]}")

    # STEP 6: Save results
    print("\n" + "="*80)
    print("STEP 6: Save Results")
    print("="*80)

    output_file = 'categorized_transactions.csv'
    categorized_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved categorized transactions to: {output_file}")

    summary_file = 'category_summary.csv'
    summary.to_csv(summary_file)
    print(f"✓ Saved category summary to: {summary_file}")

    # STEP 7: Display monthly breakdown
    print("\n" + "="*80)
    print("STEP 7: Monthly Breakdown")
    print("="*80)

    categorized_df['month'] = categorized_df['date'].dt.to_period('M')
    monthly = categorized_df.groupby(['month', 'category'])['amount'].sum().unstack(fill_value=0)

    print("\nMonthly spending by category:")
    print(monthly.round(2))

    print("\n" + "="*80)
    print("Workflow Complete!")
    print("="*80)
    print(f"\nFiles created:")
    print(f"  - {output_file} (all categorized transactions)")
    print(f"  - {summary_file} (category summary)")
    print(f"  - {categorizer.cache_file} (categorization cache)")
    print(f"  - {categorizer.overrides_file} (manual overrides)")


if __name__ == '__main__':
    main()
