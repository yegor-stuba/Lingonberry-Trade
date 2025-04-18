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
        super().__init__(name="combined")  # Add name parameter
        self.smc_strategy = SMCStrategy()
        self.ict_strategy = ICTStrategy()
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        logger.info("Initialized combined strategy with SMC, ICT, Technical, and Sentiment analysis")


    def generate_signals(self, symbol: str, df: pd.DataFrame, timeframe: str) -> List[Dict]:
        """
        Generate trading signals for a symbol
        
        Args:
            symbol (str): Trading symbol
            df (pd.DataFrame): OHLCV data
            timeframe (str): Timeframe
            
        Returns:
            list: List of trading signals
        """
        # Get analysis
        analysis = self.analyze(df, symbol, timeframe)
        
        # Extract signals from analysis
        signals = analysis.get('signals', [])
        
        # Extract trade setups
        trade_setups = analysis.get('trade_setups', [])
        
        # Convert trade setups to signals format if needed
        for setup in trade_setups:
            if setup not in signals:
                signals.append(setup)
        
        return signals
    
    async def analyze_with_sentiment(self, df: pd.DataFrame, symbol: str, timeframe: str, market_type: str = 'forex') -> Dict:
        # Get sentiment analysis
        sentiment_future = self.sentiment_analyzer.get_combined_sentiment(symbol, market_type)
        sentiment_data = await sentiment_future  # Await the future to get the actual data
        
        # Get regular analysis
        analysis = self.analyze(df, symbol, timeframe)
        
        # Add sentiment data
        analysis['sentiment'] = sentiment_data
        
        # Adjust signals based on sentiment
        self._adjust_signals_with_sentiment(analysis, sentiment_data)
        
        return analysis


    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """Analyze price data using multiple strategies"""
        logger.info(f"Analyzing {symbol} on {timeframe} with combined strategy")
        
        # Check for empty dataframe
        if df is None or df.empty:
            logger.warning(f"Empty dataframe provided for {symbol} on {timeframe}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'bias': 'neutral',
                'signals': [],
                'trade_setups': []
            }
        
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
        
        # Ensure we have data
        if df is None or df.empty:
            logger.warning(f"Empty dataframe provided for {symbol}")
            return high_prob_setups
        
        # Get current price - ensure it's not 0
        current_price = df.iloc[-1]['close'] if not df.empty else 0
        if current_price == 0:
            logger.error(f"Current price is 0 for {symbol}")
            return high_prob_setups
        
        # Filter signals by strength - use a lower threshold to get more signals
        strong_signals = [s for s in signals if s.get('strength', 0) >= 60]
        
        # If we don't have any strong signals, use all signals
        if not strong_signals:
            strong_signals = signals
        
        # Group signals by type
        bullish_signals = [s for s in strong_signals if s.get('type') == 'bullish' or s.get('direction') == 'BUY']
        bearish_signals = [s for s in strong_signals if s.get('type') == 'bearish' or s.get('direction') == 'SELL']
        
        # Find key levels from SMC and ICT
        key_levels = self._extract_key_levels(df)
        
        # Process bullish setups
        if bullish_signals and (bias == 'bullish' or bias == 'neutral'):
            # Find supports for stop loss
            supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
            
            # If no supports found, create one based on recent lows
            if not supports:
                recent_low = df['low'].iloc[-20:].min()
                supports = [{'type': 'support', 'price': recent_low, 'strength': 60}]
            
            # Find resistances for take profit
            resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
            
            # If no resistances found, create one based on recent highs
            if not resistances:
                recent_high = df['high'].iloc[-20:].max()
                resistances = [{'type': 'resistance', 'price': recent_high * 1.01, 'strength': 60}]
            
            # Create multiple trade setups with different risk-reward ratios
            for support in supports[:1]:  # Use top support
                for resistance in resistances[:1]:  # Use top resistance
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = support['price'] * 0.998  # Just below support
                    take_profit = resistance['price']
                    
                    # Ensure stop loss is below entry for BUY orders
                    if stop_loss >= entry:
                        stop_loss = entry * 0.99  # Default to 1% below entry
                    
                    # Calculate risk-reward ratio
                    risk = entry - stop_loss
                    reward = take_profit - entry
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 2
                    if risk_reward >= 2:
                        # Get the strongest signal
                        strongest_signal = max(bullish_signals, key=lambda x: x.get('strength', 0))
                        
                        high_prob_setups.append({
                            'symbol': symbol,
                            'direction': 'BUY',
                            'entry_price': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': strongest_signal.get('strength', 0),
                            'reason': f"Strong bullish setup with {risk_reward:.2f} RR. Support at {stop_loss:.5f}, resistance at {take_profit:.5f}",
                            'signals': [s.get('description', '') for s in bullish_signals[:3]]
                        })
        
        # Process bearish setups
        if bearish_signals and (bias == 'bearish' or bias == 'neutral'):
            # Find resistances for stop loss
            resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
            
            # If no resistances found, create one based on recent highs
            if not resistances:
                recent_high = df['high'].iloc[-20:].max()
                resistances = [{'type': 'resistance', 'price': recent_high, 'strength': 60}]
            
            # Find supports for take profit
            supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
            
            # If no supports found, create one based on recent lows
            if not supports:
                recent_low = df['low'].iloc[-20:].min()
                supports = [{'type': 'support', 'price': recent_low * 0.999, 'strength': 60}]
            
            # Create multiple trade setups with different risk-reward ratios
            for resistance in resistances[:1]:  # Use top resistance
                for support in supports[:1]:  # Use top support
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = resistance['price'] * 1.002  # Just above resistance
                    take_profit = support['price']
                    
                    # Ensure stop loss is above entry for SELL orders
                    if stop_loss <= entry:
                        stop_loss = entry * 1.01  # Default to 1% above entry
                    
                    # Calculate risk-reward ratio
                    risk = stop_loss - entry
                    reward = entry - take_profit
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 2
                    if risk_reward >= 2:
                        # Get the strongest signal
                        strongest_signal = max(bearish_signals, key=lambda x: x.get('strength', 0))
                        
                        high_prob_setups.append({
                            'symbol': symbol,
                            'direction': 'SELL',
                            'entry_price': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': strongest_signal.get('strength', 0),
                            'reason': f"Strong bearish setup with {risk_reward:.2f} RR. Resistance at {stop_loss:.5f}, support at {take_profit:.5f}",
                            'signals': [s.get('description', '') for s in bearish_signals[:3]]
                        })
        
        # Sort setups by risk-reward ratio and limit to top 2
        high_prob_setups.sort(key=lambda x: x.get('risk_reward', 0), reverse=True)
        return high_prob_setups[:2]  # Return maximum 2 setups

    def analyze_with_htf_context(self, symbol: str, timeframes: List[str]) -> Dict:
        """
        Analyze a symbol across multiple timeframes to identify HTF direction and POIs
        
        Args:
            symbol (str): Trading symbol
            timeframes (list): List of timeframes to analyze, from highest to lowest
            
        Returns:
            dict: Analysis results with HTF context
        """
        results = {
            'symbol': symbol,
            'htf_bias': 'neutral',
            'key_levels': [],
            'poi': [],
            'ltf_entries': []
        }
        
        # Get data for each timeframe
        data = {}
        for tf in timeframes:
            try:
                df = self.data_processor.get_data(symbol, tf)
                if df is not None and not df.empty:
                    data[tf] = df
            except Exception as e:
                logger.error(f"Error getting data for {symbol} {tf}: {e}")
        
        if not data:
            logger.error(f"No data available for {symbol} across any timeframes")
            return results
        
        # Analyze HTF first (highest timeframe)
        htf = timeframes[0]
        if htf in data:
            htf_analysis = self.analyze(data[htf], symbol, htf)
            results['htf_bias'] = htf_analysis.get('bias', 'neutral')
            
            # Extract key levels from HTF
            htf_levels = self._extract_key_levels(data[htf])
            for level in htf_levels:
                results['key_levels'].append({
                    'timeframe': htf,
                    'type': level['type'],
                    'price': level['price'],
                    'strength': level.get('strength', 50)
                })
            
            # Extract POIs from HTF
            htf_poi = self._identify_points_of_interest(data[htf], htf_analysis)
            for poi in htf_poi:
                results['poi'].append({
                    'timeframe': htf,
                    'type': poi['type'],
                    'price': poi['price'],
                    'strength': poi.get('strength', 50),
                    'description': poi.get('description', '')
                })
        
        # Analyze LTF for entries
        for tf in timeframes[1:]:  # Skip the HTF
            if tf in data:
                ltf_analysis = self.analyze(data[tf], symbol, tf)
                
                # Find entries that align with HTF bias and POIs
                for setup in ltf_analysis.get('trade_setups', []):
                    # Check if setup aligns with HTF bias
                    if (results['htf_bias'] == 'bullish' and setup.get('direction') == 'BUY') or \
                    (results['htf_bias'] == 'bearish' and setup.get('direction') == 'SELL') or \
                    results['htf_bias'] == 'neutral':
                        
                        # Check if setup aligns with POIs
                        aligned_with_poi = self._check_alignment_with_poi(setup, results['poi'])
                        
                        if aligned_with_poi:
                            setup['timeframe'] = tf
                            setup['aligned_with_htf'] = True
                            setup['aligned_with_poi'] = True
                            results['ltf_entries'].append(setup)
        
        # Sort entries by risk-reward ratio
        results['ltf_entries'].sort(key=lambda x: x.get('risk_reward', 0), reverse=True)
        
        # Limit to top 2 entries
        results['ltf_entries'] = results['ltf_entries'][:2]
        
        return results

    def _identify_points_of_interest(self, df: pd.DataFrame, analysis: Dict) -> List[Dict]:
        """
        Identify Points of Interest (POI) from price data
        
        Args:
            df (pd.DataFrame): OHLCV data
            analysis (dict): Analysis results
            
        Returns:
            list: Points of Interest
        """
        poi = []
        
        # Extract order blocks
        order_blocks = self._identify_order_blocks(df)
        for ob in order_blocks:
            poi.append({
                'type': 'order_block',
                'subtype': ob['type'],  # bullish or bearish
                'price': ob['price'],
                'high': ob.get('high', ob['price']),
                'low': ob.get('low', ob['price']),
                'strength': 80,  # Order blocks are strong POIs
                'description': f"{'Bullish' if ob['type'] == 'bullish' else 'Bearish'} Order Block"
            })
        
        # Extract fair value gaps
        fvgs = self._identify_fair_value_gaps(df)
        for fvg in fvgs:
            poi.append({
                'type': 'fair_value_gap',
                'subtype': fvg['type'],  # bullish or bearish
                'price': fvg['price'],
                'top': fvg.get('top', fvg['price']),
                'bottom': fvg.get('bottom', fvg['price']),
                'strength': 75,  # FVGs are strong POIs
                'description': f"{'Bullish' if fvg['type'] == 'bullish' else 'Bearish'} Fair Value Gap"
            })
        
        # Extract liquidity levels
        liquidity_levels = self._identify_liquidity_levels(df)
        for ll in liquidity_levels:
            poi.append({
                'type': 'liquidity',
                'subtype': ll['type'],  # buy_side_liquidity or sell_side_liquidity
                'price': ll['price'],
                'strength': ll.get('strength', 70),
                'description': f"{'Buy-side' if ll['type'] == 'buy_side_liquidity' else 'Sell-side'} Liquidity"
            })
        
        # Extract key support/resistance levels
        key_levels = self.technical_analyzer.identify_key_levels(df) if hasattr(self, 'technical_analyzer') else []
        for level in key_levels:
            poi.append({
                'type': level['type'],  # support or resistance
                'price': level['price'],
                'strength': level.get('strength', 65),
                'description': f"{level['type'].capitalize()} Level"
            })
        
        # Sort POIs by strength
        poi.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return poi

    def generate_trade_setups_with_htf(self, symbol: str, timeframes: List[str]) -> List[Dict]:
        """
        Generate trade setups with Higher Timeframe (HTF) context
        
        Args:
            symbol (str): Trading symbol
            timeframes (list): List of timeframes to analyze, from highest to lowest
            
        Returns:
            list: Trade setups with HTF context
        """
        # Analyze with HTF context
        htf_analysis = self.analyze_with_htf_context(symbol, timeframes)
        
        # If we have entries aligned with HTF, return those
        if htf_analysis['ltf_entries']:
            return htf_analysis['ltf_entries']
        
        # Otherwise, generate setups based on HTF bias and POIs
        htf_bias = htf_analysis['htf_bias']
        poi_list = htf_analysis['poi']
        
        # Get data for the lowest timeframe
        ltf = timeframes[-1]
        try:
            df = self.data_processor.get_data(symbol, ltf)
            if df is None or df.empty:
                logger.error(f"No data available for {symbol} on {ltf}")
                return []
        except Exception as e:
            logger.error(f"Error getting data for {symbol} {ltf}: {e}")
            return []
        
        # Generate signals for LTF
        signals = self.generate_signals(symbol, df, ltf)
        
        # Filter signals based on HTF bias
        if htf_bias == 'bullish':
            filtered_signals = [s for s in signals if s.get('direction', '') == 'BUY' or s.get('type', '') == 'bullish']
        elif htf_bias == 'bearish':
            filtered_signals = [s for s in signals if s.get('direction', '') == 'SELL' or s.get('type', '') == 'bearish']
        else:
            filtered_signals = signals
        
        # Current price
        current_price = df.iloc[-1]['close'] if not df.empty else 0
        
        # Create trade setups
        trade_setups = []
        
        # For bullish bias
        if htf_bias == 'bullish' or htf_bias == 'neutral':
            # Find support POIs for stop loss
            support_pois = [p for p in poi_list if p['type'] in ['support', 'order_block', 'fair_value_gap'] 
                            and p['price'] < current_price]
            
            # If no support POIs, use recent lows
            if not support_pois:
                recent_low = df['low'].iloc[-20:].min()
                support_pois = [{'type': 'support', 'price': recent_low, 'strength': 60}]
            
            # Find resistance POIs for take profit
            resistance_pois = [p for p in poi_list if p['type'] in ['resistance', 'liquidity'] 
                            and p['price'] > current_price]
            
            # If no resistance POIs, use recent highs
            if not resistance_pois:
                recent_high = df['high'].iloc[-20:].max()
                resistance_pois = [{'type': 'resistance', 'price': recent_high * 1.01, 'strength': 60}]
            
            # Create bullish setups
            for support in support_pois[:1]:  # Use top support
                for resistance in resistance_pois[:1]:  # Use top resistance
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = support['price'] * 0.998  # Just below support
                    take_profit = resistance['price']
                    
                    # Ensure stop loss is below entry for BUY orders
                    if stop_loss >= entry:
                        stop_loss = entry * 0.99  # Default to 1% below entry
                    
                    # Calculate risk-reward ratio
                    risk = entry - stop_loss
                    reward = take_profit - entry
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 2
                    if risk_reward >= 2:
                        trade_setups.append({
                            'symbol': symbol,
                            'direction': 'BUY',
                            'entry_price': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': 80,  # High strength due to HTF alignment
                            'timeframe': ltf,
                            'htf_bias': htf_bias,
                            'reason': (f"Bullish setup aligned with {htf_bias} HTF bias. "
                                    f"RR: {risk_reward:.2f}. "
                                    f"Stop loss at {support['type']} ({stop_loss:.5f}), "
                                    f"Take profit at {resistance['type']} ({take_profit:.5f})"),
                            'aligned_with_htf': True
                        })
        
        # For bearish bias
        if htf_bias == 'bearish' or htf_bias == 'neutral':
            # Find resistance POIs for stop loss
            resistance_pois = [p for p in poi_list if p['type'] in ['resistance', 'order_block', 'fair_value_gap'] 
                            and p['price'] > current_price]
            
            # If no resistance POIs, use recent highs
            if not resistance_pois:
                recent_high = df['high'].iloc[-20:].max()
                resistance_pois = [{'type': 'resistance', 'price': recent_high, 'strength': 60}]
            
            # Find support POIs for take profit
            support_pois = [p for p in poi_list if p['type'] in ['support', 'liquidity'] 
                            and p['price'] < current_price]
            
            # If no support POIs, use recent lows
            if not support_pois:
                recent_low = df['low'].iloc[-20:].min()
                support_pois = [{'type': 'support', 'price': recent_low * 0.999, 'strength': 60}]
            
            # Create bearish setups
            for resistance in resistance_pois[:1]:  # Use top resistance
                for support in support_pois[:1]:  # Use top support
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = resistance['price'] * 1.002  # Just above resistance
                    take_profit = support['price']
                    
                    # Ensure stop loss is above entry for SELL orders
                    if stop_loss <= entry:
                        stop_loss = entry * 1.01  # Default to 1% above entry
                    
                    # Calculate risk-reward ratio
                    risk = stop_loss - entry
                    reward = entry - take_profit
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with RR >= 2
                    if risk_reward >= 2:
                        trade_setups.append({
                            'symbol': symbol,
                            'direction': 'SELL',
                            'entry_price': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': 80,  # High strength due to HTF alignment
                            'timeframe': ltf,
                            'htf_bias': htf_bias,
                            'reason': (f"Bearish setup aligned with {htf_bias} HTF bias. "
                                    f"RR: {risk_reward:.2f}. "
                                    f"Stop loss at {resistance['type']} ({stop_loss:.5f}), "
                                    f"Take profit at {support['type']} ({take_profit:.5f})"),
                            'aligned_with_htf': True
                        })
        
        # Sort setups by risk-reward ratio
        trade_setups.sort(key=lambda x: x.get('risk_reward', 0), reverse=True)
        
        # Return top 2 setups
        return trade_setups[:2]


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

    def calculate_position_size(self, account_size: float, risk_percentage: float, 
                            entry_price: float, stop_loss: float, symbol: str = None) -> float:
        """Calculate optimal position size based on risk parameters"""
        return self.technical_analyzer.calculate_optimal_position_size(
            account_size, risk_percentage, entry_price, stop_loss
        ).get('position_size', 0)


    def calculate_risk_reward(self, entry_price: float, stop_loss: float, 
                         take_profit: float) -> float:
        """Calculate risk-reward ratio for a trade setup"""
        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit)
        return reward / risk if risk > 0 else 0

    def _identify_smart_money_concepts(self, df: pd.DataFrame) -> Dict:
        """Identify Smart Money Concepts elements in the chart"""
        return {
            'order_blocks': self._identify_order_blocks(df),
            'fair_value_gaps': self._identify_fair_value_gaps(df),
            'liquidity_levels': self._identify_liquidity_levels(df),
            'market_structure': []  # Add market structure analysis
        }

    def _identify_ict_concepts(self, df: pd.DataFrame) -> Dict:
        """Identify ICT concepts in the chart"""
        return {
            'premium_discount': [],
            'optimal_trade_entries': [],
            'breaker_blocks': [],
            'inducement_points': []
        }

    def _identify_liquidity_levels(self, df: pd.DataFrame) -> List[Dict]:
        """Identify liquidity levels in the chart"""
        liquidity_levels = []
        
        # Look for potential liquidity levels above swing highs
        for i in range(5, len(df) - 5):
            # Check for swing high
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, 5)) and \
            all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, 5)):
                liquidity_levels.append({
                    'type': 'buy_side_liquidity',
                    'price': df['high'].iloc[i] * 1.001,  # Just above swing high
                    'strength': 70
                })
        
        # Look for potential liquidity levels below swing lows
        for i in range(5, len(df) - 5):
            # Check for swing low
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, 5)) and \
            all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, 5)):
                liquidity_levels.append({
                    'type': 'sell_side_liquidity',
                    'price': df['low'].iloc[i] * 0.999,  # Just below swing low
                    'strength': 70
                })
        
        return liquidity_levels

    def _combine_analysis(self, smc_analysis: Dict, ict_analysis: Dict, technical_analysis: Dict, symbol: str, timeframe: str) -> Dict:
        """Combine analysis results from different strategies"""
        # Extract key components from each analysis
        combined = {
            'symbol': symbol,
            'timeframe': timeframe,
            'datetime': smc_analysis.get('datetime', None),
            'current_price': smc_analysis.get('current_price', None),
            'bias': self._determine_combined_bias(smc_analysis, ict_analysis, technical_analysis),
            'signals': [],
            'key_levels': [],
            'smc_analysis': smc_analysis,
            'ict_analysis': ict_analysis,
            'technical_analysis': technical_analysis
        }
        
        # Combine signals
        combined['signals'].extend(smc_analysis.get('signals', []))
        combined['signals'].extend(ict_analysis.get('signals', []))
        combined['signals'].extend(technical_analysis.get('signals', []))
        
        # Sort signals by strength
        combined['signals'].sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return combined

    def determine_bias(self, signals: List[Dict]) -> Dict:
        """Determine market bias based on signals"""
        bullish_signals = [s for s in signals if s.get('direction', '') == 'buy' or s.get('type', '') == 'bullish']
        bearish_signals = [s for s in signals if s.get('direction', '') == 'sell' or s.get('type', '') == 'bearish']
        
        # Calculate weighted strength
        bullish_strength = sum(s.get('strength', 50) for s in bullish_signals)
        bearish_strength = sum(s.get('strength', 50) for s in bearish_signals)
        
        # Determine direction
        if bullish_strength > bearish_strength:
            direction = 'bullish'
            strength = bullish_strength / (bullish_strength + bearish_strength) if (bullish_strength + bearish_strength) > 0 else 0.5
        elif bearish_strength > bullish_strength:
            direction = 'bearish'
            strength = bearish_strength / (bullish_strength + bearish_strength) if (bullish_strength + bearish_strength) > 0 else 0.5
        else:
            direction = 'neutral'
            strength = 0.5
        
        # Calculate confidence based on signal consistency
        if len(bullish_signals) + len(bearish_signals) > 0:
            if direction == 'bullish':
                confidence = len(bullish_signals) / (len(bullish_signals) + len(bearish_signals))
            elif direction == 'bearish':
                confidence = len(bearish_signals) / (len(bullish_signals) + len(bearish_signals))
            else:
                confidence = 0.5
        else:
            confidence = 0
        
        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence
        }

    def find_best_trade_setup(self, signals: List[Dict], df: pd.DataFrame) -> Dict:
        """Find the best trade setup from a list of signals"""
        if not signals:
            return None
        
        # Filter for entry signals
        entry_signals = [s for s in signals if s.get('type') == 'entry']
        if not entry_signals:
            return None
        
        # Get the strongest signal
        strongest_signal = max(entry_signals, key=lambda x: x.get('strength', 0))
        
        # Create a trade setup
        direction = strongest_signal.get('direction', '')
        entry_price = strongest_signal.get('price', df['close'].iloc[-1])
        
        # Calculate stop loss and take profit
        atr = self.technical_analyzer._calculate_atr(df, 14).iloc[-1]
        
        if direction == 'buy':
            stop_loss = entry_price - (2 * atr)
            take_profit = entry_price + (3 * atr)
        else:  # sell
            stop_loss = entry_price + (2 * atr)
            take_profit = entry_price - (3 * atr)
        
        # Calculate risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'symbol': strongest_signal.get('symbol', ''),
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'strength': strongest_signal.get('strength', 0),
            'reason': strongest_signal.get('description', '')
        }
