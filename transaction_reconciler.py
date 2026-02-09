"""
Transaction Reconciler for identifying transfer matches, duplicates, and anomalies.

This module helps reconcile transactions across accounts by finding matching
transfers, flagging potential duplicates, and identifying orphaned transfers.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from datetime import timedelta


class TransactionReconciler:
    """Reconciles transactions to find matches, duplicates, and anomalies."""

    def __init__(self, date_window_days: int = 3, amount_tolerance: float = 0.01):
        """
        Initialize the TransactionReconciler.

        Args:
            date_window_days: Number of days to search for matching transfers (default: 3)
            amount_tolerance: Amount difference tolerance for matching (default: 0.01)
        """
        self.date_window_days = date_window_days
        self.amount_tolerance = amount_tolerance

    def find_transfer_matches(
        self,
        df: pd.DataFrame,
        date_col: str = 'date',
        amount_col: str = 'amount',
        account_col: str = 'account_name',
        category_col: str = 'category'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find matching transfers between accounts.

        A transfer match is defined as:
        - Same absolute amount (within tolerance)
        - Opposite signs (one positive, one negative)
        - Within date_window_days of each other
        - Between different accounts
        - Both categorized as 'Transfer' (if category exists)

        Args:
            df: DataFrame with transaction data
            date_col: Name of date column
            amount_col: Name of amount column
            account_col: Name of account column
            category_col: Name of category column (optional)

        Returns:
            Tuple of (matched_df, unmatched_df):
            - matched_df: DataFrame with 'transfer_pair_id' column linking matches
            - unmatched_df: DataFrame of unmatched transfers
        """
        # Create a copy to avoid modifying original
        result_df = df.copy()
        result_df['transfer_pair_id'] = None

        # Ensure date column is datetime
        result_df[date_col] = pd.to_datetime(result_df[date_col])

        # Look for potential transfers using multiple heuristics
        # Strategy: Cast a wide net, then narrow down with matching logic
        transfer_mask = pd.Series([False] * len(result_df), index=result_df.index)

        # Include transactions already marked as Transfer
        if category_col in result_df.columns:
            transfer_mask |= result_df[category_col] == 'Transfer'

        # Include transactions with transfer-like descriptions
        transfer_keywords = ['TRANSFER', 'TFR', 'BPAY', 'PAYMENT', 'DEPOSIT ONLINE',
                            'WITHDRAWAL', 'ONLINE PAYMENT RECEIVED']
        desc_col = 'description' if 'description' in result_df.columns else None
        if desc_col:
            for keyword in transfer_keywords:
                transfer_mask |= result_df[desc_col].str.upper().str.contains(
                    keyword, na=False
                )

        # Also include any transaction that might have a matching opposite amount
        # (We'll filter these properly in the matching logic)
        transfers = result_df[transfer_mask].copy()

        if len(transfers) == 0:
            return result_df, pd.DataFrame()

        # Ensure date column is datetime
        transfers[date_col] = pd.to_datetime(transfers[date_col])

        # Sort by date for efficient matching (keep original index)
        transfers = transfers.sort_values(date_col)

        matched_indices = set()
        pair_id = 1

        # For each transfer, try to find a matching opposite transfer
        for idx, row in transfers.iterrows():
            if idx in matched_indices:
                continue

            amount = row[amount_col]
            date = row[date_col]
            account = row[account_col]

            # Look for opposite amount in different account within date window
            target_amount = -amount
            date_min = date - timedelta(days=self.date_window_days)
            date_max = date + timedelta(days=self.date_window_days)

            # Find potential matches (look both forward and backward)
            potential_matches = transfers[
                (~transfers.index.isin(matched_indices)) &
                (transfers.index != idx) &  # Don't match with self
                (transfers[account_col] != account) &
                (transfers[date_col] >= date_min) &
                (transfers[date_col] <= date_max) &
                (np.abs(transfers[amount_col] - target_amount) <= self.amount_tolerance)
            ]

            if len(potential_matches) > 0:
                # Take the closest match by date
                potential_matches = potential_matches.copy()
                potential_matches['date_diff'] = np.abs(
                    (potential_matches[date_col] - date).dt.total_seconds()
                )
                match_idx = potential_matches['date_diff'].idxmin()

                # Mark both as matched with the same pair_id
                result_df.loc[row.name, 'transfer_pair_id'] = pair_id
                result_df.loc[match_idx, 'transfer_pair_id'] = pair_id

                # Override category to Transfer for matched pairs
                if category_col in result_df.columns:
                    result_df.loc[row.name, category_col] = 'Transfer'
                    result_df.loc[match_idx, category_col] = 'Transfer'

                matched_indices.add(idx)
                matched_indices.add(match_idx)
                pair_id += 1

        # Split into matched and unmatched
        matched_df = result_df[result_df['transfer_pair_id'].notna()].copy()
        unmatched_transfers = result_df[
            transfer_mask & result_df['transfer_pair_id'].isna()
        ].copy()

        return result_df, unmatched_transfers

    def find_duplicates(
        self,
        df: pd.DataFrame,
        date_col: str = 'date',
        amount_col: str = 'amount',
        description_col: str = 'description',
        account_col: str = 'account_name'
    ) -> pd.DataFrame:
        """
        Find potential duplicate transactions.

        A duplicate is defined as:
        - Same amount (within tolerance)
        - Same description (case-insensitive)
        - Same date
        - Same account

        Args:
            df: DataFrame with transaction data
            date_col: Name of date column
            amount_col: Name of amount column
            description_col: Name of description column
            account_col: Name of account column

        Returns:
            DataFrame with potential duplicates, including 'duplicate_group_id' column
        """
        result_df = df.copy()

        # Normalize description for comparison
        result_df['_normalized_desc'] = result_df[description_col].str.upper().str.strip()

        # Create composite key for grouping
        result_df['_dup_key'] = (
            result_df[date_col].astype(str) + '_' +
            result_df[account_col] + '_' +
            result_df['_normalized_desc'] + '_' +
            result_df[amount_col].round(2).astype(str)
        )

        # Find groups with more than one transaction
        dup_counts = result_df['_dup_key'].value_counts()
        dup_keys = dup_counts[dup_counts > 1].index

        # Filter to only duplicates
        duplicates = result_df[result_df['_dup_key'].isin(dup_keys)].copy()

        if len(duplicates) > 0:
            # Assign duplicate group IDs
            key_to_group = {key: idx + 1 for idx, key in enumerate(dup_keys)}
            duplicates['duplicate_group_id'] = duplicates['_dup_key'].map(key_to_group)

            # Sort by group for easier viewing
            duplicates = duplicates.sort_values('duplicate_group_id')

        # Clean up temporary columns
        duplicates = duplicates.drop(columns=['_normalized_desc', '_dup_key'])

        return duplicates

    def find_orphaned_transfers(
        self,
        df: pd.DataFrame,
        date_col: str = 'date',
        amount_col: str = 'amount',
        category_col: str = 'category',
        transfer_pair_col: str = 'transfer_pair_id'
    ) -> pd.DataFrame:
        """
        Find orphaned transfers that don't have matching pairs.

        These might indicate:
        - Missing data from another account
        - Transfers to/from external accounts
        - Miscategorized transactions

        Args:
            df: DataFrame with transaction data (should have been processed by find_transfer_matches)
            date_col: Name of date column
            amount_col: Name of amount column
            category_col: Name of category column
            transfer_pair_col: Name of transfer pair ID column

        Returns:
            DataFrame of orphaned transfers
        """
        if transfer_pair_col not in df.columns:
            raise ValueError(
                f"Column '{transfer_pair_col}' not found. "
                "Run find_transfer_matches() first to identify transfer pairs."
            )

        # Find transfers without a pair
        if category_col in df.columns:
            orphaned = df[
                (df[category_col] == 'Transfer') &
                (df[transfer_pair_col].isna())
            ].copy()
        else:
            orphaned = df[df[transfer_pair_col].isna()].copy()

        # Sort by date for easier review
        orphaned = orphaned.sort_values(date_col)

        return orphaned

    def reconcile(
        self,
        df: pd.DataFrame,
        date_col: str = 'date',
        amount_col: str = 'amount',
        description_col: str = 'description',
        account_col: str = 'account_name',
        category_col: str = 'category'
    ) -> Dict:
        """
        Perform complete reconciliation analysis.

        This runs all reconciliation checks and returns a comprehensive report.

        Args:
            df: DataFrame with transaction data
            date_col: Name of date column
            amount_col: Name of amount column
            description_col: Name of description column
            account_col: Name of account column
            category_col: Name of category column

        Returns:
            Dictionary containing:
            - 'reconciled_df': Original DataFrame with transfer_pair_id added
            - 'matched_transfers': DataFrame of matched transfer pairs
            - 'orphaned_transfers': DataFrame of unmatched transfers
            - 'duplicates': DataFrame of potential duplicate transactions
            - 'summary': Summary statistics dictionary
        """
        print("Running reconciliation...")

        # 1. Find transfer matches
        print("\n1. Finding transfer matches...")
        reconciled_df, orphaned_transfers = self.find_transfer_matches(
            df, date_col, amount_col, account_col, category_col
        )

        matched_transfers = reconciled_df[
            reconciled_df['transfer_pair_id'].notna()
        ].sort_values('transfer_pair_id')

        num_matched_pairs = matched_transfers['transfer_pair_id'].nunique()
        num_orphaned = len(orphaned_transfers)

        print(f"   Found {num_matched_pairs} matched transfer pairs")
        print(f"   Found {num_orphaned} orphaned transfers")

        # 2. Find duplicates
        print("\n2. Finding potential duplicates...")
        duplicates = self.find_duplicates(
            df, date_col, amount_col, description_col, account_col
        )

        num_dup_groups = duplicates['duplicate_group_id'].nunique() if len(duplicates) > 0 else 0
        num_dup_transactions = len(duplicates)

        print(f"   Found {num_dup_groups} duplicate groups ({num_dup_transactions} transactions)")

        # 3. Calculate summary statistics
        summary = {
            'total_transactions': len(df),
            'matched_transfer_pairs': num_matched_pairs,
            'matched_transfer_transactions': len(matched_transfers),
            'orphaned_transfers': num_orphaned,
            'duplicate_groups': num_dup_groups,
            'duplicate_transactions': num_dup_transactions,
            'transfer_match_rate': (len(matched_transfers) / (len(matched_transfers) + num_orphaned) * 100)
                if (len(matched_transfers) + num_orphaned) > 0 else 0
        }

        # 4. Add orphaned transfer details
        if num_orphaned > 0:
            summary['orphaned_outflows'] = len(orphaned_transfers[orphaned_transfers[amount_col] < 0])
            summary['orphaned_inflows'] = len(orphaned_transfers[orphaned_transfers[amount_col] > 0])
            summary['orphaned_total_amount'] = orphaned_transfers[amount_col].sum()

        print("\n✓ Reconciliation complete")

        return {
            'reconciled_df': reconciled_df,
            'matched_transfers': matched_transfers,
            'orphaned_transfers': orphaned_transfers,
            'duplicates': duplicates,
            'summary': summary
        }

    def generate_report(self, reconciliation_result: Dict) -> str:
        """
        Generate a human-readable reconciliation report.

        Args:
            reconciliation_result: Dictionary returned from reconcile()

        Returns:
            Formatted report string
        """
        summary = reconciliation_result['summary']
        matched = reconciliation_result['matched_transfers']
        orphaned = reconciliation_result['orphaned_transfers']
        duplicates = reconciliation_result['duplicates']

        report = []
        report.append("="*80)
        report.append("TRANSACTION RECONCILIATION REPORT")
        report.append("="*80)

        # Summary
        report.append("\nSUMMARY")
        report.append("-"*80)
        report.append(f"Total Transactions: {summary['total_transactions']:,}")
        report.append(f"Matched Transfer Pairs: {summary['matched_transfer_pairs']:,}")
        report.append(f"  (involving {summary['matched_transfer_transactions']:,} transactions)")
        report.append(f"Orphaned Transfers: {summary['orphaned_transfers']:,}")
        report.append(f"Transfer Match Rate: {summary['transfer_match_rate']:.1f}%")
        report.append(f"Potential Duplicates: {summary['duplicate_transactions']:,} transactions in {summary['duplicate_groups']:,} groups")

        # Matched Transfers
        if len(matched) > 0:
            report.append("\n" + "="*80)
            report.append("MATCHED TRANSFER PAIRS")
            report.append("="*80)
            report.append(f"\nFirst 10 matched pairs:")

            for pair_id in matched['transfer_pair_id'].unique()[:10]:
                pair = matched[matched['transfer_pair_id'] == pair_id]
                report.append(f"\nPair {int(pair_id)}:")
                for _, row in pair.iterrows():
                    report.append(
                        f"  {row['date'].strftime('%Y-%m-%d')} | "
                        f"{row['account_name']:20s} | "
                        f"${row['amount']:10.2f} | "
                        f"{row.get('description', '')[:40]}"
                    )

        # Orphaned Transfers
        if len(orphaned) > 0:
            report.append("\n" + "="*80)
            report.append("ORPHANED TRANSFERS (No Matching Pair)")
            report.append("="*80)
            report.append(f"\nTotal: {len(orphaned)} transactions")

            if 'orphaned_outflows' in summary:
                report.append(f"  Outflows: {summary['orphaned_outflows']}")
                report.append(f"  Inflows: {summary['orphaned_inflows']}")
                report.append(f"  Net Amount: ${summary['orphaned_total_amount']:.2f}")

            report.append(f"\nFirst 20 orphaned transfers:")
            for _, row in orphaned.head(20).iterrows():
                report.append(
                    f"  {row['date'].strftime('%Y-%m-%d')} | "
                    f"{row['account_name']:20s} | "
                    f"${row['amount']:10.2f} | "
                    f"{row.get('description', '')[:40]}"
                )

        # Duplicates
        if len(duplicates) > 0:
            report.append("\n" + "="*80)
            report.append("POTENTIAL DUPLICATES")
            report.append("="*80)
            report.append(f"\nFound {summary['duplicate_groups']} groups:")

            for group_id in duplicates['duplicate_group_id'].unique()[:10]:
                group = duplicates[duplicates['duplicate_group_id'] == group_id]
                report.append(f"\nGroup {int(group_id)} ({len(group)} transactions):")
                for _, row in group.iterrows():
                    report.append(
                        f"  {row['date'].strftime('%Y-%m-%d')} | "
                        f"{row['account_name']:20s} | "
                        f"${row['amount']:10.2f} | "
                        f"{row.get('description', '')[:40]}"
                    )

        report.append("\n" + "="*80)

        return "\n".join(report)


def main():
    """Example usage of TransactionReconciler."""
    import pandas as pd
    from transaction_normalizer import TransactionNormalizer
    from transaction_categorizer import TransactionCategorizer

    # Load and categorize transactions
    print("Loading transactions...")
    normalizer = TransactionNormalizer()
    files = [
        ('Westpac Sample download Data_export_05022026 (1).csv', 'westpac'),
        ('Amex Sample Download - activity.csv', 'amex')
    ]
    df = normalizer.normalize_multiple(files)

    # Load existing categorized data if available
    try:
        df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])
        print(f"Loaded {len(df)} categorized transactions")
    except FileNotFoundError:
        print("No existing categorized data found. Run categorization first.")
        return

    # Reconcile
    reconciler = TransactionReconciler(date_window_days=3)
    result = reconciler.reconcile(df)

    # Generate and print report
    report = reconciler.generate_report(result)
    print("\n" + report)

    # Save results
    result['reconciled_df'].to_csv('reconciled_transactions.csv', index=False)
    result['orphaned_transfers'].to_csv('orphaned_transfers.csv', index=False)
    if len(result['duplicates']) > 0:
        result['duplicates'].to_csv('potential_duplicates.csv', index=False)

    print("\nFiles saved:")
    print("  - reconciled_transactions.csv (all transactions with transfer_pair_id)")
    print("  - orphaned_transfers.csv (transfers without matches)")
    if len(result['duplicates']) > 0:
        print("  - potential_duplicates.csv (potential duplicate transactions)")


if __name__ == '__main__':
    main()
