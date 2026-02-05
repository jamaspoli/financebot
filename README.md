# FinanceBot

A Python toolkit for ingesting, normalizing, and categorizing bank transactions from Westpac and Amex using AI.

## Features

### Transaction Normalizer
- Normalizes Westpac and Amex CSV exports into a unified format
- Handles different date formats and transaction types
- Consistent amount representation: negative = expenses, positive = income
- Handles multiline fields in Amex CSV exports
- Can process multiple files and combine them into a single dataset

### Transaction Categorizer
- **AI-Powered Categorization** using Claude API
- **Smart Batching**: 50-100 transactions per API call to minimize costs
- **Intelligent Caching**: Remembers merchant categorizations
- **Manual Overrides**: Set persistent rules for specific merchants
- **11 Categories**: Groceries, Dining, Transport, Utilities, Entertainment, Health, Shopping, Income, Transfer, Fees, Other

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Anthropic API key (for categorization):
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or copy `.env.example` to `.env` and add your key there.

## Quick Start

### Complete Workflow

```python
from transaction_normalizer import TransactionNormalizer
from transaction_categorizer import TransactionCategorizer

# 1. Normalize bank CSV files
normalizer = TransactionNormalizer()
files = [
    ('westpac.csv', 'westpac'),
    ('amex.csv', 'amex')
]
df = normalizer.normalize_multiple(files)

# 2. Categorize transactions
categorizer = TransactionCategorizer()
categorizer.add_override('WOOLWORTHS', 'Groceries')
categorizer.add_override('NETFLIX', 'Entertainment')

categorized_df = categorizer.categorize(df)

# 3. Analyze and save
summary = categorizer.get_category_summary(categorized_df)
print(summary)
categorized_df.to_csv('categorized_transactions.csv', index=False)
```

### Run Complete Example

```bash
python example_complete_workflow.py
```

This will:
1. Normalize sample Westpac and Amex CSV files
2. Add common merchant overrides
3. Categorize all transactions using Claude API
4. Generate summary statistics
5. Save categorized results

## Normalized Format

All transactions are normalized to these columns:

| Column | Description |
|--------|-------------|
| **date** | Transaction date (YYYY-MM-DD) |
| **amount** | Amount (negative = expense, positive = income) |
| **description** | Transaction description |
| **account_name** | Account identifier (e.g., "Westpac-5391") |
| **original_balance** | Balance after transaction (Westpac only) |
| **category** | AI-assigned category (after categorization) |

## Categories

- **Groceries**: Supermarkets, food stores
- **Dining**: Restaurants, cafes, takeaway
- **Transport**: Fuel, public transport, parking, rideshare
- **Utilities**: Electricity, gas, water, internet, phone
- **Entertainment**: Streaming, movies, games, subscriptions
- **Health**: Medical, dental, pharmacy, insurance, gym
- **Shopping**: Retail, clothing, electronics, online shopping
- **Income**: Salary, payments received
- **Transfer**: Account transfers, internal payments
- **Fees**: Bank fees, service charges
- **Other**: Anything else

## Usage Examples

### 1. Normalize Transactions Only

```python
from transaction_normalizer import TransactionNormalizer

normalizer = TransactionNormalizer()

# Single file
westpac_df = normalizer.normalize('westpac.csv', 'westpac')
amex_df = normalizer.normalize('amex.csv', 'amex')

# Multiple files combined
files = [
    ('westpac_jan.csv', 'westpac'),
    ('amex_jan.csv', 'amex')
]
df = normalizer.normalize_multiple(files)
df.to_csv('normalized.csv', index=False)
```

### 2. Categorize Pre-Normalized Data

```python
from transaction_categorizer import TransactionCategorizer
import pandas as pd

# Load normalized data
df = pd.read_csv('normalized.csv')

# Categorize
categorizer = TransactionCategorizer()
categorized_df = categorizer.categorize(df)
categorized_df.to_csv('categorized.csv', index=False)
```

### 3. Manual Overrides

```python
categorizer = TransactionCategorizer()

# Add overrides for specific merchants
categorizer.add_override('WOOLWORTHS', 'Groceries')
categorizer.add_override('SPOTIFY', 'Entertainment')
categorizer.add_override('TELSTRA', 'Utilities')

# List all overrides
overrides = categorizer.list_overrides()

# Remove an override
categorizer.remove_override('SPOTIFY')
```

### 4. Category Analysis

```python
# Get summary by category
summary = categorizer.get_category_summary(categorized_df)
print(summary)

# Output:
#                Count    Total  Average
# Transport         45  -234.56    -5.21
# Groceries         89  -756.32    -8.50
# Dining           123 -1234.56   -10.04
```

## Bank Format Details

### Westpac
- **Columns**: Bank Account, Date, Narrative, Debit Amount, Credit Amount, Balance, Categories, Serial
- **Date format**: DD/MM/YYYY
- **Debit Amount**: Expenses (converted to negative)
- **Credit Amount**: Income (kept positive)

### Amex
- **Columns**: Date, Date Processed, Description, Card Member, Account #, Amount, ...
- **Date format**: DD/MM/YYYY
- **Amount**: Positive = charges (converted to negative), Negative = payments (converted to positive)
- **Note**: Amex exports don't include balance information

## Caching & Performance

The categorizer uses two persistent files:

1. **transaction_cache.json**: Auto-generated AI categorizations
2. **category_overrides.json**: Manual rules (take precedence)

**First run** (no cache): ~1 API call per 75 transactions
**Subsequent runs**: Only new merchants need categorization

**Cost estimate**: $0.003-0.005 per 1000 transactions (first run)

## Documentation

- [Transaction Normalizer API](README.md) - This file
- [Transaction Categorizer Guide](CATEGORIZER_README.md) - Detailed categorizer docs

## Example Scripts

- `test_normalizer.py` - Test normalization with sample files
- `test_categorizer.py` - Test categorization with sample data
- `example_complete_workflow.py` - Full end-to-end example

## API Reference

### TransactionNormalizer

#### `normalize(csv_path, bank)`
Normalize a single bank CSV file.

**Parameters:**
- `csv_path`: Path to CSV file
- `bank`: 'westpac' or 'amex'

**Returns:** DataFrame with normalized columns

#### `normalize_multiple(file_bank_pairs)`
Normalize and combine multiple CSV files.

**Parameters:**
- `file_bank_pairs`: List of (csv_path, bank_type) tuples

**Returns:** Combined DataFrame sorted by date

### TransactionCategorizer

#### `categorize(df, description_col='description', amount_col='amount')`
Categorize transactions in a DataFrame.

**Parameters:**
- `df`: DataFrame with transaction data
- `description_col`: Column name for descriptions
- `amount_col`: Column name for amounts

**Returns:** DataFrame with new 'category' column

#### `add_override(description, category)`
Add manual category override for a merchant.

#### `get_category_summary(df)`
Get summary statistics by category.

**Returns:** DataFrame with Count, Total, Average per category

## Troubleshooting

**"API key required" error**
→ Set `ANTHROPIC_API_KEY` environment variable

**Categories seem incorrect**
→ Add manual overrides for specific merchants

**Too many API calls**
→ Ensure cache file is being saved/loaded

**Slow processing**
→ Increase `batch_size` parameter (up to 100)

## License

MIT
