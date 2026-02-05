"""Test script for transaction normalizer."""

from transaction_normalizer import TransactionNormalizer

def main():
    normalizer = TransactionNormalizer()

    # Test with the actual sample files
    print("Testing Westpac normalization...")
    westpac_df = normalizer.normalize(
        'Westpac Sample download Data_export_05022026 (1).csv',
        'westpac'
    )
    print(f"Westpac: {len(westpac_df)} transactions")
    print("\nFirst 5 Westpac transactions:")
    print(westpac_df.head())
    print("\nWestpac amount summary:")
    print(f"  Min (most expensive): ${westpac_df['amount'].min():.2f}")
    print(f"  Max (largest income): ${westpac_df['amount'].max():.2f}")
    print(f"  Total: ${westpac_df['amount'].sum():.2f}")

    print("\n" + "="*80 + "\n")

    print("Testing Amex normalization...")
    amex_df = normalizer.normalize(
        'Amex Sample Download - activity.csv',
        'amex'
    )
    print(f"Amex: {len(amex_df)} transactions")
    print("\nFirst 5 Amex transactions:")
    print(amex_df.head())
    print("\nAmex amount summary:")
    print(f"  Min (most expensive): ${amex_df['amount'].min():.2f}")
    print(f"  Max (largest income): ${amex_df['amount'].max():.2f}")
    print(f"  Total: ${amex_df['amount'].sum():.2f}")

    print("\n" + "="*80 + "\n")

    print("Testing combined normalization...")
    files = [
        ('Westpac Sample download Data_export_05022026 (1).csv', 'westpac'),
        ('Amex Sample Download - activity.csv', 'amex')
    ]
    combined_df = normalizer.normalize_multiple(files)
    print(f"Combined: {len(combined_df)} transactions")
    print("\nFirst 10 combined transactions (sorted by date):")
    print(combined_df.head(10))

    # Save to CSV
    combined_df.to_csv('normalized_transactions.csv', index=False)
    print("\n✓ Saved normalized transactions to 'normalized_transactions.csv'")


if __name__ == '__main__':
    main()
