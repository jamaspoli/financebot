# Transaction Categorizer

Automatically categorize financial transactions using Claude AI with intelligent caching and manual override support.

## Features

- **AI-Powered Categorization**: Uses Claude API to intelligently categorize transactions
- **Batching**: Processes 50-100 transactions per API call to minimize costs
- **Smart Caching**: Remembers merchant categorizations to avoid repeat API calls
- **Manual Overrides**: Set persistent rules for specific merchants
- **11 Categories**: Groceries, Dining, Transport, Utilities, Entertainment, Health, Shopping, Income, Transfer, Fees, Other

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or pass it directly:
```python
categorizer = TransactionCategorizer(api_key='your-api-key-here')
```

## Quick Start

```python
from transaction_categorizer import TransactionCategorizer
import pandas as pd

# Initialize categorizer
categorizer = TransactionCategorizer()

# Load your transaction data
df = pd.read_csv('transactions.csv')

# Categorize (requires 'description' and 'amount' columns)
categorized_df = categorizer.categorize(df)

# Save results
categorized_df.to_csv('categorized.csv', index=False)
```

## Complete Workflow Example

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

# 2. Initialize categorizer
categorizer = TransactionCategorizer(batch_size=75)

# 3. Add manual overrides for known merchants
categorizer.add_override('WOOLWORTHS', 'Groceries')
categorizer.add_override('COLES', 'Groceries')
categorizer.add_override('NETFLIX', 'Entertainment')

# 4. Categorize all transactions
categorized_df = categorizer.categorize(df)

# 5. Get summary by category
summary = categorizer.get_category_summary(categorized_df)
print(summary)

# 6. Save results
categorized_df.to_csv('all_categorized.csv', index=False)
```

## Categories

| Category | Examples |
|----------|----------|
| **Groceries** | Supermarkets (Woolworths, Coles), food stores |
| **Dining** | Restaurants, cafes, takeaway food |
| **Transport** | Fuel, public transport, parking, tolls, Uber |
| **Utilities** | Electricity, gas, water, internet, phone bills |
| **Entertainment** | Movies, streaming (Netflix, Spotify), games |
| **Health** | Medical, dental, pharmacy, insurance, gym |
| **Shopping** | Retail, clothing, electronics, Amazon |
| **Income** | Salary, payments received |
| **Transfer** | Account transfers, payments between accounts |
| **Fees** | Bank fees, service charges, foreign transaction fees |
| **Other** | Anything that doesn't fit above categories |

## Caching System

The categorizer uses two types of persistent storage:

### 1. Cache (`transaction_cache.json`)
- Automatically stores AI-generated categorizations
- Keyed by normalized merchant name
- Reduces API calls for recurring merchants
- Example:
```json
{
  "WOOLWORTHS 2718 KELVIN": "Groceries",
  "APPLE.COM/BILL": "Entertainment",
  "TRANSLINK TICKETING": "Transport"
}
```

### 2. Overrides (`category_overrides.json`)
- Manually set rules that take precedence over cache
- Persistent across sessions
- Perfect for correcting AI mistakes or enforcing business rules
- Example:
```json
{
  "NETFLIX": "Entertainment",
  "CHARLOTTE AND ARMANDO": "Dining"
}
```

## Managing Overrides

### Add Override
```python
categorizer.add_override('SPOTIFY', 'Entertainment')
```

### Remove Override
```python
categorizer.remove_override('SPOTIFY')
```

### List All Overrides
```python
overrides = categorizer.list_overrides()
for merchant, category in overrides.items():
    print(f"{merchant}: {category}")
```

### Clear Cache (but keep overrides)
```python
categorizer.clear_cache()
```

## Advanced Usage

### Custom Batch Size
```python
# Smaller batches for more detailed results
categorizer = TransactionCategorizer(batch_size=25)

# Larger batches for faster processing
categorizer = TransactionCategorizer(batch_size=100)
```

### Custom Cache Files
```python
categorizer = TransactionCategorizer(
    cache_file='my_cache.json',
    overrides_file='my_overrides.json'
)
```

### Skip Cache Saving
```python
# Don't save cache during categorization (useful for testing)
df = categorizer.categorize(df, save_cache=False)
```

### Category Summary Statistics
```python
summary = categorizer.get_category_summary(categorized_df)
print(summary)

# Output:
#                Count    Total  Average
# Transport         45  -234.56    -5.21
# Groceries         89  -756.32    -8.50
# Dining           123 -1234.56   -10.04
# ...
```

## API Costs

The categorizer uses Claude Sonnet 4.5 with ~1024 token output per batch:

- **First run** (no cache): ~1 API call per 75 transactions
- **Subsequent runs** (with cache): Minimal API calls for new merchants only
- **Estimated cost**: $0.003-0.005 per 1000 transactions (first run)

Example: 10,000 transactions with 500 unique merchants:
- First run: ~7 API calls (~$0.03-0.05)
- Later runs: Only new merchants (~$0.001-0.01)

## Merchant Normalization

The categorizer normalizes merchant names for better cache matching:

```python
"WOOLWORTHS 2718 KELVIN KELVIN GROVE AUS" → "WOOLWORTHS 2718 KELVIN KELVIN GROVE"
"Apple.com/bill SYDNEY AUS" → "APPLE.COM/BILL SYDNEY"
"Coles The Gap 4506 THE GAP" → "COLES THE GAP 4506 THE GAP"
```

This ensures variations of the same merchant use cached categories.

## Error Handling

The categorizer gracefully handles API errors:

- **Network errors**: Uncategorized transactions default to 'Other'
- **Invalid responses**: Logs warning and uses 'Other'
- **Missing API key**: Raises clear error at initialization

## Performance Tips

1. **Use batching**: Default batch size of 75 is optimal for cost/speed
2. **Set overrides early**: Add common merchants as overrides before categorizing
3. **Reuse cache**: The cache file persists across runs - don't delete it!
4. **Process incrementally**: Categorize new transactions separately to maximize cache hits

## Example Output

```csv
date,amount,description,account_name,original_balance,category
2026-02-03,-6.10,CHARLOTTE AND ARMANDO SPRING HILL AUS,Westpac-5391,0.0,Dining
2026-02-03,-136.45,Oracle Thai Massage Red Hill AUS,Westpac-5391,0.0,Health
2026-02-02,-868.39,TAL LIFE LIMITED SYDNEY AUS,Westpac-5391,0.0,Health
2026-02-04,-39.99,APPLE.COM/BILL SYDNEY,Amex-21001,,Entertainment
```

## Troubleshooting

**Problem**: "API key required" error
- **Solution**: Set `ANTHROPIC_API_KEY` environment variable or pass `api_key` parameter

**Problem**: Categories seem wrong
- **Solution**: Add manual overrides for specific merchants

**Problem**: Too many API calls
- **Solution**: Check if cache file is being saved/loaded properly

**Problem**: Slow processing
- **Solution**: Increase `batch_size` parameter (up to 100)

## API Reference

### `TransactionCategorizer`

#### `__init__(api_key, cache_file, overrides_file, batch_size)`
Initialize the categorizer with optional configuration.

#### `categorize(df, description_col='description', amount_col='amount', save_cache=True)`
Categorize transactions in a DataFrame. Returns DataFrame with new 'category' column.

#### `add_override(description, category, save=True)`
Add manual category override for a merchant.

#### `remove_override(description, save=True)`
Remove a manual category override.

#### `list_overrides()`
Get dictionary of all manual overrides.

#### `clear_cache(save=True)`
Clear the categorization cache.

#### `get_category_summary(df)`
Get summary statistics grouped by category.

## License

MIT
