# Transaction Reconciler

Identifies matching transfers between accounts, flags potential duplicates, and detects orphaned transfers that might indicate missing data.

## Features

- **Transfer Matching**: Automatically links transfers between accounts (same amount, opposite signs, within date window)
- **Duplicate Detection**: Flags potential duplicate transactions (same amount, description, date, account)
- **Orphaned Transfer Identification**: Finds transfers without matching pairs that might indicate missing data
- **Comprehensive Reporting**: Generates detailed reconciliation reports with statistics

## Quick Start

```python
from transaction_reconciler import TransactionReconciler
import pandas as pd

# Load your categorized transactions
df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])

# Initialize reconciler
reconciler = TransactionReconciler(
    date_window_days=3,      # Search within 3 days for matches
    amount_tolerance=0.01    # Allow $0.01 difference
)

# Run full reconciliation
result = reconciler.reconcile(df)

# Generate report
report = reconciler.generate_report(result)
print(report)

# Save results
result['reconciled_df'].to_csv('reconciled_transactions.csv', index=False)
result['orphaned_transfers'].to_csv('orphaned_transfers.csv', index=False)
result['duplicates'].to_csv('potential_duplicates.csv', index=False)
```

## How It Works

### 1. Transfer Matching

The reconciler identifies matching transfers by looking for:

**Criteria:**
- Same absolute amount (within tolerance, default $0.01)
- Opposite signs (one positive, one negative)
- Within date window (default 3 days)
- Between different accounts
- Both categorized as 'Transfer'

**Example Match:**
```
Date       | Account      | Amount    | Description
2025-02-09 | Westpac-5391 | -1000.00  | Transfer to Savings
2025-02-09 | Amex-21001   | +1000.00  | Transfer from Checking
```

These would be linked with the same `transfer_pair_id`.

### 2. Duplicate Detection

Flags transactions that appear to be duplicates:

**Criteria:**
- Same amount (exact match)
- Same description (case-insensitive)
- Same date
- Same account

**Common Causes:**
- Data export errors
- Payment processing issues
- Multiple charges from merchant
- CSV file imported twice

**Example Duplicates:**
```
Date       | Account    | Amount  | Description
2025-11-25 | Amex-21001 | -4.00   | MICROSOFT MSBILL.INFO
2025-11-25 | Amex-21001 | -4.00   | MICROSOFT MSBILL.INFO
2025-11-25 | Amex-21001 | -4.00   | MICROSOFT MSBILL.INFO
```

### 3. Orphaned Transfer Identification

Finds transfers without matching pairs, which might indicate:

- **Missing data** from another account
- **External transfers** (to/from accounts not in dataset)
- **Miscategorized transactions** (should not be 'Transfer')
- **Timing issues** (match outside date window)

**Example Orphaned Transfer:**
```
Date       | Account      | Amount    | Description
2025-02-09 | Westpac-5391 | +69690.40 | TFR FROM Westpac Choice
```

This is an inflow from an external account (Westpac Choice) not in the dataset.

## API Reference

### `TransactionReconciler`

#### `__init__(date_window_days=3, amount_tolerance=0.01)`

Initialize the reconciler.

**Parameters:**
- `date_window_days` (int): Days to search for matching transfers (default: 3)
- `amount_tolerance` (float): Amount difference tolerance in dollars (default: 0.01)

#### `find_transfer_matches(df, ...)`

Find matching transfers between accounts.

**Parameters:**
- `df` (DataFrame): Transaction data
- `date_col` (str): Date column name (default: 'date')
- `amount_col` (str): Amount column name (default: 'amount')
- `account_col` (str): Account column name (default: 'account_name')
- `category_col` (str): Category column name (default: 'category')

**Returns:**
- Tuple of (reconciled_df, unmatched_transfers_df)
- reconciled_df includes `transfer_pair_id` column

#### `find_duplicates(df, ...)`

Find potential duplicate transactions.

**Parameters:**
- `df` (DataFrame): Transaction data
- `date_col` (str): Date column name (default: 'date')
- `amount_col` (str): Amount column name (default: 'amount')
- `description_col` (str): Description column name (default: 'description')
- `account_col` (str): Account column name (default: 'account_name')

**Returns:**
- DataFrame of potential duplicates with `duplicate_group_id` column

#### `find_orphaned_transfers(df, ...)`

Find orphaned transfers without matching pairs.

**Parameters:**
- `df` (DataFrame): Transaction data (must have `transfer_pair_id` from find_transfer_matches)
- `date_col` (str): Date column name (default: 'date')
- `amount_col` (str): Amount column name (default: 'amount')
- `category_col` (str): Category column name (default: 'category')
- `transfer_pair_col` (str): Transfer pair ID column name (default: 'transfer_pair_id')

**Returns:**
- DataFrame of orphaned transfers

#### `reconcile(df, ...)`

Perform complete reconciliation analysis.

**Parameters:**
- `df` (DataFrame): Transaction data
- Additional column name parameters (same as above methods)

**Returns:**
- Dictionary containing:
  - `'reconciled_df'`: DataFrame with transfer_pair_id added
  - `'matched_transfers'`: Matched transfer pairs
  - `'orphaned_transfers'`: Unmatched transfers
  - `'duplicates'`: Potential duplicates
  - `'summary'`: Statistics dictionary

#### `generate_report(reconciliation_result)`

Generate human-readable reconciliation report.

**Parameters:**
- `reconciliation_result` (dict): Result from `reconcile()`

**Returns:**
- Formatted report string

## Usage Examples

### Basic Reconciliation

```python
from transaction_reconciler import TransactionReconciler
import pandas as pd

# Load data
df = pd.read_csv('categorized_transactions.csv', parse_dates=['date'])

# Reconcile
reconciler = TransactionReconciler()
result = reconciler.reconcile(df)

# Print summary
print(f"Matched pairs: {result['summary']['matched_transfer_pairs']}")
print(f"Orphaned transfers: {result['summary']['orphaned_transfers']}")
print(f"Duplicates: {result['summary']['duplicate_transactions']}")
```

### Analyzing Orphaned Transfers

```python
# Get orphaned transfers
orphaned = result['orphaned_transfers']

# Analyze by direction
outflows = orphaned[orphaned['amount'] < 0]
inflows = orphaned[orphaned['amount'] > 0]

print(f"Orphaned outflows: {len(outflows)} (${outflows['amount'].sum():.2f})")
print(f"Orphaned inflows: {len(inflows)} (${inflows['amount'].sum():.2f})")

# Find largest orphaned transfers
largest = orphaned.nlargest(10, lambda x: abs(x['amount']))
print(largest[['date', 'account_name', 'amount', 'description']])
```

### Handling Duplicates

```python
# Get duplicates
duplicates = result['duplicates']

if len(duplicates) > 0:
    # Group by duplicate_group_id
    for group_id in duplicates['duplicate_group_id'].unique():
        group = duplicates[duplicates['duplicate_group_id'] == group_id]
        print(f"\nDuplicate Group {group_id}:")
        print(group[['date', 'account_name', 'amount', 'description']])

        # Decide action: keep first, remove others, or investigate
        # ...
```

### Custom Date Window

```python
# Look for matches within 7 days (for slower transfers)
reconciler = TransactionReconciler(date_window_days=7)
result = reconciler.reconcile(df)

# Or be strict: same day only
reconciler = TransactionReconciler(date_window_days=0)
result = reconciler.reconcile(df)
```

### Custom Amount Tolerance

```python
# Allow up to $1 difference (for fees/FX)
reconciler = TransactionReconciler(amount_tolerance=1.00)
result = reconciler.reconcile(df)

# Be strict: exact match only
reconciler = TransactionReconciler(amount_tolerance=0.00)
result = reconciler.reconcile(df)
```

## Interpreting Results

### High Match Rate (>80%)
✓ Good data quality
✓ Most transfers are properly paired
✓ Minimal missing data

### Low Match Rate (<50%)
⚠ Possible issues:
- Missing data from other accounts
- Many external transfers
- Incorrect categorization
- Date window too narrow

### Many Duplicates
⚠ Investigate:
- Was data imported multiple times?
- Are these legitimate repeated charges?
- Check with merchant if unclear

### Large Orphaned Transfers
⚠ Review carefully:
- External accounts not in dataset?
- Transfer timing outside window?
- Misclassified as transfer?

## Output Files

### reconciled_transactions.csv
All transactions with added `transfer_pair_id` column:
- Matched transfers have same pair ID
- Unmatched transfers have null pair ID

### orphaned_transfers.csv
Transfers without matching pairs:
- Review for missing data
- Identify external accounts
- Check categorization accuracy

### potential_duplicates.csv
Groups of potentially duplicate transactions:
- Each group has same `duplicate_group_id`
- Review and decide on action
- Remove true duplicates, keep legitimate charges

## Integration with Other Modules

```python
from transaction_normalizer import TransactionNormalizer
from transaction_categorizer import TransactionCategorizer
from transaction_reconciler import TransactionReconciler

# Complete workflow
normalizer = TransactionNormalizer()
df = normalizer.normalize_multiple([
    ('westpac.csv', 'westpac'),
    ('amex.csv', 'amex')
])

categorizer = TransactionCategorizer()
df = categorizer.categorize(df)

reconciler = TransactionReconciler()
result = reconciler.reconcile(df)

# Save final reconciled data
result['reconciled_df'].to_csv('final_transactions.csv', index=False)
```

## Best Practices

1. **Run reconciliation after categorization** - Needs 'Transfer' category
2. **Review orphaned transfers regularly** - May indicate missing data
3. **Investigate all duplicates** - Some may be legitimate
4. **Adjust date window based on your banks** - Some transfers take longer
5. **Use amount tolerance for FX transactions** - Account for fees
6. **Keep original data** - Don't delete until duplicates confirmed

## Troubleshooting

**No transfers found**
- Check if transactions are categorized as 'Transfer'
- Verify category column exists and is named correctly

**No matches found**
- All transfers might be to/from external accounts
- Try increasing date_window_days
- Check if amounts are truly opposite signs

**Too many false duplicates**
- Some merchants charge multiple times legitimately
- Review each group individually
- Consider transaction IDs if available

## Performance

- Fast even with large datasets (10,000+ transactions)
- O(n²) worst case for matching, but optimized with sorting
- Duplicate detection uses efficient grouping
- Typical runtime: <5 seconds for 5,000 transactions

## License

MIT
