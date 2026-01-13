"""Gamma calculation engine - SpotGamma-like analysis."""
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from loguru import logger
from config import config


class GammaEngine:
    """Calculate gamma exposure levels and identify key support/resistance."""
    
    def __init__(self):
        """Initialize the gamma calculation engine."""
        self.levels = {}
        self.regime = "neutral"
        
    def calculate_dealer_gamma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate dealer gamma exposure per strike.
        
        Dealer gamma exposure = OI × Gamma × 100 × (±1 for call/put perspective)
        
        Dealers are:
        - Long gamma when they sell options (negative gamma exposure)
        - Short gamma when they buy options (positive gamma exposure)
        
        We assume dealers are net short options (selling to retail).
        
        Args:
            df: Options DataFrame with OI, gamma, type
            
        Returns:
            DataFrame with dealer gamma calculations
        """
        if df.empty or 'gamma' not in df.columns:
            logger.warning("Cannot calculate dealer gamma - missing data")
            return df
        
        df = df.copy()
        
        # Fill NaN gammas with 0
        df['gamma'] = df['gamma'].fillna(0)
        
        # Dealer gamma exposure calculation
        # Dealers sell options (net short), so they have opposite position
        # Calls: Dealers are short, so negative gamma exposure (multiplied by -1)
        # Puts: Dealers are short, so negative gamma exposure (multiplied by -1)
        df['dealer_gamma'] = df.apply(
            lambda row: -row['open_interest'] * row['gamma'] * 100,
            axis=1
        )
        
        # Separate call and put gamma
        df['call_gamma'] = df.apply(
            lambda row: row['dealer_gamma'] if row['type'] == 'call' else 0,
            axis=1
        )
        
        df['put_gamma'] = df.apply(
            lambda row: row['dealer_gamma'] if row['type'] == 'put' else 0,
            axis=1
        )
        
        logger.info("Dealer gamma exposure calculated")
        return df
    
    def aggregate_by_strike(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate gamma exposure by strike.
        
        Args:
            df: Options DataFrame with dealer gamma
            
        Returns:
            Aggregated DataFrame by strike
        """
        if df.empty:
            return df
        
        # Group by strike and sum gamma exposures
        agg_df = df.groupby('strike').agg({
            'dealer_gamma': 'sum',
            'call_gamma': 'sum',
            'put_gamma': 'sum',
            'volume': 'sum',
            'open_interest': 'sum'
        }).reset_index()
        
        # Calculate net gamma
        agg_df['net_gamma'] = agg_df['call_gamma'] + agg_df['put_gamma']
        
        # Sort by strike
        agg_df = agg_df.sort_values('strike').reset_index(drop=True)
        
        logger.info(f"Aggregated to {len(agg_df)} unique strikes")
        return agg_df
    
    def identify_key_levels(self, df: pd.DataFrame, current_price: float) -> Dict[str, float]:
        """Identify key gamma levels: Put Wall, Call Wall, Gamma Flip.
        
        Args:
            df: Aggregated DataFrame by strike with gamma exposures
            current_price: Current SPX price
            
        Returns:
            Dictionary with key levels
        """
        if df.empty:
            logger.warning("Cannot identify levels - empty DataFrame")
            return {}
        
        levels = {}
        
        # Put Wall: Strike with maximum absolute put gamma below current price
        put_strikes = df[df['strike'] < current_price].copy()
        if put_strikes.empty:
            put_strikes = df[df['strike'] <= current_price].copy()
        if not put_strikes.empty:
            put_wall_idx = put_strikes['put_gamma'].abs().idxmax()
            levels['put_wall'] = float(put_strikes.loc[put_wall_idx, 'strike'])
            levels['put_wall_gamma'] = float(put_strikes.loc[put_wall_idx, 'put_gamma'])
            logger.info(f"Put Wall identified at ${levels['put_wall']:.2f} (Gamma: {levels['put_wall_gamma']:.2e})")
        
        # Call Wall: Strike with maximum absolute call gamma above current price
        call_strikes = df[df['strike'] > current_price].copy()
        if call_strikes.empty:
            call_strikes = df[df['strike'] >= current_price].copy()
        if not call_strikes.empty:
            call_wall_idx = call_strikes['call_gamma'].abs().idxmax()
            levels['call_wall'] = float(call_strikes.loc[call_wall_idx, 'strike'])
            levels['call_wall_gamma'] = float(call_strikes.loc[call_wall_idx, 'call_gamma'])
            logger.info(f"Call Wall identified at ${levels['call_wall']:.2f} (Gamma: {levels['call_wall_gamma']:.2e})")
        
        # Gamma Flip: Where net gamma changes sign (from negative to positive or vice versa)
        # This indicates transition from dealer long to short gamma (or vice versa)
        df_sorted = df.sort_values('strike').copy()
        df_sorted['gamma_sign_change'] = df_sorted['net_gamma'].diff().abs()
        
        # Find zero crossing or largest sign change near current price
        near_price = df_sorted[
            (df_sorted['strike'] >= current_price * 0.99) & 
            (df_sorted['strike'] <= current_price * 1.01)
        ]
        
        if not near_price.empty:
            # Find where net gamma crosses zero or is closest to zero
            gamma_flip_idx = near_price['net_gamma'].abs().idxmin()
            levels['gamma_flip'] = float(near_price.loc[gamma_flip_idx, 'strike'])
            levels['gamma_flip_value'] = float(near_price.loc[gamma_flip_idx, 'net_gamma'])
            logger.info(f"Gamma Flip identified at ${levels['gamma_flip']:.2f} (Net Gamma: {levels['gamma_flip_value']:.2e})")
        
        # Store levels
        self.levels = levels
        
        return levels
    
    def rank_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rank strikes by importance (gamma × volume).
        
        Args:
            df: Aggregated DataFrame by strike
            
        Returns:
            Top N levels ranked by score
        """
        if df.empty:
            return df
        
        # Calculate importance score
        df = df.copy()
        df['score'] = df['net_gamma'].abs() * df['volume']
        
        # Sort by score and take top N
        top_levels = df.nlargest(config.top_levels_count, 'score')
        
        logger.info(f"Top {len(top_levels)} levels by importance:")
        for _, row in top_levels.iterrows():
            logger.info(f"  ${row['strike']:.2f} - Score: {row['score']:.2e}, Net Gamma: {row['net_gamma']:.2e}")
        
        return top_levels
    
    def determine_regime(self, df: pd.DataFrame, current_price: float) -> str:
        """Determine market regime based on gamma exposure.
        
        Args:
            df: Aggregated DataFrame with net gamma
            current_price: Current SPX price
            
        Returns:
            Regime string: "long_gamma", "short_gamma", or "neutral"
        """
        if df.empty or 'gamma_flip' not in self.levels:
            return "neutral"
        
        gamma_flip = self.levels['gamma_flip']
        
        # If price is above gamma flip, dealers are long gamma (market is short gamma)
        # This typically means lower volatility, mean reversion
        if current_price > gamma_flip:
            regime = "short_gamma"  # Market perspective
            logger.info(f"Market regime: SHORT GAMMA (price ${current_price:.2f} > flip ${gamma_flip:.2f}) - Expect higher volatility")
        else:
            regime = "long_gamma"  # Market perspective
            logger.info(f"Market regime: LONG GAMMA (price ${current_price:.2f} < flip ${gamma_flip:.2f}) - Expect mean reversion")
        
        self.regime = regime
        return regime
    
    def process_options_data(self, df: pd.DataFrame, current_price: float) -> Tuple[pd.DataFrame, Dict[str, float], str]:
        """Complete gamma analysis pipeline.
        
        Args:
            df: Raw options DataFrame
            current_price: Current SPX price
            
        Returns:
            Tuple of (aggregated_df, key_levels, regime)
        """
        logger.info("Starting gamma analysis pipeline")
        
        # Step 1: Calculate dealer gamma
        df_gamma = self.calculate_dealer_gamma(df)
        
        # Step 2: Aggregate by strike
        df_agg = self.aggregate_by_strike(df_gamma)
        
        # Step 3: Identify key levels
        levels = self.identify_key_levels(df_agg, current_price)
        
        # Step 4: Rank levels
        top_levels = self.rank_levels(df_agg)
        
        # Step 5: Determine regime
        regime = self.determine_regime(df_agg, current_price)
        
        logger.info("Gamma analysis pipeline completed")
        
        return df_agg, levels, regime
