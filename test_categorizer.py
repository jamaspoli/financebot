"""Test script for transaction categorizer."""

from transaction_normalizer import TransactionNormalizer
from transaction_categorizer import TransactionCategorizer

def main():
    print("="*80)
    print("Transaction Categorizer Test")
    print("="*80)

    # Step 1: Load and normalize transactions
    print("\n1. Loading and normalizing transactions...")
    normalizer = TransactionNormalizer()

    files = [
        ('Westpac Sample download Data_export_05022026 (1).csv', 'westpac'),
        ('Amex Sample Download - activity.csv', 'amex')
    ]
    df = normalizer.normalize_multiple(files)
    print(f"   Loaded {len(df)} transactions")

    # Take a sample for testing (first 50 transactions)
    sample_df = df.head(50).copy()
    print(f"   Using sample of {len(sample_df)} transactions for testing")

    # Step 2: Initialize categorizer
    print("\n2. Initializing categorizer...")
    categorizer = TransactionCategorizer(batch_size=25)

    # Step 3: Add some manual overrides
    print("\n3. Adding manual overrides...")
    overrides = {
        'WOOLWORTHS': 'Groceries',
        'COLES': 'Groceries',
        'APPLE.COM/BILL': 'Entertainment',
        'NETFLIX': 'Entertainment',
        'TRANSLINK': 'Transport',
    }

    for merchant, category in overrides.items():
        categorizer.add_override(merchant, category, save=False)

    # Save all overrides at once
    categorizer._save_json(categorizer.overrides, categorizer.overrides_file)
    print(f"   Added {len(overrides)} overrides")

    # Step 4: Categorize transactions
    print("\n4. Categorizing transactions...")
    categorized_df = categorizer.categorize(sample_df)

    # Step 5: Show results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    print("\nSample categorized transactions:")
    print(categorized_df[['date', 'description', 'amount', 'category']].head(20).to_string(index=False))

    print("\n" + "-"*80)
    print("\nCategory Summary:")
    summary = categorizer.get_category_summary(categorized_df)
    print(summary)

    # Step 6: Save results
    print("\n" + "="*80)
    categorized_df.to_csv('categorized_sample.csv', index=False)
    print("✓ Saved categorized transactions to 'categorized_sample.csv'")
    print(f"✓ Cache contains {len(categorizer.cache)} merchants")
    print(f"✓ {len(categorizer.overrides)} manual overrides active")

    # Show cache and override info
    print("\n" + "="*80)
    print("CACHE & OVERRIDES INFO")
    print("="*80)
    print(f"\nCache file: {categorizer.cache_file}")
    print(f"Overrides file: {categorizer.overrides_file}")
    print("\nActive overrides:")
    for merchant, category in sorted(categorizer.overrides.items()):
        print(f"  {merchant}: {category}")


if __name__ == '__main__':
    main()
