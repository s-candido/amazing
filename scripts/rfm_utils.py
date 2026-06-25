"""
RFM Scoring Module - Reusable utility functions for RFM calculations

This module provides core RFM calculation functions that can be imported and used
in other scripts, notebooks, or applications.

Example Usage:
    from rfm_utils import RFMCalculator, RFM_CONFIG
    
    # Using default config
    calculator = RFMCalculator()
    
    # Process a dataframe
    df_with_rfm = calculator.calculate_rfm(df)
    
    # Or use custom config
    custom_config = {...}
    calculator = RFMCalculator(custom_config)
"""

import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# Default RFM Configuration
RFM_CONFIG = {
    'r_column': 'days_since_last_event',
    'r_thresholds': [30, 150],      # days
    'r_scores': [2, 1, 0],          # [recent, medium, old]
    'f_column': 'total_purchases',  # or 'frequency' or 'number_of_purchases'
    'f_thresholds': [2, 10],        # count
    'f_scores': [0, 1, 2],          # [low, medium, high]
    'm_column': 'total_spent',      # monetary
    'm_thresholds': [20, 50],       # amount
    'm_scores': [0, 1, 2],          # [low, medium, high]
    'segment_thresholds': [0, 2, 3, 4, 6],
    'days_to_months': 30
}


class RFMCalculator:
    """
    Calculator for Recency, Frequency, and Monetary (RFM) analysis.
    
    This class handles all RFM score calculations and segment assignments.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the RFM calculator with configuration.
        
        Args:
            config: Optional RFM configuration dict. Uses RFM_CONFIG if not provided.
        """
        self.config = config or RFM_CONFIG.copy()
        logger.info("✓ RFM Calculator initialized")
        logger.info(f"  Recency thresholds: {self.config['r_thresholds']}")
        logger.info(f"  Frequency thresholds: {self.config['f_thresholds']}")
        logger.info(f"  Monetary thresholds: {self.config['m_thresholds']}")
    
    @staticmethod
    def calculate_r_score(days_since_event: float, thresholds: List[int], 
                         scores: List[int]) -> int:
        """
        Calculate Recency score.
        
        Lower days_since_last_event = higher recency score (more recent customer).
        
        Args:
            days_since_event: Number of days since last event
            thresholds: [30, 150] - breakpoints for scoring
            scores: [2, 1, 0] - scores for each boundary
        
        Returns:
            Recency score (0, 1, or 2)
        """
        if pd.isna(days_since_event):
            return 0
        
        days = float(days_since_event)
        if days <= thresholds[0]:
            return scores[0]  # 2 - most recent
        elif days <= thresholds[1]:
            return scores[1]  # 1 - somewhat recent
        else:
            return scores[2]  # 0 - not recent
    
    @staticmethod
    def calculate_f_score(frequency: float, thresholds: List[int], 
                         scores: List[int]) -> int:
        """
        Calculate Frequency score.
        
        Higher frequency = higher score (more purchases).
        
        Args:
            frequency: Number of purchases/transactions
            thresholds: [2, 10] - breakpoints for scoring
            scores: [0, 1, 2] - scores for each boundary
        
        Returns:
            Frequency score (0, 1, or 2)
        """
        if pd.isna(frequency):
            return 0
        
        freq = float(frequency)
        if freq < thresholds[0]:
            return scores[0]  # 0 - low frequency
        elif freq < thresholds[1]:
            return scores[1]  # 1 - medium frequency
        else:
            return scores[2]  # 2 - high frequency
    
    @staticmethod
    def calculate_m_score(monetary: float, thresholds: List[float], 
                         scores: List[int]) -> int:
        """
        Calculate Monetary score.
        
        Higher monetary value = higher score (higher spending).
        
        Args:
            monetary: Total amount spent
            thresholds: [20, 50] - breakpoints for scoring
            scores: [0, 1, 2] - scores for each boundary
        
        Returns:
            Monetary score (0, 1, or 2)
        """
        if pd.isna(monetary):
            return 0
        
        amount = float(monetary)
        if amount < thresholds[0]:
            return scores[0]  # 0 - low spending
        elif amount < thresholds[1]:
            return scores[1]  # 1 - medium spending
        else:
            return scores[2]  # 2 - high spending
    
    @staticmethod
    def calculate_segment(r_score: int, f_score: int, m_score: int, 
                         thresholds: List[int]) -> int:
        """
        Calculate segment based on RFM score sum.
        
        Args:
            r_score, f_score, m_score: Individual RFM scores (0-2)
            thresholds: [0, 2, 3, 4, 6] - segment boundaries
            
        Returns:
            Segment number (0-4 or custom based on thresholds)
        """
        total_score = r_score + f_score + m_score
        
        # Find which segment based on thresholds
        for i in range(len(thresholds) - 1):
            if thresholds[i] <= total_score < thresholds[i + 1]:
                return i
        
        # Default to last segment if score >= last threshold
        return len(thresholds) - 2
    
    def _find_column(self, df: pd.DataFrame, possible_names: List[str], 
                    default: str) -> str:
        """
        Find the actual column name in dataframe from a list of possible names.
        
        Args:
            df: DataFrame to search in
            possible_names: List of possible column names
            default: Default name if not found
            
        Returns:
            Actual column name in dataframe
        """
        available_cols = {col.lower(): col for col in df.columns}
        
        for name in possible_names:
            if name.lower() in available_cols:
                return available_cols[name.lower()]
        
        return default
    
    def calculate_rfm(self, df: pd.DataFrame, add_timestamp: bool = True) -> pd.DataFrame:
        """
        Calculate RFM scores and segments for a dataframe.
        
        Args:
            df: Input dataframe with required columns
            add_timestamp: Whether to add a 'processed_at' timestamp
            
        Returns:
            DataFrame with added/updated columns: recency, frequency, monetary, segment
        """
        df = df.copy()  # Don't modify original
        
        # Find actual column names
        r_col = self._find_column(
            df,
            [self.config['r_column'], 'days_since_last_event', 'recency_days'],
            self.config['r_column']
        )
        
        f_col = self._find_column(
            df,
            [self.config['f_column'], 'total_purchases', 'number_of_purchases', 
             'frequency', 'nb_purchases', 'purchase_count'],
            self.config['f_column']
        )
        
        m_col = self._find_column(
            df,
            [self.config['m_column'], 'total_spent', 'total_amount', 
             'revenue', 'monetary'],
            self.config['m_column']
        )
        
        logger.info(f"Calculating RFM for {len(df)} records...")
        logger.info(f"  Recency column: {r_col}")
        logger.info(f"  Frequency column: {f_col}")
        logger.info(f"  Monetary column: {m_col}")
        
        # Calculate RFM scores
        df['recency'] = df[r_col].apply(
            lambda x: self.calculate_r_score(x, self.config['r_thresholds'], 
                                           self.config['r_scores'])
        )
        
        df['frequency'] = df[f_col].apply(
            lambda x: self.calculate_f_score(x, self.config['f_thresholds'], 
                                            self.config['f_scores'])
        )
        
        df['monetary'] = df[m_col].apply(
            lambda x: self.calculate_m_score(x, self.config['m_thresholds'], 
                                            self.config['m_scores'])
        )
        
        # Calculate segment
        df['segment'] = df.apply(
            lambda row: self.calculate_segment(
                row['recency'], row['frequency'], row['monetary'],
                self.config['segment_thresholds']
            ),
            axis=1
        )
        
        if add_timestamp:
            df['processed_at'] = datetime.now()
        
        logger.info("✓ RFM calculations complete")
        logger.info(f"  Recency distribution: {df['recency'].value_counts().to_dict()}")
        logger.info(f"  Frequency distribution: {df['frequency'].value_counts().to_dict()}")
        logger.info(f"  Monetary distribution: {df['monetary'].value_counts().to_dict()}")
        logger.info(f"  Segment distribution: {df['segment'].value_counts().sort_index().to_dict()}")
        
        return df
    
    def get_segment_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get a summary of RFM segments.
        
        Args:
            df: DataFrame with 'recency', 'frequency', 'monetary', 'segment' columns
            
        Returns:
            Summary dataframe with segment statistics
        """
        if 'segment' not in df.columns:
            raise ValueError("DataFrame must contain 'segment' column. Run calculate_rfm() first.")
        
        summary = df.groupby('segment').agg({
            'user_id': 'count' if 'user_id' in df.columns else 'size',
            'recency': ['mean', 'median', 'min', 'max'],
            'frequency': ['mean', 'median', 'min', 'max'],
            'monetary': ['mean', 'median', 'min', 'max']
        }).round(2)
        
        return summary
    
    def get_segment_interpretation(self, segment: int) -> str:
        """
        Get human-readable interpretation of a segment.
        
        Args:
            segment: Segment number (0-4)
            
        Returns:
            Interpretation string
        """
        interpretations = {
            0: "Low-value (inactive, infrequent, low spender)",
            1: "Low-medium value",
            2: "Medium value (balanced profile)",
            3: "Medium-high value",
            4: "High-value (active, frequent, high spender)"
        }
        
        return interpretations.get(segment, f"Segment {segment}")


def create_rfm_report(df: pd.DataFrame, calculator: Optional[RFMCalculator] = None) -> str:
    """
    Create a text report of RFM analysis.
    
    Args:
        df: DataFrame with RFM columns calculated
        calculator: Optional RFMCalculator instance for interpretations
        
    Returns:
        Formatted report string
    """
    if calculator is None:
        calculator = RFMCalculator()
    
    report = []
    report.append("=" * 70)
    report.append("RFM Analysis Report")
    report.append("=" * 70)
    
    # Overall statistics
    report.append(f"\nTotal Records: {len(df):,}")
    report.append(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Segment breakdown
    report.append("\n--- Segment Distribution ---")
    segment_counts = df['segment'].value_counts().sort_index()
    for seg, count in segment_counts.items():
        pct = (count / len(df) * 100)
        interp = calculator.get_segment_interpretation(seg)
        report.append(f"  Segment {seg}: {count:>5} ({pct:>5.1f}%) - {interp}")
    
    # RFM Score statistics
    report.append("\n--- RFM Score Statistics ---")
    for score_type in ['recency', 'frequency', 'monetary']:
        if score_type in df.columns:
            report.append(f"\n{score_type.capitalize()}:")
            dist = df[score_type].value_counts().sort_index()
            for score, count in dist.items():
                pct = (count / len(df) * 100)
                report.append(f"    Score {score}: {count:>5} ({pct:>5.1f}%)")
    
    report.append("\n" + "=" * 70)
    
    return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    sample_data = {
        'user_id': range(1, 11),
        'days_since_last_event': [5, 15, 45, 100, 200, 2, 25, 60, 150, 300],
        'total_purchases': [0, 1, 2, 5, 15, 0, 3, 8, 12, 20],
        'total_spent': [0, 10, 25, 75, 150, 5, 45, 100, 200, 500]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Calculate RFM
    calculator = RFMCalculator()
    df_with_rfm = calculator.calculate_rfm(df)
    
    # Print results
    print("\nData with RFM scores:")
    print(df_with_rfm[['user_id', 'recency', 'frequency', 'monetary', 'segment']])
    
    # Generate report
    print(create_rfm_report(df_with_rfm, calculator))
