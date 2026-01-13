"""SPX to ES conversion module with spread calculation."""
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import json
from pathlib import Path
from config import config


class SPXtoESConverter:
    """Convert SPX gamma levels to ES future levels using spread."""
    
    def __init__(self):
        """Initialize converter."""
        self.spread = None
        self.spread_timestamp = None
        self.spread_cache_file = config.data_dir / "daily_spread.json"
        
    def calculate_spread(self, spx_price: float, es_price: float) -> float:
        """Calculate and cache ES-SPX spread.
        
        This should be called once per day at market open (15:30 CET).
        The spread remains fixed for the trading day.
        
        Args:
            spx_price: Current SPX price
            es_price: Current ES price
            
        Returns:
            Spread value (ES - SPX)
        """
        self.spread = es_price - spx_price
        self.spread_timestamp = datetime.now()
        
        # Cache spread to file
        spread_data = {
            'spread': self.spread,
            'timestamp': self.spread_timestamp.isoformat(),
            'spx_price': spx_price,
            'es_price': es_price,
            'date': datetime.now().date().isoformat()
        }
        
        with open(self.spread_cache_file, 'w') as f:
            json.dump(spread_data, f, indent=2)
        
        logger.info(f"Spread calculated and cached: {self.spread:.2f} (ES: {es_price:.2f}, SPX: {spx_price:.2f})")
        
        return self.spread
    
    def load_cached_spread(self) -> Optional[float]:
        """Load today's spread from cache if available.
        
        Returns:
            Cached spread or None if not available or outdated
        """
        if not self.spread_cache_file.exists():
            logger.debug("No cached spread file found")
            return None
        
        try:
            with open(self.spread_cache_file, 'r') as f:
                spread_data = json.load(f)
            
            # Check if spread is from today
            cached_date = spread_data.get('date')
            today = datetime.now().date().isoformat()
            
            if cached_date == today:
                self.spread = spread_data['spread']
                self.spread_timestamp = datetime.fromisoformat(spread_data['timestamp'])
                logger.info(f"Loaded cached spread: {self.spread:.2f} (from {self.spread_timestamp})")
                return self.spread
            else:
                logger.debug(f"Cached spread is outdated (from {cached_date}, today is {today})")
                return None
                
        except Exception as e:
            logger.error(f"Error loading cached spread: {e}")
            return None
    
    def get_spread(self) -> Optional[float]:
        """Get current spread (from cache or memory).
        
        Returns:
            Current spread or None if not calculated yet
        """
        if self.spread is not None:
            return self.spread
        
        return self.load_cached_spread()
    
    def convert_spx_level_to_es(self, spx_level: float) -> Optional[float]:
        """Convert a SPX level to ES level using spread.
        
        Formula: ES_level = SPX_level + spread
        
        Args:
            spx_level: SPX price level
            
        Returns:
            Corresponding ES level or None if spread not available
        """
        spread = self.get_spread()
        
        if spread is None:
            logger.warning("Cannot convert to ES - spread not available")
            return None
        
        es_level = spx_level + spread
        
        return es_level
    
    def convert_levels_dict(self, spx_levels: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Convert all SPX levels to ES levels.
        
        Args:
            spx_levels: Dictionary of SPX levels (e.g., {'put_wall': 5800, 'call_wall': 5900})
            
        Returns:
            Dictionary with both SPX and ES levels for each key
        """
        converted = {}
        
        spread = self.get_spread()
        if spread is None:
            logger.warning("Cannot convert levels - spread not available")
            return converted
        
        for level_name, spx_value in spx_levels.items():
            if isinstance(spx_value, (int, float)):
                es_value = self.convert_spx_level_to_es(spx_value)
                
                converted[level_name] = {
                    'spx': spx_value,
                    'es': es_value,
                    'spread': spread
                }
                
                logger.debug(f"{level_name}: SPX ${spx_value:.2f} → ES ${es_value:.2f}")
        
        logger.info(f"Converted {len(converted)} levels from SPX to ES")
        
        return converted
    
    def get_conversion_summary(self) -> Dict:
        """Get summary of current conversion state.
        
        Returns:
            Dictionary with conversion metadata
        """
        return {
            'spread': self.spread,
            'spread_timestamp': self.spread_timestamp.isoformat() if self.spread_timestamp else None,
            'spread_available': self.spread is not None,
            'cached_spread_file': str(self.spread_cache_file),
            'cache_exists': self.spread_cache_file.exists()
        }
