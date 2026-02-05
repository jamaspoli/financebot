"""Test script for transaction reporter."""

import pandas as pd
from transaction_reporter import TransactionReporter


def main():
    print("="*80)
    print("Transaction Reporter Test")
    print("="*80)

    # Load categorized transactions
    print("\nLoading transaction data...")
    try:
        df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])
        print(f"✓ Loaded {len(df)} transactions")
        print(f"  Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        print(f"  Accounts: {', '.join(df['account_name'].unique())}")
    except FileNotFoundError:
        print("✗ categorized_transactions.csv not found!")
        print("  Run example_complete_workflow.py first to generate categorized data.")
        return

    # Initialize reporter
    print("\n" + "="*80)
    print("Initializing Reporter")
    print("="*80)
    reporter = TransactionReporter(df)
    print("✓ Reporter initialized")

    # Generate all reports
    print("\n" + "="*80)
    print("Generating Reports")
    print("="*80)
    reports = reporter.generate_all_reports(print_to_console=True)

    # Additional custom analyses
    print("\n" + "="*80)
    print("ADDITIONAL INSIGHTS")
    print("="*80)

    # Highest spending months
    print("\nTop 5 Highest Spending Months:")
    monthly_expenses = reports['monthly']['Expenses'].drop('TOTAL').sort_values()
    for month, amount in monthly_expenses.head(5).items():
        print(f"  {month}: ${amount:,.2f}")

    # Best savings months
    print("\nTop 5 Best Savings Months:")
    monthly_savings = reports['monthly']['Net'].drop('TOTAL').sort_values(ascending=False)
    for month, amount in monthly_savings.head(5).items():
        savings_rate = reports['monthly'].loc[month, 'Savings Rate %']
        print(f"  {month}: ${amount:,.2f} ({savings_rate}% savings rate)")

    # Category insights
    if 'by_category' in reports:
        print("\nLargest Expense Categories:")
        for idx, row in reports['by_category'].head(5).iterrows():
            print(f"  {idx}: ${row['Total Spent']:,.2f} ({row['Transactions']:.0f} transactions, ${row['Average']:.2f} avg)")

    # Export reports
    print("\n" + "="*80)
    print("Exporting Reports")
    print("="*80)

    # Export to Excel
    reporter.export_to_excel('financial_report.xlsx', reports)

    # Export to CSV
    reporter.export_to_csv('reports', reports)

    print("\n" + "="*80)
    print("Testing Complete!")
    print("="*80)
    print("\nGenerated files:")
    print("  - financial_report.xlsx (Excel workbook with all reports)")
    print("  - reports/ directory (individual CSV files)")


if __name__ == '__main__':
    main()
