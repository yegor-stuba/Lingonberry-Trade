"""
Data loading utilities for backtesting
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Union
import os

from trading_bot.config import settings

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Class for loading historical data for backtesting
    """
    
    def __init__(self):
        """Initialize the data loader"""
        self.charts_dir = Path(settings.BASE_DIR).parent / "charts"
    
    def get_available_symbols(self, market_type: str) -> List[str]:
        """
        Get list of available symbols for a market type
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            list: List of available symbols
        """
        try:
            # Map market type to directory
            if market_type.lower() == 'forex':
                market_dir = self.charts_dir / "forex"
            elif market_type.lower() == 'crypto':
                market_dir = self.charts_dir / "crypto"
            elif market_type.lower() == 'indices':
                market_dir = self.charts_dir / "indeces"
            elif market_type.lower() == 'metals':
                market_dir = self.charts_dir / "metals"
            else:
                logger.error(f"Unsupported market type: {market_type}")
                return []
            
            # Get all CSV files
            csv_files = list(market_dir.glob("*.csv"))
            
            # Extract unique symbols
            symbols = set()
            for file in csv_files:
                # Extract symbol by removing timeframe suffix
                symbol = ''.join(c for c in file.stem if not c.isdigit())
                symbols.add(symbol)
            
            return sorted(list(symbols))
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []
    
    def get_available_timeframes(self, market_type: str, symbol: str) -> List[str]:
        """
        Get list of available timeframes for a symbol
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            
        Returns:
            list: List of available timeframes
        """
        try:
            # Map market type to directory
            if market_type.lower() == 'forex':
                market_dir = self.charts_dir / "forex"
            elif market_type.lower() == 'crypto':
                market_dir = self.charts_dir / "crypto"
            elif market_type.lower() == 'indices':
                market_dir = self.charts_dir / "indeces"
            elif market_type.lower() == 'metals':
                market_dir = self.charts_dir / "metals"
            else:
                logger.error(f"Unsupported market type: {market_type}")
                return []
            
            # Get all CSV files for this symbol
            csv_files = list(market_dir.glob(f"{symbol}*.csv"))
            
            # Map file suffixes to timeframes
            suffix_to_timeframe = {
                '1': '1m',
                '5': '5m',
                '15': '15m',
                '30': '30m',
                '60': '1h',
                '240': '4h',
                '1440': '1d',
                '10080': '1w'
            }
            
            # Extract timeframes
            timeframes = []
            for file in csv_files:
                # Extract suffix (digits at the end of the filename)
                suffix = ''.join(c for c in file.stem if c.isdigit())
                if suffix in suffix_to_timeframe:
                    timeframes.append(suffix_to_timeframe[suffix])
            
            return sorted(timeframes, key=lambda x: self._timeframe_to_minutes(x))
            
        except Exception as e:
            logger.error(f"Error getting available timeframes: {e}")
            return []
    
    def load_data(self, market_type: str, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Load historical data for a symbol and timeframe
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframe (str): Timeframe for analysis
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        try:
            # Map timeframe to CSV file suffix
            timeframe_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '1h': '60',
                '4h': '240',
                '1d': '1440',
                '1w': '10080'
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            csv_suffix = timeframe_map[timeframe]
            
            # Construct CSV file path
            if market_type.lower() == 'forex':
                csv_path = self.charts_dir / "forex" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'crypto':
                csv_path = self.charts_dir / "crypto" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'indices':
                csv_path = self.charts_dir / "indeces" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'metals':
                csv_path = self.charts_dir / "metals" / f"{symbol}{csv_suffix}.csv"
            else:
                logger.error(f"Unsupported market type: {market_type}")
                return None
            
            if not csv_path.exists():
                logger.error(f"CSV file not found: {csv_path}")
                return None
            
            # Read CSV file
            df = pd.read_csv(csv_path, sep='\t', header=None)
            
            # Rename columns
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # Convert datetime
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe string to minutes for sorting
        
        Args:
            timeframe (str): Timeframe string (e.g., '1m', '1h', '1d')
            
        Returns:
            int: Timeframe in minutes
        """
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 60 * 24
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 60 * 24 * 7
        else:
            return 0
