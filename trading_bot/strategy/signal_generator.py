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
        
        # Add default strategies
        from trading_bot.strategy.smc_strategy import SMCStrategy
        from trading_bot.strategy.ict_strategy import ICTStrategy
        
        self.add_strategy("smc", SMCStrategy())
        self.add_strategy("ict", ICTStrategy())
        
        # Try to add combined strategy if available
        try:
            from trading_bot.strategy.combined_strategy import CombinedStrategy
            self.add_strategy("combined", CombinedStrategy())
        except (ImportError, TypeError) as e:
            logger.warning(f"Could not load CombinedStrategy: {e}")
        
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
                # Generate signals using the strategy
                signals = strategy.generate_signals(symbol, df, timeframe)
                
                # Ensure each signal has the required fields
                for signal in signals:
                    # Add symbol if not present
                    if 'symbol' not in signal:
                        signal['symbol'] = symbol
                    
                    # Add strategy name if not present
                    if 'strategy' not in signal:
                        signal['strategy'] = strategy_name
                    
                    # Ensure risk-reward is calculated
                    if 'risk_reward' not in signal and 'entry_price' in signal and 'stop_loss' in signal and 'take_profit' in signal:
                        if signal.get('direction') == 'BUY':
                            risk = signal['entry_price'] - signal['stop_loss']
                            reward = signal['take_profit'] - signal['entry_price']
                        else:  # SELL
                            risk = signal['stop_loss'] - signal['entry_price']
                            reward = signal['entry_price'] - signal['take_profit']
                        
                        if risk > 0:
                            signal['risk_reward'] = reward / risk
                        else:
                            signal['risk_reward'] = 0
                    
                    # Ensure strength is present
                    if 'strength' not in signal:
                        signal['strength'] = 70  # Default strength
                
                # Add signals to the collection
                all_signals.extend(signals)
                
                logger.info(f"Strategy {strategy_name} generated {len(signals)} signals")
            except Exception as e:
                logger.error(f"Error generating signals with {strategy_name} strategy: {e}", exc_info=True)
        
        # Add timestamp to all signals
        for signal in all_signals:
            if 'timestamp' not in signal:
                signal['timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
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
        Get trade setup from a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup
        """
        if not signal:
            return {}
        
        # Extract basic signal info
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', '')
        
        # Get entry, stop loss, and take profit
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        
        # If entry price is not provided, use the current price
        if entry_price == 0 and 'price' in signal:
            entry_price = signal['price']
        
        # If stop loss or take profit are not provided, calculate them
        if stop_loss == 0 or take_profit == 0:
            # Get the current price if not already set
            current_price = entry_price if entry_price > 0 else signal.get('price', 0)
            
            # If we still don't have a price, we can't calculate
            if current_price == 0:
                return {}
            
            # Calculate ATR-based stop loss and take profit
            atr_value = signal.get('atr', 0)
            if atr_value == 0:
                # Use a default percentage if ATR is not available
                atr_value = current_price * 0.01  # 1% of price
            
            if direction == 'BUY':
                if stop_loss == 0:
                    stop_loss = current_price - (2 * atr_value)
                if take_profit == 0:
                    take_profit = current_price + (4 * atr_value)  # 2:1 risk-reward
            else:  # SELL
                if stop_loss == 0:
                    stop_loss = current_price + (2 * atr_value)
                if take_profit == 0:
                    take_profit = current_price - (4 * atr_value)  # 2:1 risk-reward
        
        # Calculate risk-reward ratio
        if direction == 'BUY':
            risk = entry_price - stop_loss if stop_loss > 0 else 0
            reward = take_profit - entry_price if take_profit > 0 else 0
        else:  # SELL
            risk = stop_loss - entry_price if stop_loss > 0 else 0
            reward = entry_price - take_profit if take_profit > 0 else 0
        
        risk_reward = reward / risk if risk > 0 else 0
        
        # Calculate risk and reward percentages
        risk_pct = (risk / entry_price) * 100 if entry_price > 0 else 0
        reward_pct = (reward / entry_price) * 100 if entry_price > 0 else 0
        
        # Get reason or create one
        reason = signal.get('reason', '')
        if not reason and 'description' in signal:
            reason = signal['description']
        if not reason:
            reason = f"{direction} signal with {risk_reward:.2f} risk-reward ratio"
        
        # Get strategy name
        strategy_name = signal.get('strategy', 'Unknown')
        
        # Create trade setup
        trade_setup = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'risk_pct': risk_pct,
            'reward_pct': reward_pct,
            'reason': reason,
            'strategy': strategy_name,
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
            dict: Best signal or None if no signals
        """
        if not signals:
            return None
        
        # Sort signals by a combination of risk-reward and strength
        # This prioritizes signals with good risk-reward and high strength
        sorted_signals = sorted(signals, key=lambda x: (
            x.get('risk_reward', 0) * 10 + x.get('strength', 0) / 10
        ), reverse=True)
        
        # Return the best signal
        return sorted_signals[0] if sorted_signals else None

    
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
