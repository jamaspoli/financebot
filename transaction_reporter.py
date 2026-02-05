"""
Transaction Reporter for generating financial reports and exports.

This module provides comprehensive reporting capabilities including monthly
spending analysis, balance tracking, merchant analysis, and income/expense summaries.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class TransactionReporter:
    """Generates financial reports from transaction data."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize the TransactionReporter.

        Args:
            df: DataFrame with transaction data
                Required columns: date, amount, description, account_name
                Optional columns: category, original_balance
        """
        self.df = df.copy()

        # Ensure date is datetime
        if not pd.api.types.is_datetime64_any_dtype(self.df['date']):
            self.df['date'] = pd.to_datetime(self.df['date'])

        # Add month column for grouping
        self.df['month'] = self.df['date'].dt.to_period('M')
        self.df['year_month'] = self.df['date'].dt.strftime('%Y-%m')

        # Separate income and expenses
        self.df['is_expense'] = self.df['amount'] < 0
        self.df['is_income'] = self.df['amount'] > 0

    def generate_monthly_category_report(self) -> pd.DataFrame:
        """
        Generate monthly spending by category report.

        Returns:
            DataFrame with months as rows and categories as columns
        """
        if 'category' not in self.df.columns:
            raise ValueError("DataFrame must have 'category' column for this report")

        # Pivot table: months x categories
        monthly_category = self.df.pivot_table(
            values='amount',
            index='year_month',
            columns='category',
            aggfunc='sum',
            fill_value=0
        )

        # Add total column
        monthly_category['Total'] = monthly_category.sum(axis=1)

        # Add summary row
        summary = monthly_category.sum()
        summary.name = 'TOTAL'
        monthly_category = pd.concat([monthly_category, summary.to_frame().T])

        # Sort columns by total spending (most negative first)
        col_order = monthly_category.loc['TOTAL'].drop('Total').sort_values().index.tolist()
        col_order.append('Total')
        monthly_category = monthly_category[col_order]

        return monthly_category

    def generate_balance_report(self) -> pd.DataFrame:
        """
        Generate account balances over time.

        Calculates running balance for each account by month.

        Returns:
            DataFrame with months as rows and accounts as columns
        """
        # Sort by date for running balance calculation
        df_sorted = self.df.sort_values(['account_name', 'date'])

        # Calculate running balance per account
        df_sorted['running_balance'] = df_sorted.groupby('account_name')['amount'].cumsum()

        # Get end-of-month balances
        monthly_balance = df_sorted.groupby(['year_month', 'account_name']).agg({
            'running_balance': 'last',
            'date': 'last'
        }).reset_index()

        # Pivot to wide format
        balance_pivot = monthly_balance.pivot(
            index='year_month',
            columns='account_name',
            values='running_balance'
        ).ffill()  # Forward fill for months with no transactions

        # Add total column
        balance_pivot['Total'] = balance_pivot.sum(axis=1)

        return balance_pivot

    def generate_top_merchants_report(
        self,
        top_n: int = 20,
        min_transactions: int = 2
    ) -> pd.DataFrame:
        """
        Generate top merchants by spending report.

        Args:
            top_n: Number of top merchants to include
            min_transactions: Minimum number of transactions required

        Returns:
            DataFrame with merchant statistics
        """
        # Normalize merchant names (remove location suffixes)
        df_merchants = self.df.copy()
        df_merchants['merchant'] = df_merchants['description'].str.upper().str.strip()

        # Remove common location suffixes for better grouping
        for suffix in [' AUS', ' AUSTRALIA', ' SYDNEY', ' MELBOURNE', ' BRISBANE', ' QLD', ' NSW']:
            df_merchants['merchant'] = df_merchants['merchant'].str.replace(
                suffix + '$', '', regex=True
            )

        # Group by merchant
        merchant_stats = df_merchants.groupby('merchant').agg({
            'amount': ['count', 'sum', 'mean', 'min', 'max'],
            'date': ['min', 'max']
        }).reset_index()

        # Flatten column names
        merchant_stats.columns = [
            'Merchant', 'Transactions', 'Total', 'Average', 'Min', 'Max',
            'First Transaction', 'Last Transaction'
        ]

        # Filter by minimum transactions
        merchant_stats = merchant_stats[merchant_stats['Transactions'] >= min_transactions]

        # Sort by total spending (most negative = most spent)
        merchant_stats = merchant_stats.sort_values('Total').head(top_n)

        # Format dates
        merchant_stats['First Transaction'] = pd.to_datetime(
            merchant_stats['First Transaction']
        ).dt.strftime('%Y-%m-%d')
        merchant_stats['Last Transaction'] = pd.to_datetime(
            merchant_stats['Last Transaction']
        ).dt.strftime('%Y-%m-%d')

        return merchant_stats.reset_index(drop=True)

    def generate_income_expense_summary(self) -> Dict[str, pd.DataFrame]:
        """
        Generate comprehensive income vs expenses summary.

        Returns:
            Dictionary containing multiple summary DataFrames:
            - 'monthly': Monthly income, expenses, and net
            - 'by_category': Expenses broken down by category
            - 'by_account': Income and expenses by account
            - 'overall': Overall statistics
        """
        summaries = {}

        # 1. Monthly summary
        monthly = self.df.groupby('year_month').agg({
            'amount': [
                lambda x: x[x > 0].sum(),  # Income
                lambda x: x[x < 0].sum(),  # Expenses
                'sum'  # Net
            ]
        })
        monthly.columns = ['Income', 'Expenses', 'Net']
        monthly['Savings Rate %'] = (monthly['Net'] / monthly['Income'] * 100).round(1)

        # Add totals row
        totals = monthly.sum()
        totals['Savings Rate %'] = (totals['Net'] / totals['Income'] * 100).round(1)
        totals.name = 'TOTAL'
        monthly = pd.concat([monthly, totals.to_frame().T])

        summaries['monthly'] = monthly

        # 2. By category (expenses only)
        if 'category' in self.df.columns:
            expenses_df = self.df[self.df['amount'] < 0].copy()
            by_category = expenses_df.groupby('category').agg({
                'amount': ['sum', 'count', 'mean']
            })
            by_category.columns = ['Total Spent', 'Transactions', 'Average']
            by_category = by_category.sort_values('Total Spent')

            # Add percentage of total expenses
            total_expenses = by_category['Total Spent'].sum()
            by_category['% of Total'] = (by_category['Total Spent'] / total_expenses * 100).round(1)

            summaries['by_category'] = by_category

        # 3. By account
        by_account = self.df.groupby('account_name').agg({
            'amount': [
                lambda x: x[x > 0].sum(),  # Income
                lambda x: x[x < 0].sum(),  # Expenses
                'sum',  # Net
                'count'  # Transactions
            ]
        })
        by_account.columns = ['Income', 'Expenses', 'Net', 'Transactions']

        # Add totals row
        totals = by_account.sum()
        totals.name = 'TOTAL'
        by_account = pd.concat([by_account, totals.to_frame().T])

        summaries['by_account'] = by_account

        # 4. Overall statistics
        total_income = self.df[self.df['amount'] > 0]['amount'].sum()
        total_expenses = self.df[self.df['amount'] < 0]['amount'].sum()
        net = total_income + total_expenses

        date_range = f"{self.df['date'].min().strftime('%Y-%m-%d')} to {self.df['date'].max().strftime('%Y-%m-%d')}"
        num_months = self.df['month'].nunique()

        overall = pd.DataFrame({
            'Metric': [
                'Date Range',
                'Number of Months',
                'Total Transactions',
                'Total Income',
                'Total Expenses',
                'Net (Income + Expenses)',
                'Average Monthly Income',
                'Average Monthly Expenses',
                'Average Monthly Net',
                'Savings Rate %'
            ],
            'Value': [
                date_range,
                num_months,
                f"{len(self.df):,}",
                f"${total_income:,.2f}",
                f"${total_expenses:,.2f}",
                f"${net:,.2f}",
                f"${total_income / num_months:,.2f}",
                f"${total_expenses / num_months:,.2f}",
                f"${net / num_months:,.2f}",
                f"{(net / total_income * 100):.1f}%"
            ]
        })

        summaries['overall'] = overall

        return summaries

    def generate_category_trends(self) -> pd.DataFrame:
        """
        Generate category spending trends over time.

        Returns:
            DataFrame showing how spending in each category changes month-to-month
        """
        if 'category' not in self.df.columns:
            raise ValueError("DataFrame must have 'category' column for this report")

        # Get monthly spending by category (expenses only)
        expenses = self.df[self.df['amount'] < 0].copy()

        trends = expenses.pivot_table(
            values='amount',
            index='year_month',
            columns='category',
            aggfunc='sum',
            fill_value=0
        )

        return trends

    def print_report(self, title: str, df: pd.DataFrame, format_money: bool = True):
        """
        Print a formatted report to terminal.

        Args:
            title: Report title
            df: DataFrame to display
            format_money: Whether to format numbers as currency
        """
        print("\n" + "="*80)
        print(title)
        print("="*80)

        if format_money:
            # Format numeric columns as currency
            df_display = df.copy()
            for col in df_display.columns:
                if pd.api.types.is_numeric_dtype(df_display[col]):
                    if col not in ['Transactions', '% of Total', 'Savings Rate %']:
                        df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
        else:
            df_display = df

        print(df_display.to_string())
        print()

    def generate_all_reports(self, print_to_console: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Generate all available reports.

        Args:
            print_to_console: Whether to print reports to console

        Returns:
            Dictionary of all generated reports
        """
        reports = {}

        if print_to_console:
            print("\n" + "="*80)
            print("GENERATING FINANCIAL REPORTS")
            print("="*80)

        # 1. Monthly category report
        try:
            reports['monthly_category'] = self.generate_monthly_category_report()
            if print_to_console:
                self.print_report("MONTHLY SPENDING BY CATEGORY", reports['monthly_category'])
        except ValueError as e:
            if print_to_console:
                print(f"\nSkipping monthly category report: {e}")

        # 2. Balance report
        reports['balances'] = self.generate_balance_report()
        if print_to_console:
            self.print_report("ACCOUNT BALANCES OVER TIME", reports['balances'])

        # 3. Top merchants
        reports['top_merchants'] = self.generate_top_merchants_report(top_n=20)
        if print_to_console:
            self.print_report("TOP 20 MERCHANTS BY SPENDING", reports['top_merchants'])

        # 4. Income/Expense summaries
        income_expense = self.generate_income_expense_summary()
        reports.update(income_expense)

        if print_to_console:
            self.print_report("MONTHLY INCOME VS EXPENSES", reports['monthly'])

            if 'by_category' in reports:
                self.print_report("EXPENSES BY CATEGORY", reports['by_category'])

            self.print_report("INCOME/EXPENSES BY ACCOUNT", reports['by_account'])

            print("\n" + "="*80)
            print("OVERALL SUMMARY")
            print("="*80)
            print(reports['overall'].to_string(index=False))
            print()

        return reports

    def export_to_excel(
        self,
        filename: str = 'financial_report.xlsx',
        reports: Optional[Dict[str, pd.DataFrame]] = None
    ):
        """
        Export reports to Excel file with multiple sheets.

        Args:
            filename: Output Excel filename
            reports: Dictionary of reports (if None, generates all reports)
        """
        if reports is None:
            reports = self.generate_all_reports(print_to_console=False)

        print(f"\nExporting reports to Excel: {filename}")

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Sheet 1: Overall Summary
            if 'overall' in reports:
                reports['overall'].to_excel(
                    writer, sheet_name='Summary', index=False
                )
                print("  ✓ Summary")

            # Sheet 2: Monthly Income/Expenses
            if 'monthly' in reports:
                reports['monthly'].to_excel(
                    writer, sheet_name='Monthly Income-Expenses'
                )
                print("  ✓ Monthly Income-Expenses")

            # Sheet 3: Monthly by Category
            if 'monthly_category' in reports:
                reports['monthly_category'].to_excel(
                    writer, sheet_name='Monthly by Category'
                )
                print("  ✓ Monthly by Category")

            # Sheet 4: Category Summary
            if 'by_category' in reports:
                reports['by_category'].to_excel(
                    writer, sheet_name='Expenses by Category'
                )
                print("  ✓ Expenses by Category")

            # Sheet 5: Account Summary
            if 'by_account' in reports:
                reports['by_account'].to_excel(
                    writer, sheet_name='By Account'
                )
                print("  ✓ By Account")

            # Sheet 6: Account Balances
            if 'balances' in reports:
                reports['balances'].to_excel(
                    writer, sheet_name='Account Balances'
                )
                print("  ✓ Account Balances")

            # Sheet 7: Top Merchants
            if 'top_merchants' in reports:
                reports['top_merchants'].to_excel(
                    writer, sheet_name='Top Merchants', index=False
                )
                print("  ✓ Top Merchants")

        print(f"\n✓ Excel report saved: {filename}")

    def export_to_csv(
        self,
        output_dir: str = 'reports',
        reports: Optional[Dict[str, pd.DataFrame]] = None
    ):
        """
        Export reports to separate CSV files.

        Args:
            output_dir: Output directory for CSV files
            reports: Dictionary of reports (if None, generates all reports)
        """
        if reports is None:
            reports = self.generate_all_reports(print_to_console=False)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\nExporting reports to CSV in: {output_dir}/")

        for name, df in reports.items():
            filename = output_path / f"{name}.csv"
            df.to_csv(filename)
            print(f"  ✓ {filename.name}")

        print(f"\n✓ CSV reports saved in: {output_dir}/")


def main():
    """Example usage of TransactionReporter."""
    import pandas as pd

    # Load categorized and reconciled transactions
    print("Loading transaction data...")
    try:
        df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])
        print(f"✓ Loaded {len(df)} transactions")
    except FileNotFoundError:
        print("✗ categorized_transactions.csv not found!")
        print("  Run example_complete_workflow.py first.")
        return

    # Generate reports
    reporter = TransactionReporter(df)

    # Generate and display all reports
    reports = reporter.generate_all_reports(print_to_console=True)

    # Export to Excel
    reporter.export_to_excel('financial_report.xlsx', reports)

    # Export to CSV
    reporter.export_to_csv('reports', reports)

    print("\n" + "="*80)
    print("REPORTING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
