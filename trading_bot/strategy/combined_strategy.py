"""
Combined strategy module
Integrates SMC, ICT, Technical Analysis, and Sentiment Analysis
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
import asyncio

from trading_bot.strategy.strategy_base import Strategy
from trading_bot.strategy.smc_strategy import SMCStrategy
from trading_bot.strategy.ict_strategy import ICTStrategy
from trading_bot.analysis.technical import TechnicalAnalyzer
from trading_bot.analysis.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

class CombinedStrategy(Strategy):
    """
    Combined strategy that integrates multiple analysis methods
    to identify high-probability trade setups with improved RR
    """
    
    def __init__(self):
        """Initialize the combined strategy"""
        super().__init__()
        self.smc_strategy = SMCStrategy()
        self.ict_strategy = ICTStrategy()
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        logger.info("Initialized combined strategy with SMC, ICT, Technical, and Sentiment analysis")
    
    async def analyze_with_sentiment(self, df: pd.DataFrame, symbol: str, timeframe: str, market_type: str = 'forex') -> Dict:
        """
        Analyze with sentiment data included
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            dict: Analysis results
        """
        # Get sentiment analysis
        sentiment_data = await self.sentiment_analyzer.get_combined_sentiment(symbol, market_type)
        
        # Get regular analysis
        analysis = self.analyze(df, symbol, timeframe)
        
        # Add sentiment data
        analysis['sentiment'] = sentiment_data
        
        # Adjust signals based on sentiment
        self._adjust_signals_with_sentiment(analysis, sentiment_data)
        
        return analysis
    
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Analyze price data using multiple strategies
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Analysis results
        """
        logger.info(f"Analyzing {symbol} on {timeframe} with combined strategy")
        
        # Get analysis from each component
        smc_analysis = self.smc_strategy.analyze(df, symbol, timeframe)
        ict_analysis = self.ict_strategy.analyze(df, symbol, timeframe)
        technical_analysis = self.technical_analyzer.analyze_chart(df, symbol)
        
        # Combine signals
        all_signals = []
        all_signals.extend(smc_analysis.get('signals', []))
        all_signals.extend(ict_analysis.get('signals', []))
        all_signals.extend(technical_analysis.get('signals', []))
        
        # Sort signals by strength
        all_signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        # Determine overall bias
        bias = self._determine_combined_bias(smc_analysis, ict_analysis, technical_analysis)
        
        # Find high-probability setups
        trade_setups = self._find_high_probability_setups(df, symbol, all_signals, bias)
        
        # Compile analysis results
        analysis = {
            'symbol': symbol,
            'timeframe': timeframe,
            'datetime': df.index[-1] if not df.empty else None,
            'current_price': df.iloc[-1]['close'] if not df.empty else None,
            'bias': bias,
            'signals': all_signals,
            'trade_setups': trade_setups,
            'smc_analysis': smc_analysis,
            'ict_analysis': ict_analysis,
            'technical_analysis': technical_analysis
        }
        
        return analysis
    
    def _determine_combined_bias(self, smc_analysis: Dict, ict_analysis: Dict, technical_analysis: Dict) -> str:
        """
        Determine overall market bias from multiple analyses
        
        Args:
            smc_analysis (dict): SMC analysis results
            ict_analysis (dict): ICT analysis results
            technical_analysis (dict): Technical analysis results
            
        Returns:
            str: Overall market bias ('bullish', 'bearish', or 'neutral')
        """
        # Extract bias from each analysis
        smc_bias = smc_analysis.get('bias', 'neutral')
        ict_bias = ict_analysis.get('bias', 'neutral')
        tech_bias = technical_analysis.get('bias', 'neutral')
        
        # Count biases
        bullish_count = sum(1 for bias in [smc_bias, ict_bias, tech_bias] if bias == 'bullish')
        bearish_count = sum(1 for bias in [smc_bias, ict_bias, tech_bias] if bias == 'bearish')
        
        # Determine overall bias
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _find_high_probability_setups(self, df: pd.DataFrame, symbol: str, signals: List[Dict], bias: str) -> List[Dict]:
        """
        Find high-probability trade setups with good RR
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            signals (list): Combined signals
            bias (str): Overall market bias
            
        Returns:
            list: High-probability trade setups
        """
        high_prob_setups = []
        
        # Filter signals by strength and alignment with bias
        strong_signals = [s for s in signals if s.get('strength', 0) >= 70]
        aligned_signals = [s for s in strong_signals if 
                          (s.get('type') == 'bullish' and bias == 'bullish') or 
                          (s.get('type') == 'bearish' and bias == 'bearish')]
        
        # If we have aligned signals, use them; otherwise use strong signals
        filtered_signals = aligned_signals if aligned_signals else strong_signals
        
        # Group signals by type
        bullish_signals = [s for s in filtered_signals if s.get('type') == 'bullish']
        bearish_signals = [s for s in filtered_signals if s.get('type') == 'bearish']
        
        # Current price
        current_price = df.iloc[-1]['close'] if not df.empty else 0
        
        # Find key levels from SMC and ICT
        key_levels = self._extract_key_levels(df)
        
        # Process bullish setups
        if bullish_signals and (bias == 'bullish' or bias == 'neutral'):
            # Find nearest support for stop loss
            supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
            if supports:
                # Use the strongest support level
                strongest_support = max(supports, key=lambda x: x.get('strength', 0))
                
                # Find resistance levels for take profit
                resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
                if resistances:
                    # Use the strongest resistance level
                    strongest_resistance = max(resistances, key=lambda x: x.get('strength', 0))
                    
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = strongest_support['price'] * 0.998  # Just below support
                    take_profit = strongest_resistance['price']
                    
                    # Calculate risk-reward ratio
                    risk = entry - stop_loss
                    reward = take_profit - entry
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 3
                    if risk_reward >= 3:
                        # Get the strongest signal
                        strongest_signal = max(bullish_signals, key=lambda x: x.get('strength', 0))
                        
                        high_prob_setups.append({
                            'symbol': symbol,
                            'direction': 'BUY',
                            'entry': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': strongest_signal.get('strength', 0),
                            'reason': f"Strong bullish setup with {risk_reward:.2f} RR. Support at {stop_loss:.5f}, resistance at {take_profit:.5f}",
                            'signals': [s.get('description', '') for s in bullish_signals[:3]]
                        })
        
        # Process bearish setups
        if bearish_signals and (bias == 'bearish' or bias == 'neutral'):
            # Find nearest resistance for stop loss
            resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
            if resistances:
                # Use the strongest resistance level
                strongest_resistance = max(resistances, key=lambda x: x.get('strength', 0))
                
                # Find support levels for take profit
                supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
                if supports:
                    # Use the strongest support level
                    strongest_support = max(supports, key=lambda x: x.get('strength', 0))
                    
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = strongest_resistance['price'] * 1.002  # Just above resistance
                    take_profit = strongest_support['price']
                    
                    # Calculate risk-reward ratio
                    risk = stop_loss - entry
                    reward = entry - take_profit
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 3
                    if risk_reward >= 3:
                        # Get the strongest signal
                        strongest_signal = max(bearish_signals, key=lambda x: x.get('strength', 0))
                        
                        high_prob_setups.append({
                            'symbol': symbol,
                            'direction': 'SELL',
                            'entry': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': strongest_signal.get('strength', 0),
                            'reason': f"Strong bearish setup with {risk_reward:.2f} RR. Resistance at {stop_loss:.5f}, support at {take_profit:.5f}",
                            'signals': [s.get('description', '') for s in bearish_signals[:3]]
                        })
        
        return high_prob_setups
    
    def _extract_key_levels(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extract key levels from SMC and technical analysis
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Key price levels
        """
        # Get key levels from technical analysis
        key_levels = self.technical_analyzer.identify_key_levels(df)
        
        # Add SMC order blocks as key levels
        order_blocks = self._identify_order_blocks(df)
        for ob in order_blocks:
            level_type = 'support' if ob['type'] == 'bullish' else 'resistance'
            key_levels.append({
                'type': level_type,
                'price': ob['price'],
                'strength': 80,  # Order blocks are strong levels
                'source': 'smc_order_block'
            })
        
        # Add ICT fair value gaps as key levels
        fvgs = self._identify_fair_value_gaps(df)
        for fvg in fvgs:
            level_type = 'support' if fvg['type'] == 'bullish' else 'resistance'
            key_levels.append({
                'type': level_type,
                'price': fvg['price'],
                'strength': 75,  # FVGs are strong levels
                'source': 'ict_fvg'
            })
        
        return key_levels
    
    def _identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify SMC order blocks
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Order blocks
        """
        order_blocks = []
        
        # This is a simplified implementation
        # In a real implementation, you would use the SMC strategy's order block detection
        
        # Look for potential bullish order blocks (strong bearish candles followed by bullish move)
        for i in range(3, len(df) - 3):
            # Check for a strong bearish candle
            if df['close'].iloc[i] < df['open'].iloc[i] and (df['open'].iloc[i] - df['close'].iloc[i]) / df['open'].iloc[i] > 0.003:
                # Check if followed by bullish move
                if df['close'].iloc[i+3] > df['high'].iloc[i]:
                    order_blocks.append({
                        'type': 'bullish',
                        'price': (df['high'].iloc[i] + df['low'].iloc[i]) / 2,
                        'high': df['high'].iloc[i],
                        'low': df['low'].iloc[i],
                        'index': i
                    })
        
        # Look for potential bearish order blocks (strong bullish candles followed by bearish move)
        for i in range(3, len(df) - 3):
            # Check for a strong bullish candle
            if df['close'].iloc[i] > df['open'].iloc[i] and (df['close'].iloc[i] - df['open'].iloc[i]) / df['open'].iloc[i] > 0.003:
                # Check if followed by bearish move
                if df['close'].iloc[i+3] < df['low'].iloc[i]:
                    order_blocks.append({
                        'type': 'bearish',
                        'price': (df['high'].iloc[i] + df['low'].iloc[i]) / 2,
                        'high': df['high'].iloc[i],
                        'low': df['low'].iloc[i],
                        'index': i
                    })
        
        return order_blocks
    
    def _identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify ICT fair value gaps
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Fair value gaps
        """
        fvgs = []
        
        # This is a simplified implementation
        # In a real implementation, you would use the ICT strategy's FVG detection
        
        # Look for bullish FVGs (gap up)
        for i in range(1, len(df) - 1):
            if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
                fvgs.append({
                    'type': 'bullish',
                    'price': (df['high'].iloc[i-1] + df['low'].iloc[i+1]) / 2,
                    'top': df['low'].iloc[i+1],
                    'bottom': df['high'].iloc[i-1],
                    'index': i
                })
        
        # Look for bearish FVGs (gap down)
        for i in range(1, len(df) - 1):
            if df['high'].iloc[i+1] < df['low'].iloc[i-1]:
                fvgs.append({
                    'type': 'bearish',
                    'price': (df['low'].iloc[i-1] + df['high'].iloc[i+1]) / 2,
                    'top': df['low'].iloc[i-1],
                    'bottom': df['high'].iloc[i+1],
                    'index': i
                })
        
        return fvgs
    
    def _adjust_signals_with_sentiment(self, analysis: Dict, sentiment_data: Dict) -> None:
        """
        Adjust signals based on sentiment data
        
        Args:
            analysis (dict): Analysis results
            sentiment_data (dict): Sentiment analysis data
        """
        if not sentiment_data:
            return
        
        sentiment = sentiment_data.get('sentiment', 'neutral')
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        confidence = sentiment_data.get('confidence', 0)
        
        # Adjust signal strengths based on sentiment
        for signal in analysis.get('signals', []):
            # Boost bullish signals if sentiment is bullish
            if signal.get('type') == 'bullish' and sentiment == 'bullish':
                signal['strength'] = min(100, signal.get('strength', 0) + int(confidence * 10))
                signal['description'] += f" (Boosted by bullish sentiment: {sentiment_score:.2f})"
            
            # Boost bearish signals if sentiment is bearish
            elif signal.get('type') == 'bearish' and sentiment == 'bearish':
                signal['strength'] = min(100, signal.get('strength', 0) + int(confidence * 10))
                signal['description'] += f" (Boosted by bearish sentiment: {sentiment_score:.2f})"
            
            # Reduce signal strength if it contradicts sentiment
            elif (signal.get('type') == 'bullish' and sentiment == 'bearish') or \
                 (signal.get('type') == 'bearish' and sentiment == 'bullish'):
                signal['strength'] = max(0, signal.get('strength', 0) - int(confidence * 10))
                signal['description'] += f" (Reduced due to contrary sentiment: {sentiment_score:.2f})"
        
        # Re-sort signals by adjusted strength
        analysis['signals'].sort(key=lambda x: x.get('strength', 0), reverse=True)
    
    def get_multi_timeframe_analysis(self, dfs: Dict[str, pd.DataFrame], symbol: str, market_type: str = 'forex') -> Dict:
        """
        Perform multi-timeframe analysis to identify HTF POIs and LTF entries
        
        Args:
            dfs (dict): Dictionary of dataframes for different timeframes
            symbol (str): Trading symbol
            market_type (str): Market type
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        mtf_analysis = {
            'symbol': symbol,
            'timeframes': {},
            'htf_poi': [],
            'ltf_entries': [],
            'overall_bias': 'neutral'
        }
        
        # Define timeframe hierarchy
        timeframe_hierarchy = {
            '1m': 0, '5m': 1, '15m': 2, '30m': 3, '1h': 4, '4h': 5, '1d': 6
        }
        
        # Sort timeframes by hierarchy
        sorted_timeframes = sorted(dfs.keys(), key=lambda tf: timeframe_hierarchy.get(tf, 0))
        
        # Analyze each timeframe
        for timeframe in sorted_timeframes:
            df = dfs[timeframe]
            analysis = self.analyze(df, symbol, timeframe)
            mtf_analysis['timeframes'][timeframe] = analysis
        
        # Identify HTF POIs (from higher timeframes)
        htf_timeframes = [tf for tf in sorted_timeframes if timeframe_hierarchy.get(tf, 0) >= 4]  # 4h and above
        for tf in htf_timeframes:
            if tf in mtf_analysis['timeframes']:
                analysis = mtf_analysis['timeframes'][tf]
                
                # Extract key levels from HTF
                key_levels = self._extract_key_levels(dfs[tf])
                
                # Add to HTF POIs
                for level in key_levels:
                    mtf_analysis['htf_poi'].append({
                        'timeframe': tf,
                        'type': level['type'],
                        'price': level['price'],
                        'strength': level.get('strength', 50),
                        'source': level.get('source', 'key_level')
                    })
        
        # Sort POIs by strength
        mtf_analysis['htf_poi'].sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        # Identify LTF entries (from lower timeframes)
        ltf_timeframes = [tf for tf in sorted_timeframes if timeframe_hierarchy.get(tf, 0) <= 3]  # 30m and below
        for tf in ltf_timeframes:
            if tf in mtf_analysis['timeframes']:
                analysis = mtf_analysis['timeframes'][tf]
                
                # Get trade setups from LTF
                for setup in analysis.get('trade_setups', []):
                    # Check if setup aligns with HTF POI
                    aligned_with_poi = self._check_alignment_with_poi(setup, mtf_analysis['htf_poi'])
                    
                    if aligned_with_poi:
                        setup['timeframe'] = tf
                        setup['aligned_with_htf'] = True
                        mtf_analysis['ltf_entries'].append(setup)
        
        # Determine overall bias from HTF
        htf_biases = [mtf_analysis['timeframes'][tf].get('bias', 'neutral') for tf in htf_timeframes if tf in mtf_analysis['timeframes']]
        bullish_count = htf_biases.count('bullish')
        bearish_count = htf_biases.count('bearish')
        
        if bullish_count > bearish_count:
            mtf_analysis['overall_bias'] = 'bullish'
        elif bearish_count > bullish_count:
            mtf_analysis['overall_bias'] = 'bearish'
        else:
            mtf_analysis['overall_bias'] = 'neutral'
        
        return mtf_analysis
    
    def _check_alignment_with_poi(self, setup: Dict, pois: List[Dict]) -> bool:
        """
        Check if a trade setup aligns with HTF POIs
        
        Args:
            setup (dict): Trade setup
            pois (list): List of POIs
            
        Returns:
            bool: True if setup aligns with POI, False otherwise
        """
        direction = setup.get('direction', '')
        entry = setup.get('entry', 0)
        stop_loss = setup.get('stop_loss', 0)
        take_profit = setup.get('take_profit', 0)
        
        # For buy setups, check if stop loss is near a support POI
        if direction == 'BUY':
            for poi in pois:
                if poi['type'] == 'support':
                    # Check if stop loss is near POI
                    if abs(stop_loss - poi['price']) / poi['price'] < 0.005:  # Within 0.5%
                        return True
        
        # For sell setups, check if stop loss is near a resistance POI
        elif direction == 'SELL':
            for poi in pois:
                if poi['type'] == 'resistance':
                    # Check if stop loss is near POI
                    if abs(stop_loss - poi['price']) / poi['price'] < 0.005:  # Within 0.5%
                        return True
        
        return False
    
    def get_trade_setup(self, signal: Dict) -> Dict:
        """
        Get trade setup details from a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup details
        """
        # Extract basic signal info
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', '')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        risk_reward = signal.get('risk_reward', 0)
        
        # Calculate position size based on risk management
        account_size = 10000  # Default account size
        risk_percentage = 1.0  # Default risk percentage
        
        position_sizing = self.technical_analyzer.calculate_optimal_position_size(
            account_size, risk_percentage, entry, stop_loss
        )
        
        # Create comprehensive trade setup
        trade_setup = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'position_size': position_sizing.get('position_size', 0),
            'risk_amount': position_sizing.get('risk_amount', 0),
            'strategy': 'combined',
            'signals': signal.get('signals', []),
            'reason': signal.get('reason', ''),
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return trade_setup
