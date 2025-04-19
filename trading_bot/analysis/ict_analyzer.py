"""
ICT (Inner Circle Trader) analysis module
Implements key ICT concepts for market analysis
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

class ICTAnalyzer:
    """
    Analyzer for ICT (Inner Circle Trader) concepts
    Implements methods to identify ICT patterns and setups
    """
    
    def __init__(self):
        """Initialize the ICT analyzer"""
        self.fibonacci_levels = {
            'start': 1.0,
            'ote_level1': 0.62,
            'ote_level2': 0.705,
            'ote_level3': 0.79,
            'equilibrium': 0.5,
            'end': 0.0,
            'target1': -0.5,
            'target2': -1.0,
            'symmetrical': -2.0
        }
    
    def analyze(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        Perform comprehensive ICT analysis on price data
        
        Args:
            df (pd.DataFrame): OHLCV data with columns [open, high, low, close, volume]
            symbol (str, optional): Symbol being analyzed
            
        Returns:
            dict: Analysis results containing all ICT concepts
        """
        if df.empty or len(df) < 50:
            logger.warning(f"Not enough data for ICT analysis: {len(df)} bars")
            return {'error': 'Not enough data for analysis'}
        
        # Make a copy to avoid modifying the original dataframe
        df = df.copy()
        
        # Ensure we have all required columns
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns for ICT analysis. Available: {df.columns}")
            return {'error': 'Missing required columns'}
        
        # Get market structure
        market_structure = self.analyze_market_structure(df)
        
        # Get daily bias
        daily_bias = self.determine_daily_bias(df)
        
        # Identify key ICT concepts
        inducement_zones = self.identify_inducement(df, market_structure)
        bos_zones = self.identify_break_of_structure(df, market_structure)
        choch_zones = self.identify_change_of_character(df, market_structure)
        ote_zones = self.identify_optimal_trade_entry(df, daily_bias)
        liquidity_levels = self.identify_liquidity_levels(df)
        fair_value_gaps = self.identify_fair_value_gaps(df)
        order_blocks = self.identify_order_blocks(df)
        breaker_blocks = self.identify_breaker_blocks(df, order_blocks)
        
        # Identify session-based setups
        kill_zones = self.identify_kill_zones(df)
        
        # Combine all analysis
        analysis = {
            'symbol': symbol,
            'market_structure': market_structure,
            'daily_bias': daily_bias,
            'inducement_zones': inducement_zones,
            'bos_zones': bos_zones,
            'choch_zones': choch_zones,
            'ote_zones': ote_zones,
            'liquidity_levels': liquidity_levels,
            'fair_value_gaps': fair_value_gaps,
            'order_blocks': order_blocks,
            'breaker_blocks': breaker_blocks,
            'kill_zones': kill_zones
        }
        
        return analysis
    
    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        Analyze market structure to identify trend and key levels
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            dict: Market structure analysis
        """
        # Identify swing highs and lows
        swing_highs, swing_lows = self._find_swing_points(df)
        
        # Determine trend based on swing points
        trend = self._determine_trend(df, swing_highs, swing_lows)
        
        # Find displacement moves
        displacement_moves = self._find_displacement_moves(df)
        
        # Identify market structure shifts
        structure_shifts = self._identify_market_structure_shifts(df, swing_highs, swing_lows)
        
        return {
            'trend': trend,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'displacement_moves': displacement_moves,
            'structure_shifts': structure_shifts
        }
    
    def determine_daily_bias(self, df: pd.DataFrame) -> Dict:
        """
        Determine the daily bias (bullish, bearish, or neutral)
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            dict: Daily bias information
        """
        # Get the most recent structure shift
        market_structure = self.analyze_market_structure(df)
        structure_shifts = market_structure['structure_shifts']
        
        if not structure_shifts:
            # If no structure shifts, use trend
            bias_direction = market_structure['trend']
            confidence = 50  # Medium confidence
        else:
            # Sort by recency (highest index is most recent)
            recent_shift = sorted(structure_shifts, key=lambda x: x['index'])[-1]
            bias_direction = recent_shift['direction']
            
            # Calculate confidence based on strength of the shift
            shift_strength = recent_shift.get('strength', 50)
            recency_factor = 1.0 - (len(df) - recent_shift['index']) / len(df)
            confidence = int(shift_strength * (0.5 + 0.5 * recency_factor))
        
        # Check if we're in a discount or premium zone
        current_price = df['close'].iloc[-1]
        recent_high = df['high'].max()
        recent_low = df['low'].min()
        price_range = recent_high - recent_low
        
        if price_range > 0:
            relative_position = (current_price - recent_low) / price_range
            zone = 'premium' if relative_position > 0.5 else 'discount'
        else:
            zone = 'neutral'
        
        return {
            'direction': bias_direction,
            'confidence': confidence,
            'zone': zone,
            'price': current_price
        }
    
    def identify_inducement(self, df: pd.DataFrame, market_structure: Dict) -> List[Dict]:
        """
        Identify inducement zones based on market structure
        
        Args:
            df (pd.DataFrame): OHLCV data
            market_structure (dict): Market structure analysis
            
        Returns:
            list: Inducement zones
        """
        inducement_zones = []
        swing_highs = market_structure['swing_highs']
        swing_lows = market_structure['swing_lows']
        structure_shifts = market_structure['structure_shifts']
        
        # For each structure shift, find the inducement that preceded it
        for shift in structure_shifts:
            shift_index = shift['index']
            shift_direction = shift['direction']
            
            if shift_direction == 'bullish':
                # For bullish shifts, look for the valid pullback before the shift
                # This would be a bearish move that was later invalidated
                for i, low in enumerate(swing_lows):
                    if low['index'] < shift_index:
                        # Check if this low was followed by a higher low before the shift
                        for j in range(i+1, len(swing_lows)):
                            if swing_lows[j]['index'] < shift_index and swing_lows[j]['value'] > low['value']:
                                # This is a potential inducement
                                inducement_zones.append({
                                    'type': 'bullish',
                                    'start_index': low['index'] - 3,  # Include a few bars before
                                    'end_index': low['index'] + 3,    # Include a few bars after
                                    'price': low['value'],
                                    'strength': self._calculate_inducement_strength(df, low['index'], shift_index),
                                    'related_shift': shift_index
                                })
                                break
            
            elif shift_direction == 'bearish':
                # For bearish shifts, look for the valid pullback before the shift
                # This would be a bullish move that was later invalidated
                for i, high in enumerate(swing_highs):
                    if high['index'] < shift_index:
                        # Check if this high was followed by a lower high before the shift
                        for j in range(i+1, len(swing_highs)):
                            if swing_highs[j]['index'] < shift_index and swing_highs[j]['value'] < high['value']:
                                # This is a potential inducement
                                inducement_zones.append({
                                    'type': 'bearish',
                                    'start_index': high['index'] - 3,  # Include a few bars before
                                    'end_index': high['index'] + 3,    # Include a few bars after
                                    'price': high['value'],
                                    'strength': self._calculate_inducement_strength(df, high['index'], shift_index),
                                    'related_shift': shift_index
                                })
                                break
        
        return inducement_zones
    
    def identify_break_of_structure(self, df: pd.DataFrame, market_structure: Dict) -> List[Dict]:
        """
        Identify break of structure (BOS) zones
        
        Args:
            df (pd.DataFrame): OHLCV data
            market_structure (dict): Market structure analysis
            
        Returns:
            list: Break of structure zones
        """
        bos_zones = []
        swing_highs = market_structure['swing_highs']
        swing_lows = market_structure['swing_lows']
        
        # Look for breaks of swing highs (bullish BOS)
        for i in range(1, len(swing_highs)):
            current_high = swing_highs[i]
            previous_high = swing_highs[i-1]
            
            # Check if this is a higher high
            if current_high['value'] > previous_high['value']:
                # Find the candle that broke the previous high
                for j in range(previous_high['index'] + 1, current_high['index'] + 1):
                    if j < len(df) and df['high'].iloc[j] > previous_high['value']:
                        # This is a bullish BOS
                        bos_zones.append({
                            'type': 'bullish',
                            'index': j,
                            'price': previous_high['value'],
                            'strength': self._calculate_bos_strength(df, j, previous_high['value'], 'bullish')
                        })
                        break
        
        # Look for breaks of swing lows (bearish BOS)
        for i in range(1, len(swing_lows)):
            current_low = swing_lows[i]
            previous_low = swing_lows[i-1]
            
            # Check if this is a lower low
            if current_low['value'] < previous_low['value']:
                # Find the candle that broke the previous low
                for j in range(previous_low['index'] + 1, current_low['index'] + 1):
                    if j < len(df) and df['low'].iloc[j] < previous_low['value']:
                        # This is a bearish BOS
                        bos_zones.append({
                            'type': 'bearish',
                            'index': j,
                            'price': previous_low['value'],
                            'strength': self._calculate_bos_strength(df, j, previous_low['value'], 'bearish')
                        })
                        break
        
        return bos_zones
    
    def identify_change_of_character(self, df: pd.DataFrame, market_structure: Dict) -> List[Dict]:
        """
        Identify change of character (CHOCH) zones
        
        Args:
            df (pd.DataFrame): OHLCV data
            market_structure (dict): Market structure analysis
            
        Returns:
            list: Change of character zones
        """
        choch_zones = []
        trend = market_structure['trend']
        structure_shifts = market_structure['structure_shifts']
        
        # CHOCH is essentially a break of structure in the opposite direction of the prevailing trend
        for i in range(1, len(structure_shifts)):
            current_shift = structure_shifts[i]
            previous_shift = structure_shifts[i-1]
            
            # Check if direction changed
            if current_shift['direction'] != previous_shift['direction']:
                # This is a change of character
                choch_zones.append({
                    'type': current_shift['direction'],
                    'index': current_shift['index'],
                    'price': current_shift['price'],
                    'strength': current_shift.get('strength', 50),
                    'previous_direction': previous_shift['direction']
                })
        
        return choch_zones
    
    def identify_optimal_trade_entry(self, df: pd.DataFrame, daily_bias: Dict) -> List[Dict]:
        """
        Identify Optimal Trade Entry (OTE) zones
        
        Args:
            df (pd.DataFrame): OHLCV data
            daily_bias (dict): Daily bias information
            
        Returns:
            list: OTE zones
        """
        ote_zones = []
        
        # We need at least 50 bars to identify meaningful OTE zones
        if len(df) < 50:
            return ote_zones
        
        # Find significant price moves (legs)
        legs = self._find_price_legs(df)
        
        for leg in legs:
            start_idx = leg['start_index']
            end_idx = leg['end_index']
            direction = leg['direction']
            
            # Skip if the leg is too old (more than 100 bars ago)
            if len(df) - end_idx > 100:
                continue
            
            # Calculate OTE levels based on the leg
            if direction == 'bullish':
                start_price = df['low'].iloc[start_idx]
                end_price = df['high'].iloc[end_idx]
                
                # Calculate OTE levels
                ote_level1 = end_price - (end_price - start_price) * self.fibonacci_levels['ote_level1']
                ote_level2 = end_price - (end_price - start_price) * self.fibonacci_levels['ote_level2']
                ote_level3 = end_price - (end_price - start_price) * self.fibonacci_levels['ote_level3']
                
                # Create OTE zone
                ote_zones.append({
                    'type': 'bullish',
                    'start_index': start_idx,
                    'end_index': end_idx,
                    'top': ote_level1,
                    'middle': ote_level2,
                    'bottom': ote_level3,
                    'strength': self._calculate_ote_strength(df, start_idx, end_idx, 'bullish'),
                    'leg_size': end_price - start_price
                })
                
            elif direction == 'bearish':
                start_price = df['high'].iloc[start_idx]
                end_price = df['low'].iloc[end_idx]
                
                # Calculate OTE levels
                ote_level1 = end_price + (start_price - end_price) * self.fibonacci_levels['ote_level1']
                ote_level2 = end_price + (start_price - end_price) * self.fibonacci_levels['ote_level2']
                ote_level3 = end_price + (start_price - end_price) * self.fibonacci_levels['ote_level3']
                
                # Create OTE zone
                ote_zones.append({
                    'type': 'bearish',
                    'start_index': start_idx,
                    'end_index': end_idx,
                    'top': ote_level3,
                    'middle': ote_level2,
                    'bottom': ote_level1,
                    'strength': self._calculate_ote_strength(df, start_idx, end_idx, 'bearish'),
                    'leg_size': start_price - end_price
                })
        
        # Filter OTE zones based on daily bias
        bias_direction = daily_bias['direction']
        filtered_ote_zones = []
        
        for zone in ote_zones:
            # Only keep zones that align with the daily bias
            if (bias_direction == 'bullish' and zone['type'] == 'bullish') or \
               (bias_direction == 'bearish' and zone['type'] == 'bearish'):
                filtered_ote_zones.append(zone)
        
        # Sort by strength (descending)
        filtered_ote_zones.sort(key=lambda x: x['strength'], reverse=True)
        
        return filtered_ote_zones
    
    def identify_liquidity_levels(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify liquidity levels (stop hunts, equal highs/lows)
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Liquidity levels
        """
        liquidity_levels = []
        
        # Find equal highs (potential stop hunts)
        for i in range(5, len(df) - 5):
            # Look for 3 or more similar highs
            high_values = [df['high'].iloc[j] for j in range(i-5, i+5)]
            high_clusters = self._find_price_clusters(high_values)
            
            for cluster in high_clusters:
                if len(cluster['indices']) >= 3:
                    # This is a potential liquidity level
                    liquidity_levels.append({
                        'type': 'high',
                        'price': cluster['price'],
                        'indices': [i-5+idx for idx in cluster['indices']],
                        'strength': len(cluster['indices']) * 10  # More occurrences = stronger
                    })
        
        # Find equal lows (potential stop hunts)
        for i in range(5, len(df) - 5):
            # Look for 3 or more similar lows
            low_values = [df['low'].iloc[j] for j in range(i-5, i+5)]
            low_clusters = self._find_price_clusters(low_values)
            
            for cluster in low_clusters:
                if len(cluster['indices']) >= 3:
                    # This is a potential liquidity level
                    liquidity_levels.append({
                        'type': 'low',
                        'price': cluster['price'],
                        'indices': [i-5+idx for idx in cluster['indices']],
                        'strength': len(cluster['indices']) * 10  # More occurrences = stronger
                    })
        
        # Remove duplicates (levels that are very close to each other)
        filtered_levels = []
        for level in liquidity_levels:
            # Check if this level is already in filtered_levels
            is_duplicate = False
            for filtered in filtered_levels:
                if filtered['type'] == level['type'] and abs(filtered['price'] - level['price']) / level['price'] < 0.001:
                    # This is a duplicate, update the existing one if this one is stronger
                    if level['strength'] > filtered['strength']:
                        filtered['strength'] = level['strength']
                        filtered['indices'] = level['indices']
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_levels.append(level)
        
        return filtered_levels
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify Fair Value Gaps (FVGs)
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Fair Value Gaps
        """
        fvgs = []
        
        # Look for bullish FVGs (low of candle 1 > high of candle 3)
        for i in range(2, len(df)):
            if df['low'].iloc[i-2] > df['high'].iloc[i]:
                # This is a bullish FVG
                fvg_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                fvg_top = df['low'].iloc[i-2]
                fvg_bottom = df['high'].iloc[i]
                
                # Calculate strength based on size and volume
                strength = self._calculate_fvg_strength(df, i-2, i, fvg_size, 'bullish')
                
                fvgs.append({
                    'type': 'bullish',
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'middle': (fvg_top + fvg_bottom) / 2,
                    'size': fvg_size,
                    'start_index': i-2,
                    'end_index': i,
                    'strength': strength,
                    'filled': False
                })
        
        # Look for bearish FVGs (high of candle 1 < low of candle 3)
        for i in range(2, len(df)):
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                # This is a bearish FVG
                fvg_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                fvg_top = df['low'].iloc[i]
                fvg_bottom = df['high'].iloc[i-2]
                
                # Calculate strength based on size and volume
                strength = self._calculate_fvg_strength(df, i-2, i, fvg_size, 'bearish')
                
                fvgs.append({
                    'type': 'bearish',
                    'top': fvg_top,
                    'bottom': fvg_bottom,
                    'middle': (fvg_top + fvg_bottom) / 2,
                    'size': fvg_size,
                    'start_index': i-2,
                    'end_index': i,
                    'strength': strength,
                    'filled': False
                })
        
        # Check if FVGs have been filled
        for fvg in fvgs:
            # Check all candles after the FVG
            for i in range(fvg['end_index'] + 1, len(df)):
                if fvg['type'] == 'bullish':
                    # Bullish FVG is filled if price trades back into the gap
                    if df['high'].iloc[i] >= fvg['bottom'] and df['low'].iloc[i] <= fvg['top']:
                        fvg['filled'] = True
                        fvg['fill_index'] = i
                        break
                else:
                    # Bearish FVG is filled if price trades back into the gap
                    if df['high'].iloc[i] >= fvg['bottom'] and df['low'].iloc[i] <= fvg['top']:
                        fvg['filled'] = True
                        fvg['fill_index'] = i
                        break
        
        # Filter out filled FVGs
        unfilled_fvgs = [fvg for fvg in fvgs if not fvg['filled']]
        
        # Sort by strength (descending)
        unfilled_fvgs.sort(key=lambda x: x['strength'], reverse=True)
        
        return unfilled_fvgs
    
    def identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify Order Blocks (OBs)
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Order Blocks
        """
        order_blocks = []
        
        # Find significant price moves (legs)
        legs = self._find_price_legs(df)
        
        for leg in legs:
            start_idx = leg['start_index']
            end_idx = leg['end_index']
            direction = leg['direction']
            
            if direction == 'bullish':
                # For bullish legs, look for the last bearish candle before the move
                for i in range(start_idx, -1, -1):
                    if i < len(df) and df['close'].iloc[i] < df['open'].iloc[i]:
                        # This is a potential bearish order block
                        ob_top = df['high'].iloc[i]
                        ob_bottom = df['low'].iloc[i]
                        ob_size = ob_top - ob_bottom
                        
                        # Calculate strength based on the subsequent move
                        strength = self._calculate_ob_strength(df, i, start_idx, end_idx, 'bullish')
                        
                        order_blocks.append({
                            'type': 'bullish',  # This is a bullish OB (causes bullish move)
                            'top': ob_top,
                            'bottom': ob_bottom,
                            'middle': (ob_top + ob_bottom) / 2,
                            'size': ob_size,
                            'index': i,
                            'leg_start': start_idx,
                            'leg_end': end_idx,
                            'strength': strength,
                            'mitigated': False
                        })
                        break
            
            elif direction == 'bearish':
                # For bearish legs, look for the last bullish candle before the move
                for i in range(start_idx, -1, -1):
                    if i < len(df) and df['close'].iloc[i] > df['open'].iloc[i]:
                        # This is a potential bullish order block
                        ob_top = df['high'].iloc[i]
                        ob_bottom = df['low'].iloc[i]
                        ob_size = ob_top - ob_bottom
                        
                        # Calculate strength based on the subsequent move
                        strength = self._calculate_ob_strength(df, i, start_idx, end_idx, 'bearish')
                        
                        order_blocks.append({
                            'type': 'bearish',  # This is a bearish OB (causes bearish move)
                            'top': ob_top,
                            'bottom': ob_bottom,
                            'middle': (ob_top + ob_bottom) / 2,
                            'size': ob_size,
                            'index': i,
                            'leg_start': start_idx,
                            'leg_end': end_idx,
                            'strength': strength,
                            'mitigated': False
                        })
                        break
        
        # Check if order blocks have been mitigated
        for ob in order_blocks:
            # Check all candles after the order block
            for i in range(ob['leg_end'] + 1, len(df)):
                if ob['type'] == 'bullish':
                    # Bullish OB is mitigated if price trades below its low
                    if df['low'].iloc[i] < ob['bottom']:
                        ob['mitigated'] = True
                        ob['mitigation_index'] = i
                        break
                else:
                    # Bearish OB is mitigated if price trades above its high
                    if df['high'].iloc[i] > ob['top']:
                        ob['mitigated'] = True
                        ob['mitigation_index'] = i
                        break
        
        # Filter out mitigated order blocks
        unmitigated_obs = [ob for ob in order_blocks if not ob['mitigated']]
        
        # Sort by strength (descending)
        unmitigated_obs.sort(key=lambda x: x['strength'], reverse=True)
        
        return unmitigated_obs
    
    def identify_breaker_blocks(self, df: pd.DataFrame, order_blocks: List[Dict]) -> List[Dict]:
        """
        Identify Breaker Blocks (BBs)
        
        Args:
            df (pd.DataFrame): OHLCV data
            order_blocks (list): Order blocks
            
        Returns:
            list: Breaker blocks
        """
        breaker_blocks = []
        
        # A breaker block is an order block that has been broken and then retested
        for ob in order_blocks:
            ob_idx = ob['index']
            ob_type = ob['type']
            
            # Skip if the order block is too recent (need room for break and retest)
            if ob_idx > len(df) - 20:
                continue
            
            # Check if the order block has been broken
            broken = False
            break_idx = None
            
            for i in range(ob_idx + 1, len(df)):
                if ob_type == 'bullish':
                    # Bullish OB is broken if price trades below its low
                    if df['low'].iloc[i] < ob['bottom']:
                        broken = True
                        break_idx = i
                        break
                else:
                    # Bearish OB is broken if price trades above its high
                    if df['high'].iloc[i] > ob['top']:
                        broken = True
                        break_idx = i
                        break
            
            # If broken, check for a retest
            if broken and break_idx is not None:
                retested = False
                retest_idx = None
                
                for i in range(break_idx + 1, len(df)):
                    if ob_type == 'bullish':
                        # Retest of bullish OB occurs when price trades back up to the OB
                        if df['high'].iloc[i] >= ob['bottom'] and df['high'].iloc[i] <= ob['top']:
                            retested = True
                            retest_idx = i
                            break
                    else:
                        # Retest of bearish OB occurs when price trades back down to the OB
                        if df['low'].iloc[i] <= ob['top'] and df['low'].iloc[i] >= ob['bottom']:
                            retested = True
                            retest_idx = i
                            break
                
                # If retested, this is a breaker block
                if retested and retest_idx is not None:
                    # Calculate strength based on the original OB and the retest
                    strength = ob['strength'] * 1.5  # Breaker blocks are stronger than regular OBs
                    breaker_blocks.append({
                        'type': ob_type,
                        'top': ob['top'],
                        'bottom': ob['bottom'],
                        'middle': ob['middle'],
                        'size': ob['size'],
                        'original_index': ob_idx,
                        'break_index': break_idx,
                        'retest_index': retest_idx,
                        'strength': strength
                    })
        
        # Sort by strength (descending)
        breaker_blocks.sort(key=lambda x: x['strength'], reverse=True)
        
        return breaker_blocks
    
    def identify_kill_zones(self, df: pd.DataFrame) -> Dict:
        """
        Identify trading session kill zones (London, New York, Asian)
        
        Args:
            df (pd.DataFrame): OHLCV data with datetime index
            
        Returns:
            dict: Kill zones with their statistics
        """
        # Check if we have a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("DataFrame does not have a DatetimeIndex, cannot identify kill zones")
            return {}
        
        # Define session hours (UTC)
        sessions = {
            'asian': (0, 3),     # Asian session: 00:00-03:00 UTC
            'london': (8, 11),   # London session: 08:00-11:00 UTC
            'new_york': (13, 16) # New York session: 13:00-16:00 UTC
        }
        
        kill_zones = {}
        
        # Analyze each session
        for session_name, (start_hour, end_hour) in sessions.items():
            # Filter data for this session
            session_mask = (df.index.hour >= start_hour) & (df.index.hour < end_hour)
            session_data = df[session_mask]
            
            if len(session_data) == 0:
                continue
            
            # Calculate session statistics
            avg_range = (session_data['high'] - session_data['low']).mean()
            avg_volume = session_data['volume'].mean() if 'volume' in session_data.columns else None
            
            # Calculate directional bias
            bullish_days = sum(session_data['close'] > session_data['open'])
            bearish_days = sum(session_data['close'] < session_data['open'])
            total_days = len(session_data)
            
            if total_days > 0:
                bullish_bias = bullish_days / total_days * 100
                bearish_bias = bearish_days / total_days * 100
            else:
                bullish_bias = bearish_bias = 50
            
            # Determine overall bias
            if bullish_bias > bearish_bias:
                bias = 'bullish'
                bias_strength = bullish_bias
            else:
                bias = 'bearish'
                bias_strength = bearish_bias
            
            # Store session info
            kill_zones[session_name] = {
                'bias': bias,
                'bias_strength': bias_strength,
                'avg_range': avg_range,
                'avg_volume': avg_volume,
                'total_days': total_days,
                'bullish_days': bullish_days,
                'bearish_days': bearish_days
            }
        
        return kill_zones
    
    def _find_swing_points(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """
        Find swing high and swing low points
        
        Args:
            df (pd.DataFrame): OHLCV data
            window (int): Window size for swing point detection
            
        Returns:
            tuple: Lists of swing highs and swing lows
        """
        swing_highs = []
        swing_lows = []
        
        # We need at least 2*window+1 bars
        if len(df) < 2 * window + 1:
            return swing_highs, swing_lows
        
        # Find swing highs
        for i in range(window, len(df) - window):
            is_swing_high = True
            for j in range(1, window + 1):
                if df['high'].iloc[i] <= df['high'].iloc[i - j] or df['high'].iloc[i] <= df['high'].iloc[i + j]:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'value': df['high'].iloc[i]
                })
        
        # Find swing lows
        for i in range(window, len(df) - window):
            is_swing_low = True
            for j in range(1, window + 1):
                if df['low'].iloc[i] >= df['low'].iloc[i - j] or df['low'].iloc[i] >= df['low'].iloc[i + j]:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'value': df['low'].iloc[i]
                })
        
        return swing_highs, swing_lows
    
    def _determine_trend(self, df: pd.DataFrame, swing_highs: List[Dict], swing_lows: List[Dict]) -> str:
        """
        Determine the trend based on swing points
        
        Args:
            df (pd.DataFrame): OHLCV data
            swing_highs (list): Swing high points
            swing_lows (list): Swing low points
            
        Returns:
            str: Trend direction ('bullish', 'bearish', or 'neutral')
        """
        # Not enough swing points to determine trend
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            # Use simple moving average as fallback
            if 'close' in df.columns and len(df) >= 50:
                sma20 = df['close'].rolling(20).mean()
                sma50 = df['close'].rolling(50).mean()
                
                if sma20.iloc[-1] > sma50.iloc[-1]:
                    return 'bullish'
                elif sma20.iloc[-1] < sma50.iloc[-1]:
                    return 'bearish'
            
            return 'neutral'
        
        # Sort swing points by index
        sorted_highs = sorted(swing_highs, key=lambda x: x['index'])
        sorted_lows = sorted(swing_lows, key=lambda x: x['index'])
        
        # Get the most recent swing points
        recent_highs = sorted_highs[-2:]
        recent_lows = sorted_lows[-2:]
        
        # Check for higher highs and higher lows (bullish)
        higher_highs = recent_highs[1]['value'] > recent_highs[0]['value'] if len(recent_highs) >= 2 else False
        higher_lows = recent_lows[1]['value'] > recent_lows[0]['value'] if len(recent_lows) >= 2 else False
        
        # Check for lower highs and lower lows (bearish)
        lower_highs = recent_highs[1]['value'] < recent_highs[0]['value'] if len(recent_highs) >= 2 else False
        lower_lows = recent_lows[1]['value'] < recent_lows[0]['value'] if len(recent_lows) >= 2 else False
        
        # Determine trend
        if higher_highs and higher_lows:
            return 'bullish'
        elif lower_highs and lower_lows:
            return 'bearish'
        else:
            # Check the most recent swing point
            most_recent_high = sorted_highs[-1]['index'] if sorted_highs else -1
            most_recent_low = sorted_lows[-1]['index'] if sorted_lows else -1
            
            if most_recent_high > most_recent_low:
                return 'bullish' if higher_highs else 'bearish'
            else:
                return 'bearish' if lower_lows else 'bullish'
    
    def _find_displacement_moves(self, df: pd.DataFrame, threshold: float = 0.01) -> List[Dict]:
        """
        Find significant price displacement moves
        
        Args:
            df (pd.DataFrame): OHLCV data
            threshold (float): Minimum percentage move to consider
            
        Returns:
            list: Displacement moves
        """
        displacement_moves = []
        
        # We need at least 10 bars
        if len(df) < 10:
            return displacement_moves
        
        # Calculate percentage changes
        pct_changes = df['close'].pct_change(1)
        
        # Find significant moves
        for i in range(1, len(df)):
            if abs(pct_changes.iloc[i]) >= threshold:
                direction = 'bullish' if pct_changes.iloc[i] > 0 else 'bearish'
                
                displacement_moves.append({
                    'index': i,
                    'direction': direction,
                    'magnitude': abs(pct_changes.iloc[i]),
                    'price': df['close'].iloc[i]
                })
        
        return displacement_moves
    
    def _identify_market_structure_shifts(self, df: pd.DataFrame, swing_highs: List[Dict], swing_lows: List[Dict]) -> List[Dict]:
        """
        Identify market structure shifts
        
        Args:
            df (pd.DataFrame): OHLCV data
            swing_highs (list): Swing high points
            swing_lows (list): Swing low points
            
        Returns:
            list: Market structure shifts
        """
        structure_shifts = []
        
        # Not enough swing points to determine structure shifts
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return structure_shifts
        
        # Sort swing points by index
        sorted_highs = sorted(swing_highs, key=lambda x: x['index'])
        sorted_lows = sorted(swing_lows, key=lambda x: x['index'])
        
        # Check for bullish structure shifts (higher low followed by break of previous high)
        for i in range(1, len(sorted_lows)):
            current_low = sorted_lows[i]
            previous_low = sorted_lows[i-1]
            
            # Check if this is a higher low
            if current_low['value'] > previous_low['value']:
                # Find the most recent swing high before this low
                previous_high = None
                for high in reversed(sorted_highs):
                    if high['index'] < current_low['index']:
                        previous_high = high
                        break
                
                if previous_high is not None:
                    # Check if price broke above this high after the higher low
                    for j in range(current_low['index'] + 1, len(df)):
                        if df['high'].iloc[j] > previous_high['value']:
                            # This is a bullish structure shift
                            structure_shifts.append({
                                'direction': 'bullish',
                                'index': j,
                                'price': df['high'].iloc[j],
                                'previous_high': previous_high['value'],
                                'higher_low': current_low['value'],
                                'strength': self._calculate_structure_shift_strength(df, j, 'bullish')
                            })
                            break
        
        # Check for bearish structure shifts (lower high followed by break of previous low)
        for i in range(1, len(sorted_highs)):
            current_high = sorted_highs[i]
            previous_high = sorted_highs[i-1]
            
            # Check if this is a lower high
            if current_high['value'] < previous_high['value']:
                # Find the most recent swing low before this high
                previous_low = None
                for low in reversed(sorted_lows):
                    if low['index'] < current_high['index']:
                        previous_low = low
                        break
                
                if previous_low is not None:
                    # Check if price broke below this low after the lower high
                    for j in range(current_high['index'] + 1, len(df)):
                        if df['low'].iloc[j] < previous_low['value']:
                            # This is a bearish structure shift
                            structure_shifts.append({
                                'direction': 'bearish',
                                'index': j,
                                'price': df['low'].iloc[j],
                                'previous_low': previous_low['value'],
                                'lower_high': current_high['value'],
                                'strength': self._calculate_structure_shift_strength(df, j, 'bearish')
                            })
                            break
        
        return structure_shifts
    
    def _find_price_legs(self, df: pd.DataFrame, min_bars: int = 5, min_move: float = 0.005) -> List[Dict]:
        """
        Find significant price legs (directional moves)
        
        Args:
            df (pd.DataFrame): OHLCV data
            min_bars (int): Minimum number of bars in a leg
            min_move (float): Minimum percentage move to consider
            
        Returns:
            list: Price legs
        """
        legs = []
        
        # We need at least 2*min_bars bars
        if len(df) < 2 * min_bars:
            return legs
        
        # Find swing points
        swing_highs, swing_lows = self._find_swing_points(df)
        
        # Sort swing points by index
        all_swings = swing_highs + swing_lows
        all_swings.sort(key=lambda x: x['index'])
        
        # Need at least 2 swing points to form a leg
        if len(all_swings) < 2:
            return legs
        
        # Create legs between consecutive swing points
        for i in range(1, len(all_swings)):
            start_swing = all_swings[i-1]
            end_swing = all_swings[i]
            
            start_idx = start_swing['index']
            end_idx = end_swing['index']
            
            # Ensure the leg is long enough
            if end_idx - start_idx < min_bars:
                continue
            
            # Calculate the percentage move
            start_price = df['close'].iloc[start_idx]
            end_price = df['close'].iloc[end_idx]
            pct_move = abs(end_price - start_price) / start_price
            
            # Ensure the move is significant enough
            if pct_move < min_move:
                continue
            
            # Determine direction
            direction = 'bullish' if end_price > start_price else 'bearish'
            
            legs.append({
                'start_index': start_idx,
                'end_index': end_idx,
                'direction': direction,
                'magnitude': pct_move,
                'start_price': start_price,
                'end_price': end_price
            })
        
        return legs
    
    def _find_price_clusters(self, prices: List[float], tolerance: float = 0.001) -> List[Dict]:
        """
        Find clusters of similar prices
        
        Args:
            prices (list): List of price values
            tolerance (float): Percentage tolerance for clustering
            
        Returns:
            list: Price clusters
        """
        clusters = []
        
        # Sort prices
        sorted_prices = sorted([(i, p) for i, p in enumerate(prices)], key=lambda x: x[1])
        
        # Find clusters
        current_cluster = {'price': sorted_prices[0][1], 'indices': [sorted_prices[0][0]]}
        
        for i in range(1, len(sorted_prices)):
            idx, price = sorted_prices[i]
            prev_price = sorted_prices[i-1][1]
            
            # Check if this price is within tolerance of the previous price
            if abs(price - prev_price) / prev_price <= tolerance:
                # Add to current cluster
                current_cluster['indices'].append(idx)
            else:
                # Start a new cluster
                if len(current_cluster['indices']) > 0:
                    # Calculate average price for the cluster
                    cluster_prices = [prices[i] for i in current_cluster['indices']]
                    current_cluster['price'] = sum(cluster_prices) / len(cluster_prices)
                    clusters.append(current_cluster)
                
                current_cluster = {'price': price, 'indices': [idx]}
        
        # Add the last cluster
        if len(current_cluster['indices']) > 0:
            # Calculate average price for the cluster
            cluster_prices = [prices[i] for i in current_cluster['indices']]
            current_cluster['price'] = sum(cluster_prices) / len(cluster_prices)
            clusters.append(current_cluster)
        
        return clusters
    
    def _calculate_inducement_strength(self, df: pd.DataFrame, inducement_idx: int, shift_idx: int) -> int:
        """
        Calculate the strength of an inducement zone
        
        Args:
            df (pd.DataFrame): OHLCV data
            inducement_idx (int): Index of the inducement
            shift_idx (int): Index of the related structure shift
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Volume at inducement
        if 'volume' in df.columns:
            avg_volume = df['volume'].iloc[max(0, inducement_idx-5):inducement_idx+5].mean()
            if df['volume'].iloc[inducement_idx] > avg_volume * 1.5:
                strength += 10
        
        # 2. Size of the subsequent move
        price_change = abs(df['close'].iloc[shift_idx] - df['close'].iloc[inducement_idx])
        avg_range = (df['high'] - df['low']).iloc[max(0, inducement_idx-10):inducement_idx+10].mean()
        if price_change > avg_range * 3:
            strength += 15
        elif price_change > avg_range * 2:
            strength += 10
        elif price_change > avg_range:
            strength += 5
        
        # 3. Recency (more recent = stronger)
        recency_factor = 1.0 - (shift_idx - inducement_idx) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))
    
    def _calculate_bos_strength(self, df: pd.DataFrame, bos_idx: int, level: float, direction: str) -> int:
        """
        Calculate the strength of a break of structure
        
        Args:
            df (pd.DataFrame): OHLCV data
            bos_idx (int): Index of the BOS
            level (float): Price level that was broken
            direction (str): Direction of the break ('bullish' or 'bearish')
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Volume at break
        if 'volume' in df.columns:
            avg_volume = df['volume'].iloc[max(0, bos_idx-5):bos_idx+5].mean()
            if df['volume'].iloc[bos_idx] > avg_volume * 1.5:
                strength += 10
        
        # 2. Size of the break candle
        candle_range = df['high'].iloc[bos_idx] - df['low'].iloc[bos_idx]
        avg_range = (df['high'] - df['low']).iloc[max(0, bos_idx-10):bos_idx+10].mean()
        if candle_range > avg_range * 1.5:
            strength += 10
        
        # 3. Momentum of the break
        if direction == 'bullish':
            momentum = (df['close'].iloc[bos_idx] - df['open'].iloc[bos_idx]) / candle_range
            if momentum > 0.7:  # Strong bullish candle
                strength += 10
        else:
            momentum = (df['open'].iloc[bos_idx] - df['close'].iloc[bos_idx]) / candle_range
            if momentum > 0.7:  # Strong bearish candle
                strength += 10
        
        # 4. Recency (more recent = stronger)
        recency_factor = 1.0 - (len(df) - bos_idx) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))
    
    def _calculate_ote_strength(self, df: pd.DataFrame, start_idx: int, end_idx: int, direction: str) -> int:
        """
        Calculate the strength of an OTE zone
        
        Args:
            df (pd.DataFrame): OHLCV data
            start_idx (int): Start index of the leg
            end_idx (int): End index of the leg
            direction (str): Direction of the leg ('bullish' or 'bearish')
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Size of the leg
        if direction == 'bullish':
            leg_size = df['high'].iloc[end_idx] - df['low'].iloc[start_idx]
        else:
            leg_size = df['high'].iloc[start_idx] - df['low'].iloc[end_idx]
        
        avg_range = (df['high'] - df['low']).iloc[max(0, start_idx-10):end_idx+10].mean()
        if leg_size > avg_range * 3:
            strength += 15
        elif leg_size > avg_range * 2:
            strength += 10
        elif leg_size > avg_range:
            strength += 5
        
        # 2. Volume during the leg
        if 'volume' in df.columns:
            leg_volume = df['volume'].iloc[start_idx:end_idx+1].mean()
            avg_volume = df['volume'].iloc[max(0, start_idx-10):end_idx+10].mean()
            if leg_volume > avg_volume * 1.2:
                strength += 10
        
        # 3. Momentum of the leg
        if direction == 'bullish':
            momentum = (df['close'].iloc[end_idx] - df['open'].iloc[start_idx]) / leg_size
            if momentum > 0.7:  # Strong bullish momentum
                strength += 10
        else:
            momentum = (df['open'].iloc[start_idx] - df['close'].iloc[end_idx]) / leg_size
            if momentum > 0.7:  # Strong bearish momentum
                strength += 10
        
        # 4. Recency (more recent = stronger)
        recency_factor = 1.0 - (len(df) - end_idx) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))
    
    def _calculate_fvg_strength(self, df: pd.DataFrame, start_idx: int, end_idx: int, fvg_size: float, direction: str) -> int:
        """
        Calculate the strength of a Fair Value Gap
        
        Args:
            df (pd.DataFrame): OHLCV data
            start_idx (int): Start index of the FVG
            end_idx (int): End index of the FVG
            fvg_size (float): Size of the FVG
            direction (str): Direction of the FVG ('bullish' or 'bearish')
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Size of the FVG relative to average range
        avg_range = (df['high'] - df['low']).iloc[max(0, start_idx-10):end_idx+10].mean()
        if fvg_size > avg_range * 1.5:
            strength += 15
        elif fvg_size > avg_range:
            strength += 10
        elif fvg_size > avg_range * 0.5:
            strength += 5
        
        # 2. Volume during the FVG formation
        if 'volume' in df.columns:
            fvg_volume = df['volume'].iloc[start_idx:end_idx+1].mean()
            avg_volume = df['volume'].iloc[max(0, start_idx-10):end_idx+10].mean()
            if fvg_volume > avg_volume * 1.2:
                strength += 10
        
        # 3. Momentum of the move creating the FVG
        if direction == 'bullish':
            momentum = (df['close'].iloc[end_idx] - df['open'].iloc[start_idx]) / fvg_size
            if momentum > 1.0:  # Strong bullish momentum
                strength += 10
        else:
            momentum = (df['open'].iloc[start_idx] - df['close'].iloc[end_idx]) / fvg_size
            if momentum > 1.0:  # Strong bearish momentum
                strength += 10
        
        # 4. Recency (more recent = stronger)
        recency_factor = 1.0 - (len(df) - end_idx) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))
    
    def _calculate_ob_strength(self, df: pd.DataFrame, ob_idx: int, leg_start: int, leg_end: int, direction: str) -> int:
        """
        Calculate the strength of an Order Block
        
        Args:
            df (pd.DataFrame): OHLCV data
            ob_idx (int): Index of the order block
            leg_start (int): Start index of the subsequent leg
            leg_end (int): End index of the subsequent leg
            direction (str): Direction of the order block ('bullish' or 'bearish')
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Volume at the order block
        if 'volume' in df.columns:
            avg_volume = df['volume'].iloc[max(0, ob_idx-5):ob_idx+5].mean()
            if df['volume'].iloc[ob_idx] > avg_volume * 1.5:
                strength += 10
        
        # 2. Size of the subsequent move
        if direction == 'bullish':
            move_size = df['high'].iloc[leg_end] - df['low'].iloc[leg_start]
        else:
            move_size = df['high'].iloc[leg_start] - df['low'].iloc[leg_end]
        
        avg_range = (df['high'] - df['low']).iloc[max(0, ob_idx-10):leg_end+10].mean()
        if move_size > avg_range * 3:
            strength += 15
        elif move_size > avg_range * 2:
            strength += 10
        elif move_size > avg_range:
            strength += 5
        
        # 3. Speed of the subsequent move
        move_duration = leg_end - leg_start
        if move_duration > 0:
            speed = move_size / move_duration
            avg_speed = avg_range / 5  # Assume average move takes 5 bars
            if speed > avg_speed * 2:
                strength += 10
            elif speed > avg_speed:
                strength += 5
        
        # 4. Recency (more recent = stronger)
        recency_factor = 1.0 - (len(df) - leg_end) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))
    
    def _calculate_structure_shift_strength(self, df: pd.DataFrame, shift_idx: int, direction: str) -> int:
        """
        Calculate the strength of a market structure shift
        
        Args:
            df (pd.DataFrame): OHLCV data
            shift_idx (int): Index of the structure shift
            direction (str): Direction of the shift ('bullish' or 'bearish')
            
        Returns:
            int: Strength score (0-100)
        """
        # Base strength
        strength = 50
        
        # Factors that increase strength:
        # 1. Volume at the structure shift
        if 'volume' in df.columns:
            avg_volume = df['volume'].iloc[max(0, shift_idx-5):shift_idx+5].mean()
            if df['volume'].iloc[shift_idx] > avg_volume * 1.5:
                strength += 10
        
        # 2. Size of the structure shift candle
        candle_range = df['high'].iloc[shift_idx] - df['low'].iloc[shift_idx]
        avg_range = (df['high'] - df['low']).iloc[max(0, shift_idx-10):shift_idx+10].mean()
        if candle_range > avg_range * 1.5:
            strength += 10
        
        # 3. Momentum of the shift
        if direction == 'bullish':
            momentum = (df['close'].iloc[shift_idx] - df['open'].iloc[shift_idx]) / candle_range
            if momentum > 0.7:  # Strong bullish candle
                strength += 10
        else:
            momentum = (df['open'].iloc[shift_idx] - df['close'].iloc[shift_idx]) / candle_range
            if momentum > 0.7:  # Strong bearish candle
                strength += 10
        
        # 4. Recency (more recent = stronger)
        recency_factor = 1.0 - (len(df) - shift_idx) / len(df)
        strength = int(strength * (0.7 + 0.3 * recency_factor))
        
        # Ensure strength is within bounds
        return max(0, min(100, strength))



