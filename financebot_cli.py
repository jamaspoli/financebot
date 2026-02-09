#!/usr/bin/env python3
"""
FinanceBot CLI - Command-line interface for transaction processing and analysis.

A comprehensive financial transaction processing toolkit with CSV ingestion,
AI-powered categorization, reconciliation, and reporting capabilities.
"""

import click
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from transaction_normalizer import TransactionNormalizer
from transaction_categorizer import TransactionCategorizer
from transaction_reconciler import TransactionReconciler
from transaction_reporter import TransactionReporter
from transaction_reporter_v2 import EnhancedTransactionReporter


class FinanceBotConfig:
    """Manages FinanceBot configuration and data storage."""

    def __init__(self, config_dir: str = '.financebot'):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.config_file = self.config_dir / 'config.json'
        self.registry_file = self.config_dir / 'file_registry.json'
        self.transactions_file = self.config_dir / 'all_transactions.csv'

        self.config = self._load_config()
        self.registry = self._load_registry()

    def _load_config(self) -> dict:
        """Load configuration or create default."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {
            'created': datetime.now().isoformat(),
            'version': '1.0.0',
            'auto_categorize': True,
            'auto_reconcile': True
        }

    def _save_config(self):
        """Save configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _load_registry(self) -> dict:
        """Load file registry or create empty."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {'files': []}

    def _save_registry(self):
        """Save file registry."""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)

    def add_file(self, filepath: str, bank: str):
        """Add file to registry."""
        entry = {
            'filepath': str(filepath),
            'bank': bank,
            'ingested_at': datetime.now().isoformat(),
            'size': Path(filepath).stat().st_size
        }
        self.registry['files'].append(entry)
        self._save_registry()

    def is_file_ingested(self, filepath: str) -> bool:
        """Check if file has been ingested."""
        for entry in self.registry['files']:
            if entry['filepath'] == str(filepath):
                return True
        return False

    def get_transactions(self) -> Optional[pd.DataFrame]:
        """Load all transactions."""
        if self.transactions_file.exists():
            return pd.read_csv(self.transactions_file, parse_dates=['date'])
        return None

    def save_transactions(self, df: pd.DataFrame):
        """Save all transactions."""
        df.to_csv(self.transactions_file, index=False)


# Global config instance
config = FinanceBotConfig()


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    FinanceBot - Financial transaction processing toolkit.

    Process bank transactions with AI-powered categorization, reconciliation,
    and comprehensive reporting.
    """
    pass


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--bank', type=click.Choice(['westpac', 'amex'], case_sensitive=False),
              required=True, help='Bank type for CSV file')
@click.option('--force', is_flag=True, help='Re-ingest file even if already processed')
def ingest(filepath: str, bank: str, force: bool):
    """
    Ingest a new CSV file from Westpac or Amex.

    Example:
        financebot ingest westpac_jan.csv --bank westpac
        financebot ingest amex_feb.csv --bank amex
    """
    filepath = Path(filepath).resolve()

    # Check if already ingested
    if not force and config.is_file_ingested(str(filepath)):
        click.echo(f"⚠️  File already ingested: {filepath.name}")
        click.echo("   Use --force to re-ingest")
        return

    click.echo(f"📥 Ingesting: {filepath.name}")
    click.echo(f"   Bank: {bank.upper()}")

    try:
        # Normalize the new file
        normalizer = TransactionNormalizer()
        new_df = normalizer.normalize(filepath, bank.lower())

        click.echo(f"   ✓ Normalized {len(new_df)} transactions")

        # Load existing transactions
        existing_df = config.get_transactions()

        if existing_df is not None:
            # Merge with existing
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # Remove duplicates based on date, amount, description, account
            before_count = len(combined_df)
            combined_df = combined_df.drop_duplicates(
                subset=['date', 'amount', 'description', 'account_name'],
                keep='first'
            )
            duplicates_removed = before_count - len(combined_df)

            if duplicates_removed > 0:
                click.echo(f"   ✓ Removed {duplicates_removed} duplicate transactions")

            combined_df = combined_df.sort_values('date').reset_index(drop=True)
        else:
            combined_df = new_df

        # Save combined transactions
        config.save_transactions(combined_df)
        config.add_file(str(filepath), bank.lower())

        click.echo(f"\n✅ Successfully ingested!")
        click.echo(f"   Total transactions: {len(combined_df)}")
        click.echo(f"   Date range: {combined_df['date'].min().strftime('%Y-%m-%d')} to {combined_df['date'].max().strftime('%Y-%m-%d')}")

        # Prompt for next steps
        if not combined_df.get('category', pd.Series()).notna().all():
            click.echo("\n💡 Next: Run 'financebot reconcile' to categorize and reconcile transactions")

    except Exception as e:
        click.echo(f"\n❌ Error ingesting file: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--skip-categorize', is_flag=True, help='Skip AI categorization')
@click.option('--skip-reconcile', is_flag=True, help='Skip reconciliation')
def reconcile(skip_categorize: bool, skip_reconcile: bool):
    """
    Process all transactions: categorize and reconcile.

    This runs the full pipeline:
    1. AI categorization (uses Claude API)
    2. Transfer matching and duplicate detection

    Example:
        financebot reconcile
        financebot reconcile --skip-categorize  # Only reconcile
    """
    df = config.get_transactions()

    if df is None or len(df) == 0:
        click.echo("❌ No transactions found. Run 'financebot ingest' first.")
        raise click.Abort()

    click.echo(f"🔄 Processing {len(df)} transactions...\n")

    # Step 1: Categorization
    if not skip_categorize:
        click.echo("1️⃣  AI Categorization")
        click.echo("   " + "="*60)

        try:
            categorizer = TransactionCategorizer()

            # Count uncategorized
            if 'category' not in df.columns:
                has_uncategorized = True
                uncategorized_count = len(df)
            else:
                has_uncategorized = df['category'].isna().any()
                uncategorized_count = df['category'].isna().sum()

            if has_uncategorized:
                click.echo(f"   Categorizing {uncategorized_count} transactions...")

                df = categorizer.categorize(df)
                config.save_transactions(df)

                click.echo(f"   ✓ Categorization complete")
                click.echo(f"   Cache: {len(categorizer.cache)} merchants")
            else:
                click.echo("   ✓ All transactions already categorized")

        except Exception as e:
            click.echo(f"   ❌ Categorization failed: {str(e)}", err=True)
            click.echo("   Continuing with existing categories...")
            df = config.get_transactions()

    # Step 2: Reconciliation
    if not skip_reconcile:
        click.echo("\n2️⃣  Reconciliation")
        click.echo("   " + "="*60)

        try:
            reconciler = TransactionReconciler()
            result = reconciler.reconcile(df)

            # Save reconciled data
            df = result['reconciled_df']
            config.save_transactions(df)

            # Also save to root for compatibility
            df.to_csv('reconciled_transactions.csv', index=False)

            # Show summary
            click.echo(f"\n   ✅ Reconciliation complete!")
            click.echo(f"   • Matched transfer pairs: {result['summary']['matched_transfer_pairs']}")
            click.echo(f"   • Orphaned transfers: {result['summary']['orphaned_transfers']}")
            click.echo(f"   • Duplicate groups: {result['summary']['duplicate_groups']}")

            # Save detailed results
            if len(result['orphaned_transfers']) > 0:
                result['orphaned_transfers'].to_csv('.financebot/orphaned_transfers.csv', index=False)
                click.echo(f"\n   📄 Saved: .financebot/orphaned_transfers.csv")

            if len(result['duplicates']) > 0:
                result['duplicates'].to_csv('.financebot/potential_duplicates.csv', index=False)
                click.echo(f"   📄 Saved: .financebot/potential_duplicates.csv")

        except Exception as e:
            click.echo(f"   ❌ Reconciliation failed: {str(e)}", err=True)

    click.echo("\n" + "="*70)
    click.echo("✅ Processing complete!")
    click.echo("\n💡 Next: Run 'financebot report' to generate financial reports")


@cli.command()
@click.option('--excel', 'output_excel', is_flag=True, help='Generate Excel report')
@click.option('--csv', 'output_csv', is_flag=True, help='Generate CSV reports')
@click.option('--console', 'output_console', is_flag=True, default=True, help='Display in console')
@click.option('--output', '-o', default='financial_report.xlsx', help='Excel output filename')
@click.option('--enhanced', is_flag=True, help='Use enhanced reporting (separate expenses, transfers, income)')
def report(output_excel: bool, output_csv: bool, output_console: bool, output: str, enhanced: bool):
    """
    Generate financial reports.

    Use --enhanced for separate Expense, Transfer, and Income analysis.

    Reports include:
    - Monthly spending by category
    - Account balances over time
    - Top merchants by spending
    - Income vs expenses summary

    Example:
        financebot report                    # Console output
        financebot report --excel            # Generate Excel
        financebot report --enhanced --excel # Separate reports
    """
    df = config.get_transactions()

    if df is None or len(df) == 0:
        click.echo("❌ No transactions found. Run 'financebot ingest' first.")
        raise click.Abort()

    # Check if categorized
    if 'category' not in df.columns or df['category'].isna().any():
        uncategorized_count = df['category'].isna().sum() if 'category' in df.columns else len(df)
        click.echo(f"⚠️  Warning: {uncategorized_count} transactions not categorized")
        click.echo("   Run 'financebot reconcile' first for complete reports\n")

    click.echo(f"📊 Generating reports for {len(df)} transactions...\n")

    try:
        if enhanced:
            # Use enhanced reporter with separate expense/transfer/income analysis
            reporter = EnhancedTransactionReporter(df)

            if output_console:
                reporter.print_expense_summary()
                reporter.print_transfer_summary()
                reporter.print_income_summary()

            if output_excel or (not output_csv and not output_console):
                reporter.export_all_to_excel(output)

        else:
            # Use original reporter
            reporter = TransactionReporter(df)
            reports = reporter.generate_all_reports(print_to_console=output_console)

            # Export to Excel
            if output_excel or (not output_csv and not output_console):
                click.echo(f"\n📄 Exporting to Excel: {output}")
                reporter.export_to_excel(output, reports)

            # Export to CSV
            if output_csv:
                click.echo("\n📁 Exporting to CSV: reports/")
                reporter.export_to_csv('reports', reports)

        click.echo("\n✅ Reports generated successfully!")

    except Exception as e:
        click.echo(f"\n❌ Report generation failed: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--uncategorized', is_flag=True, help='Show uncategorized transactions')
@click.option('--duplicates', is_flag=True, help='Show potential duplicates')
@click.option('--orphaned', is_flag=True, help='Show orphaned transfers')
@click.option('--all', 'show_all', is_flag=True, help='Show all flagged items')
@click.option('--limit', '-n', default=20, help='Number of items to show')
def review(uncategorized: bool, duplicates: bool, orphaned: bool, show_all: bool, limit: int):
    """
    Review uncategorized or flagged transactions.

    This helps identify items that need manual attention:
    - Uncategorized transactions
    - Potential duplicates
    - Orphaned transfers

    Example:
        financebot review --all              # Show all issues
        financebot review --uncategorized    # Show only uncategorized
        financebot review --duplicates -n 10 # Show first 10 duplicates
    """
    df = config.get_transactions()

    if df is None or len(df) == 0:
        click.echo("❌ No transactions found. Run 'financebot ingest' first.")
        raise click.Abort()

    # If no flags, default to --all
    if not any([uncategorized, duplicates, orphaned, show_all]):
        show_all = True

    # Show uncategorized
    if show_all or uncategorized:
        click.echo("\n" + "="*70)
        click.echo("🔍 UNCATEGORIZED TRANSACTIONS")
        click.echo("="*70)

        if 'category' in df.columns:
            uncat = df[df['category'].isna() | (df['category'] == 'Other')]
            if len(uncat) > 0:
                click.echo(f"\nFound {len(uncat)} transactions\n")

                for idx, row in uncat.head(limit).iterrows():
                    click.echo(
                        f"{row['date'].strftime('%Y-%m-%d')} | "
                        f"{row['account_name']:20s} | "
                        f"${row['amount']:10.2f} | "
                        f"{row['description'][:40]}"
                    )

                if len(uncat) > limit:
                    click.echo(f"\n... and {len(uncat) - limit} more")

                click.echo(f"\n💡 Add overrides: financebot override add \"MERCHANT\" \"Category\"")
            else:
                click.echo("\n✅ All transactions categorized!")
        else:
            click.echo("\n⚠️  No categories found. Run 'financebot reconcile' first.")

    # Show duplicates
    if show_all or duplicates:
        click.echo("\n" + "="*70)
        click.echo("🔍 POTENTIAL DUPLICATES")
        click.echo("="*70)

        dup_file = Path('.financebot/potential_duplicates.csv')
        if dup_file.exists():
            dups = pd.read_csv(dup_file, parse_dates=['date'])
            click.echo(f"\nFound {len(dups)} transactions in {dups['duplicate_group_id'].nunique()} groups\n")

            for group_id in dups['duplicate_group_id'].unique()[:min(5, limit)]:
                group = dups[dups['duplicate_group_id'] == group_id]
                click.echo(f"\nGroup {int(group_id)} ({len(group)} transactions):")
                for idx, row in group.iterrows():
                    click.echo(
                        f"  {row['date'].strftime('%Y-%m-%d')} | "
                        f"{row['account_name']:20s} | "
                        f"${row['amount']:10.2f} | "
                        f"{row['description'][:35]}"
                    )
        else:
            click.echo("\n✅ No duplicates found!")
            click.echo("   Run 'financebot reconcile' to check for duplicates")

    # Show orphaned transfers
    if show_all or orphaned:
        click.echo("\n" + "="*70)
        click.echo("🔍 ORPHANED TRANSFERS")
        click.echo("="*70)

        orphan_file = Path('.financebot/orphaned_transfers.csv')
        if orphan_file.exists():
            orphans = pd.read_csv(orphan_file, parse_dates=['date'])
            click.echo(f"\nFound {len(orphans)} orphaned transfers\n")

            for idx, row in orphans.head(limit).iterrows():
                click.echo(
                    f"{row['date'].strftime('%Y-%m-%d')} | "
                    f"{row['account_name']:20s} | "
                    f"${row['amount']:10.2f} | "
                    f"{row['description'][:40]}"
                )

            if len(orphans) > limit:
                click.echo(f"\n... and {len(orphans) - limit} more")
        else:
            click.echo("\n✅ No orphaned transfers found!")
            click.echo("   Run 'financebot reconcile' to check for orphaned transfers")


@cli.group()
def override():
    """Manage category overrides for merchants."""
    pass


@override.command('add')
@click.argument('merchant')
@click.argument('category')
def override_add(merchant: str, category: str):
    """
    Add a category override for a merchant.

    Example:
        financebot override add "WOOLWORTHS" "Groceries"
        financebot override add "NETFLIX" "Entertainment"
    """
    from transaction_categorizer import TransactionCategorizer

    categorizer = TransactionCategorizer()

    try:
        categorizer.add_override(merchant, category)
        click.echo(f"✅ Added override: {merchant} → {category}")
        click.echo("\n💡 Run 'financebot reconcile' to re-categorize with new override")
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        click.echo(f"\nValid categories: {', '.join(TransactionCategorizer.CATEGORIES)}")


@override.command('list')
def override_list():
    """List all category overrides."""
    from transaction_categorizer import TransactionCategorizer

    categorizer = TransactionCategorizer()
    overrides = categorizer.list_overrides()

    if overrides:
        click.echo("\n📋 Category Overrides:")
        click.echo("="*70)
        for merchant, category in sorted(overrides.items()):
            click.echo(f"  {merchant:40s} → {category}")
        click.echo(f"\nTotal: {len(overrides)} overrides")
    else:
        click.echo("No overrides configured.")


@override.command('remove')
@click.argument('merchant')
def override_remove(merchant: str):
    """
    Remove a category override.

    Example:
        financebot override remove "WOOLWORTHS"
    """
    from transaction_categorizer import TransactionCategorizer

    categorizer = TransactionCategorizer()
    categorizer.remove_override(merchant)
    click.echo(f"✅ Removed override for: {merchant}")


@cli.command()
def status():
    """Show FinanceBot status and statistics."""
    click.echo("\n" + "="*70)
    click.echo("📊 FINANCEBOT STATUS")
    click.echo("="*70)

    # Check for transactions
    df = config.get_transactions()

    if df is None or len(df) == 0:
        click.echo("\n❌ No transactions loaded")
        click.echo("\n💡 Get started: financebot ingest <file> --bank <westpac|amex>")
        return

    # Basic stats
    click.echo(f"\n📈 Transaction Data:")
    click.echo(f"   • Total transactions: {len(df):,}")
    click.echo(f"   • Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    click.echo(f"   • Accounts: {', '.join(df['account_name'].unique())}")

    # Categorization status
    if 'category' in df.columns:
        categorized = df['category'].notna().sum()
        uncategorized = len(df) - categorized
        click.echo(f"\n🏷️  Categorization:")
        click.echo(f"   • Categorized: {categorized:,} ({categorized/len(df)*100:.1f}%)")
        if uncategorized > 0:
            click.echo(f"   • Uncategorized: {uncategorized:,}")
    else:
        click.echo(f"\n🏷️  Categorization: Not run yet")

    # File registry
    files = config.registry.get('files', [])
    if files:
        click.echo(f"\n📁 Ingested Files: {len(files)}")
        for file in files[-5:]:  # Show last 5
            click.echo(f"   • {Path(file['filepath']).name} ({file['bank']}) - {file['ingested_at'][:10]}")

    # Check for reports
    click.echo(f"\n📊 Reports:")
    if Path('financial_report.xlsx').exists():
        size = Path('financial_report.xlsx').stat().st_size / 1024
        click.echo(f"   • financial_report.xlsx ({size:.1f} KB)")
    else:
        click.echo(f"   • No reports generated yet")

    click.echo("\n" + "="*70)


@cli.command()
def init():
    """Initialize FinanceBot in the current directory."""
    click.echo("🚀 Initializing FinanceBot...\n")

    config_dir = Path('.financebot')
    if config_dir.exists() and any(config_dir.iterdir()):
        click.echo("⚠️  FinanceBot already initialized in this directory")
        if not click.confirm("Reinitialize?"):
            return

    config_dir.mkdir(exist_ok=True)

    click.echo("✅ Created .financebot directory")
    click.echo("\n📝 Configuration:")
    click.echo("   • Auto-categorize: enabled")
    click.echo("   • Auto-reconcile: enabled")

    click.echo("\n🎉 FinanceBot initialized!")
    click.echo("\n📚 Quick Start:")
    click.echo("   1. financebot ingest <file> --bank <westpac|amex>")
    click.echo("   2. financebot reconcile")
    click.echo("   3. financebot report --excel")
    click.echo("\n💡 Run 'financebot --help' for more commands")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
