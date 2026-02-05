"""Test script for transaction reconciler."""

import pandas as pd
from transaction_reconciler import TransactionReconciler


def main():
    print("="*80)
    print("Transaction Reconciliation Test")
    print("="*80)

    # Load categorized transactions
    print("\nLoading categorized transactions...")
    try:
        df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])
        print(f"✓ Loaded {len(df)} transactions")
    except FileNotFoundError:
        print("✗ categorized_transactions.csv not found!")
        print("  Run example_complete_workflow.py first to generate categorized data.")
        return

    # Show data summary
    print(f"\nData Overview:")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Accounts: {', '.join(df['account_name'].unique())}")
    print(f"  Categories: {', '.join(df['category'].unique())}")

    # Check for transfers
    transfer_count = (df['category'] == 'Transfer').sum()
    print(f"  Transfers: {transfer_count} transactions")

    # Initialize reconciler
    print("\n" + "="*80)
    print("Initializing Reconciler")
    print("="*80)
    reconciler = TransactionReconciler(
        date_window_days=3,  # Look for matches within 3 days
        amount_tolerance=0.01  # Allow $0.01 difference
    )
    print("✓ Reconciler initialized")
    print(f"  Date window: {reconciler.date_window_days} days")
    print(f"  Amount tolerance: ${reconciler.amount_tolerance}")

    # Run reconciliation
    print("\n" + "="*80)
    result = reconciler.reconcile(df)

    # Generate and display report
    print("\n" + "="*80)
    report = reconciler.generate_report(result)
    print(report)

    # Save detailed results
    print("\n" + "="*80)
    print("Saving Results")
    print("="*80)

    result['reconciled_df'].to_csv('reconciled_transactions.csv', index=False)
    print("✓ reconciled_transactions.csv")

    if len(result['orphaned_transfers']) > 0:
        result['orphaned_transfers'].to_csv('orphaned_transfers.csv', index=False)
        print("✓ orphaned_transfers.csv")

    if len(result['duplicates']) > 0:
        result['duplicates'].to_csv('potential_duplicates.csv', index=False)
        print("✓ potential_duplicates.csv")

    # Additional analysis
    print("\n" + "="*80)
    print("Additional Analysis")
    print("="*80)

    # Analyze orphaned transfers by account
    if len(result['orphaned_transfers']) > 0:
        print("\nOrphaned Transfers by Account:")
        orphaned_by_account = result['orphaned_transfers'].groupby('account_name').agg({
            'amount': ['count', 'sum']
        })
        orphaned_by_account.columns = ['Count', 'Total Amount']
        print(orphaned_by_account)

        # Show largest orphaned transfers
        print("\nTop 10 Largest Orphaned Transfers (by absolute value):")
        orphaned_sorted = result['orphaned_transfers'].copy()
        orphaned_sorted['abs_amount'] = orphaned_sorted['amount'].abs()
        top_orphaned = orphaned_sorted.nlargest(10, 'abs_amount')

        for _, row in top_orphaned.iterrows():
            print(
                f"  {row['date'].strftime('%Y-%m-%d')} | "
                f"{row['account_name']:20s} | "
                f"${row['amount']:10.2f} | "
                f"{row['description'][:45]}"
            )

    # Analyze matched transfers
    if len(result['matched_transfers']) > 0:
        print("\nMatched Transfer Statistics:")
        matched_pairs = result['matched_transfers'].groupby('transfer_pair_id')

        print(f"  Total pairs: {len(matched_pairs)}")

        # Calculate time differences for matched pairs
        time_diffs = []
        for pair_id, group in matched_pairs:
            if len(group) == 2:
                dates = sorted(group['date'].tolist())
                diff = (dates[1] - dates[0]).days
                time_diffs.append(diff)

        if time_diffs:
            print(f"  Same-day matches: {time_diffs.count(0)}")
            print(f"  1-day difference: {time_diffs.count(1)}")
            print(f"  2-day difference: {time_diffs.count(2)}")
            print(f"  3-day difference: {time_diffs.count(3)}")
            print(f"  Average difference: {sum(time_diffs)/len(time_diffs):.1f} days")

    print("\n" + "="*80)
    print("Reconciliation Complete!")
    print("="*80)


if __name__ == '__main__':
    main()
