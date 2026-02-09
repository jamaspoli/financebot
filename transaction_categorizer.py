"""
Transaction Categorizer using Claude API.

This module categorizes financial transactions using Claude AI with intelligent
caching and batching to minimize API calls.
"""

import pandas as pd
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from anthropic import Anthropic


class TransactionCategorizer:
    """Categorizes transactions using Claude API with caching and batching."""

    CATEGORIES = [
        'Groceries',
        'Dining',
        'Transport',
        'Utilities',
        'Entertainment',
        'Health',
        'Shopping',
        'Income',
        'Transfer',
        'Fees',
        'Education',
        'Home Renovation',
        'Insurance',
        'Property',
        'Other'
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_file: str = 'transaction_cache.json',
        overrides_file: str = 'category_overrides.json',
        batch_size: int = 75
    ):
        """
        Initialize the TransactionCategorizer.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var
            cache_file: Path to cache file for storing categorization results
            overrides_file: Path to manual overrides file
            batch_size: Number of transactions to process in one API call (default: 75)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key required. Provide via api_key parameter or ANTHROPIC_API_KEY env var"
            )

        self.client = Anthropic(api_key=self.api_key)
        self.cache_file = Path(cache_file)
        self.overrides_file = Path(overrides_file)
        self.batch_size = batch_size

        # Load cache and overrides
        self.cache = self._load_json(self.cache_file)
        self.overrides = self._load_json(self.overrides_file)

    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file or return empty dict if file doesn't exist."""
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_json(self, data: Dict, file_path: Path):
        """Save data to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _normalize_merchant(self, description: str) -> str:
        """
        Normalize merchant name for cache key.

        Extracts core merchant name by removing common suffixes and extra info.
        """
        if pd.isna(description):
            return "UNKNOWN"

        # Convert to uppercase and strip
        normalized = str(description).upper().strip()

        # Remove common location suffixes
        for suffix in [' AUS', ' AUSTRALIA', ' USA', ' SYDNEY', ' MELBOURNE', ' BRISBANE']:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()

        return normalized

    def _get_category_from_cache(self, description: str) -> Optional[str]:
        """
        Get category from cache or overrides.

        Overrides take precedence over cache.
        """
        merchant = self._normalize_merchant(description)

        # Check overrides first
        if merchant in self.overrides:
            return self.overrides[merchant]

        # Then check cache
        if merchant in self.cache:
            return self.cache[merchant]

        return None

    def _categorize_batch(self, transactions: List[Dict]) -> Dict[str, str]:
        """
        Categorize a batch of transactions using Claude API.

        Args:
            transactions: List of dicts with 'description' and 'amount' keys

        Returns:
            Dict mapping description to category
        """
        # Build prompt with transaction list
        transaction_list = []
        for i, txn in enumerate(transactions, 1):
            amount = txn['amount']
            desc = txn['description']
            transaction_list.append(f"{i}. {desc} (${amount:.2f})")

        prompt = f"""Categorize these financial transactions into one of these categories:
{', '.join(self.CATEGORIES)}

Transactions:
{chr(10).join(transaction_list)}

For each transaction, respond with ONLY the transaction number and category, one per line.
Format: "1: Category"

Rules:
- Groceries: Supermarkets, food stores (Woolworths, Coles, etc.)
- Dining: Restaurants, cafes, takeaway food
- Transport: Fuel, public transport, parking, tolls, ride-sharing
- Utilities: Electricity, gas, water, internet, phone bills
- Entertainment: Movies, streaming services, games, events, subscriptions
- Health: Medical, dental, pharmacy, insurance, gym, fitness
- Shopping: Retail purchases, clothing, electronics, online shopping
- Income: Salary, payments received (positive amounts usually)
- Transfer: Account transfers, payments between own accounts
- Fees: Bank fees, service charges, foreign transaction fees
- Education: School fees, tuition, educational expenses, school donations
- Home Renovation: Construction, bathroom/kitchen renovations, major home improvements
- Insurance: All insurance (life, health, car, home, travel, income protection)
- Property: Property management, real estate, strata fees, property services
- Other: Anything that doesn't fit above categories

Be concise and accurate."""

        # Call Claude API
        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text
        categories = {}

        for line in response_text.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                try:
                    num_str, category = line.split(':', 1)
                    num = int(num_str.strip()) - 1  # Convert to 0-indexed
                    category = category.strip()

                    # Validate category
                    if category in self.CATEGORIES and 0 <= num < len(transactions):
                        desc = transactions[num]['description']
                        categories[desc] = category
                except (ValueError, IndexError):
                    continue

        return categories

    def categorize(self, df: pd.DataFrame, description_col: str = 'description',
                   amount_col: str = 'amount', save_cache: bool = True) -> pd.DataFrame:
        """
        Categorize transactions in a DataFrame.

        Args:
            df: DataFrame with transaction data
            description_col: Name of column containing transaction descriptions
            amount_col: Name of column containing transaction amounts
            save_cache: Whether to save cache after categorization (default: True)

        Returns:
            DataFrame with new 'category' column added
        """
        # Create a copy to avoid modifying original
        result_df = df.copy()

        # Initialize category column
        result_df['category'] = None

        # Track which transactions need API categorization
        uncategorized_indices = []
        uncategorized_transactions = []

        # First pass: check cache and overrides
        for idx, row in result_df.iterrows():
            description = row[description_col]
            cached_category = self._get_category_from_cache(description)

            if cached_category:
                result_df.at[idx, 'category'] = cached_category
            else:
                uncategorized_indices.append(idx)
                uncategorized_transactions.append({
                    'description': description,
                    'amount': row[amount_col]
                })

        # Process uncategorized transactions in batches
        if uncategorized_transactions:
            print(f"Categorizing {len(uncategorized_transactions)} transactions using Claude API...")

            for i in range(0, len(uncategorized_transactions), self.batch_size):
                batch = uncategorized_transactions[i:i + self.batch_size]
                batch_indices = uncategorized_indices[i:i + self.batch_size]

                print(f"  Processing batch {i // self.batch_size + 1} "
                      f"({len(batch)} transactions)...")

                try:
                    categories = self._categorize_batch(batch)

                    # Update results and cache
                    for idx, txn in zip(batch_indices, batch):
                        desc = txn['description']
                        if desc in categories:
                            category = categories[desc]
                            result_df.at[idx, 'category'] = category

                            # Add to cache
                            merchant = self._normalize_merchant(desc)
                            self.cache[merchant] = category
                        else:
                            # Fallback to 'Other' if not categorized
                            result_df.at[idx, 'category'] = 'Other'

                except Exception as e:
                    print(f"  Error processing batch: {e}")
                    # Set uncategorized to 'Other'
                    for idx in batch_indices:
                        if pd.isna(result_df.at[idx, 'category']):
                            result_df.at[idx, 'category'] = 'Other'

        # Save cache if requested
        if save_cache:
            self._save_json(self.cache, self.cache_file)

        # Fill any remaining nulls with 'Other'
        result_df['category'] = result_df['category'].fillna('Other')

        print(f"Categorization complete. Cache size: {len(self.cache)} merchants")

        return result_df

    def add_override(self, description: str, category: str, save: bool = True):
        """
        Add a manual category override for a merchant.

        Args:
            description: Transaction description or merchant name
            category: Category to assign
            save: Whether to save overrides to file immediately (default: True)

        Raises:
            ValueError: If category is not valid
        """
        if category not in self.CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: {', '.join(self.CATEGORIES)}"
            )

        merchant = self._normalize_merchant(description)
        self.overrides[merchant] = category

        if save:
            self._save_json(self.overrides, self.overrides_file)
            print(f"Added override: {merchant} -> {category}")

    def remove_override(self, description: str, save: bool = True):
        """
        Remove a manual category override.

        Args:
            description: Transaction description or merchant name
            save: Whether to save overrides to file immediately (default: True)
        """
        merchant = self._normalize_merchant(description)
        if merchant in self.overrides:
            del self.overrides[merchant]
            if save:
                self._save_json(self.overrides, self.overrides_file)
                print(f"Removed override: {merchant}")
        else:
            print(f"No override found for: {merchant}")

    def list_overrides(self) -> Dict[str, str]:
        """Return all manual overrides."""
        return self.overrides.copy()

    def clear_cache(self, save: bool = True):
        """
        Clear the categorization cache.

        Args:
            save: Whether to save empty cache to file (default: True)
        """
        self.cache = {}
        if save:
            self._save_json(self.cache, self.cache_file)
            print("Cache cleared")

    def get_category_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics by category.

        Args:
            df: DataFrame with 'category' and 'amount' columns

        Returns:
            DataFrame with category statistics
        """
        if 'category' not in df.columns:
            raise ValueError("DataFrame must have 'category' column")

        summary = df.groupby('category').agg({
            'amount': ['count', 'sum', 'mean']
        }).round(2)

        summary.columns = ['Count', 'Total', 'Average']
        summary = summary.sort_values('Total')

        return summary


def main():
    """Example usage of TransactionCategorizer."""
    from transaction_normalizer import TransactionNormalizer

    # Load and normalize transactions
    normalizer = TransactionNormalizer()
    df = normalizer.normalize('westpac.csv', 'westpac')

    # Categorize transactions
    categorizer = TransactionCategorizer()

    # Add some manual overrides
    categorizer.add_override('WOOLWORTHS', 'Groceries')
    categorizer.add_override('COLES', 'Groceries')

    # Categorize
    categorized_df = categorizer.categorize(df)

    # Show summary
    summary = categorizer.get_category_summary(categorized_df)
    print("\nCategory Summary:")
    print(summary)

    # Save results
    categorized_df.to_csv('categorized_transactions.csv', index=False)
    print("\nSaved to categorized_transactions.csv")


if __name__ == '__main__':
    main()
