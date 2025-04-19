"""
ICT (Inner Circle Trader) strategy implementation
Implements trading strategies based on ICT concepts
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union

from trading_bot.strategy.strategy_base import Strategy
from trading_bot.analysis.ict_analyzer import ICTAnalyzer

logger = logging.getLogger(__name__)

class ICTStrategy(Strategy):
    """
    Strategy based on ICT (Inner Circle Trader) concepts
    """
    
    def __init__(self):
        """Initialize the ICT strategy"""
        super().__init__("ICT")
        self.analyzer = ICTAnalyzer()
        
        # Define ICT setups with their weights
        self.setups = {
            'bos_retest': 0.8,           # Break of Structure with retest
            'ote_with_ob': 0.9,          # OTE zone with Order Block
            'fvg_with_liquidity': 0.85,  # Fair Value Gap with liquidity level
            'breaker_block': 0.95,       # Breaker Block setup
            'inducement_to_liquidity': 0.9,  # Inducement to liquidity
            'choch_flip': 0.85,          # Change of Character with market flip
            'kill_zone_entry': 0.8       # Entry during session kill zone
        }
        
        # Define session preferences
        self.session_preferences = {
            'london': 0.9,    # London session
            'new_york': 0.85, # New York session
            'asian': 0.7      # Asian session
        }
    
    def analyze(self, df: pd.DataFrame, symbol: str = None, timeframe: str = None) -> Dict:
        """
        Analyze price data using ICT concepts
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str, optional): Symbol being analyzed
            timeframe (str, optional): Timeframe being analyzed
            
        Returns:
            dict: Analysis results
        """
        # Perform ICT analysis
        analysis = self.analyzer.analyze(df, symbol)
        
        # Add strategy-specific information
        analysis['strategy'] = 'ICT'
        analysis['timeframe'] = timeframe
        
        # Find potential setups
        setups = self._find_setups(analysis, df)
        analysis['setups'] = setups
        
        # Determine overall bias
        bias = self._determine_bias(analysis)
        analysis['bias'] = bias
        
        return analysis
    
    def generate_signals(self, symbol: str, df: pd.DataFrame, timeframe: str = None) -> List[Dict]:
        """
        Generate trading signals based on ICT analysis
        
        Args:
            symbol (str): Symbol being analyzed
            df (pd.DataFrame): OHLCV data
            timeframe (str, optional): Timeframe being analyzed
            
        Returns:
            list: Trading signals
        """
        # Perform analysis
        analysis = self.analyze(df, symbol, timeframe)
        
        # Generate signals from setups
        signals = []
        
        for setup in analysis['setups']:
            # Convert setup to signal
            signal = self._setup_to_signal(setup, df, symbol, timeframe)
            if signal:
                signals.append(signal)
        
        # Sort signals by strength (descending)
        signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return signals

    
    def get_trade_setup(self, signal: Dict) -> Dict:
        """
        Convert a signal to a trade setup
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup
        """
        # Extract signal properties
        symbol = signal.get('symbol')
        direction = signal.get('direction')
        entry_price = signal.get('entry_price')
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        risk_reward = signal.get('risk_reward', 0)
        strength = signal.get('strength', 0)
        reason = signal.get('reason', '')
        setup_type = signal.get('setup', '')
        
        # Skip invalid signals
        if not entry_price or not stop_loss or not take_profit:
            return None
        
        # Create trade setup
        trade_setup = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'strength': strength,
            'strategy': 'ICT',
            'setup_type': setup_type,
            'reason': reason
        }
        
        # Calculate potential profit and loss in pips/points
        if direction == 'bullish' or direction == 'BUY':
            risk_points = entry_price - stop_loss
            reward_points = take_profit - entry_price
        else:
            risk_points = stop_loss - entry_price
            reward_points = entry_price - take_profit
        
        trade_setup['risk_points'] = abs(risk_points)
        trade_setup['reward_points'] = abs(reward_points)
        
        # Add HTF context if available
        if 'htf_bias' in signal:
            trade_setup['htf_bias'] = signal.get('htf_bias')
            trade_setup['aligned_with_htf'] = signal.get('aligned_with_htf', False)
        
        return trade_setup


    def _find_setups(self, analysis: Dict, df: pd.DataFrame) -> List[Dict]:
        """
        Find potential ICT setups from analysis
        
        Args:
            analysis (dict): ICT analysis results
            df (pd.DataFrame): OHLCV data
            
        Returns:
            list: Potential setups
        """
        setups = []
        
        # Extract components from analysis
        market_structure = analysis.get('market_structure', {})
        daily_bias = analysis.get('daily_bias', {})
        inducement_zones = analysis.get('inducement_zones', [])
        bos_zones = analysis.get('bos_zones', [])
        choch_zones = analysis.get('choch_zones', [])
        ote_zones = analysis.get('ote_zones', [])
        liquidity_levels = analysis.get('liquidity_levels', [])
        fair_value_gaps = analysis.get('fair_value_gaps', [])
        order_blocks = analysis.get('order_blocks', [])
        breaker_blocks = analysis.get('breaker_blocks', [])
        kill_zones = analysis.get('kill_zones', {})
        
        # 1. BOS Retest Setup
        bos_retest_setups = self._find_bos_retest_setups(df, bos_zones, market_structure)
        setups.extend(bos_retest_setups)
        
        # 2. OTE with Order Block Setup
        ote_ob_setups = self._find_ote_with_ob_setups(df, ote_zones, order_blocks, daily_bias)
        setups.extend(ote_ob_setups)
        
        # 3. FVG with Liquidity Setup
        fvg_liquidity_setups = self._find_fvg_with_liquidity_setups(df, fair_value_gaps, liquidity_levels)
        setups.extend(fvg_liquidity_setups)
        
        # 4. Breaker Block Setup
        breaker_setups = self._find_breaker_block_setups(df, breaker_blocks, daily_bias)
        setups.extend(breaker_setups)
        
        # 5. Inducement to Liquidity Setup
        inducement_setups = self._find_inducement_to_liquidity_setups(df, inducement_zones, liquidity_levels)
        setups.extend(inducement_setups)
        
        # 6. CHOCH Flip Setup
        choch_setups = self._find_choch_flip_setups(df, choch_zones, market_structure)
        setups.extend(choch_setups)
        
        # 7. Kill Zone Entry Setup
        kill_zone_setups = self._find_kill_zone_setups(df, kill_zones, daily_bias)
        setups.extend(kill_zone_setups)
        
        # Sort setups by strength (descending)
        setups.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return setups
    
    def _determine_bias(self, analysis: Dict) -> Dict:
        """
        Determine overall market bias from analysis
        
        Args:
            analysis (dict): ICT analysis results
            
        Returns:
            dict: Market bias information
        """
        # Extract components from analysis
        market_structure = analysis.get('market_structure', {})
        daily_bias = analysis.get('daily_bias', {})
        
        # Start with the daily bias
        bias_direction = daily_bias.get('direction', 'neutral')
        bias_strength = daily_bias.get('confidence', 50)
        
        # Adjust based on market structure
        structure_trend = market_structure.get('trend', 'neutral')
        
        # If market structure trend agrees with daily bias, increase strength
        if structure_trend == bias_direction:
            bias_strength = min(100, bias_strength + 10)
        # If market structure trend disagrees with daily bias, decrease strength
        elif structure_trend != 'neutral' and bias_direction != 'neutral':
            bias_strength = max(0, bias_strength - 10)
            
            # If bias strength is very low, switch to market structure trend
            if bias_strength < 30:
                bias_direction = structure_trend
                bias_strength = 40
        
        return {
            'direction': bias_direction,
            'strength': bias_strength,
            'zone': daily_bias.get('zone', 'neutral'),
            'price': daily_bias.get('price', None)
        }
    
    def _find_bos_retest_setups(self, df: pd.DataFrame, bos_zones: List[Dict], market_structure: Dict) -> List[Dict]:
        """
        Find Break of Structure with Retest setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            bos_zones (list): Break of structure zones
            market_structure (dict): Market structure analysis
            
        Returns:
            list: BOS Retest setups
        """
        setups = []
        
        # Need at least one BOS zone
        if not bos_zones:
            return setups
        
        # Get trend from market structure
        trend = market_structure.get('trend', 'neutral')
        
        for bos in bos_zones:
            bos_idx = bos.get('index')
            bos_type = bos.get('type')
            bos_price = bos.get('price')
            
            # Skip if BOS is too old (more than 50 bars ago)
            if len(df) - bos_idx > 50:
                continue
            
            # Skip if BOS doesn't align with trend
            if (trend == 'bullish' and bos_type != 'bullish') or (trend == 'bearish' and bos_type != 'bearish'):
                continue
            
            # Look for a retest of the BOS level
            retest_found = False
            retest_idx = None
            
            for i in range(bos_idx + 1, len(df)):
                if bos_type == 'bullish':
                    # For bullish BOS, look for a pullback to the breakout level
                    if df['low'].iloc[i] <= bos_price <= df['high'].iloc[i]:
                        retest_found = True
                        retest_idx = i
                        break
                else:
                    # For bearish BOS, look for a pullback to the breakout level
                    if df['low'].iloc[i] <= bos_price <= df['high'].iloc[i]:
                        retest_found = True
                        retest_idx = i
                        break
            
            if retest_found and retest_idx is not None:
                # Calculate setup strength
                base_strength = bos.get('strength', 50)
                
                # Adjust strength based on factors
                # 1. Recency of retest
                recency_factor = 1.0 - (len(df) - retest_idx) / len(df)
                adjusted_strength = base_strength * (0.7 + 0.3 * recency_factor)
                
                # 2. Alignment with trend
                if (bos_type == 'bullish' and trend == 'bullish') or (bos_type == 'bearish' and trend == 'bearish'):
                    adjusted_strength *= 1.2
                
                # 3. Apply setup weight
                final_strength = adjusted_strength * self.setups['bos_retest']
                
                # Create setup
                setup = {
                    'type': 'bos_retest',
                    'direction': bos_type,
                    'bos_index': bos_idx,
                    'retest_index': retest_idx,
                    'entry_price': bos_price,
                    'strength': min(100, int(final_strength)),
                    'description': f"{bos_type.capitalize()} Break of Structure with Retest"
                }
                
                # Calculate stop loss and take profit
                if bos_type == 'bullish':
                    # For bullish setups, find recent low for stop loss
                    stop_loss = df['low'].iloc[max(0, retest_idx-5):retest_idx+1].min()
                    # Take profit based on recent swing high
                    take_profit = bos_price + (bos_price - stop_loss) * 2
                else:
                    # For bearish setups, find recent high for stop loss
                    stop_loss = df['high'].iloc[max(0, retest_idx-5):retest_idx+1].max()
                    # Take profit based on recent swing low
                    take_profit = bos_price - (stop_loss - bos_price) * 2
                
                setup['stop_loss'] = stop_loss
                setup['take_profit'] = take_profit
                
                # Calculate risk-reward ratio
                if bos_type == 'bullish':
                    risk = bos_price - stop_loss
                    reward = take_profit - bos_price
                else:
                    risk = stop_loss - bos_price
                    reward = bos_price - take_profit
                
                if risk > 0:
                    setup['risk_reward'] = abs(reward / risk)
                else:
                    setup['risk_reward'] = 0
                
                setups.append(setup)
        
        return setups
    
    def _find_ote_with_ob_setups(self, df: pd.DataFrame, ote_zones: List[Dict], order_blocks: List[Dict], daily_bias: Dict) -> List[Dict]:
        """
        Find OTE with Order Block setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            ote_zones (list): OTE zones
            order_blocks (list): Order blocks
            daily_bias (dict): Daily bias information
            
        Returns:
            list: OTE with Order Block setups
        """
        setups = []
        
        # Need at least one OTE zone and one order block
        if not ote_zones or not order_blocks:
            return setups
        
        # Get bias direction
        bias_direction = daily_bias.get('direction', 'neutral')
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        for ote in ote_zones:
            ote_type = ote.get('type')
            
            # Skip if OTE doesn't align with bias
            if bias_direction != 'neutral' and ote_type != bias_direction:
                continue
            
            # Check if price is near the OTE zone
            ote_top = ote.get('top')
            ote_bottom = ote.get('bottom')
            
            # Skip if price is not near the OTE zone
            if not (ote_bottom * 0.99 <= current_price <= ote_top * 1.01):
                continue
            
            # Look for an order block that aligns with the OTE
            for ob in order_blocks:
                ob_type = ob.get('type')
                
                # Skip if OB doesn't align with OTE
                if ob_type != ote_type:
                    continue
                
                # Check if the OB is in a good location relative to the OTE
                ob_top = ob.get('top')
                ob_bottom = ob.get('bottom')
                
                # For bullish setups, OB should be below OTE
                # For bearish setups, OB should be above OTE
                valid_location = False
                
                if ote_type == 'bullish' and ob_top <= ote_bottom:
                    valid_location = True
                elif ote_type == 'bearish' and ob_bottom >= ote_top:
                    valid_location = True
                
                if valid_location:
                    # Calculate setup strength
                    ote_strength = ote.get('strength', 50)
                    ob_strength = ob.get('strength', 50)
                    
                    # Combined strength
                    combined_strength = (ote_strength + ob_strength) / 2
                    
                    # Apply setup weight
                    final_strength = combined_strength * self.setups['ote_with_ob']
                    
                    # Create setup
                    setup = {
                        'type': 'ote_with_ob',
                        'direction': ote_type,
                        'ote_zone': {
                            'top': ote_top,
                            'bottom': ote_bottom,
                            'middle': ote.get('middle')
                        },
                        'order_block': {
                            'top': ob_top,
                            'bottom': ob_bottom,
                            'middle': ob.get('middle')
                        },
                        'strength': min(100, int(final_strength)),
                        'description': f"{ote_type.capitalize()} OTE Zone with Order Block"
                    }
                    
                    # Calculate entry, stop loss and take profit
                    if ote_type == 'bullish':
                        # Entry at the middle of the OTE zone
                        entry_price = ote.get('middle')
                        # Stop loss below the OTE zone
                        stop_loss = ote_bottom * 0.99
                        # Take profit based on the leg size
                        leg_size = ote.get('leg_size', 0)
                        take_profit = entry_price + leg_size
                    else:
                        # Entry at the middle of the OTE zone
                        entry_price = ote.get('middle')
                        # Stop loss above the OTE zone
                        stop_loss = ote_top * 1.01
                        # Take profit based on the leg size
                        leg_size = ote.get('leg_size', 0)
                        take_profit = entry_price - leg_size
                    
                    setup['entry_price'] = entry_price
                    setup['stop_loss'] = stop_loss
                    setup['take_profit'] = take_profit
                    
                    # Calculate risk-reward ratio
                    if ote_type == 'bullish':
                        risk = entry_price - stop_loss
                        reward = take_profit - entry_price
                    else:
                        risk = stop_loss - entry_price
                        reward = entry_price - take_profit
                    
                    if risk > 0:
                        setup['risk_reward'] = abs(reward / risk)
                    else:
                        setup['risk_reward'] = 0
                    
                    setups.append(setup)
        
        return setups
    
    def _find_fvg_with_liquidity_setups(self, df: pd.DataFrame, fair_value_gaps: List[Dict], liquidity_levels: List[Dict]) -> List[Dict]:
        """
        Find Fair Value Gap with Liquidity setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            fair_value_gaps (list): Fair value gaps
            liquidity_levels (list): Liquidity levels
            
        Returns:
            list: FVG with Liquidity setups
        """
        setups = []
        
        # Need at least one FVG and one liquidity level
        if not fair_value_gaps or not liquidity_levels:
            return setups
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        for fvg in fair_value_gaps:
            fvg_type = fvg.get('type')
            fvg_top = fvg.get('top')
            fvg_bottom = fvg.get('bottom')
            
            # Skip if price is not near the FVG
            if not (fvg_bottom * 0.99 <= current_price <= fvg_top * 1.01):
                continue
            
            # Look for a liquidity level that aligns with the FVG
            for liq in liquidity_levels:
                liq_type = liq.get('type')
                liq_price = liq.get('price')
                
                # For bullish FVG, we want a low liquidity level
                # For bearish FVG, we want a high liquidity level
                valid_combination = False
                
                if fvg_type == 'bullish' and liq_type == 'low' and liq_price < fvg_bottom:
                    valid_combination = True
                elif fvg_type == 'bearish' and liq_type == 'high' and liq_price > fvg_top:
                    valid_combination = True
                
                if valid_combination:
                    # Calculate setup strength
                    fvg_strength = fvg.get('strength', 50)
                    liq_strength = liq.get('strength', 50)
                    
                    # Combined strength
                    combined_strength = (fvg_strength + liq_strength) / 2
                    
                    # Apply setup weight
                    final_strength = combined_strength * self.setups['fvg_with_liquidity']
                    
                    # Create setup
                    setup = {
                        'type': 'fvg_with_liquidity',
                        'direction': fvg_type,
                        'fvg': {
                            'top': fvg_top,
                            'bottom': fvg_bottom,
                            'middle': fvg.get('middle')
                        },
                        'liquidity': {
                            'type': liq_type,
                            'price': liq_price
                        },
                        'strength': min(100, int(final_strength)),
                        'description': f"{fvg_type.capitalize()} FVG with {liq_type.capitalize()} Liquidity"
                    }
                    
                    # Calculate entry, stop loss and take profit
                    if fvg_type == 'bullish':
                        # Entry at the middle of the FVG
                        entry_price = fvg.get('middle')
                        # Stop loss below the liquidity level
                        stop_loss = liq_price * 0.99
                        # Take profit based on the FVG size
                        fvg_size = fvg_top - fvg_bottom
                        take_profit = entry_price + fvg_size * 2
                    else:
                        # Entry at the middle of the FVG
                        entry_price = fvg.get('middle')
                        # Stop loss above the liquidity level
                        stop_loss = liq_price * 1.01
                        # Take profit based on the FVG size
                        fvg_size = fvg_top - fvg_bottom
                        take_profit = entry_price - fvg_size * 2
                    
                    setup['entry_price'] = entry_price
                    setup['stop_loss'] = stop_loss
                    setup['take_profit'] = take_profit
                    
                    # Calculate risk-reward ratio
                    if fvg_type == 'bullish':
                        risk = entry_price - stop_loss
                        reward = take_profit - entry_price
                    else:
                        risk = stop_loss - entry_price
                        reward = entry_price - take_profit
                    
                    if risk > 0:
                        setup['risk_reward'] = abs(reward / risk)
                    else:
                        setup['risk_reward'] = 0
                    
                    setups.append(setup)
        
        return setups
    
    def _find_breaker_block_setups(self, df: pd.DataFrame, breaker_blocks: List[Dict], daily_bias: Dict) -> List[Dict]:
        """
        Find Breaker Block setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            breaker_blocks (list): Breaker blocks
            daily_bias (dict): Daily bias information
            
        Returns:
            list: Breaker Block setups
        """
        setups = []
        
        # Need at least one breaker block
        if not breaker_blocks:
            return setups
        
        # Get bias direction
        bias_direction = daily_bias.get('direction', 'neutral')
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        for bb in breaker_blocks:
            bb_type = bb.get('type')
            bb_top = bb.get('top')
            bb_bottom = bb.get('bottom')
            
            # Skip if breaker block doesn't align with bias
            if bias_direction != 'neutral' and bb_type != bias_direction:
                continue
            
            # Check if price is near the breaker block
            if not (bb_bottom * 0.99 <= current_price <= bb_top * 1.01):
                continue
            
            # Calculate setup strength
            base_strength = bb.get('strength', 50)
            
            # Apply setup weight
            final_strength = base_strength * self.setups['breaker_block']
            
            # Create setup
            setup = {
                'type': 'breaker_block',
                'direction': bb_type,
                'breaker_block': {
                    'top': bb_top,
                    'bottom': bb_bottom,
                    'middle': bb.get('middle')
                },
                'strength': min(100, int(final_strength)),
                'description': f"{bb_type.capitalize()} Breaker Block"
            }
            
            # Calculate entry, stop loss and take profit
            if bb_type == 'bullish':
                # Entry at the middle of the breaker block
                entry_price = bb.get('middle')
                # Stop loss below the breaker block
                stop_loss = bb_bottom * 0.99
                # Take profit based on the breaker block size
                bb_size = bb_top - bb_bottom
                take_profit = entry_price + bb_size * 3
            else:
                # Entry at the middle of the breaker block
                entry_price = bb.get('middle')
                # Stop loss above the breaker block
                stop_loss = bb_top * 1.01
                # Take profit based on the breaker block size
                bb_size = bb_top - bb_bottom
                take_profit = entry_price - bb_size * 3
            
            setup['entry_price'] = entry_price
            setup['stop_loss'] = stop_loss
            setup['take_profit'] = take_profit
            
            # Calculate risk-reward ratio
            if bb_type == 'bullish':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk > 0:
                setup['risk_reward'] = abs(reward / risk)
            else:
                setup['risk_reward'] = 0
            
            setups.append(setup)
        
        return setups
    
    def _find_inducement_to_liquidity_setups(self, df: pd.DataFrame, inducement_zones: List[Dict], liquidity_levels: List[Dict]) -> List[Dict]:
        """
        Find Inducement to Liquidity setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            inducement_zones (list): Inducement zones
            liquidity_levels (list): Liquidity levels
            
        Returns:
            list: Inducement to Liquidity setups
        """
        setups = []
        
        # Need at least one inducement zone and one liquidity level
        if not inducement_zones or not liquidity_levels:
            return setups
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        for ind in inducement_zones:
            ind_type = ind.get('type')
            ind_price = ind.get('price')
            
            # Skip if price is not near the inducement zone
            if not (ind_price * 0.99 <= current_price <= ind_price * 1.01):
                continue
            
            # Look for a liquidity level that aligns with the inducement
            for liq in liquidity_levels:
                liq_type = liq.get('type')
                liq_price = liq.get('price')
                
                # For bullish inducement, we want a high liquidity level
                # For bearish inducement, we want a low liquidity level
                valid_combination = False
                
                if ind_type == 'bullish' and liq_type == 'high' and liq_price > ind_price:
                    valid_combination = True
                elif ind_type == 'bearish' and liq_type == 'low' and liq_price < ind_price:
                    valid_combination = True
                
                if valid_combination:
                    # Calculate setup strength
                    ind_strength = ind.get('strength', 50)
                    liq_strength = liq.get('strength', 50)
                    
                    # Combined strength
                    combined_strength = (ind_strength + liq_strength) / 2
                    
                    # Apply setup weight
                    final_strength = combined_strength * self.setups['inducement_to_liquidity']
                    
                    # Create setup
                    setup = {
                        'type': 'inducement_to_liquidity',
                        'direction': ind_type,
                        'inducement': {
                            'price': ind_price
                        },
                        'liquidity': {
                            'type': liq_type,
                            'price': liq_price
                        },
                        'strength': min(100, int(final_strength)),
                        'description': f"{ind_type.capitalize()} Inducement to {liq_type.capitalize()} Liquidity"
                    }
                    
                    # Calculate entry, stop loss and take profit
                    if ind_type == 'bullish':
                        # Entry at the inducement price
                        entry_price = ind_price
                        # Stop loss below the inducement
                        stop_loss = entry_price * 0.99
                        # Take profit at the liquidity level
                        take_profit = liq_price
                    else:
                        # Entry at the inducement price
                        entry_price = ind_price
                        # Stop loss above the inducement
                        stop_loss = entry_price * 1.01
                        # Take profit at the liquidity level
                        take_profit = liq_price
                    
                    setup['entry_price'] = entry_price
                    setup['stop_loss'] = stop_loss
                    setup['take_profit'] = take_profit
                    
                    # Calculate risk-reward ratio
                    if ind_type == 'bullish':
                        risk = entry_price - stop_loss
                        reward = take_profit - entry_price
                    else:
                        risk = stop_loss - entry_price
                        reward = entry_price - take_profit
                    
                    if risk > 0:
                        setup['risk_reward'] = abs(reward / risk)
                    else:
                        setup['risk_reward'] = 0
                    
                    setups.append(setup)
        
        return setups
    
    def _find_choch_flip_setups(self, df: pd.DataFrame, choch_zones: List[Dict], market_structure: Dict) -> List[Dict]:
        """
        Find Change of Character (CHOCH) Flip setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            choch_zones (list): Change of character zones
            market_structure (dict): Market structure analysis
            
        Returns:
            list: CHOCH Flip setups
        """
        setups = []
        
        # Need at least one CHOCH zone
        if not choch_zones:
            return setups
        
        # Get trend from market structure
        trend = market_structure.get('trend', 'neutral')
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        for choch in choch_zones:
            choch_type = choch.get('type')
            choch_price = choch.get('price')
            
            # Skip if CHOCH doesn't align with trend
            if trend != 'neutral' and choch_type != trend:
                continue
            
            # Check if price is near the CHOCH zone
            if not (choch_price * 0.99 <= current_price <= choch_price * 1.01):
                continue
            
            # Calculate setup strength
            base_strength = choch.get('strength', 50)
            
            # Apply setup weight
            final_strength = base_strength * self.setups['choch_flip']
            
            # Create setup
            setup = {
                'type': 'choch_flip',
                'direction': choch_type,
                'choch': {
                    'price': choch_price
                },
                'strength': min(100, int(final_strength)),
                'description': f"{choch_type.capitalize()} Change of Character Flip"
            }
            
            # Calculate entry, stop loss and take profit
            if choch_type == 'bullish':
                # Entry at the CHOCH price
                entry_price = choch_price
                # Stop loss below the CHOCH
                stop_loss = entry_price * 0.99
                # Take profit based on recent swing high
                recent_high = df['high'].iloc[-20:].max()
                take_profit = entry_price + (recent_high - entry_price) * 1.5
            else:
                # Entry at the CHOCH price
                entry_price = choch_price
                # Stop loss above the CHOCH
                stop_loss = entry_price * 1.01
                # Take profit based on recent swing low
                recent_low = df['low'].iloc[-20:].min()
                take_profit = entry_price - (entry_price - recent_low) * 1.5
            
            setup['entry_price'] = entry_price
            setup['stop_loss'] = stop_loss
            setup['take_profit'] = take_profit
            
            # Calculate risk-reward ratio
            if choch_type == 'bullish':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk > 0:
                setup['risk_reward'] = abs(reward / risk)
            else:
                setup['risk_reward'] = 0
            
            setups.append(setup)
        
        return setups
    
    def _find_kill_zone_setups(self, df: pd.DataFrame, kill_zones: Dict, daily_bias: Dict) -> List[Dict]:
        """
        Find Kill Zone Entry setups
        
        Args:
            df (pd.DataFrame): OHLCV data
            kill_zones (dict): Session kill zones
            daily_bias (dict): Daily bias information
            
        Returns:
            list: Kill Zone Entry setups
        """
        setups = []
        
        # Need at least one kill zone
        if not kill_zones:
            return setups
        
        # Get bias direction
        bias_direction = daily_bias.get('direction', 'neutral')
        
        # Skip if no clear bias
        if bias_direction == 'neutral':
            return setups
        
        # Check if we're in a kill zone now
        # This would require datetime index and current time analysis
        # For simplicity, we'll just check if any kill zone has a strong bias
        
        for session_name, session_data in kill_zones.items():
            session_bias = session_data.get('bias')
            bias_strength = session_data.get('bias_strength', 0)
            
            # Skip if session bias doesn't align with daily bias
            if session_bias != bias_direction:
                continue
            
            # Skip if bias strength is too low
            if bias_strength < 60:
                continue
            
            # Calculate setup strength
            base_strength = bias_strength
            
            # Adjust based on session preference
            session_weight = self.session_preferences.get(session_name, 0.7)
            
            # Apply setup weight
            final_strength = base_strength * self.setups['kill_zone_entry'] * session_weight
            
            # Create setup
            setup = {
                'type': 'kill_zone_entry',
                'direction': bias_direction,
                'session': session_name,
                'strength': min(100, int(final_strength)),
                'description': f"{bias_direction.capitalize()} {session_name.capitalize()} Kill Zone Entry"
            }
            
            # Calculate entry, stop loss and take profit
            current_price = df['close'].iloc[-1]
            
            if bias_direction == 'bullish':
                # Entry at current price
                entry_price = current_price
                # Stop loss based on session average range
                avg_range = session_data.get('avg_range', 0)
                stop_loss = entry_price - avg_range * 0.5
                # Take profit based on session average range
                take_profit = entry_price + avg_range * 1.5
            else:
                # Entry at current price
                entry_price = current_price
                # Stop loss based on session average range
                avg_range = session_data.get('avg_range', 0)
                stop_loss = entry_price + avg_range * 0.5
                # Take profit based on session average range
                take_profit = entry_price - avg_range * 1.5
            
            setup['entry_price'] = entry_price
            setup['stop_loss'] = stop_loss
            setup['take_profit'] = take_profit
            
            # Calculate risk-reward ratio
            if bias_direction == 'bullish':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk > 0:
                setup['risk_reward'] = abs(reward / risk)
            else:
                setup['risk_reward'] = 0
            
            setups.append(setup)
        
        return setups
    
    def _setup_to_signal(self, setup: Dict, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Convert a setup to a trading signal
        
        Args:
            setup (dict): Trading setup
            df (pd.DataFrame): OHLCV data
            symbol (str): Symbol being analyzed
            timeframe (str): Timeframe being analyzed
            
        Returns:
            dict: Trading signal
        """
        # Extract common setup properties
        setup_type = setup.get('type')
        direction = setup.get('direction')
        entry_price = setup.get('entry_price')
        stop_loss = setup.get('stop_loss')
        take_profit = setup.get('take_profit')
        risk_reward = setup.get('risk_reward', 0)
        strength = setup.get('strength', 0)
        description = setup.get('description', '')
        
        # Skip invalid setups
        if not entry_price or not stop_loss or not take_profit:
            return None
        
        # Skip setups with poor risk-reward
        if risk_reward < 1.5:
            return None
        
        # Create signal
        signal = {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': 'ICT',
            'setup': setup_type,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': risk_reward,
            'strength': strength,
            'timestamp': pd.Timestamp.now(),
            'reason': description
        }
        
        # Add current price
        signal['price'] = df['close'].iloc[-1]
        
        return signal
    
    def generate_trade_setups_with_htf(self, symbol: str, timeframes: List[str]) -> List[Dict]:
        """
        Generate trade setups with higher timeframe context
        
        Args:
            symbol (str): Symbol to analyze
            timeframes (list): List of timeframes from highest to lowest
            
        Returns:
            list: Trade setups with HTF context
        """
        from trading_bot.data.data_processor import DataProcessor
        
        # Initialize data processor
        data_processor = DataProcessor()
        
        # Get data for each timeframe
        dfs = {}
        for tf in timeframes:
            # Create a new event loop for this request
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async method in the new loop
                df = loop.run_until_complete(data_processor.get_data(symbol, tf))
                if df is not None and not df.empty:
                    dfs[tf] = df
            except Exception as e:
                logger.error(f"Error getting data for {symbol} on {tf}: {e}")
            finally:
                # Close the loop
                loop.close()
        
        # Check if we have data for all timeframes
        if len(dfs) != len(timeframes):
            logger.warning(f"Could not get data for all timeframes for {symbol}")
            return []
        
        # Analyze each timeframe
        analyses = {}
        for tf, df in dfs.items():
            analyses[tf] = self.analyze(df, symbol, tf)
        
        # Determine HTF bias
        htf_bias = self._determine_htf_bias(analyses, timeframes)
        
        # Generate setups for the lowest timeframe
        ltf = timeframes[-1]
        ltf_setups = []
        
        for setup in analyses[ltf].get('setups', []):
            # Skip setups that don't align with HTF bias
            if htf_bias['direction'] != 'neutral' and setup.get('direction') != htf_bias['direction']:
                continue
            
            # Add HTF context to the setup
            setup['htf_bias'] = htf_bias['direction']
            setup['htf_strength'] = htf_bias['strength']
            setup['aligned_with_htf'] = True
            
            # Adjust setup strength based on HTF alignment
            setup['strength'] = min(100, int(setup.get('strength', 50) * 1.2))
            
            ltf_setups.append(setup)
        
        # Sort setups by strength (descending)
        ltf_setups.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return ltf_setups
    
    def _determine_htf_bias(self, analyses: Dict[str, Dict], timeframes: List[str]) -> Dict:
        """
        Determine higher timeframe bias
        
        Args:
            analyses (dict): Analysis results for each timeframe
            timeframes (list): List of timeframes from highest to lowest
            
        Returns:
            dict: HTF bias information
        """
        # Start with neutral bias
        bias = {
            'direction': 'neutral',
            'strength': 50,
            'timeframe': None
        }
        
        # Check each timeframe from highest to lowest
        for tf in timeframes[:-1]:  # Skip the lowest timeframe
            tf_bias = analyses[tf].get('bias', {})
            tf_direction = tf_bias.get('direction', 'neutral')
            tf_strength = tf_bias.get('strength', 0)
            
            # Skip neutral bias
            if tf_direction == 'neutral':
                continue
            
            # If this is the first non-neutral bias, use it
            if bias['direction'] == 'neutral':
                bias['direction'] = tf_direction
                bias['strength'] = tf_strength
                bias['timeframe'] = tf
                continue
            
            # If this bias agrees with the current bias, increase strength
            if tf_direction == bias['direction']:
                bias['strength'] = min(100, bias['strength'] + 10)
            # If this bias disagrees with the current bias, decrease strength
            else:
                bias['strength'] = max(0, bias['strength'] - 20)
                
                # If strength is very low, switch to this timeframe's bias
                if bias['strength'] < 30:
                    bias['direction'] = tf_direction
                    bias['strength'] = tf_strength
                    bias['timeframe'] = tf
        
        return bias

