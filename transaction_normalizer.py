"""
Transaction Normalizer for Westpac and Amex CSV files.

This module provides functionality to ingest and normalize CSV files from
Westpac and Amex banks into a common format.
"""

import pandas as pd
from pathlib import Path
from typing import Literal, Optional, Union
from datetime import datetime


class TransactionNormalizer:
    """Normalizes bank transaction CSV files from different banks into a common format."""

    NORMALIZED_COLUMNS = ['date', 'amount', 'description', 'account_name', 'original_balance']

    def __init__(self):
        """Initialize the TransactionNormalizer."""
        pass

    def normalize_westpac(self, csv_path: Union[str, Path]) -> pd.DataFrame:
        """
        Normalize Westpac CSV file.

        Westpac format:
        - Bank Account, Date, Narrative, Debit Amount, Credit Amount, Balance, Categories, Serial
        - Debit Amount: money going out (expenses)
        - Credit Amount: money coming in (income)

        Args:
            csv_path: Path to the Westpac CSV file

        Returns:
            DataFrame with normalized columns: date, amount, description, account_name, original_balance
        """
        df = pd.read_csv(csv_path)

        # Parse date
        df['date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')

        # Convert amount: Debit becomes negative, Credit becomes positive
        df['Debit Amount'] = pd.to_numeric(df['Debit Amount'], errors='coerce').fillna(0)
        df['Credit Amount'] = pd.to_numeric(df['Credit Amount'], errors='coerce').fillna(0)
        df['amount'] = df['Credit Amount'] - df['Debit Amount']

        # Map other fields
        df['description'] = df['Narrative']
        df['account_name'] = 'Westpac-' + df['Bank Account'].astype(str)
        df['original_balance'] = pd.to_numeric(df['Balance'], errors='coerce')

        # Select and return only normalized columns
        return df[self.NORMALIZED_COLUMNS].copy()

    def normalize_amex(self, csv_path: Union[str, Path]) -> pd.DataFrame:
        """
        Normalize Amex CSV file.

        Amex format:
        - Date, Date Processed, Description, Card Member, Account #, Amount, ...
        - Positive amounts: charges (money going out)
        - Negative amounts: payments/credits (money coming in)

        Args:
            csv_path: Path to the Amex CSV file

        Returns:
            DataFrame with normalized columns: date, amount, description, account_name, original_balance
        """
        # Read CSV, handling potential multiline fields in quoted columns
        df = pd.read_csv(csv_path, quotechar='"', skipinitialspace=True)

        # Parse date
        df['date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')

        # Convert amount: flip the sign (positive charges become negative, negative payments become positive)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['amount'] = -df['Amount']

        # Map other fields
        df['description'] = df['Description']
        df['account_name'] = 'Amex' + df['Account #'].astype(str)

        # Amex doesn't provide balance in the export, so set to NaN
        df['original_balance'] = float('nan')

        # Select and return only normalized columns
        return df[self.NORMALIZED_COLUMNS].copy()

    def normalize(
        self,
        csv_path: Union[str, Path],
        bank: Literal['westpac', 'amex']
    ) -> pd.DataFrame:
        """
        Normalize a bank CSV file based on the bank type.

        Args:
            csv_path: Path to the CSV file
            bank: Bank name ('westpac' or 'amex')

        Returns:
            DataFrame with normalized columns: date, amount, description, account_name, original_balance

        Raises:
            ValueError: If bank type is not supported
        """
        bank = bank.lower()

        if bank == 'westpac':
            return self.normalize_westpac(csv_path)
        elif bank == 'amex':
            return self.normalize_amex(csv_path)
        else:
            raise ValueError(f"Unsupported bank type: {bank}. Supported types: 'westpac', 'amex'")

    def normalize_multiple(
        self,
        file_bank_pairs: list
    ) -> pd.DataFrame:
        """
        Normalize multiple CSV files and combine them into a single DataFrame.

        Args:
            file_bank_pairs: List of tuples containing (csv_path, bank_type)

        Returns:
            Combined DataFrame with all normalized transactions, sorted by date

        Example:
            >>> normalizer = TransactionNormalizer()
            >>> files = [
            ...     ('westpac.csv', 'westpac'),
            ...     ('amex.csv', 'amex')
            ... ]
            >>> df = normalizer.normalize_multiple(files)
        """
        dfs = []

        for csv_path, bank in file_bank_pairs:
            df = self.normalize(csv_path, bank)
            dfs.append(df)

        # Combine all dataframes
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)

            # Sort by date
            combined_df = combined_df.sort_values('date').reset_index(drop=True)

            return combined_df
        else:
            # Return empty DataFrame with correct columns if no data
            return pd.DataFrame(columns=self.NORMALIZED_COLUMNS)


def main():
    """Example usage of the TransactionNormalizer."""
    normalizer = TransactionNormalizer()

    # Example: normalize individual files
    westpac_df = normalizer.normalize('westpac.csv', 'westpac')
    amex_df = normalizer.normalize('amex.csv', 'amex')

    # Example: normalize multiple files at once
    files = [
        ('westpac.csv', 'westpac'),
        ('amex.csv', 'amex')
    ]
    combined_df = normalizer.normalize_multiple(files)

    # Save to CSV
    combined_df.to_csv('normalized_transactions.csv', index=False)

    print(f"Normalized {len(combined_df)} transactions")
    print(combined_df.head())


if __name__ == '__main__':
    main()
