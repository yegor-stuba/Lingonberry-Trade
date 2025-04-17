"""
Signal generator module
Combines multiple strategies to generate trading signals
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import asyncio

from trading_bot.strategy.strategy_base import Strategy
from trading_bot.strategy.smc_strategy import SMCStrategy
from trading_bot.strategy.ict_strategy import ICTStrategy
from trading_bot.strategy.combined_strategy import CombinedStrategy
from trading_bot.analysis.technical import TechnicalAnalyzer
from trading_bot.analysis.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Signal generator that combines multiple strategies
    to generate trading signals
    """
    
    def __init__(self):
        """Initialize the signal generator"""
        self.strategies = {}
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Add default strategies
        self.add_strategy("smc", SMCStrategy())
        self.add_strategy("ict", ICTStrategy())
        self.add_strategy("combined", CombinedStrategy())
        
        logger.info(f"Initialized signal generator with {len(self.strategies)} strategies")
    
    def add_strategy(self, name: str, strategy: Strategy):
        """
        Add a strategy to the signal generator
        
        Args:
            name (str): Strategy name
            strategy (Strategy): Strategy instance
        """
        self.strategies[name] = strategy
        logger.info(f"Added {name} strategy to signal generator")
    
    def remove_strategy(self, name: str):
        """
        Remove a strategy from the signal generator
        
        Args:
            name (str): Strategy name
        """
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"Removed {name} strategy from signal generator")
    
    async def generate_signals_with_sentiment(self, symbol: str, df: pd.DataFrame, timeframe: str, 
                                             market_type: str = 'forex') -> List[Dict]:
        """
        Generate trading signals with sentiment analysis
        
        Args:
            symbol (str): Trading symbol
            df (pd.DataFrame): OHLCV data
            timeframe (str): Timeframe
            market_type (str): Market type
            
        Returns:
            list: Trading signals
        """
        logger.info(f"Generating signals with sentiment for {symbol} on {timeframe}")
        
        # Get sentiment data
        sentiment_data = await self.sentiment_analyzer.get_combined_sentiment(symbol, market_type)
        logger.info(f"Sentiment for {symbol}: {sentiment_data.get('sentiment', 'neutral')} ({sentiment_data.get('sentiment_score', 0):.2f})")
        
        # Generate regular signals
        signals = self.generate_signals(symbol, df, timeframe)
        
        # Adjust signals based on sentiment
        adjusted_signals = self._adjust_signals_with_sentiment(signals, sentiment_data)
        
        return adjusted_signals
    
    def generate_signals(self, symbol: str, df: pd.DataFrame, timeframe: str) -> List[Dict]:
        """
        Generate trading signals for a symbol
        
        Args:
            symbol (str): Trading symbol
            df (pd.DataFrame): OHLCV data
            timeframe (str): Timeframe
            
        Returns:
            list: Trading signals
        """
        logger.info(f"Generating signals for {symbol} on {timeframe} timeframe")
        
        # Validate inputs
        if not isinstance(df, pd.DataFrame):
            logger.error(f"Invalid data format: {type(df)}")
            return []
        
        if df.empty:
            logger.warning(f"Empty DataFrame provided for {symbol} {timeframe}")
            return []
        
        # Collect signals from all strategies
        all_signals = []
        
        for strategy_name, strategy in self.strategies.items():
            try:
                analysis = strategy.analyze(df, symbol, timeframe)
                signals = analysis.get('signals', [])
                
                if signals:
                    logger.info(f"Strategy {strategy_name} generated {len(signals)} signals")
                    
                    # Add strategy name to signals
                    for signal in signals:
                        signal['strategy'] = strategy_name
                    
                    all_signals.extend(signals)
                else:
                    logger.info(f"Strategy {strategy_name} generated no signals")
                    
            except Exception as e:
                logger.error(f"Error in strategy {strategy_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Sort signals by strength
        all_signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return all_signals
    
    def _adjust_signals_with_sentiment(self, signals: List[Dict], sentiment_data: Dict) -> List[Dict]:
        """
        Adjust signals based on sentiment data
        
        Args:
            signals (list): List of signals
            sentiment_data (dict): Sentiment analysis data
            
        Returns:
            list: Adjusted signals
        """
        if not sentiment_data:
            return signals
        
        sentiment = sentiment_data.get('sentiment', 'neutral')
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        confidence = sentiment_data.get('confidence', 0)
        
        adjusted_signals = []
        
        for signal in signals:
            # Make a copy of the signal to avoid modifying the original
            adjusted_signal = signal.copy()
            
            # Boost bullish signals if sentiment is bullish
            if adjusted_signal.get('type') == 'bullish' and sentiment == 'bullish':
                adjusted_signal['strength'] = min(100, adjusted_signal.get('strength', 0) + int(confidence * 10))
                adjusted_signal['description'] = f"{adjusted_signal.get('description', '')} (Boosted by bullish sentiment: {sentiment_score:.2f})"
            
            # Boost bearish signals if sentiment is bearish
            elif adjusted_signal.get('type') == 'bearish' and sentiment == 'bearish':
                adjusted_signal['strength'] = min(100, adjusted_signal.get('strength', 0) + int(confidence * 10))
                adjusted_signal['description'] = f"{adjusted_signal.get('description', '')} (Boosted by bearish sentiment: {sentiment_score:.2f})"
            
            # Reduce signal strength if it contradicts sentiment
            elif (adjusted_signal.get('type') == 'bullish' and sentiment == 'bearish') or \
                 (adjusted_signal.get('type') == 'bearish' and sentiment == 'bullish'):
                adjusted_signal['strength'] = max(0, adjusted_signal.get('strength', 0) - int(confidence * 10))
                adjusted_signal['description'] = f"{adjusted_signal.get('description', '')} (Reduced due to contrary sentiment: {sentiment_score:.2f})"
            
            adjusted_signals.append(adjusted_signal)
        
        # Sort adjusted signals by strength
        adjusted_signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return adjusted_signals
    
    def get_trade_setup(self, signal: Dict) -> Dict:
        """
        Get trade setup details from a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup details
        """
        strategy_name = signal.get('strategy')
        
        if strategy_name and strategy_name in self.strategies:
            # Use the specified strategy
            strategy = self.strategies[strategy_name]
            return strategy.get_trade_setup(signal)
        
        # Default implementation if strategy not found
        symbol = signal.get('symbol', '')
        signal_type = signal.get('type', '')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        risk_reward = signal.get('risk_reward', 0)
        reason = signal.get('reason', '')
        
        # Calculate risk percentage
        risk_pct = abs(entry - stop_loss) / entry * 100 if entry > 0 else 0
        
        # Calculate potential reward percentage
        reward_pct = abs(entry - take_profit) / entry * 100 if entry > 0 else 0
        
        # Determine direction
        direction = 'LONG' if signal_type == 'buy' else 'SHORT'
        
        # Create trade setup
        trade_setup = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'risk_pct': risk_pct,
            'reward_pct': reward_pct,
            'reason': reason,
            'strategy': strategy_name or 'Unknown',
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return trade_setup
    
    def filter_signals(self, signals: List[Dict], min_risk_reward: float = 3.0, 
                      min_strength: int = 70) -> List[Dict]:
        """
        Filter signals based on criteria
        
        Args:
            signals (list): List of signals
            min_risk_reward (float): Minimum risk-reward ratio
            min_strength (int): Minimum signal strength
            
        Returns:
            list: Filtered signals
        """
        filtered = []
        
        for signal in signals:
            risk_reward = signal.get('risk_reward', 0)
            strength = signal.get('strength', 0)
            
            if risk_reward >= min_risk_reward and strength >= min_strength:
                filtered.append(signal)
        
        return filtered
    
    def get_best_signal(self, signals: List[Dict]) -> Optional[Dict]:
        """
        Get the best signal from a list of signals
        
        Args:
            signals (list): List of signals
            
        Returns:
            dict or None: Best signal or None if no signals
        """
        if not signals:
            return None
        
        # Sort by strength and risk-reward ratio
        sorted_signals = sorted(signals, key=lambda x: (x.get('strength', 0), x.get('risk_reward', 0)), reverse=True)
        
        return sorted_signals[0]
    
    def get_conflicting_signals(self, signals: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group signals by direction to identify conflicts
        
        Args:
            signals (list): List of signals
            
        Returns:
            dict: Signals grouped by direction
        """
        grouped = {'buy': [], 'sell': []}
        
        for signal in signals:
            signal_type = signal.get('type', '')
            if signal_type in ['buy', 'sell']:
                grouped[signal_type].append(signal)
        
        return grouped
    
    def resolve_conflicts(self, signals: List[Dict]) -> List[Dict]:
        """
        Resolve conflicting signals
        
        Args:
            signals (list): List of signals
            
        Returns:
            list: Resolved signals
        """
        # Group signals by direction
        grouped = self.get_conflicting_signals(signals)
        
        # If we have both buy and sell signals, keep only the stronger ones
        if grouped['buy'] and grouped['sell']:
            # Calculate average strength for each direction
            buy_strength = sum(s.get('strength', 0) for s in grouped['buy']) / len(grouped['buy'])
            sell_strength = sum(s.get('strength', 0) for s in grouped['sell']) / len(grouped['sell'])
            
            # Keep only the stronger direction
            if buy_strength > sell_strength:
                logger.info(f"Resolving conflict: Buy signals stronger ({buy_strength:.1f} vs {sell_strength:.1f})")
                return grouped['buy']
            else:
                logger.info(f"Resolving conflict: Sell signals stronger ({sell_strength:.1f} vs {buy_strength:.1f})")
                return grouped['sell']
        
        # If no conflicts, return all signals
        return signals
    
    async def analyze_multi_timeframe(self, symbol: str, dfs: Dict[str, pd.DataFrame], 
                                     market_type: str = 'forex') -> Dict:
        """
        Perform multi-timeframe analysis to identify HTF POIs and LTF entries
        
        Args:
            symbol (str): Trading symbol
            dfs (dict): Dictionary of dataframes for different timeframes
            market_type (str): Market type
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        logger.info(f"Performing multi-timeframe analysis for {symbol}")
        
        # Use the combined strategy for MTF analysis
        if 'combined' in self.strategies:
            combined_strategy = self.strategies['combined']
            mtf_analysis = combined_strategy.get_multi_timeframe_analysis(dfs, symbol, market_type)
            
            # Add sentiment analysis
            sentiment_data = await self.sentiment_analyzer.get_combined_sentiment(symbol, market_type)
            mtf_analysis['sentiment'] = sentiment_data
            
            return mtf_analysis
        else:
            logger.warning("Combined strategy not available for MTF analysis")
            return {
                'symbol': symbol,
                'error': 'Combined strategy not available',
                'timeframes': {}
            }
