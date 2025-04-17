"""
Base strategy class for the trading bot
Defines the interface for all trading strategies
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

class Strategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str):
        """
        Initialize the strategy
        
        Args:
            name (str): Strategy name
        """
        self.name = name
        logger.info(f"Initialized {name} strategy")
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Analyze market data and generate trading signals
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Analysis results
        """
        pass
    
    @abstractmethod
    def generate_signals(self, analysis: Dict) -> List[Dict]:
        """
        Generate trading signals from analysis
        
        Args:
            analysis (dict): Analysis results
            
        Returns:
            list: Trading signals
        """
        pass
    
    @abstractmethod
    def get_trade_setup(self, signal: Dict) -> Dict:
        """
        Get trade setup details from a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup details
        """
        pass
    
    def multi_timeframe_analysis(self, dfs: Dict[str, pd.DataFrame], symbol: str) -> Dict:
        """
        Perform multi-timeframe analysis
        
        Args:
            dfs (dict): Dictionary of dataframes for different timeframes
            symbol (str): Trading symbol
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        mtf_results = {}
        
        for timeframe, df in dfs.items():
            mtf_results[timeframe] = self.analyze(df, symbol, timeframe)
        
        return self._combine_mtf_results(mtf_results, symbol)
    
    def _combine_mtf_results(self, mtf_results: Dict[str, Dict], symbol: str) -> Dict:
        """
        Combine multi-timeframe analysis results
        
        Args:
            mtf_results (dict): Results from each timeframe
            symbol (str): Trading symbol
            
        Returns:
            dict: Combined results
        """
        # Default implementation - can be overridden by subclasses
        combined = {
            'symbol': symbol,
            'timeframes': mtf_results,
            'signals': []
        }
        
        # Collect signals from all timeframes
        for timeframe, results in mtf_results.items():
            signals = results.get('signals', [])
            for signal in signals:
                signal['timeframe'] = timeframe
                combined['signals'].append(signal)
        
        # Sort signals by strength (descending)
        combined['signals'].sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return combined