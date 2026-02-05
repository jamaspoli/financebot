# FinanceBot CLI

A comprehensive command-line interface for financial transaction processing with AI-powered categorization, reconciliation, and reporting.

## Installation

### Option 1: Development Install (Recommended)

```bash
# Clone or navigate to the project
cd financebot

# Install in development mode
pip install -e .
```

### Option 2: Direct Install

```bash
pip install -r requirements.txt
python setup.py install
```

After installation, the `financebot` command will be available globally.

## Quick Start

```bash
# 1. Initialize FinanceBot
financebot init

# 2. Ingest CSV files
financebot ingest westpac_jan.csv --bank westpac
financebot ingest amex_jan.csv --bank amex

# 3. Process transactions
financebot reconcile

# 4. Generate reports
financebot report --excel

# 5. Review status
financebot status
```

## Commands

### `financebot init`

Initialize FinanceBot in the current directory.

Creates `.financebot/` directory with configuration files.

```bash
financebot init
```

### `financebot ingest`

Ingest a new CSV file from Westpac or Amex.

**Syntax:**
```bash
financebot ingest <filepath> --bank <westpac|amex> [--force]
```

**Examples:**
```bash
# Ingest Westpac file
financebot ingest westpac_jan_2026.csv --bank westpac

# Ingest Amex file
financebot ingest amex_feb.csv --bank amex

# Re-ingest a file (force)
financebot ingest westpac_jan.csv --bank westpac --force
```

**Features:**
- Automatically detects and removes duplicates
- Tracks ingested files to prevent double-processing
- Merges with existing transaction data
- Shows transaction count and date range

**Output:**
```
📥 Ingesting: westpac_jan.csv
   Bank: WESTPAC
   ✓ Normalized 523 transactions
   ✓ Removed 5 duplicate transactions

✅ Successfully ingested!
   Total transactions: 2,731
   Date range: 2025-01-01 to 2026-02-04
```

### `financebot reconcile`

Process all transactions: categorize and reconcile.

**Syntax:**
```bash
financebot reconcile [--skip-categorize] [--skip-reconcile]
```

**Examples:**
```bash
# Full reconciliation (categorize + reconcile)
financebot reconcile

# Skip categorization, only reconcile
financebot reconcile --skip-categorize

# Skip reconciliation, only categorize
financebot reconcile --skip-reconcile
```

**What it does:**
1. **AI Categorization** - Uses Claude API to categorize transactions
   - Batches 75 transactions per API call
   - Uses cached merchant categorizations
   - Applies manual overrides
2. **Reconciliation** - Finds transfer matches and duplicates
   - Links transfers between accounts
   - Detects potential duplicates
   - Identifies orphaned transfers

**Output:**
```
🔄 Processing 2,731 transactions...

1️⃣  AI Categorization
   ============================================================
   Categorizing 2,731 transactions...
   Processing batch 1 (75 transactions)...
   Processing batch 2 (75 transactions)...
   ...
   ✓ Categorization complete
   Cache: 1,231 merchants

2️⃣  Reconciliation
   ============================================================

   ✅ Reconciliation complete!
   • Matched transfer pairs: 12
   • Orphaned transfers: 25
   • Duplicate groups: 33

✅ Processing complete!
```

### `financebot report`

Generate financial reports.

**Syntax:**
```bash
financebot report [--excel] [--csv] [--console] [-o <filename>]
```

**Examples:**
```bash
# Console output only
financebot report

# Generate Excel report
financebot report --excel

# Generate CSV reports
financebot report --csv

# Both Excel and CSV
financebot report --excel --csv

# Custom Excel filename
financebot report --excel -o february_report.xlsx
```

**Reports Generated:**
- Monthly spending by category
- Account balances over time
- Top 20 merchants by spending
- Income vs expenses summary
- Category breakdown with percentages
- Account-level summary
- Overall statistics

**Output Formats:**
- **Console**: Formatted tables in terminal
- **Excel**: Multi-sheet workbook (default: `financial_report.xlsx`)
- **CSV**: Individual files in `reports/` directory

### `financebot review`

Review uncategorized or flagged transactions.

**Syntax:**
```bash
financebot review [--uncategorized] [--duplicates] [--orphaned] [--all] [-n <limit>]
```

**Examples:**
```bash
# Show all flagged items (default)
financebot review

# Show only uncategorized transactions
financebot review --uncategorized

# Show potential duplicates
financebot review --duplicates

# Show orphaned transfers
financebot review --orphaned

# Show first 50 items
financebot review -n 50
```

**Output:**
```
======================================================================
🔍 UNCATEGORIZED TRANSACTIONS
======================================================================

Found 15 transactions

2026-02-03 | Westpac-5391         |     $-6.10 | LS Between The Flags C Dicky Beach AUS
2026-02-02 | Westpac-5391         |   $-868.39 | TAL LIFE LIMITED SYDNEY AUS
...

💡 Add overrides: financebot override add "MERCHANT" "Category"

======================================================================
🔍 POTENTIAL DUPLICATES
======================================================================

Found 74 transactions in 33 groups

Group 1 (4 transactions):
  2025-11-25 | Amex-21001           |      $4.00 | MICROSOFT MSBILL.INFO
  2025-11-25 | Amex-21001           |      $4.00 | MICROSOFT MSBILL.INFO
  2025-11-25 | Amex-21001           |      $4.00 | MICROSOFT MSBILL.INFO
  2025-11-25 | Amex-21001           |      $4.00 | MICROSOFT MSBILL.INFO
```

### `financebot override`

Manage category overrides for merchants.

#### `financebot override add`

Add a category override for a merchant.

**Syntax:**
```bash
financebot override add "<merchant>" "<category>"
```

**Examples:**
```bash
financebot override add "WOOLWORTHS" "Groceries"
financebot override add "NETFLIX" "Entertainment"
financebot override add "TELSTRA" "Utilities"
```

**Valid Categories:**
- Groceries
- Dining
- Transport
- Utilities
- Entertainment
- Health
- Shopping
- Income
- Transfer
- Fees
- Other

#### `financebot override list`

List all configured overrides.

```bash
financebot override list
```

**Output:**
```
📋 Category Overrides:
======================================================================
  APPLE.COM/BILL                           → Entertainment
  COLES                                    → Groceries
  NETFLIX                                  → Entertainment
  TELSTRA                                  → Utilities
  WOOLWORTHS                               → Groceries

Total: 5 overrides
```

#### `financebot override remove`

Remove a category override.

```bash
financebot override remove "WOOLWORTHS"
```

### `financebot status`

Show FinanceBot status and statistics.

```bash
financebot status
```

**Output:**
```
======================================================================
📊 FINANCEBOT STATUS
======================================================================

📈 Transaction Data:
   • Total transactions: 2,731
   • Date range: 2025-01-01 to 2026-02-04
   • Accounts: Amex-21001, Westpac-5391, Amex-21019

🏷️  Categorization:
   • Categorized: 2,731 (100.0%)

📁 Ingested Files: 2
   • Westpac Sample download Data_export_05022026 (1).csv (westpac) - 2026-02-05
   • Amex Sample Download - activity.csv (amex) - 2026-02-05

📊 Reports:
   • financial_report.xlsx (13.5 KB)

======================================================================
```

## Directory Structure

After initialization, FinanceBot creates the following structure:

```
.financebot/
├── config.json              # Configuration settings
├── file_registry.json       # Ingested files registry
├── all_transactions.csv     # All normalized transactions
├── orphaned_transfers.csv   # Orphaned transfers (after reconcile)
└── potential_duplicates.csv # Potential duplicates (after reconcile)

reports/                     # CSV reports (after report --csv)
├── monthly_category.csv
├── balances.csv
├── top_merchants.csv
├── monthly.csv
├── by_category.csv
├── by_account.csv
└── overall.csv

financial_report.xlsx        # Excel report (after report --excel)

transaction_cache.json       # AI categorization cache (shared)
category_overrides.json      # Manual overrides (shared)
```

## Workflows

### Daily Workflow

```bash
# 1. Download CSV from bank
# 2. Ingest new file
financebot ingest ~/Downloads/westpac_today.csv --bank westpac

# 3. Process (only categorizes new transactions)
financebot reconcile

# 4. Review if needed
financebot review --uncategorized
```

### Monthly Reporting

```bash
# 1. Generate reports
financebot report --excel --csv

# 2. Review duplicates
financebot review --duplicates

# 3. Check status
financebot status
```

### Setting Up Overrides

```bash
# 1. Find uncategorized merchants
financebot review --uncategorized

# 2. Add overrides for common merchants
financebot override add "WOOLWORTHS" "Groceries"
financebot override add "COLES" "Groceries"
financebot override add "NETFLIX" "Entertainment"

# 3. Re-categorize with new overrides
financebot reconcile

# 4. Verify
financebot review --uncategorized
```

## Configuration

Configuration is stored in `.financebot/config.json`:

```json
{
  "created": "2026-02-05T20:00:00",
  "version": "1.0.0",
  "auto_categorize": true,
  "auto_reconcile": true
}
```

## Environment Variables

- `ANTHROPIC_API_KEY` - Required for AI categorization
  - Set in `.env` file or environment
  - Get your key from https://console.anthropic.com/

## Features

### Smart Duplicate Detection

When ingesting files, FinanceBot automatically detects and removes duplicates based on:
- Date
- Amount
- Description
- Account name

### Incremental Processing

- Only new/uncategorized transactions are sent to AI
- Cached merchant categorizations are reused
- Manual overrides are applied first
- Efficient API usage minimizes costs

### File Registry

Tracks all ingested files to prevent accidental double-processing:
- Filename
- Bank type
- Ingestion timestamp
- File size

Use `--force` flag to re-ingest if needed.

## Tips & Best Practices

1. **Set up overrides early** - Add common merchants before first reconcile
2. **Review regularly** - Check `financebot review` after each reconcile
3. **Keep original files** - Don't delete CSVs until verified
4. **Export regularly** - Generate reports monthly for records
5. **Use status often** - Quick check on current state
6. **Version control .env** - Keep API key in `.env`, not in git

## Troubleshooting

**"No transactions found"**
- Run `financebot ingest` first to add data

**"API key required"**
- Set `ANTHROPIC_API_KEY` environment variable
- Or add to `.env` file in project root

**"File already ingested"**
- Use `--force` flag to re-ingest
- Or use a different filename

**Categorization seems wrong**
- Add manual overrides with `financebot override add`
- Re-run `financebot reconcile`

**Reports show wrong date range**
- Check transaction dates in `.financebot/all_transactions.csv`
- Verify CSV files have correct date format

## Advanced Usage

### Scripting

```bash
#!/bin/bash
# Monthly report script

# Process all CSVs in downloads
for file in ~/Downloads/bank_*.csv; do
    bank=$(echo $file | grep -o "westpac\|amex")
    financebot ingest "$file" --bank "$bank"
done

# Reconcile and report
financebot reconcile
financebot report --excel --csv

# Send report via email
mail -s "Monthly Finance Report" you@example.com < financial_report.xlsx
```

### Batch Operations

```bash
# Process multiple months
for month in jan feb mar; do
    financebot ingest westpac_${month}.csv --bank westpac
    financebot ingest amex_${month}.csv --bank amex
done

financebot reconcile
financebot report --excel -o q1_report.xlsx
```

## API Costs

Typical costs with Claude Sonnet 4.5:
- First reconcile (2,731 transactions): ~$0.15-0.20
- Subsequent reconciles (cached): ~$0.001-0.01
- Average monthly processing: <$0.05

## Performance

- Ingestion: ~0.5-1 second per file
- Categorization: ~2-3 seconds per 75 transactions
- Reconciliation: ~1-2 seconds for 2,731 transactions
- Reporting: ~2-3 seconds total

## Version

FinanceBot CLI v1.0.0

## License

MIT
