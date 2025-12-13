"""
Data loader module for Indian Bank Branch Analytics Dashboard.
Handles loading and cleaning sample data from various banks.
"""

import pandas as pd
import os
from pathlib import Path
import re

class BankDataLoader:
    """Load and preprocess bank branch data for analytics."""

    def __init__(self, data_dir="data/sample"):
        self.data_dir = Path(data_dir)
        self.combined_file = self.data_dir / "combined_banks_sample.csv"

    def load_combined_data(self):
        """Load the combined dataset with all banks."""
        if not self.combined_file.exists():
            raise FileNotFoundError(f"Combined data file not found: {self.combined_file}")

        # Load with standard comma delimiter
        df = pd.read_csv(self.combined_file, on_bad_lines='skip')

        return self._clean_dataframe(df)

    def load_individual_bank(self, bank_name):
        """Load data for a specific bank."""
        filename = f"{bank_name.lower().replace(' ', '_')}_sample.csv"
        filepath = self.data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        # Load with standard comma delimiter
        df = pd.read_csv(filepath, on_bad_lines='skip')

        return self._clean_dataframe(df)

    def _clean_dataframe(self, df):
        """Clean and standardize dataframe columns."""
        # Standardize column names (convert to title case)
        df.columns = df.columns.str.strip().str.replace('_', ' ').str.title()

        # Common column mapping
        column_mapping = {
            'Bank Name': 'Bank',
            'Branch Name': 'Branch',
            'Location Type': 'Type'
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)

        # Clean latitude and longitude
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
            df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

            # Filter invalid coordinates (India bounds: lat 6-37, lng 68-97)
            df = df[
                (df['Latitude'].notna()) &
                (df['Longitude'].notna()) &
                (df['Latitude'] >= 6) &
                (df['Latitude'] <= 37) &
                (df['Longitude'] >= 68) &
                (df['Longitude'] <= 97)
            ]

        # Extract pincode from address if not present
        if 'Pincode' not in df.columns and 'Address' in df.columns:
            df['Pincode'] = df['Address'].apply(self._extract_pincode)

        # Clean state and city names
        for col in ['State', 'City']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()
                # Replace 'Nan' string with actual NaN
                df.loc[df[col] == 'Nan', col] = None

        return df

    @staticmethod
    def _extract_pincode(address):
        """Extract 6-digit pincode from address string."""
        if pd.isna(address):
            return None

        # Match 6-digit pincodes
        match = re.search(r'\b\d{6}\b', str(address))
        return match.group(0) if match else None

    def get_available_banks(self):
        """Get list of all available banks in the dataset."""
        df = self.load_combined_data()
        if 'Bank' in df.columns:
            return sorted(df['Bank'].unique().tolist())
        return []

    def get_statistics(self):
        """Get basic statistics about the dataset."""
        df = self.load_combined_data()

        stats = {
            'total_branches': len(df),
            'total_banks': df['Bank'].nunique() if 'Bank' in df.columns else 0,
            'total_states': df['State'].nunique() if 'State' in df.columns else 0,
            'total_cities': df['City'].nunique() if 'City' in df.columns else 0,
            'with_coordinates': df[['Latitude', 'Longitude']].notna().all(axis=1).sum() if 'Latitude' in df.columns else 0,
        }

        return stats

    def get_state_distribution(self):
        """Get branch count by state."""
        df = self.load_combined_data()

        if 'State' not in df.columns:
            return pd.DataFrame()

        state_counts = df['State'].value_counts().reset_index()
        state_counts.columns = ['State', 'Branch Count']
        return state_counts

    def get_bank_distribution(self):
        """Get branch count by bank."""
        df = self.load_combined_data()

        if 'Bank' not in df.columns:
            return pd.DataFrame()

        bank_counts = df['Bank'].value_counts().reset_index()
        bank_counts.columns = ['Bank', 'Branch Count']
        return bank_counts

    def filter_data(self, df=None, state=None, city=None, bank=None):
        """Filter dataframe by state, city, and/or bank."""
        if df is None:
            df = self.load_combined_data()

        filtered_df = df.copy()

        if state and 'State' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['State'] == state]

        if city and 'City' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['City'] == city]

        if bank and 'Bank' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Bank'] == bank]

        return filtered_df


if __name__ == "__main__":
    # Test the data loader
    loader = BankDataLoader()

    print("Loading combined data...")
    df = loader.load_combined_data()
    print(f"✓ Loaded {len(df)} records")
    print(f"  Columns: {list(df.columns)}")

    print("\nDataset Statistics:")
    stats = loader.get_statistics()
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    print("\nAvailable Banks:")
    banks = loader.get_available_banks()
    for bank in banks[:5]:
        print(f"  - {bank}")
    print(f"  ... and {len(banks) - 5} more")

    print("\nTop 5 States by Branch Count:")
    state_dist = loader.get_state_distribution().head()
    print(state_dist.to_string(index=False))
