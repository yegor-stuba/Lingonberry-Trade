"""
Smart Money Concepts (SMC) analysis module
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class SMCAnalyzer:
    """
    Analyzer for Smart Money Concepts (SMC) trading methodology
    """
    
    def __init__(self):
        """Initialize the SMC analyzer"""
        pass
    
    def analyze_chart(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        Analyze a price chart using SMC methodology
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            symbol (str, optional): Symbol being analyzed
            
        Returns:
            dict: Analysis results
        """
        try:
            logger.info(f"Starting SMC analysis for {symbol} with {len(df)} candles")
            
            # Ensure dataframe has required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col.lower() in df.columns for col in required_columns):
                logger.error(f"Dataframe missing required columns. Available: {df.columns}")
                return {'error': 'Missing required columns in dataframe'}
            
            # Standardize column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Identify market structure
            market_structure = self.identify_market_structure(df)
            logger.info(f"Market structure for {symbol}: {market_structure.get('trend', 'unknown')}")
            
            # Identify key levels
            key_levels = self.identify_key_levels(df)
            logger.info(f"Found {len(key_levels)} key levels for {symbol}")
            
            # Identify order blocks
            order_blocks = self.identify_order_blocks(df)
            logger.info(f"Found {len(order_blocks)} order blocks for {symbol}")
            
            # Identify fair value gaps
            fair_value_gaps = self.identify_fair_value_gaps(df)
            logger.info(f"Found {len(fair_value_gaps)} fair value gaps for {symbol}")
            
            # Identify liquidity levels
            liquidity_levels = self.identify_liquidity_levels(df)
            logger.info(f"Found {len(liquidity_levels)} liquidity levels for {symbol}")
            
            # Identify order flow
            order_flow = self.identify_order_flow(df)
            logger.info(f"Order flow analysis completed for {symbol}")
            
            # Identify liquidity sweeps
            liquidity_sweeps = self.identify_liquidity_sweeps(df, market_structure)
            logger.info(f"Found {len(liquidity_sweeps)} liquidity sweeps for {symbol}")
            
            # Find trade setups
            trade_setups = self.find_trade_setups(df)
            logger.info(f"Found {len(trade_setups)} trade setups for {symbol}")
            
            # Determine overall market bias
            bias = market_structure.get('trend', 'neutral')
            
            # Return analysis results
            return {
                'symbol': symbol,
                'bias': bias,
                'market_structure': market_structure,
                'key_levels': key_levels,
                'order_blocks': order_blocks,
                'fair_value_gaps': fair_value_gaps,
                'liquidity_levels': liquidity_levels,
                'order_flow': order_flow,
                'liquidity_sweeps': liquidity_sweeps,
                'trade_setups': trade_setups
            }
            
        except Exception as e:
            logger.error(f"Error analyzing chart: {e}")
            return {'error': str(e)}
    
    def identify_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        Identify market structure (trend, swing highs/lows, HH, HL, LL, LH)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            dict: Market structure details
        """
        try:
            # Check for empty dataframe
            if df is None or df.empty or len(df) < 50:  # Need enough data for analysis
                return {
                    'trend': 'neutral',
                    'structure': 'undefined',
                    'swing_highs': [],
                    'swing_lows': [],
                    'hh_hl_ll_lh': {'higher_highs': [], 'higher_lows': [], 'lower_lows': [], 'lower_highs': []}
                }

            # Simple trend identification based on moving averages
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            
            # Determine trend based on MA relationship
            current_close = df['close'].iloc[-1]
            current_ma20 = df['ma20'].iloc[-1]
            current_ma50 = df['ma50'].iloc[-1]
            
            if current_ma20 > current_ma50 and current_close > current_ma20:
                trend = 'bullish'
            elif current_ma20 < current_ma50 and current_close < current_ma20:
                trend = 'bearish'
            else:
                trend = 'neutral'
            
            # Find swing highs and lows (simple method)
            swing_highs = []
            swing_lows = []
            
            # Use a window of 5 candles to identify swings
            window = 5
            for i in range(window, len(df) - window):
                # Check for swing high
                if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
                   all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                    swing_highs.append({
                        'index': i,
                        'price': df['high'].iloc[i],
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None
                    })
                
                # Check for swing low
                if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
                   all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                    swing_lows.append({
                        'index': i,
                        'price': df['low'].iloc[i],
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None
                    })
            
            # Identify Higher Highs (HH), Higher Lows (HL), Lower Lows (LL), Lower Highs (LH)
            hh_hl_ll_lh = self._identify_hh_hl_ll_lh(swing_highs, swing_lows)
            
            # Determine market structure based on HH, HL, LL, LH
            if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                recent_swing_highs = sorted(swing_highs[-2:], key=lambda x: x['index'])
                recent_swing_lows = sorted(swing_lows[-2:], key=lambda x: x['index'])
                
                higher_highs = recent_swing_highs[1]['price'] > recent_swing_highs[0]['price']
                higher_lows = recent_swing_lows[1]['price'] > recent_swing_lows[0]['price']
                
                if higher_highs and higher_lows:
                    structure = 'uptrend'
                elif not higher_highs and not higher_lows:
                    structure = 'downtrend'
                else:
                    structure = 'consolidation'
            else:
                structure = 'undefined'
            
            return {
                'trend': trend,
                'structure': structure,
                'swing_highs': swing_highs[-5:] if swing_highs else [],  # Last 5 swing highs
                'swing_lows': swing_lows[-5:] if swing_lows else [],     # Last 5 swing lows
                'hh_hl_ll_lh': hh_hl_ll_lh
            }

        except Exception as e:
            logger.error(f"Error identifying market structure: {e}")
            return {
                'trend': 'neutral',
                'structure': 'undefined',
                'swing_highs': [],
                'swing_lows': [],
                'hh_hl_ll_lh': {'higher_highs': [], 'higher_lows': [], 'lower_lows': [], 'lower_highs': []}
            }
    
    def _identify_hh_hl_ll_lh(self, swing_highs: List[Dict], swing_lows: List[Dict]) -> Dict:
        """
        Identify Higher Highs (HH), Higher Lows (HL), Lower Lows (LL), Lower Highs (LH)
        
        Args:
            swing_highs (list): List of swing highs
            swing_lows (list): List of swing lows
            
        Returns:
            dict: HH, HL, LL, LH information
        """
        hh = []
        hl = []
        ll = []
        lh = []
        
        # Need at least 2 swing highs/lows to identify patterns
        if len(swing_highs) >= 2:
            # Check for Higher Highs (HH) and Lower Highs (LH)
            for i in range(1, len(swing_highs)):
                if swing_highs[i]['price'] > swing_highs[i-1]['price']:
                    hh.append({
                        'index': swing_highs[i]['index'],
                        'price': swing_highs[i]['price'],
                        'date': swing_highs[i]['date'],
                        'previous_price': swing_highs[i-1]['price'],
                        'previous_index': swing_highs[i-1]['index']
                    })
                else:
                    lh.append({
                        'index': swing_highs[i]['index'],
                        'price': swing_highs[i]['price'],
                        'date': swing_highs[i]['date'],
                        'previous_price': swing_highs[i-1]['price'],
                        'previous_index': swing_highs[i-1]['index']
                    })
        
        if len(swing_lows) >= 2:
            # Check for Higher Lows (HL) and Lower Lows (LL)
            for i in range(1, len(swing_lows)):
                if swing_lows[i]['price'] > swing_lows[i-1]['price']:
                    hl.append({
                        'index': swing_lows[i]['index'],
                        'price': swing_lows[i]['price'],
                        'date': swing_lows[i]['date'],
                        'previous_price': swing_lows[i-1]['price'],
                        'previous_index': swing_lows[i-1]['index']
                    })
                else:
                    ll.append({
                        'index': swing_lows[i]['index'],
                        'price': swing_lows[i]['price'],
                        'date': swing_lows[i]['date'],
                        'previous_price': swing_lows[i-1]['price'],
                        'previous_index': swing_lows[i-1]['index']
                    })
        
        return {
            'higher_highs': hh,
            'higher_lows': hl,
            'lower_lows': ll,
            'lower_highs': lh
        }
    
    def identify_key_levels(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify key support and resistance levels
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Key levels with type and price
        """
        key_levels = []
        
        # Use recent swing highs and lows as key levels
        market_structure = self.identify_market_structure(df)
        
        # Add swing highs as resistance
        for high in market_structure['swing_highs']:
            key_levels.append({
                'type': 'resistance',
                'price': high['price'],
                'strength': self._calculate_level_strength(df, high['price'], 'resistance')
            })
        
        # Add swing lows as support
        for low in market_structure['swing_lows']:
            key_levels.append({
                'type': 'support',
                'price': low['price'],
                'strength': self._calculate_level_strength(df, low['price'], 'support')
            })
        
        # Add psychological levels (round numbers)
        current_price = df['close'].iloc[-1]
        
        # Find appropriate scale for psychological levels based on price
        if current_price < 1:
            scales = [0.1, 0.25, 0.5, 0.75]
        elif current_price < 10:
            scales = [1, 2.5, 5, 7.5]
        elif current_price < 100:
            scales = [10, 25, 50, 75]
        elif current_price < 1000:
            scales = [100, 250, 500, 750]
        else:
            scales = [1000, 2500, 5000, 7500]
        
        # Add psychological levels near current price
        for scale in scales:
            level = round(current_price / scale) * scale
            if abs(level - current_price) / current_price < 0.05:  # Within 5% of current price
                key_levels.append({
                    'type': 'psychological',
                    'price': level,
                    'strength': 50  # Medium strength for psychological levels
                })
        
        # Sort by price
        key_levels.sort(key=lambda x: x['price'])
        
        return key_levels
    
    def _calculate_level_strength(self, df: pd.DataFrame, price: float, level_type: str) -> int:
        """
        Calculate the strength of a support/resistance level
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            price (float): Level price
            level_type (str): 'support' or 'resistance'
            
        Returns:
            int: Strength score (0-100)
        """
        # Count how many times price has respected this level
        touches = 0
        strong_touches = 0
        
        # Define price range for level (0.1% of price)
        price_range = price * 0.001
        
        for i in range(len(df)):
            if level_type == 'support':
                # Price came within range of level and bounced up
                if abs(df['low'].iloc[i] - price) <= price_range and df['close'].iloc[i] > df['open'].iloc[i]:
                    touches += 1
                    # Strong bounce (closed significantly higher)
                    if (df['close'].iloc[i] - df['low'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) > 0.7:
                        strong_touches += 1
            else:  # resistance
                # Price came within range of level and bounced down
                if abs(df['high'].iloc[i] - price) <= price_range and df['close'].iloc[i] < df['open'].iloc[i]:
                    touches += 1
                    # Strong bounce (closed significantly lower)
                    if (df['high'].iloc[i] - df['close'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) > 0.7:
                        strong_touches += 1
        
        # Calculate strength based on touches and strong touches
        strength = min(100, touches * 10 + strong_touches * 15)
        
        return strength
    
    def identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify order blocks (OB)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Order blocks with type, price range, and strength
        """
        order_blocks = []
        
        # We need at least 20 candles for reliable order block identification
        if len(df) < 20:
            logger.warning("Not enough data to identify order blocks")
            return order_blocks
        
        # Look for bullish and bearish order blocks
        for i in range(3, len(df) - 1):
            # Bullish Order Block (BOB): 
            # A bearish candle followed by strong bullish momentum
            if (df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Bearish candle
                df['close'].iloc[i] > df['open'].iloc[i] and      # Bullish candle
                df['close'].iloc[i] > df['high'].iloc[i-1] and    # Strong momentum
                df['close'].iloc[i+1] > df['close'].iloc[i]):     # Continuation
                
                # Calculate strength based on volume and subsequent price movement
                strength = self._calculate_ob_strength(df, i-1, 'bullish')
                
                # Only include significant order blocks
                if strength > 30:
                    order_blocks.append({
                        'type': 'bullish',
                        'index': i-1,
                        'date': df.index[i-1] if hasattr(df.index, '__getitem__') else None,
                        'top': df['open'].iloc[i-1],
                        'bottom': df['close'].iloc[i-1],
                        'strength': strength,
                        'age': len(df) - i + 1  # How many candles ago
                    })
            
            # Bearish Order Block (BOB): 
            # A bullish candle followed by strong bearish momentum
            if (df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Bullish candle
                df['close'].iloc[i] < df['open'].iloc[i] and      # Bearish candle
                df['close'].iloc[i] < df['low'].iloc[i-1] and     # Strong momentum
                df['close'].iloc[i+1] < df['close'].iloc[i]):     # Continuation
                
                # Calculate strength based on volume and subsequent price movement
                strength = self._calculate_ob_strength(df, i-1, 'bearish')
                
                # Only include significant order blocks
                if strength > 30:
                    order_blocks.append({
                        'type': 'bearish',
                        'index': i-1,
                        'date': df.index[i-1] if hasattr(df.index, '__getitem__') else None,
                        'top': df['close'].iloc[i-1],
                        'bottom': df['open'].iloc[i-1],
                        'strength': strength,
                        'age': len(df) - i + 1  # How many candles ago
                    })
        
        # Sort by strength (descending)
        order_blocks.sort(key=lambda x: x['strength'], reverse=True)
        
        # Return top 10 order blocks
        return order_blocks[:10]
    
    def _calculate_ob_strength(self, df: pd.DataFrame, index: int, ob_type: str) -> int:
        """
        Calculate the strength of an order block
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            index (int): Index of the order block candle
            ob_type (str): 'bullish' or 'bearish'
            
        Returns:
            int: Strength score (0-100)
        """
        strength = 50  # Base strength
        
        # Factor 1: Volume - higher volume means stronger order block
        avg_volume = df['volume'].iloc[max(0, index-10):index].mean()
        if df['volume'].iloc[index] > 2 * avg_volume:
            strength += 20
        elif df['volume'].iloc[index] > avg_volume:
            strength += 10
        
        # Factor 2: Subsequent price movement - stronger if price moved significantly
        if ob_type == 'bullish':
            # Calculate how far price moved up after the order block
            price_move = 0
            for i in range(index + 1, min(index + 10, len(df))):
                if df['high'].iloc[i] > df['high'].iloc[index:i].max():
                    price_move = max(price_move, (df['high'].iloc[i] - df['close'].iloc[index]) / df['close'].iloc[index])
            
            # Adjust strength based on price movement
            if price_move > 0.02:  # More than 2% move
                strength += 20
            elif price_move > 0.01:  # More than 1% move
                strength += 10
        else:  # bearish
            # Calculate how far price moved down after the order block
            price_move = 0
            for i in range(index + 1, min(index + 10, len(df))):
                if df['low'].iloc[i] < df['low'].iloc[index:i].min():
                    price_move = max(price_move, (df['close'].iloc[index] - df['low'].iloc[i]) / df['close'].iloc[index])
            
            # Adjust strength based on price movement
            if price_move > 0.02:  # More than 2% move
                strength += 20
            elif price_move > 0.01:  # More than 1% move
                strength += 10
        
        # Factor 3: Age of order block - newer is stronger
        age = len(df) - index
        if age < 5:
            strength += 10
        elif age < 10:
            strength += 5
        elif age > 30:
            strength -= 10
        
        # Ensure strength is within 0-100 range
        return max(0, min(100, strength))
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify fair value gaps (FVG)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Fair value gaps with type, price range, and status
        """
        fair_value_gaps = []
        
        # We need at least 3 candles for FVG identification
        if len(df) < 3:
            logger.warning("Not enough data to identify fair value gaps")
            return fair_value_gaps
        
        # Look for bullish and bearish FVGs
        for i in range(1, len(df) - 1):
            # Bullish FVG: Low of current candle > High of previous candle
            if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
                # Calculate gap size
                gap_size = df['low'].iloc[i+1] - df['high'].iloc[i-1]
                gap_percentage = gap_size / df['close'].iloc[i-1] * 100
                
                # Only include significant gaps (at least 0.1%)
                if gap_percentage > 0.1:
                    # Check if gap has been filled
                    filled = False
                    for j in range(i+2, len(df)):
                        if df['low'].iloc[j] <= df['high'].iloc[i-1]:
                            filled = True
                            break
                    
                    fair_value_gaps.append({
                        'type': 'bullish',
                        'index': i,
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                        'top': df['low'].iloc[i+1],
                        'bottom': df['high'].iloc[i-1],
                        'size': gap_size,
                        'percentage': gap_percentage,
                        'filled': filled,
                        'age': len(df) - i - 1  # How many candles ago
                    })
            
            # Bearish FVG: High of current candle < Low of previous candle
            if df['high'].iloc[i+1] < df['low'].iloc[i-1]:
                # Calculate gap size
                gap_size = df['low'].iloc[i-1] - df['high'].iloc[i+1]
                gap_percentage = gap_size / df['close'].iloc[i-1] * 100
                
                # Only include significant gaps (at least 0.1%)
                if gap_percentage > 0.1:
                    # Check if gap has been filled
                    filled = False
                    for j in range(i+2, len(df)):
                        if df['high'].iloc[j] >= df['low'].iloc[i-1]:
                            filled = True
                            break
                    
                    fair_value_gaps.append({
                        'type': 'bearish',
                        'index': i,
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                        'top': df['low'].iloc[i-1],
                        'bottom': df['high'].iloc[i+1],
                        'size': gap_size,
                        'percentage': gap_percentage,
                        'filled': filled,
                        'age': len(df) - i - 1  # How many candles ago
                    })
        
        # Sort by age (ascending) and then by size (descending)
        fair_value_gaps.sort(key=lambda x: (x['age'], -x['size']))
        
        # Return unfilled gaps first, then filled gaps
        unfilled_gaps = [gap for gap in fair_value_gaps if not gap['filled']]
        filled_gaps = [gap for gap in fair_value_gaps if gap['filled']]
        
        # Return top 10 unfilled gaps and top 5 filled gaps
        return unfilled_gaps[:10] + filled_gaps[:5]
    
    def identify_liquidity_levels(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify liquidity levels (areas with stop losses)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Liquidity levels with type and price
        """
        liquidity_levels = []
        
        # We need at least 20 candles for reliable liquidity level identification
        if len(df) < 20:
            logger.warning("Not enough data to identify liquidity levels")
            return liquidity_levels
        
        # Identify swing highs and lows
        market_structure = self.identify_market_structure(df)
        swing_highs = market_structure['swing_highs']
        swing_lows = market_structure['swing_lows']
        
        # Liquidity above swing highs (stop losses from short positions)
        for high in swing_highs:
            # Calculate strength based on how many candles respected this level
            strength = self._calculate_liquidity_strength(df, high['price'], 'high')
            
            # Only include significant liquidity levels
            if strength > 30:
                liquidity_levels.append({
                    'type': 'high',
                    'price': high['price'] * 1.001,  # Slightly above swing high
                    'base_price': high['price'],
                    'strength': strength,
                    'index': high['index'],
                    'date': high['date']
                })
        
        # Liquidity below swing lows (stop losses from long positions)
        for low in swing_lows:
            # Calculate strength based on how many candles respected this level
            strength = self._calculate_liquidity_strength(df, low['price'], 'low')
            
            # Only include significant liquidity levels
            if strength > 30:
                liquidity_levels.append({
                    'type': 'low',
                    'price': low['price'] * 0.999,  # Slightly below swing low
                    'base_price': low['price'],
                    'strength': strength,
                    'index': low['index'],
                    'date': low['date']
                })
        
        # Sort by strength (descending)
        liquidity_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        # Return top 10 liquidity levels
        return liquidity_levels[:10]
    
    def _calculate_liquidity_strength(self, df: pd.DataFrame, price: float, level_type: str) -> int:
        """
        Calculate the strength of a liquidity level
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            price (float): Level price
            level_type (str): 'high' or 'low'
            
        Returns:
            int: Strength score (0-100)
        """
        strength = 50  # Base strength
        
        # Define price range for level (0.1% of price)
        price_range = price * 0.001
        
        # Count how many candles approached but didn't break the level
        approaches = 0
        for i in range(len(df)):
            if level_type == 'high':
                # Price approached but didn't break the level
                if abs(df['high'].iloc[i] - price) <= price_range and df['high'].iloc[i] <= price:
                    approaches += 1
            else:  # low
                # Price approached but didn't break the level
                if abs(df['low'].iloc[i] - price) <= price_range and df['low'].iloc[i] >= price:
                    approaches += 1
        
        # Adjust strength based on approaches
        strength += min(30, approaches * 3)
        
        # Factor: Recent approaches are more significant
        recent_approaches = 0
        for i in range(max(0, len(df) - 10), len(df)):
            if level_type == 'high':
                if abs(df['high'].iloc[i] - price) <= price_range and df['high'].iloc[i] <= price:
                    recent_approaches += 1
            else:  # low
                if abs(df['low'].iloc[i] - price) <= price_range and df['low'].iloc[i] >= price:
                    recent_approaches += 1
        
        strength += min(20, recent_approaches * 5)
        
        # Ensure strength is within 0-100 range
        return max(0, min(100, strength))
    
    def identify_order_flow(self, df: pd.DataFrame) -> Dict:
        """
        Identify order flow (OF) - buying/selling pressure
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            dict: Order flow analysis
        """
        # We need at least 20 candles for reliable order flow analysis
        if len(df) < 20:
            logger.warning("Not enough data to analyze order flow")
            return {'bias': 'neutral', 'strength': 0}
        
        # Calculate buying and selling pressure
        df['body_size'] = abs(df['close'] - df['open'])
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # Calculate volume-weighted pressure
        df['bull_pressure'] = df['body_size'] * df['volume'] * df['is_bullish']
        df['bear_pressure'] = df['body_size'] * df['volume'] * df['is_bearish']
        
        # Calculate recent pressure (last 10 candles)
        recent_bull_pressure = df['bull_pressure'].iloc[-10:].sum()
        recent_bear_pressure = df['bear_pressure'].iloc[-10:].sum()
        
        # Calculate overall pressure (last 30 candles)
        overall_bull_pressure = df['bull_pressure'].iloc[-30:].sum()
        overall_bear_pressure = df['bear_pressure'].iloc[-30:].sum()
        
        # Determine bias based on pressure ratio
        if recent_bull_pressure > recent_bear_pressure * 1.5:
            recent_bias = 'bullish'
            recent_strength = min(100, int((recent_bull_pressure / max(1, recent_bear_pressure) - 1) * 50))
        elif recent_bear_pressure > recent_bull_pressure * 1.5:
            recent_bias = 'bearish'
            recent_strength = min(100, int((recent_bear_pressure / max(1, recent_bull_pressure) - 1) * 50))
        else:
            recent_bias = 'neutral'
            recent_strength = 0
        
        if overall_bull_pressure > overall_bear_pressure * 1.3:
            overall_bias = 'bullish'
            overall_strength = min(100, int((overall_bull_pressure / max(1, overall_bear_pressure) - 1) * 30))
        elif overall_bear_pressure > overall_bull_pressure * 1.3:
            overall_bias = 'bearish'
            overall_strength = min(100, int((overall_bear_pressure / max(1, overall_bull_pressure) - 1) * 30))
        else:
            overall_bias = 'neutral'
            overall_strength = 0
        
        # Check for divergence between price and volume
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        volume_change = (df['volume'].iloc[-5:].mean() - df['volume'].iloc[-10:-5].mean()) / df['volume'].iloc[-10:-5].mean()
        
        # Positive divergence: Price down, but volume declining (bullish)
        positive_divergence = price_change < -0.01 and volume_change < -0.1
        
        # Negative divergence: Price up, but volume declining (bearish)
        negative_divergence = price_change > 0.01 and volume_change < -0.1
        
        # Return order flow analysis
        return {
            'recent_bias': recent_bias,
            'recent_strength': recent_strength,
            'overall_bias': overall_bias,
            'overall_strength': overall_strength,
            'positive_divergence': positive_divergence,
            'negative_divergence': negative_divergence,
            'bull_pressure': float(recent_bull_pressure),
            'bear_pressure': float(recent_bear_pressure)
        }
    
    def identify_liquidity_sweeps(self, df: pd.DataFrame, market_structure: Dict) -> List[Dict]:
        """
        Identify liquidity sweeps (price breaking a level then reversing)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            market_structure (dict): Market structure information
            
        Returns:
            list: Liquidity sweeps with type, price, and strength
        """
        liquidity_sweeps = []
        
        # We need at least 20 candles for reliable liquidity sweep identification
        if len(df) < 20:
            logger.warning("Not enough data to identify liquidity sweeps")
            return liquidity_sweeps
        
        # Get swing highs and lows
        swing_highs = market_structure.get('swing_highs', [])
        swing_lows = market_structure.get('swing_lows', [])
        
        # Look for high sweeps (price breaks above a swing high then reverses)
        for high in swing_highs:
            high_idx = high['index']
            high_price = high['price']
            
            # Look for candles that break above the swing high
            for i in range(high_idx + 1, min(high_idx + 20, len(df) - 2)):
                if df['high'].iloc[i] > high_price:
                    # Check if price reversed after the break
                    if df['close'].iloc[i+1] < df['open'].iloc[i+1] and df['low'].iloc[i+1] < df['low'].iloc[i]:
                        # Calculate sweep strength
                        sweep_strength = self._calculate_sweep_strength(df, i, high_price, 'high')
                        
                        # Only include significant sweeps
                        if sweep_strength > 30:
                            liquidity_sweeps.append({
                                'type': 'high_sweep',
                                'index': i,
                                'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                                'price': high_price,
                                'strength': sweep_strength,
                                'age': len(df) - i - 1  # How many candles ago
                            })
                        break
        
        # Look for low sweeps (price breaks below a swing low then reverses)
        for low in swing_lows:
            low_idx = low['index']
            low_price = low['price']
            
            # Look for candles that break below the swing low
            for i in range(low_idx + 1, min(low_idx + 20, len(df) - 2)):
                if df['low'].iloc[i] < low_price:
                    # Check if price reversed after the break
                    if df['close'].iloc[i+1] > df['open'].iloc[i+1] and df['high'].iloc[i+1] > df['high'].iloc[i]:
                        # Calculate sweep strength
                        sweep_strength = self._calculate_sweep_strength(df, i, low_price, 'low')
                        
                        # Only include significant sweeps
                        if sweep_strength > 30:
                            liquidity_sweeps.append({
                                'type': 'low_sweep',
                                'index': i,
                                'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                                'price': low_price,
                                'strength': sweep_strength,
                                'age': len(df) - i - 1  # How many candles ago
                            })
                        break
        
        # Sort by age (ascending)
        liquidity_sweeps.sort(key=lambda x: x['age'])
        
        return liquidity_sweeps
    
    def _calculate_sweep_strength(self, df: pd.DataFrame, index: int, level_price: float, sweep_type: str) -> int:
        """
        Calculate the strength of a liquidity sweep
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            index (int): Index of the sweep candle
            level_price (float): Price level that was swept
            sweep_type (str): 'high' or 'low'
            
        Returns:
            int: Strength score (0-100)
        """
        strength = 50  # Base strength
        
        # Factor 1: Volume - higher volume means stronger sweep
        avg_volume = df['volume'].iloc[max(0, index-10):index].mean()
        if df['volume'].iloc[index] > 2 * avg_volume:
            strength += 20
        elif df['volume'].iloc[index] > avg_volume:
            strength += 10
        
        # Factor 2: Reversal strength - stronger if price reversed significantly
        if sweep_type == 'high':
            # Calculate how far price reversed after the sweep
            if index + 3 < len(df):
                reversal_size = (df['high'].iloc[index] - df['low'].iloc[index+1:index+4].min()) / df['close'].iloc[index]
                if reversal_size > 0.01:  # More than 1% reversal
                    strength += 20
                elif reversal_size > 0.005:  # More than 0.5% reversal
                    strength += 10
        else:  # low sweep
            # Calculate how far price reversed after the sweep
            if index + 3 < len(df):
                reversal_size = (df['high'].iloc[index+1:index+4].max() - df['low'].iloc[index]) / df['close'].iloc[index]
                if reversal_size > 0.01:  # More than 1% reversal
                    strength += 20
                elif reversal_size > 0.005:  # More than 0.5% reversal
                    strength += 10
        
        # Factor 3: Age of sweep - newer is stronger
        age = len(df) - index
        if age < 5:
            strength += 10
        elif age < 10:
            strength += 5
        elif age > 30:
            strength -= 10
        
        # Ensure strength is within 0-100 range
        return max(0, min(100, strength))
    
    def find_trade_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find potential trade setups based on SMC analysis
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Trade setups with entry, stop loss, take profit, and reason
        """
        trade_setups = []
        
        # We need at least 50 candles for reliable trade setup identification
        if len(df) < 50:
            logger.warning("Not enough data to identify trade setups")
            return trade_setups
        
        # Perform SMC analysis
        market_structure = self.identify_market_structure(df)
        order_blocks = self.identify_order_blocks(df)
        fair_value_gaps = self.identify_fair_value_gaps(df)
        liquidity_levels = self.identify_liquidity_levels(df)
        order_flow = self.identify_order_flow(df)
        liquidity_sweeps = self.identify_liquidity_sweeps(df, market_structure)
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        # Setup 1: Order Block + Fair Value Gap + Favorable Order Flow
        for ob in order_blocks:
            # Only consider recent order blocks (less than 20 candles old)
            if ob['age'] > 20:
                continue
            
            # For bullish setups
            if ob['type'] == 'bullish' and order_flow['recent_bias'] == 'bullish':
                # Find a fair value gap above the order block
                for fvg in fair_value_gaps:
                    if fvg['type'] == 'bullish' and not fvg['filled'] and fvg['bottom'] > ob['top']:
                        # Find a liquidity level above for take profit
                        take_profit = None
                        for liq in liquidity_levels:
                            if liq['type'] == 'high' and liq['price'] > current_price:
                                take_profit = liq['price']
                                break
                        
                        # If no liquidity level found, use a default R:R of 3:1
                        if not take_profit:
                            stop_loss = ob['bottom']
                            risk = current_price - stop_loss
                            take_profit = current_price + (risk * 3)
                        else:
                            stop_loss = ob['bottom']
                        
                        # Calculate risk-reward ratio
                        risk = current_price - stop_loss
                        reward = take_profit - current_price
                        risk_reward = reward / risk if risk > 0 else 0
                        
                        # Only include setups with good R:R
                        if risk_reward >= 2:
                            trade_setups.append({
                                'type': 'buy',
                                'entry': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'risk_reward': risk_reward,
                                'reason': f"Bullish order block at {ob['bottom']:.5f} with fair value gap above and bullish order flow",
                                'strength': (ob['strength'] + order_flow['recent_strength']) / 2
                            })
            
            # For bearish setups
            elif ob['type'] == 'bearish' and order_flow['recent_bias'] == 'bearish':
                # Find a fair value gap below the order block
                for fvg in fair_value_gaps:
                    if fvg['type'] == 'bearish' and not fvg['filled'] and fvg['top'] < ob['bottom']:
                        # Find a liquidity level below for take profit
                        take_profit = None
                        for liq in liquidity_levels:
                            if liq['type'] == 'low' and liq['price'] < current_price:
                                take_profit = liq['price']
                                break
                        
                        # If no liquidity level found, use a default R:R of 3:1
                        if not take_profit:
                            stop_loss = ob['top']
                            risk = stop_loss - current_price
                            take_profit = current_price - (risk * 3)
                        else:
                            stop_loss = ob['top']
                        
                        # Calculate risk-reward ratio
                        risk = stop_loss - current_price
                        reward = current_price - take_profit
                        risk_reward = reward / risk if risk > 0 else 0
                        
                        # Only include setups with good R:R
                        if risk_reward >= 2:
                            trade_setups.append({
                                'type': 'sell',
                                'entry': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'risk_reward': risk_reward,
                                'reason': f"Bearish order block at {ob['top']:.5f} with fair value gap below and bearish order flow",
                                'strength': (ob['strength'] + order_flow['recent_strength']) / 2
                            })
        
        # Setup 2: Liquidity Sweep + Order Block
        for sweep in liquidity_sweeps:
            # Only consider recent sweeps (less than 10 candles old)
            if sweep['age'] > 10:
                continue
            
            # For bullish setups (low sweep)
            if sweep['type'] == 'low_sweep':
                # Find a bullish order block near the sweep
                for ob in order_blocks:
                    if ob['type'] == 'bullish' and abs(ob['index'] - sweep['index']) <= 5:
                        # Find a liquidity level above for take profit
                        take_profit = None
                        for liq in liquidity_levels:
                            if liq['type'] == 'high' and liq['price'] > current_price:
                                take_profit = liq['price']
                                break
                        
                        # If no liquidity level found, use a default R:R of 3:1
                        if not take_profit:
                            stop_loss = min(sweep['price'] * 0.998, ob['bottom'])  # Just below the sweep or OB
                            risk = current_price - stop_loss
                            take_profit = current_price + (risk * 3)
                        else:
                            stop_loss = min(sweep['price'] * 0.998, ob['bottom'])
                        
                        # Calculate risk-reward ratio
                        risk = current_price - stop_loss
                        reward = take_profit - current_price
                        risk_reward = reward / risk if risk > 0 else 0
                        
                        # Only include setups with good R:R
                        if risk_reward >= 2:
                            trade_setups.append({
                                'type': 'buy',
                                'entry': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'risk_reward': risk_reward,
                                'reason': f"Bullish setup: Liquidity sweep at {sweep['price']:.5f} with bullish order block",
                                'strength': (sweep['strength'] + ob['strength']) / 2
                            })
            
            # For bearish setups (high sweep)
            elif sweep['type'] == 'high_sweep':
                # Find a bearish order block near the sweep
                for ob in order_blocks:
                    if ob['type'] == 'bearish' and abs(ob['index'] - sweep['index']) <= 5:
                        # Find a liquidity level below for take profit
                        take_profit = None
                        for liq in liquidity_levels:
                            if liq['type'] == 'low' and liq['price'] < current_price:
                                take_profit = liq['price']
                                break
                        
                        # If no liquidity level found, use a default R:R of 3:1
                        if not take_profit:
                            stop_loss = max(sweep['price'] * 1.002, ob['top'])  # Just above the sweep or OB
                            risk = stop_loss - current_price
                            take_profit = current_price - (risk * 3)
                        else:
                            stop_loss = max(sweep['price'] * 1.002, ob['top'])
                        
                        # Calculate risk-reward ratio
                        risk = stop_loss - current_price
                        reward = current_price - take_profit
                        risk_reward = reward / risk if risk > 0 else 0
                        
                        # Only include setups with good R:R
                        if risk_reward >= 2:
                            trade_setups.append({
                                'type': 'sell',
                                'entry': current_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'risk_reward': risk_reward,
                                'reason': f"Bearish setup: Liquidity sweep at {sweep['price']:.5f} with bearish order block",
                                'strength': (sweep['strength'] + ob['strength']) / 2
                            })
        
        # Setup 3: Market Structure Break + Order Flow
        hh_hl_ll_lh = market_structure.get('hh_hl_ll_lh', {})
        
        # Bullish market structure break (higher low after lower high)
        higher_lows = hh_hl_ll_lh.get('higher_lows', [])
        lower_highs = hh_hl_ll_lh.get('lower_highs', [])
        
        if higher_lows and lower_highs:
            latest_hl = higher_lows[-1]
            latest_lh = lower_highs[-1]
            
            # Check if we have a higher low after a lower high (potential bullish break)
            if latest_hl['index'] > latest_lh['index'] and order_flow['recent_bias'] == 'bullish':
                # Find a liquidity level above for take profit
                take_profit = None
                for liq in liquidity_levels:
                    if liq['type'] == 'high' and liq['price'] > current_price:
                        take_profit = liq['price']
                        break
                
                # If no liquidity level found, use a default R:R of 3:1
                if not take_profit:
                    stop_loss = latest_hl['price'] * 0.998  # Just below the higher low
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * 3)
                else:
                    stop_loss = latest_hl['price'] * 0.998
                
                # Calculate risk-reward ratio
                risk = current_price - stop_loss
                reward = take_profit - current_price
                risk_reward = reward / risk if risk > 0 else 0
                
                # Only include setups with good R:R
                if risk_reward >= 2:
                    trade_setups.append({
                        'type': 'buy',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'reason': f"Bullish market structure break: Higher low at {latest_hl['price']:.5f} after lower high with bullish order flow",
                        'strength': 70  # Market structure breaks are strong signals
                    })
        
        # Bearish market structure break (lower high after higher low)
        higher_highs = hh_hl_ll_lh.get('higher_highs', [])
        lower_lows = hh_hl_ll_lh.get('lower_lows', [])
        
        if higher_highs and lower_lows:
            latest_hh = higher_highs[-1]
            latest_ll = lower_lows[-1]
            
            # Check if we have a lower high after a higher high (potential bearish break)
            if latest_ll['index'] > latest_hh['index'] and order_flow['recent_bias'] == 'bearish':
                # Find a liquidity level below for take profit
                take_profit = None
                for liq in liquidity_levels:
                    if liq['type'] == 'low' and liq['price'] < current_price:
                        take_profit = liq['price']
                        break
                
                # If no liquidity level found, use a default R:R of 3:1
                if not take_profit:
                    stop_loss = latest_ll['price'] * 1.002  # Just above the lower low
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * 3)
                else:
                    stop_loss = latest_ll['price'] * 1.002
                
                # Calculate risk-reward ratio
                risk = stop_loss - current_price
                reward = current_price - take_profit
                risk_reward = reward / risk if risk > 0 else 0
                
                # Only include setups with good R:R
                if risk_reward >= 2:
                    trade_setups.append({
                        'type': 'sell',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'reason': f"Bearish market structure break: Lower low at {latest_ll['price']:.5f} after higher high with bearish order flow",
                        'strength': 70  # Market structure breaks are strong signals
                    })
        
        # Sort trade setups by strength (descending)
        trade_setups.sort(key=lambda x: x['strength'], reverse=True)
        
        # Return top 3 trade setups
        return trade_setups[:3]
    
    def multi_timeframe_analysis(self, dfs: Dict[str, pd.DataFrame], symbol: str) -> Dict:
        """
        Perform multi-timeframe SMC analysis
        
        Args:
            dfs (dict): Dictionary of dataframes for different timeframes
            symbol (str): Trading symbol
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        mtf_analysis = {}
        
        # Analyze each timeframe
        for timeframe, df in dfs.items():
            mtf_analysis[timeframe] = self.analyze_chart(df, symbol)
        
        # Determine overall bias based on higher timeframes
        timeframe_weights = {
            '1d': 5,
            '4h': 4,
            '1h': 3,
            '30m': 2,
            '15m': 1,
            '5m': 0.5,
            '1m': 0.2
        }
        
        # Calculate weighted bias
        bullish_score = 0
        bearish_score = 0
        total_weight = 0
        
        for timeframe, analysis in mtf_analysis.items():
            weight = timeframe_weights.get(timeframe, 1)
            total_weight += weight
            
            if analysis.get('bias') == 'bullish':
                bullish_score += weight
            elif analysis.get('bias') == 'bearish':
                bearish_score += weight
        
        # Determine overall bias
        if total_weight > 0:
            if bullish_score > bearish_score * 1.5:
                overall_bias = 'bullish'
                bias_strength = int(min(100, (bullish_score / total_weight) * 100))
            elif bearish_score > bullish_score * 1.5:
                overall_bias = 'bearish'
                bias_strength = int(min(100, (bearish_score / total_weight) * 100))
            else:
                overall_bias = 'neutral'
                bias_strength = int(min(100, (max(bullish_score, bearish_score) / total_weight) * 50))
        else:
            overall_bias = 'neutral'
            bias_strength = 0
        
        # Find trade setups across timeframes
        all_setups = []
        for timeframe, analysis in mtf_analysis.items():
            setups = analysis.get('trade_setups', [])
            for setup in setups:
                setup['timeframe'] = timeframe
                all_setups.append(setup)
        
        # Sort by risk-reward ratio (descending)
        all_setups.sort(key=lambda x: x['risk_reward'], reverse=True)
        
        # Return multi-timeframe analysis
        return {
            'symbol': symbol,
            'overall_bias': overall_bias,
            'bias_strength': bias_strength,
            'timeframes': mtf_analysis,
            'trade_setups': all_setups[:5]  # Top 5 setups across all timeframes
        }
    
    def identify_ict_concepts(self, df: pd.DataFrame) -> Dict:
        """
        Identify ICT (Inner Circle Trader) concepts
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            dict: ICT concepts
        """
        ict_concepts = {}
        
        # We need at least 50 candles for reliable ICT concept identification
        if len(df) < 50:
            logger.warning("Not enough data to identify ICT concepts")
            return ict_concepts
        
        # Identify optimal trade entry (OTE)
        ote_zones = self._identify_ote_zones(df)
        ict_concepts['ote_zones'] = ote_zones
        
        # Identify breaker blocks (similar to order blocks but with specific criteria)
        breaker_blocks = self._identify_breaker_blocks(df)
        ict_concepts['breaker_blocks'] = breaker_blocks
        
        # Identify fair value gaps (already implemented in identify_fair_value_gaps)
        fair_value_gaps = self.identify_fair_value_gaps(df)
        ict_concepts['fair_value_gaps'] = fair_value_gaps
        
        # Identify market structure (already implemented in identify_market_structure)
        market_structure = self.identify_market_structure(df)
        ict_concepts['market_structure'] = market_structure
        
        # Identify kill zones (London and New York sessions)
        kill_zones = self._identify_kill_zones(df)
        ict_concepts['kill_zones'] = kill_zones
        
        return ict_concepts
    
    def _identify_ote_zones(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify Optimal Trade Entry (OTE) zones
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: OTE zones
        """
        ote_zones = []
        
        # Identify swing highs and lows
        market_structure = self.identify_market_structure(df)
        swing_highs = market_structure['swing_highs']
        swing_lows = market_structure['swing_lows']
        
        # Calculate 50% and 61.8% retracement levels for swings
        for i in range(1, len(swing_highs)):
            # For bearish moves (high to low)
            if i < len(swing_lows):
                high = swing_highs[i-1]['price']
                low = swing_lows[i]['price']
                
                # Calculate retracement levels
                range_size = high - low
                level_50 = low + range_size * 0.5
                level_618 = low + range_size * 0.618
                
                # Add OTE zone
                ote_zones.append({
                    'type': 'bullish',
                    'top': level_618,
                    'bottom': level_50,
                    'high_index': swing_highs[i-1]['index'],
                    'low_index': swing_lows[i]['index'],
                    'strength': 70
                })
        
        for i in range(1, len(swing_lows)):
            # For bullish moves (low to high)
            if i < len(swing_highs):
                low = swing_lows[i-1]['price']
                high = swing_highs[i]['price']
                
                # Calculate retracement levels
                range_size = high - low
                level_50 = high - range_size * 0.5
                level_618 = high - range_size * 0.618
                
                # Add OTE zone
                ote_zones.append({
                    'type': 'bearish',
                    'top': level_50,
                    'bottom': level_618,
                    'low_index': swing_lows[i-1]['index'],
                    'high_index': swing_highs[i]['index'],
                    'strength': 70
                })
        
        return ote_zones
    
    def _identify_breaker_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify breaker blocks (ICT concept)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            list: Breaker blocks
        """
        breaker_blocks = []
        
        # We need at least 20 candles for reliable breaker block identification
        if len(df) < 20:
            logger.warning("Not enough data to identify breaker blocks")
            return breaker_blocks
        
        # Look for bullish and bearish breaker blocks
        for i in range(3, len(df) - 5):
            # Bullish Breaker Block: 
            # A bearish candle that is later broken by price, then price continues higher
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # Bearish candle
                df['high'].iloc[i+1:i+6].max() > df['high'].iloc[i] and  # Price breaks above
                df['close'].iloc[i+5] > df['high'].iloc[i]):  # Price continues higher
                
                # Calculate strength based on volume and subsequent price movement
                strength = 60  # Base strength for breaker blocks
                
                breaker_blocks.append({
                    'type': 'bullish',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i],
                    'strength': strength,
                    'age': len(df) - i - 1  # How many candles ago
                })
            
            # Bearish Breaker Block: 
            # A bullish candle that is later broken by price, then price continues lower
            if (df['close'].iloc[i] > df['open'].iloc[i] and  # Bullish candle
                df['low'].iloc[i+1:i+6].min() < df['low'].iloc[i] and  # Price breaks below
                df['close'].iloc[i+5] < df['low'].iloc[i]):  # Price continues lower
                
                # Calculate strength based on volume and subsequent price movement
                strength = 60  # Base strength for breaker blocks
                
                breaker_blocks.append({
                    'type': 'bearish',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i],
                    'strength': strength,
                    'age': len(df) - i - 1  # How many candles ago
                })
        
        # Sort by age (ascending)
        breaker_blocks.sort(key=lambda x: x['age'])
        
        return breaker_blocks
    
    def _identify_kill_zones(self, df: pd.DataFrame) -> Dict:
        """
        Identify kill zones (London and New York sessions)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            dict: Kill zones analysis
        """
        # Check if index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("DataFrame index is not DatetimeIndex, cannot identify kill zones")
            return {'london': [], 'new_york': []}
        
        london_candles = []
        new_york_candles = []
        
        # London session: 8:00-16:00 GMT (approximately)
        # New York session: 13:00-21:00 GMT (approximately)
        
        for i in range(len(df)):
            hour = df.index[i].hour
            
            # London session
            if 8 <= hour < 16:
                london_candles.append(i)
            
            # New York session
            if 13 <= hour < 21:
                new_york_candles.append(i)
        
        # Analyze price action during kill zones
        london_analysis = self._analyze_session_price_action(df, london_candles)
        new_york_analysis = self._analyze_session_price_action(df, new_york_candles)
        
        return {
            'london': london_analysis,
            'new_york': new_york_analysis
        }
    
    def _analyze_session_price_action(self, df: pd.DataFrame, session_candles: List[int]) -> Dict:
        """
        Analyze price action during a trading session
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            session_candles (list): Indices of candles in the session
            
        Returns:
            dict: Session price action analysis
        """
        if not session_candles:
            return {'bias': 'neutral', 'strength': 0}
        
        # Get recent session candles (last 5 days)
        recent_days = min(5, len(session_candles) // 8)  # Assuming 8 candles per session on average
        recent_session_candles = session_candles[-recent_days * 8:]
        
        if not recent_session_candles:
            return {'bias': 'neutral', 'strength': 0}
        
        # Calculate bullish vs bearish candles
        bullish_candles = 0
        bearish_candles = 0
        
        for i in recent_session_candles:
            if i < len(df):
                if df['close'].iloc[i] > df['open'].iloc[i]:
                    bullish_candles += 1
                elif df['close'].iloc[i] < df['open'].iloc[i]:
                    bearish_candles += 1
        
        # Calculate average range during session
        session_ranges = []
        for i in recent_session_candles:
            if i < len(df):
                candle_range = (df['high'].iloc[i] - df['low'].iloc[i]) / df['low'].iloc[i] * 100  # Range in percentage
                session_ranges.append(candle_range)
        
        avg_range = sum(session_ranges) / len(session_ranges) if session_ranges else 0
        
        # Determine session bias
        if bullish_candles > bearish_candles * 1.5:
            bias = 'bullish'
            strength = min(100, int((bullish_candles / (bullish_candles + bearish_candles)) * 100))
        elif bearish_candles > bullish_candles * 1.5:
            bias = 'bearish'
            strength = min(100, int((bearish_candles / (bullish_candles + bearish_candles)) * 100))
        else:
            bias = 'neutral'
            strength = 50
        
        return {
            'bias': bias,
            'strength': strength,
            'avg_range': avg_range,
            'bullish_candles': bullish_candles,
            'bearish_candles': bearish_candles
        }

    def _identify_optimal_take_profit_levels(self, df: pd.DataFrame, current_price: float, direction: str) -> List[Dict]:
        """
        Identify optimal take profit levels based on market structure
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            current_price (float): Current price
            direction (str): 'bullish' or 'bearish'
            
        Returns:
            list: Potential take profit levels with prices and strengths
        """
        take_profit_levels = []
        
        # Get market structure components
        market_structure = self.identify_market_structure(df)
        swing_highs = market_structure.get('swing_highs', [])
        swing_lows = market_structure.get('swing_lows', [])
        
        # Get key levels
        key_levels = self.identify_key_levels(df)
        
        # Get liquidity levels
        liquidity_levels = self.identify_liquidity_levels(df)
        
        # Get fair value gaps
        fair_value_gaps = self.identify_fair_value_gaps(df)
        
        # For bullish direction (looking for resistance levels above current price)
        if direction == 'bullish':
            # 1. Previous swing highs
            for high in swing_highs:
                if high['price'] > current_price:
                    distance_pct = (high['price'] - current_price) / current_price * 100
                    # Only consider levels within reasonable distance (not too close, not too far)
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': high['price'],
                            'type': 'swing_high',
                            'strength': 80,  # Swing highs are strong resistance
                            'distance_pct': distance_pct
                        })
            
            # 2. Liquidity levels (high)
            for level in liquidity_levels:
                if level['type'] == 'high' and level['price'] > current_price:
                    distance_pct = (level['price'] - current_price) / current_price * 100
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': level['price'],
                            'type': 'liquidity_high',
                            'strength': level.get('strength', 60),
                            'distance_pct': distance_pct
                        })
            
            # 3. Fair value gaps (top of bullish gaps)
            for fvg in fair_value_gaps:
                if fvg['type'] == 'bullish' and fvg['top'] > current_price:
                    distance_pct = (fvg['top'] - current_price) / current_price * 100
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': fvg['top'],
                            'type': 'fvg_top',
                            'strength': 70,
                            'distance_pct': distance_pct
                        })
                    
                    # Also consider 50% of the FVG
                    mid_point = (fvg['top'] + fvg['bottom']) / 2
                    if mid_point > current_price:
                        distance_pct = (mid_point - current_price) / current_price * 100
                        if 0.5 < distance_pct < 15:
                            take_profit_levels.append({
                                'price': mid_point,
                                'type': 'fvg_midpoint',
                                'strength': 50,
                                'distance_pct': distance_pct
                            })
            
            # 4. Psychological levels
            current_price_magnitude = 10 ** (len(str(int(current_price))) - 1)
            for i in range(1, 11):
                psych_level = ((int(current_price / current_price_magnitude) + i) * current_price_magnitude)
                distance_pct = (psych_level - current_price) / current_price * 100
                if 0.5 < distance_pct < 15:
                    take_profit_levels.append({
                        'price': psych_level,
                        'type': 'psychological',
                        'strength': 40,
                        'distance_pct': distance_pct
                    })
        
        # For bearish direction (looking for support levels below current price)
        else:
            # 1. Previous swing lows
            for low in swing_lows:
                if low['price'] < current_price:
                    distance_pct = (current_price - low['price']) / current_price * 100
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': low['price'],
                            'type': 'swing_low',
                            'strength': 80,  # Swing lows are strong support
                            'distance_pct': distance_pct
                        })
            
            # 2. Liquidity levels (low)
            for level in liquidity_levels:
                if level['type'] == 'low' and level['price'] < current_price:
                    distance_pct = (current_price - level['price']) / current_price * 100
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': level['price'],
                            'type': 'liquidity_low',
                            'strength': level.get('strength', 60),
                            'distance_pct': distance_pct
                        })
            
            # 3. Fair value gaps (bottom of bearish gaps)
            for fvg in fair_value_gaps:
                if fvg['type'] == 'bearish' and fvg['bottom'] < current_price:
                    distance_pct = (current_price - fvg['bottom']) / current_price * 100
                    if 0.5 < distance_pct < 15:
                        take_profit_levels.append({
                            'price': fvg['bottom'],
                            'type': 'fvg_bottom',
                            'strength': 70,
                            'distance_pct': distance_pct
                        })
                    
                    # Also consider 50% of the FVG
                    mid_point = (fvg['top'] + fvg['bottom']) / 2
                    if mid_point < current_price:
                        distance_pct = (current_price - mid_point) / current_price * 100
                        if 0.5 < distance_pct < 15:
                            take_profit_levels.append({
                                'price': mid_point,
                                'type': 'fvg_midpoint',
                                'strength': 50,
                                'distance_pct': distance_pct
                            })
            
            # 4. Psychological levels
            current_price_magnitude = 10 ** (len(str(int(current_price))) - 1)
            for i in range(1, 11):
                psych_level = ((int(current_price / current_price_magnitude) - i) * current_price_magnitude)
                if psych_level <= 0:
                    continue
                distance_pct = (current_price - psych_level) / current_price * 100
                if 0.5 < distance_pct < 15:
                    take_profit_levels.append({
                        'price': psych_level,
                        'type': 'psychological',
                        'strength': 40,
                        'distance_pct': distance_pct
                    })
        
        # Sort by strength (descending)
        take_profit_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return take_profit_levels

    def find_optimal_take_profit(self, df: pd.DataFrame, entry_price: float, stop_loss: float, 
                                direction: str, min_rr: float = 3.0) -> Tuple[float, float]:
        """
        Find optimal take profit level based on market structure and minimum risk-reward
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            direction (str): 'buy' or 'sell'
            min_rr (float): Minimum risk-reward ratio
            
        Returns:
            tuple: (take_profit_price, risk_reward_ratio)
        """
        # Handle case where df is None
        if df is None:
            # Calculate a simple take profit based on risk-reward
            risk = abs(entry_price - stop_loss)
            if direction.lower() in ['buy', 'long']:
                take_profit = entry_price + (risk * min_rr)
            else:
                take_profit = entry_price - (risk * min_rr)
            return take_profit, min_rr
        
        # Calculate risk in price points
        if direction.lower() == 'buy':
            risk = abs(entry_price - stop_loss)
            min_reward = risk * min_rr
            min_tp_price = entry_price + min_reward
            tp_direction = 'bullish'
        else:  # sell
            risk = abs(stop_loss - entry_price)
            min_reward = risk * min_rr
            min_tp_price = entry_price - min_reward
            tp_direction = 'bearish'
        
        # Get potential take profit levels
        tp_levels = self._identify_optimal_take_profit_levels(df, entry_price, tp_direction)
        
        # Filter levels that provide at least the minimum risk-reward
        valid_tp_levels = []
        for level in tp_levels:
            if direction.lower() == 'buy':
                if level['price'] >= min_tp_price:
                    reward = level['price'] - entry_price
                    rr = reward / risk
                    valid_tp_levels.append({
                        'price': level['price'],
                        'type': level['type'],
                        'strength': level['strength'],
                        'risk_reward': rr
                    })
            else:  # sell
                if level['price'] <= min_tp_price:
                    reward = entry_price - level['price']
                    rr = reward / risk
                    valid_tp_levels.append({
                        'price': level['price'],
                        'type': level['type'],
                        'strength': level['strength'],
                        'risk_reward': rr
                    })
        
        # If we have valid levels, choose the best one based on strength and R:R
        if valid_tp_levels:
            # Sort by a combination of strength and R:R
            valid_tp_levels.sort(key=lambda x: (x['strength'] * 0.7 + (x['risk_reward'] / min_rr) * 30), reverse=True)
            best_level = valid_tp_levels[0]
            return best_level['price'], best_level['risk_reward']
        
        # If no valid levels found, use the minimum R:R
        if direction.lower() == 'buy':
            take_profit = entry_price + (risk * min_rr)
        else:  # sell
            take_profit = entry_price - (risk * min_rr)
        
        return take_profit, min_rr
