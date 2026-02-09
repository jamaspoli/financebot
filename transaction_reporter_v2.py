"""
Enhanced Transaction Reporter with separate Expense, Transfer, and Income reports.

This module provides focused reporting capabilities that separate:
1. Pure expenses (excluding transfers)
2. Internal transfers between accounts
3. Income sources
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from transaction_reporter import TransactionReporter


class EnhancedTransactionReporter(TransactionReporter):
    """Enhanced reporter with separate expense, transfer, and income reports."""

    def __init__(self, df: pd.DataFrame):
        """Initialize with transaction data."""
        super().__init__(df)

        # Create filtered dataframes
        self.expenses_df = self._get_expenses_only()
        self.transfers_df = self._get_transfers_only()
        self.income_df = self._get_income_only()

    def _get_expenses_only(self) -> pd.DataFrame:
        """Get only real expenses (negative amounts, excluding transfers)."""
        df = self.df[self.df['amount'] < 0].copy()

        if 'category' in df.columns:
            # Exclude Transfer and Income categories
            df = df[~df['category'].isin(['Transfer', 'Income'])]

        return df

    def _get_transfers_only(self) -> pd.DataFrame:
        """Get only transfers."""
        if 'category' in self.df.columns:
            return self.df[self.df['category'] == 'Transfer'].copy()
        return pd.DataFrame()

    def _get_income_only(self) -> pd.DataFrame:
        """Get only income (positive amounts or Income category)."""
        df = self.df.copy()

        if 'category' in df.columns:
            # Income category OR positive amounts that aren't transfers
            income_mask = (
                (df['category'] == 'Income') |
                ((df['amount'] > 0) & (df['category'] != 'Transfer'))
            )
            return df[income_mask].copy()
        else:
            return df[df['amount'] > 0].copy()

    # ============================================================================
    # EXPENSE REPORTS
    # ============================================================================

    def generate_expense_reports(self) -> Dict[str, pd.DataFrame]:
        """
        Generate comprehensive expense reports.

        Returns:
            Dictionary with:
            - 'monthly_by_category': Monthly spending by category
            - 'category_summary': Total by category with statistics
            - 'top_merchants': Top 50 expense merchants
            - 'monthly_total': Monthly total expenses
            - 'category_trends': Month-over-month category changes
        """
        reports = {}

        if len(self.expenses_df) == 0:
            print("⚠️  No expense transactions found")
            return reports

        # 1. Monthly by category
        if 'category' in self.expenses_df.columns:
            monthly_cat = self.expenses_df.pivot_table(
                values='amount',
                index='year_month',
                columns='category',
                aggfunc='sum',
                fill_value=0
            )
            monthly_cat['Total'] = monthly_cat.sum(axis=1)

            # Add summary row
            summary = monthly_cat.sum()
            summary.name = 'TOTAL'
            monthly_cat = pd.concat([monthly_cat, summary.to_frame().T])

            # Sort by total spending
            col_order = monthly_cat.loc['TOTAL'].drop('Total').sort_values().index.tolist()
            col_order.append('Total')
            reports['monthly_by_category'] = monthly_cat[col_order]

        # 2. Category summary
        if 'category' in self.expenses_df.columns:
            cat_summary = self.expenses_df.groupby('category').agg({
                'amount': ['sum', 'count', 'mean', 'min', 'max']
            })
            cat_summary.columns = ['Total', 'Transactions', 'Average', 'Smallest', 'Largest']
            cat_summary = cat_summary.sort_values('Total')

            # Add percentage
            total_expenses = cat_summary['Total'].sum()
            cat_summary['% of Total'] = (cat_summary['Total'] / total_expenses * 100).round(1)

            reports['category_summary'] = cat_summary

        # 3. Top 50 merchants
        expenses_df = self.expenses_df.copy()
        expenses_df['merchant'] = expenses_df['description'].str.upper().str.strip()

        # Remove location suffixes
        for suffix in [' AUS', ' AUSTRALIA', ' SYDNEY', ' MELBOURNE', ' BRISBANE',
                      ' QLD', ' NSW', ' VIC', ' SA', ' WA', ' TAS', ' ACT', ' NT']:
            expenses_df['merchant'] = expenses_df['merchant'].str.replace(
                suffix + '$', '', regex=True
            )

        merchant_stats = expenses_df.groupby('merchant').agg({
            'amount': ['count', 'sum', 'mean'],
            'date': ['min', 'max']
        })
        merchant_stats.columns = ['Transactions', 'Total', 'Average', 'First', 'Last']
        # Show top 50 by total spend (no minimum transaction filter)
        merchant_stats = merchant_stats.sort_values('Total').head(50)

        # Format dates
        merchant_stats['First'] = pd.to_datetime(merchant_stats['First']).dt.strftime('%Y-%m-%d')
        merchant_stats['Last'] = pd.to_datetime(merchant_stats['Last']).dt.strftime('%Y-%m-%d')

        reports['top_merchants'] = merchant_stats.reset_index()

        # 4. Monthly total
        monthly_total = self.expenses_df.groupby('year_month').agg({
            'amount': ['sum', 'count', 'mean']
        })
        monthly_total.columns = ['Total Spent', 'Transactions', 'Average']

        # Add summary
        summary = monthly_total.sum()
        summary['Average'] = monthly_total['Total Spent'].sum() / len(monthly_total)
        summary.name = 'TOTAL'
        monthly_total = pd.concat([monthly_total, summary.to_frame().T])

        reports['monthly_total'] = monthly_total

        # 5. Category trends (month-over-month change)
        if 'category' in self.expenses_df.columns:
            trends = self.expenses_df.pivot_table(
                values='amount',
                index='year_month',
                columns='category',
                aggfunc='sum',
                fill_value=0
            )

            # Calculate percentage change
            pct_change = trends.pct_change() * 100
            pct_change = pct_change.round(1)

            reports['category_trends'] = trends
            reports['category_pct_change'] = pct_change

        return reports

    # ============================================================================
    # TRANSFER REPORTS
    # ============================================================================

    def generate_transfer_reports(self) -> Dict[str, pd.DataFrame]:
        """
        Generate transfer reports showing money movement between accounts.

        Returns:
            Dictionary with:
            - 'transfer_summary': Summary by account
            - 'transfer_pairs': Matched transfer pairs
            - 'orphaned_transfers': Unmatched transfers
            - 'monthly_transfers': Monthly transfer activity
        """
        reports = {}

        if len(self.transfers_df) == 0:
            print("⚠️  No transfers found")
            return reports

        # 1. Summary by account
        transfer_summary = self.transfers_df.groupby('account_name').agg({
            'amount': ['count', 'sum', lambda x: (x > 0).sum(), lambda x: (x < 0).sum()]
        })
        transfer_summary.columns = ['Total Transactions', 'Net Amount', 'Inflows', 'Outflows']

        # Add totals
        totals = transfer_summary.sum()
        totals.name = 'TOTAL'
        transfer_summary = pd.concat([transfer_summary, totals.to_frame().T])

        reports['transfer_summary'] = transfer_summary

        # 2. Transfer pairs (if available)
        if 'transfer_pair_id' in self.transfers_df.columns:
            paired = self.transfers_df[self.transfers_df['transfer_pair_id'].notna()].copy()
            paired = paired.sort_values('transfer_pair_id')
            reports['transfer_pairs'] = paired[[
                'date', 'account_name', 'amount', 'description', 'transfer_pair_id'
            ]]

        # 3. Orphaned transfers
        if 'transfer_pair_id' in self.transfers_df.columns:
            orphaned = self.transfers_df[self.transfers_df['transfer_pair_id'].isna()].copy()
            reports['orphaned_transfers'] = orphaned[[
                'date', 'account_name', 'amount', 'description'
            ]].sort_values('date')

        # 4. Monthly transfer activity
        monthly_transfers = self.transfers_df.groupby('year_month').agg({
            'amount': ['count', 'sum', lambda x: (x > 0).sum(), lambda x: (x < 0).sum()]
        })
        monthly_transfers.columns = ['Transactions', 'Net', 'Inflows', 'Outflows']

        reports['monthly_transfers'] = monthly_transfers

        return reports

    # ============================================================================
    # INCOME REPORTS
    # ============================================================================

    def generate_income_reports(self) -> Dict[str, pd.DataFrame]:
        """
        Generate income reports showing where money comes from.

        Returns:
            Dictionary with:
            - 'income_sources': Top income sources
            - 'monthly_income': Monthly income breakdown
            - 'income_by_account': Income by account
        """
        reports = {}

        if len(self.income_df) == 0:
            print("⚠️  No income transactions found")
            return reports

        # 1. Top income sources
        income_df = self.income_df.copy()
        income_df['source'] = income_df['description'].str.upper().str.strip()

        # Remove location suffixes
        for suffix in [' AUS', ' AUSTRALIA', ' SYDNEY', ' MELBOURNE', ' BRISBANE',
                      ' QLD', ' NSW', ' VIC', ' SA', ' WA', ' TAS', ' ACT', ' NT']:
            income_df['source'] = income_df['source'].str.replace(
                suffix + '$', '', regex=True
            )

        source_stats = income_df.groupby('source').agg({
            'amount': ['count', 'sum', 'mean'],
            'date': ['min', 'max']
        })
        source_stats.columns = ['Occurrences', 'Total', 'Average', 'First', 'Last']
        source_stats = source_stats.sort_values('Total', ascending=False)

        # Format dates
        source_stats['First'] = pd.to_datetime(source_stats['First']).dt.strftime('%Y-%m-%d')
        source_stats['Last'] = pd.to_datetime(source_stats['Last']).dt.strftime('%Y-%m-%d')

        reports['income_sources'] = source_stats.reset_index()

        # 2. Monthly income
        monthly_income = self.income_df.groupby('year_month').agg({
            'amount': ['count', 'sum', 'mean']
        })
        monthly_income.columns = ['Transactions', 'Total', 'Average']

        # Add summary
        summary = monthly_income.sum()
        summary['Average'] = monthly_income['Total'].sum() / len(monthly_income)
        summary.name = 'TOTAL'
        monthly_income = pd.concat([monthly_income, summary.to_frame().T])

        reports['monthly_income'] = monthly_income

        # 3. Income by account
        account_income = self.income_df.groupby('account_name').agg({
            'amount': ['count', 'sum', 'mean']
        })
        account_income.columns = ['Transactions', 'Total', 'Average']
        account_income = account_income.sort_values('Total', ascending=False)

        reports['income_by_account'] = account_income

        return reports

    # ============================================================================
    # EXPORT FUNCTIONS
    # ============================================================================

    def export_all_to_excel(self, filename: str = 'financial_analysis.xlsx'):
        """
        Export all three report types to a single Excel file.

        Args:
            filename: Output filename
        """
        print(f"\n📊 Generating comprehensive financial analysis...")

        expense_reports = self.generate_expense_reports()
        transfer_reports = self.generate_transfer_reports()
        income_reports = self.generate_income_reports()

        print(f"\n📄 Exporting to Excel: {filename}")

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = {
                'Metric': [
                    'Total Transactions',
                    'Expense Transactions',
                    'Transfer Transactions',
                    'Income Transactions',
                    '',
                    'Total Expenses',
                    'Total Income',
                    'Total Transfers (Net)',
                    '',
                    'Net (Income - Expenses)',
                    'Date Range',
                    'Accounts'
                ],
                'Value': [
                    len(self.df),
                    len(self.expenses_df),
                    len(self.transfers_df),
                    len(self.income_df),
                    '',
                    f"${self.expenses_df['amount'].sum():,.2f}",
                    f"${self.income_df['amount'].sum():,.2f}",
                    f"${self.transfers_df['amount'].sum():,.2f}",
                    '',
                    f"${(self.income_df['amount'].sum() + self.expenses_df['amount'].sum()):,.2f}",
                    f"{self.df['date'].min().strftime('%Y-%m-%d')} to {self.df['date'].max().strftime('%Y-%m-%d')}",
                    ', '.join(self.df['account_name'].unique())
                ]
            }
            pd.DataFrame(overview_data).to_excel(writer, sheet_name='Overview', index=False)
            print("  ✓ Overview")

            # EXPENSE SHEETS
            if expense_reports:
                if 'monthly_by_category' in expense_reports:
                    expense_reports['monthly_by_category'].to_excel(
                        writer, sheet_name='Expenses - Monthly'
                    )
                    print("  ✓ Expenses - Monthly")

                if 'category_summary' in expense_reports:
                    expense_reports['category_summary'].to_excel(
                        writer, sheet_name='Expenses - By Category'
                    )
                    print("  ✓ Expenses - By Category")

                if 'top_merchants' in expense_reports:
                    expense_reports['top_merchants'].to_excel(
                        writer, sheet_name='Expenses - Top 50 Merchants', index=False
                    )
                    print("  ✓ Expenses - Top 50 Merchants")

                if 'monthly_total' in expense_reports:
                    expense_reports['monthly_total'].to_excel(
                        writer, sheet_name='Expenses - Monthly Total'
                    )
                    print("  ✓ Expenses - Monthly Total")

            # TRANSFER SHEETS
            if transfer_reports:
                if 'transfer_summary' in transfer_reports:
                    transfer_reports['transfer_summary'].to_excel(
                        writer, sheet_name='Transfers - Summary'
                    )
                    print("  ✓ Transfers - Summary")

                if 'transfer_pairs' in transfer_reports and len(transfer_reports['transfer_pairs']) > 0:
                    transfer_reports['transfer_pairs'].to_excel(
                        writer, sheet_name='Transfers - Matched Pairs', index=False
                    )
                    print("  ✓ Transfers - Matched Pairs")

                if 'orphaned_transfers' in transfer_reports and len(transfer_reports['orphaned_transfers']) > 0:
                    transfer_reports['orphaned_transfers'].to_excel(
                        writer, sheet_name='Transfers - Orphaned', index=False
                    )
                    print("  ✓ Transfers - Orphaned")

                if 'monthly_transfers' in transfer_reports:
                    transfer_reports['monthly_transfers'].to_excel(
                        writer, sheet_name='Transfers - Monthly'
                    )
                    print("  ✓ Transfers - Monthly")

            # INCOME SHEETS
            if income_reports:
                if 'income_sources' in income_reports:
                    income_reports['income_sources'].to_excel(
                        writer, sheet_name='Income - Sources', index=False
                    )
                    print("  ✓ Income - Sources")

                if 'monthly_income' in income_reports:
                    income_reports['monthly_income'].to_excel(
                        writer, sheet_name='Income - Monthly'
                    )
                    print("  ✓ Income - Monthly")

                if 'income_by_account' in income_reports:
                    income_reports['income_by_account'].to_excel(
                        writer, sheet_name='Income - By Account'
                    )
                    print("  ✓ Income - By Account")

            # FULL EXPENSE LIST
            expense_list = self.expenses_df.copy()
            # Select and order columns
            columns_to_export = ['date', 'year_month', 'account_name', 'amount', 'description']
            if 'category' in expense_list.columns:
                columns_to_export.append('category')

            expense_list = expense_list[columns_to_export].sort_values('date')
            expense_list.to_excel(writer, sheet_name='All Expenses', index=False)
            print("  ✓ All Expenses")

        print(f"\n✅ Excel report saved: {filename}")

    def print_expense_summary(self):
        """Print expense summary to console."""
        reports = self.generate_expense_reports()

        print("\n" + "="*80)
        print("💰 EXPENSE ANALYSIS (Excluding Transfers)")
        print("="*80)

        print(f"\nTotal Expense Transactions: {len(self.expenses_df):,}")
        print(f"Total Spent: ${self.expenses_df['amount'].sum():,.2f}")
        print(f"Average Transaction: ${self.expenses_df['amount'].mean():.2f}")

        if 'category_summary' in reports:
            print("\n" + "-"*80)
            print("SPENDING BY CATEGORY")
            print("-"*80)
            summary = reports['category_summary']
            for idx, row in summary.iterrows():
                print(f"{idx:15s} {row['Total']:>12.2f} ({row['Transactions']:>4.0f} txns, {row['% of Total']:>5.1f}%)")

        if 'top_merchants' in reports:
            print("\n" + "-"*80)
            print("TOP 10 EXPENSE MERCHANTS")
            print("-"*80)
            top10 = reports['top_merchants'].head(10)
            for idx, row in top10.iterrows():
                print(f"{row['merchant'][:40]:40s} {row['Total']:>10.2f} ({row['Transactions']:>3.0f} txns)")

    def print_transfer_summary(self):
        """Print transfer summary to console."""
        reports = self.generate_transfer_reports()

        print("\n" + "="*80)
        print("🔄 TRANSFER ANALYSIS")
        print("="*80)

        print(f"\nTotal Transfer Transactions: {len(self.transfers_df):,}")
        print(f"Net Transfer Amount: ${self.transfers_df['amount'].sum():,.2f}")

        if 'transfer_summary' in reports:
            print("\n" + "-"*80)
            print("TRANSFERS BY ACCOUNT")
            print("-"*80)
            print(reports['transfer_summary'].to_string())

    def print_income_summary(self):
        """Print income summary to console."""
        reports = self.generate_income_reports()

        print("\n" + "="*80)
        print("💵 INCOME ANALYSIS")
        print("="*80)

        print(f"\nTotal Income Transactions: {len(self.income_df):,}")
        print(f"Total Income: ${self.income_df['amount'].sum():,.2f}")
        print(f"Average Income: ${self.income_df['amount'].mean():,.2f}")

        if 'income_sources' in reports:
            print("\n" + "-"*80)
            print("TOP 10 INCOME SOURCES")
            print("-"*80)
            top10 = reports['income_sources'].head(10)
            for idx, row in top10.iterrows():
                print(f"{row['source'][:40]:40s} {row['Total']:>12.2f} ({row['Occurrences']:>3.0f} times)")
