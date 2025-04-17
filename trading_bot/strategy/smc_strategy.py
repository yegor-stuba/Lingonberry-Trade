"""
Smart Money Concepts (SMC) strategy implementation
Uses the SMC analyzer to generate trading signals
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

from trading_bot.strategy.strategy_base import Strategy
from trading_bot.analysis.smc_analyzer import SMCAnalyzer

logger = logging.getLogger(__name__)

class SMCStrategy(Strategy):
    """
    Smart Money Concepts (SMC) trading strategy
    Implements trading logic based on SMC principles
    """
    
    def __init__(self):
        """Initialize the SMC strategy"""
        super().__init__("Smart Money Concepts")
        self.analyzer = SMCAnalyzer()
        self.min_risk_reward = 2.0  # Minimum risk-reward ratio for valid setups
    
    def analyze(self, df, symbol, timeframe):
        """
        Analyze chart for SMC patterns
        
        Args:
            df (pandas.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Analysis results
        """
        logger.info(f"Analyzing {df} on {timeframe} timeframe using SMC strategy")
        
        # Check if df is a DataFrame
        if not isinstance(df, pd.DataFrame):
            logger.error(f"Expected DataFrame, got {type(df)}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'error': f'Invalid data format: {type(df)}',
                'bias': 'neutral',
                'signals': []
            }
        
        # Check if df is empty
        if df.empty:
            logger.warning(f"Empty DataFrame provided for {symbol} {timeframe}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'error': 'Empty dataframe provided',
                'bias': 'neutral',
                'signals': []
            }
        
        # Use the SMC analyzer to analyze the chart
        analysis = self.analyzer.analyze_chart(df, symbol)
        
        # Add timeframe information
        analysis['timeframe'] = timeframe
        
        # Store current price
        analysis['current_price'] = df['close'].iloc[-1] if not df.empty else None
        
        # Generate signals based on the analysis
        signals = self.generate_signals(analysis)
        analysis['signals'] = signals
        
        logger.info(f"SMC analysis for {symbol} on {timeframe} complete. Found {len(signals)} signals.")
        
        # Store the analysis for later reference
        self.last_analysis = analysis
        
        return analysis

    def generate_signals(self, analysis: Dict) -> List[Dict]:
        """
        Generate trading signals from SMC analysis
        
        Args:
            analysis (dict): SMC analysis results
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Extract key components from analysis
        symbol = analysis.get('symbol', '')
        market_structure = analysis.get('market_structure', {})
        order_blocks = analysis.get('order_blocks', [])
        fair_value_gaps = analysis.get('fair_value_gaps', [])
        liquidity_levels = analysis.get('liquidity_levels', [])
        order_flow = analysis.get('order_flow', {})
        bias = analysis.get('bias', 'neutral')
        
        # Current price (close of the last candle)
        current_price = analysis.get('current_price')
        if current_price is None:
            logger.warning(f"No price data found for {symbol}")
            return signals
        
        # Signal 1: Order Block + Fair Value Gap + Bias Alignment
        signals.extend(self._generate_ob_fvg_signals(
            symbol, order_blocks, fair_value_gaps, bias, current_price, liquidity_levels
        ))
        
        # Signal 2: Market Structure Break + Order Flow
        signals.extend(self._generate_msb_signals(
            symbol, market_structure, order_flow, current_price, liquidity_levels
        ))
        
        # Signal 3: Liquidity Sweep + Order Block
        signals.extend(self._generate_liquidity_sweep_signals(
            symbol, analysis.get('liquidity_sweeps', []), order_blocks, current_price, liquidity_levels
        ))
        
        # Filter signals by risk-reward ratio
        valid_signals = [s for s in signals if s.get('risk_reward', 0) >= self.min_risk_reward]
        
        # Sort by strength (descending)
        valid_signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return valid_signals
    
    def _generate_ob_fvg_signals(self, symbol: str, order_blocks: List[Dict], 
                                fair_value_gaps: List[Dict], bias: str, 
                                current_price: float, liquidity_levels: List[Dict] = None) -> List[Dict]:
        """
        Generate signals based on Order Blocks and Fair Value Gaps
        
        Args:
            symbol (str): Trading symbol
            order_blocks (list): Order blocks
            fair_value_gaps (list): Fair value gaps
            bias (str): Market bias
            current_price (float): Current price
            liquidity_levels (list, optional): Liquidity levels for take profit targets
        
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Filter for recent and unfilled order blocks and FVGs
        recent_bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish' and ob['age'] < 20]
        recent_bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['age'] < 20]
        
        unfilled_bullish_fvgs = [fvg for fvg in fair_value_gaps 
                               if fvg['type'] == 'bullish' and not fvg.get('filled', False)]
        unfilled_bearish_fvgs = [fvg for fvg in fair_value_gaps 
                               if fvg['type'] == 'bearish' and not fvg.get('filled', False)]
        
        # Bullish setups (if bias is bullish or neutral)
        if bias in ['bullish', 'neutral'] and recent_bullish_obs and unfilled_bullish_fvgs:
            # Sort by strength
            recent_bullish_obs.sort(key=lambda x: x.get('strength', 0), reverse=True)
            unfilled_bullish_fvgs.sort(key=lambda x: x.get('strength', 0), reverse=True)
            
            # Get the strongest OB and FVG
            best_ob = recent_bullish_obs[0]
            best_fvg = unfilled_bullish_fvgs[0]
            
            # Check if price is near the order block
            if 0.95 <= current_price / best_ob['top'] <= 1.05:
                # Calculate stop loss
                stop_loss = best_ob['bottom'] * 0.998  # Just below the order block
                
                # Find a suitable take profit level
                take_profit = None
                risk = current_price - stop_loss
                
                # First option: Use the fair value gap
                potential_tp = best_fvg['top']
                potential_reward = potential_tp - current_price
                potential_rr = potential_reward / risk if risk > 0 else 0
                
                if potential_rr >= 2.0:
                    take_profit = potential_tp
                    risk_reward = potential_rr
                
                # Second option: Use liquidity levels if available
                if not take_profit and liquidity_levels:
                    # Find the next significant liquidity level above current price
                    high_liquidity_levels = [level for level in liquidity_levels 
                                            if level['type'] == 'high' and level['price'] > current_price]
                    
                    # Sort by price (ascending)
                    high_liquidity_levels.sort(key=lambda x: x['price'])
                    
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in high_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = potential_tp - current_price
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
                
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price + (risk * 3)
                    risk_reward = 3.0  # By definition
                
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'buy',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': (best_ob['strength'] + best_fvg.get('strength', 50)) / 2,
                        'reason': f"Bullish setup: Order block at {best_ob['bottom']:.5f}-{best_ob['top']:.5f} with fair value gap above"
                    })
        
        # Bearish setups (if bias is bearish or neutral)
        if bias in ['bearish', 'neutral'] and recent_bearish_obs and unfilled_bearish_fvgs:
            # Sort by strength
            recent_bearish_obs.sort(key=lambda x: x.get('strength', 0), reverse=True)
            unfilled_bearish_fvgs.sort(key=lambda x: x.get('strength', 0), reverse=True)
            
            # Get the strongest OB and FVG
            best_ob = recent_bearish_obs[0]
            best_fvg = unfilled_bearish_fvgs[0]
            
            # Check if price is near the order block
            if 0.95 <= best_ob['bottom'] / current_price <= 1.05:
                # Calculate stop loss
                stop_loss = best_ob['top'] * 1.002  # Just above the order block
                
                # Find a suitable take profit level
                take_profit = None
                risk = stop_loss - current_price
                
                # First option: Use the fair value gap
                potential_tp = best_fvg['bottom']
                potential_reward = current_price - potential_tp
                potential_rr = potential_reward / risk if risk > 0 else 0
                
                if potential_rr >= 2.0:
                    take_profit = potential_tp
                    risk_reward = potential_rr
                
                # Second option: Use liquidity levels if available
                if not take_profit and liquidity_levels:
                    # Find the next significant liquidity level below current price
                    low_liquidity_levels = [level for level in liquidity_levels 
                                           if level['type'] == 'low' and level['price'] < current_price]
                    
                    # Sort by price (descending)
                    low_liquidity_levels.sort(key=lambda x: x['price'], reverse=True)
                    
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in low_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = current_price - potential_tp
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
                
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price - (risk * 3)
                    risk_reward = 3.0  # By definition
                
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'sell',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': (best_ob['strength'] + best_fvg.get('strength', 50)) / 2,
                        'reason': f"Bearish setup: Order block at {best_ob['bottom']:.5f}-{best_ob['top']:.5f} with fair value gap below"
                    })
        
        return signals
    
    def _generate_msb_signals(self, symbol: str, market_structure: Dict, 
                             order_flow: Dict, current_price: float, 
                             liquidity_levels: List[Dict] = None) -> List[Dict]:
        """
        Generate signals based on Market Structure Breaks
        
        Args:
            symbol (str): Trading symbol
            market_structure (dict): Market structure analysis
            order_flow (dict): Order flow analysis
            current_price (float): Current price
            liquidity_levels (list, optional): Liquidity levels for take profit targets
        
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Extract HH, HL, LL, LH information
        hh_hl_ll_lh = market_structure.get('hh_hl_ll_lh', {})
        higher_highs = hh_hl_ll_lh.get('higher_highs', [])
        higher_lows = hh_hl_ll_lh.get('higher_lows', [])
        lower_lows = hh_hl_ll_lh.get('lower_lows', [])
        lower_highs = hh_hl_ll_lh.get('lower_highs', [])
        
        # Get recent order flow bias
        recent_bias = order_flow.get('recent_bias', 'neutral')
        
        # Bullish Market Structure Break: Higher Low after Lower High
        if higher_lows and lower_highs and recent_bias in ['bullish', 'neutral']:
            latest_hl = higher_lows[-1]
            latest_lh = lower_highs[-1]
            
            # Check if we have a higher low after a lower high (potential bullish break)
            if latest_hl['index'] > latest_lh['index']:
                # Calculate stop loss and take profit
                stop_loss = latest_hl['price'] * 0.998  # Just below the higher low
                
                # Find a suitable take profit level using liquidity levels
                take_profit = None
                risk = current_price - stop_loss
                
                # If we have liquidity levels, use them for take profit
                if liquidity_levels:
                    # Find the next significant liquidity level above current price
                    high_liquidity_levels = [level for level in liquidity_levels 
                                            if level['type'] == 'high' and level['price'] > current_price]
                    
                    # Sort by price (ascending)
                    high_liquidity_levels.sort(key=lambda x: x['price'])
                    
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in high_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = potential_tp - current_price
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
                
                # If no suitable liquidity level found, use the next higher high if available
                if not take_profit and higher_highs:
                    # Find the most recent higher high above current price
                    recent_higher_highs = [hh for hh in higher_highs if hh['price'] > current_price]
                    if recent_higher_highs:
                        # Sort by index (descending) to get the most recent one
                        recent_higher_highs.sort(key=lambda x: x['index'], reverse=True)
                        potential_tp = recent_higher_highs[0]['price']
                        potential_reward = potential_tp - current_price
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price + (risk * 3)
                    risk_reward = 3.0  # By definition
                
                signals.append({
                    'symbol': symbol,
                    'type': 'buy',
                    'entry': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'risk_reward': risk_reward,
                    'strength': 80,  # Market structure breaks are strong signals
                    'reason': f"Bullish market structure break: Higher low at {latest_hl['price']:.5f} after lower high"
                })
        
        # Bearish Market Structure Break: Lower High after Higher High
        if lower_highs and higher_highs and recent_bias in ['bearish', 'neutral']:
            latest_lh = lower_highs[-1]
            latest_hh = higher_highs[-1]
            
            # Check if we have a lower high after a higher high (potential bearish break)
            if latest_lh['index'] > latest_hh['index']:
                # Calculate stop loss and take profit
                stop_loss = latest_lh['price'] * 1.002  # Just above the lower high
                
                # Find a suitable take profit level using liquidity levels
                take_profit = None
                risk = stop_loss - current_price
                
                # If we have liquidity levels, use them for take profit
                if liquidity_levels:
                    # Find the next significant liquidity level below current price
                    low_liquidity_levels = [level for level in liquidity_levels 
                                           if level['type'] == 'low' and level['price'] < current_price]
                    
                    # Sort by price (descending)
                    low_liquidity_levels.sort(key=lambda x: x['price'], reverse=True)
                    
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in low_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = current_price - potential_tp
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
                
                # If no suitable liquidity level found, use the next lower low if available
                if not take_profit and lower_lows:
                    # Find the most recent lower low below current price
                    recent_lower_lows = [ll for ll in lower_lows if ll['price'] < current_price]
                    if recent_lower_lows:
                        # Sort by index (descending) to get the most recent one
                        recent_lower_lows.sort(key=lambda x: x['index'], reverse=True)
                        potential_tp = recent_lower_lows[0]['price']
                        potential_reward = current_price - potential_tp
                        potential_rr = potential_reward / risk if risk > 0 else 0
                        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price - (risk * 3)
                    risk_reward = 3.0  # By definition
                
                signals.append({
                    'symbol': symbol,
                    'type': 'sell',
                    'entry': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'risk_reward': risk_reward,
                    'strength': 80,  # Market structure breaks are strong signals
                    'reason': f"Bearish market structure break: Lower high at {latest_lh['price']:.5f} after higher high"
                })
        
        return signals
    
    def _generate_liquidity_sweep_signals(self, symbol: str, liquidity_sweeps: List[Dict], 
                                     order_blocks: List[Dict], current_price: float,
                                     liquidity_levels: List[Dict] = None) -> List[Dict]:
        """
        Generate signals based on Liquidity Sweeps and Order Blocks
        
        Args:
            symbol (str): Trading symbol
            liquidity_sweeps (list): Liquidity sweeps
            order_blocks (list): Order blocks
            current_price (float): Current price
            liquidity_levels (list, optional): Liquidity levels for take profit targets
        
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Filter for recent liquidity sweeps and order blocks
        recent_sweeps = [sweep for sweep in liquidity_sweeps if sweep['age'] < 10]
        recent_bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish' and ob['age'] < 20]
        recent_bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['age'] < 20]
        
        # Bullish setup: Sweep of lows followed by bullish order block
        bullish_sweeps = [sweep for sweep in recent_sweeps if sweep['type'] == 'low']
        
        if bullish_sweeps and recent_bullish_obs:
            # Sort by recency (age)
            bullish_sweeps.sort(key=lambda x: x['age'])
            recent_bullish_obs.sort(key=lambda x: x['age'])
        
            latest_sweep = bullish_sweeps[0]
            latest_ob = recent_bullish_obs[0]
        
            # Check if the sweep happened before the order block
            if latest_sweep['age'] > latest_ob['age']:
                # Calculate stop loss
                stop_loss = latest_sweep['price'] * 0.998  # Just below the sweep level
        
                # Find a suitable take profit level
                take_profit = None
                risk = current_price - stop_loss
        
                # First option: Use liquidity levels if available
                if liquidity_levels:
                    # Find the next significant liquidity level above current price
                    high_liquidity_levels = [level for level in liquidity_levels 
                                            if level['type'] == 'high' and level['price'] > current_price]
        
                    # Sort by price (ascending)
                    high_liquidity_levels.sort(key=lambda x: x['price'])
        
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in high_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = potential_tp - current_price
                        potential_rr = potential_reward / risk if risk > 0 else 0
        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
        
                # Second option: Use the next bullish sweep level if available
                if not take_profit and len(bullish_sweeps) > 1:
                    # Find previous sweep levels above current price
                    higher_sweeps = [sweep for sweep in bullish_sweeps[1:] 
                                   if sweep['type'] == 'high' and sweep['price'] > current_price]
        
                    if higher_sweeps:
                        # Sort by price (ascending)
                        higher_sweeps.sort(key=lambda x: x['price'])
        
                        potential_tp = higher_sweeps[0]['price']
                        potential_reward = potential_tp - current_price
                        potential_rr = potential_reward / risk if risk > 0 else 0
        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
        
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price + (risk * 3)
                    risk_reward = 3.0  # By definition
        
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'buy',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': 75,  # Liquidity sweeps are strong signals
                        'reason': f"Bullish liquidity sweep at {latest_sweep['price']:.5f} followed by bullish order block"
                    })
        
        # Bearish setup: Sweep of highs followed by bearish order block
        bearish_sweeps = [sweep for sweep in recent_sweeps if sweep['type'] == 'high']
        
        if bearish_sweeps and recent_bearish_obs:
            # Sort by recency (age)
            bearish_sweeps.sort(key=lambda x: x['age'])
            recent_bearish_obs.sort(key=lambda x: x['age'])
        
            latest_sweep = bearish_sweeps[0]
            latest_ob = recent_bearish_obs[0]
        
            # Check if the sweep happened before the order block
            if latest_sweep['age'] > latest_ob['age']:
                # Calculate stop loss
                stop_loss = latest_sweep['price'] * 1.002  # Just above the sweep level
        
                # Find a suitable take profit level
                take_profit = None
                risk = stop_loss - current_price
        
                # First option: Use liquidity levels if available
                if liquidity_levels:
                    # Find the next significant liquidity level below current price
                    low_liquidity_levels = [level for level in liquidity_levels 
                                           if level['type'] == 'low' and level['price'] < current_price]
        
                    # Sort by price (descending)
                    low_liquidity_levels.sort(key=lambda x: x['price'], reverse=True)
        
                    # Find a liquidity level that gives at least 2:1 risk-reward
                    for level in low_liquidity_levels:
                        potential_tp = level['price']
                        potential_reward = current_price - potential_tp
                        potential_rr = potential_reward / risk if risk > 0 else 0
        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
                            break
        
                # Second option: Use the next bearish sweep level if available
                if not take_profit and len(bearish_sweeps) > 1:
                    # Find previous sweep levels below current price
                    lower_sweeps = [sweep for sweep in bearish_sweeps[1:] 
                                  if sweep['type'] == 'low' and sweep['price'] < current_price]
        
                    if lower_sweeps:
                        # Sort by price (descending)
                        lower_sweeps.sort(key=lambda x: x['price'], reverse=True)
        
                        potential_tp = lower_sweeps[0]['price']
                        potential_reward = current_price - potential_tp
                        potential_rr = potential_reward / risk if risk > 0 else 0
        
                        if potential_rr >= 2.0:
                            take_profit = potential_tp
                            risk_reward = potential_rr
        
                # If still no suitable take profit, use a default 3:1 risk-reward ratio
                if not take_profit:
                    take_profit = current_price - (risk * 3)
                    risk_reward = 3.0  # By definition
        
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'sell',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': 75,  # Liquidity sweeps are strong signals
                        'reason': f"Bearish liquidity sweep at {latest_sweep['price']:.5f} followed by bearish order block"
                    })
        
        return signals
    
    def _generate_order_block_signals(self, symbol, order_blocks, current_price, df, liquidity_levels=None):
        """Generate signals based on Order Blocks"""
        signals = []
        
        # Filter for recent and valid order blocks
        recent_bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish' and ob['age'] < 20]
        recent_bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['age'] < 20]
        
        # Bullish order block signals (for buy trades)
        for ob in recent_bullish_obs:
            # Check if price is near the order block
            if 0.98 * ob['high'] <= current_price <= 1.02 * ob['high']:
                # Calculate stop loss - below the order block low
                stop_loss = ob['low'] * 0.998  # Slightly below the low
                
                # Calculate take profit using the new method
                take_profit, risk_reward = self._calculate_take_profit(
                    df, current_price, stop_loss, 'buy', liquidity_levels
                )
                
                # Only add signal if risk-reward meets minimum criteria
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'buy',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': 70,
                        'reason': f"Bullish order block at {ob['low']:.5f}-{ob['high']:.5f}"
                    })
        
        # Bearish order block signals (for sell trades)
        for ob in recent_bearish_obs:
            # Check if price is near the order block
            if 0.98 * ob['low'] <= current_price <= 1.02 * ob['low']:
                # Calculate stop loss - above the order block high
                stop_loss = ob['high'] * 1.002  # Slightly above the high
                
                # Calculate take profit using the new method
                take_profit, risk_reward = self._calculate_take_profit(
                    df, current_price, stop_loss, 'sell', liquidity_levels
                )
                
                # Only add signal if risk-reward meets minimum criteria
                if risk_reward >= self.min_risk_reward:
                    signals.append({
                        'symbol': symbol,
                        'type': 'sell',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': 70,
                        'reason': f"Bearish order block at {ob['low']:.5f}-{ob['high']:.5f}"
                    })
        
        return signals
    
    def get_trade_setup(self, signal: Dict) -> Dict:
        """
        Get trade setup details from a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade setup details
        """
        # Extract key information from the signal
        symbol = signal.get('symbol', '')
        signal_type = signal.get('type', '')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        risk_reward = signal.get('risk_reward', 0)
        reason = signal.get('reason', '')
        
        # Calculate risk percentage
        risk_pct = abs(entry - stop_loss) / entry * 100
        
        # Calculate potential reward percentage
        reward_pct = abs(entry - take_profit) / entry * 100
        
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
            'strategy': 'SMC',
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return trade_setup
    
    def multi_timeframe_analysis(self, dfs: Dict[str, pd.DataFrame], symbol: str) -> Dict:
        """
        Perform multi-timeframe SMC analysis
        
        Args:
            dfs (dict): Dictionary of dataframes for different timeframes
            symbol (str): Trading symbol
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        # Use the SMC analyzer's multi-timeframe analysis
        return self.analyzer.multi_timeframe_analysis(dfs, symbol)
    
    def _combine_mtf_results(self, mtf_results: Dict[str, Dict], symbol: str) -> Dict:
        """
        Combine multi-timeframe analysis results with SMC-specific logic
        
        Args:
            mtf_results (dict): Results from each timeframe
            symbol (str): Trading symbol
            
        Returns:
            dict: Combined results
        """
        combined = super()._combine_mtf_results(mtf_results, symbol)
        
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
        
        for timeframe, results in mtf_results.items():
            weight = timeframe_weights.get(timeframe, 1)
            total_weight += weight
            
            if results.get('bias') == 'bullish':
                bullish_score += weight
            elif results.get('bias') == 'bearish':
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
        
        # Add to combined results
        combined['overall_bias'] = overall_bias
        combined['bias_strength'] = bias_strength
        
        # Filter signals based on alignment with overall bias
        aligned_signals = []
        for signal in combined['signals']:
            signal_type = signal.get('type', '')
            
            # Check if signal aligns with overall bias
            if (overall_bias == 'bullish' and signal_type == 'buy') or \
               (overall_bias == 'bearish' and signal_type == 'sell') or \
               (overall_bias == 'neutral'):
                # Increase strength for aligned signals
                if overall_bias != 'neutral':
                    signal['strength'] = min(100, signal.get('strength', 0) + bias_strength // 4)
                
                aligned_signals.append(signal)
        
        # If we have aligned signals, use those; otherwise, keep all signals
        if aligned_signals:
            combined['signals'] = aligned_signals
        
        # Sort signals by strength (descending)
        combined['signals'].sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return combined

    def _calculate_atr(self, df, period=14):
        """
        Calculate Average True Range
        
        Args:
            df (pd.DataFrame): Price data
            period (int): ATR period
        
        Returns:
            float: ATR value
        """
        try:
            # Calculate True Range
            df = df.copy()
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = abs(df['high'] - df['low'])
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
            # Calculate ATR
            atr = df['tr'].rolling(window=period).mean().iloc[-1]
            return atr
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None

    def _calculate_take_profit(self, df, entry_price, stop_loss, direction, liquidity_levels=None):
        """
        Calculate optimal take profit levels based on market structure
        
        Args:
            df (pd.DataFrame): Price data
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            direction (str): Trade direction ('buy' or 'sell')
            liquidity_levels (list, optional): Liquidity levels
        
        Returns:
            tuple: (take_profit_price, risk_reward_ratio)
        """
        # Calculate risk in price points
        risk = abs(entry_price - stop_loss)
        
        if risk == 0:
            logger.warning("Risk is zero, cannot calculate risk-reward ratio")
            return entry_price + (0.01 * entry_price), 1.0
        
        # Default minimum risk-reward ratio
        min_rr = self.min_risk_reward
        
        # Use the analyzer's new method to find optimal take profit
        take_profit, risk_reward = self.analyzer.find_optimal_take_profit(
            df, entry_price, stop_loss, direction, min_rr
        )
        
        # Allow for higher risk/reward based on market conditions
        symbol = df.get('symbol', '').iloc[-1] if 'symbol' in df.columns else None
        if symbol and ('BTC' in symbol or 'ETH' in symbol):
            max_rr = 5.0
        else:
            max_rr = 10.0
            
        # If the analyzer suggests a higher RR and it's within our max limits, use it
        if risk_reward > min_rr and risk_reward <= max_rr:
            return take_profit, risk_reward
            
        # If the risk-reward is less than our minimum, adjust the take profit
        if risk_reward < min_rr:
            if direction.lower() == 'buy':
                take_profit = entry_price + (risk * min_rr)
            else:  # sell
                take_profit = entry_price - (risk * min_rr)
            risk_reward = min_rr
        
        # If the analyzer suggests a very high RR, cap it at our maximum
        if risk_reward > max_rr:
            if direction.lower() == 'buy':
                take_profit = entry_price + (risk * max_rr)
            else:  # sell
                take_profit = entry_price - (risk * max_rr)
            risk_reward = max_rr
        
        return take_profit, risk_reward

    def validate_setup(self, setup: Dict, df: pd.DataFrame) -> bool:
        """
        Validate a trade setup with additional criteria
        
        Args:
            setup (dict): Trade setup to validate
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            bool: True if setup is valid, False otherwise
        """
        # Extract key information
        setup_type = setup.get('type', '')
        entry = setup.get('entry', 0)
        stop_loss = setup.get('stop_loss', 0)
        take_profit = setup.get('take_profit', 0)
        
        # Check for minimum risk-reward ratio
        risk = abs(entry - stop_loss)
        reward = abs(entry - take_profit)
        risk_reward = reward / risk if risk > 0 else 0
        
        if risk_reward < self.min_risk_reward:
            logger.debug(f"Setup rejected: Risk-reward ratio {risk_reward:.2f} below minimum {self.min_risk_reward}")
            return False
        
        # Check for minimum stop distance (avoid tight stops)
        stop_distance_pct = abs(entry - stop_loss) / entry * 100
        if stop_distance_pct < 0.1:  # Less than 0.1% stop distance
            logger.debug(f"Setup rejected: Stop distance {stop_distance_pct:.2f}% too small")
            return False
        
        # Check for proximity to key levels
        market_structure = self.analyzer.identify_market_structure(df)
        key_levels = self.analyzer.identify_key_levels(df)
        
        # For buy setups, check if price is near support
        if setup_type == 'buy':
            # Check if price is near a swing low
            near_support = False
            for low in market_structure.get('swing_lows', []):
                # If price is within 1% of a swing low
                if abs(entry - low['price']) / entry < 0.01:
                    near_support = True
                    break
            
            # Check if price is near a support level
            for level in key_levels:
                if level['type'] == 'support' and abs(entry - level['price']) / entry < 0.01:
                    near_support = True
                    break
            
            if not near_support:
                logger.debug("Buy setup not near support level")
                # Not a hard rejection, but reduce confidence
                setup['strength'] = max(10, setup.get('strength', 50) - 20)
        
        # For sell setups, check if price is near resistance
        elif setup_type == 'sell':
            # Check if price is near a swing high
            near_resistance = False
            for high in market_structure.get('swing_highs', []):
                # If price is within 1% of a swing high
                if abs(entry - high['price']) / entry < 0.01:
                    near_resistance = True
                    break
            
            # Check if price is near a resistance level
            for level in key_levels:
                if level['type'] == 'resistance' and abs(entry - level['price']) / entry < 0.01:
                    near_resistance = True
                    break
            
            if not near_resistance:
                logger.debug("Sell setup not near resistance level")
                # Not a hard rejection, but reduce confidence
                setup['strength'] = max(10, setup.get('strength', 50) - 20)
        
        # Check for confluence with other indicators (if available)
        # This is a placeholder for additional validation logic
        
        return True
    
    def adjust_position_size(self, setup: Dict, account_balance: float, risk_per_trade: float = 0.02) -> Dict:
        """
        Calculate and adjust position size based on risk parameters
        
        Args:
            setup (dict): Trade setup
            account_balance (float): Account balance
            risk_per_trade (float): Risk percentage per trade (0.02 = 2%)
            
        Returns:
            dict: Updated setup with position size information
        """
        # Extract key information
        entry = setup.get('entry', 0)
        stop_loss = setup.get('stop_loss', 0)
        
        # Calculate risk amount in account currency
        risk_amount = account_balance * risk_per_trade
        
        # Calculate risk per unit
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit <= 0:
            logger.warning("Invalid risk per unit (zero or negative)")
            setup['position_size'] = 0
            setup['risk_amount'] = 0
            return setup
        
        # Calculate position size
        position_size = risk_amount / risk_per_unit
        
        # Round position size to appropriate precision
        if entry < 1:
            position_size = round(position_size, 1)  # For low-priced assets
        elif entry < 10:
            position_size = round(position_size, 2)
        elif entry < 100:
            position_size = round(position_size, 3)
        else:
            position_size = round(position_size, 4)
        
        # Ensure minimum position size
        if position_size * entry < 10:  # Minimum order value of $10
            logger.warning(f"Position size too small: {position_size} units at {entry}")
            position_size = max(10 / entry, position_size)
        
        # Update setup with position size information
        setup['position_size'] = position_size
        setup['risk_amount'] = risk_amount
        setup['actual_risk_amount'] = position_size * risk_per_unit
        
        return setup
    
    def evaluate_market_conditions(self, df: pd.DataFrame) -> Dict:
        """
        Evaluate overall market conditions for suitability of SMC trading
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            
        Returns:
            dict: Market condition evaluation
        """
        # Calculate volatility (ATR as percentage of price)
        atr = self._calculate_atr(df, 14)
        current_price = df['close'].iloc[-1]
        volatility = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Calculate average volume
        recent_volume = df['volume'].iloc[-10:].mean()
        avg_volume = df['volume'].iloc[-30:-10].mean()
        volume_change = (recent_volume / avg_volume - 1) * 100 if avg_volume > 0 else 0
        
        # Determine trend strength using ADX-like calculation
        trend_strength = self._calculate_trend_strength(df)
        
        # Evaluate market conditions
        conditions = {
            'volatility': volatility,
            'volume_change': volume_change,
            'trend_strength': trend_strength
        }
        
        # Determine if conditions are suitable for SMC trading
        if volatility < 0.2:
            conditions['volatility_status'] = 'low'
            conditions['suitable'] = False
            conditions['reason'] = 'Low volatility environment'
        elif volatility > 2.0:
            conditions['volatility_status'] = 'high'
            conditions['suitable'] = False
            conditions['reason'] = 'Excessive volatility'
        else:
            conditions['volatility_status'] = 'normal'
            conditions['suitable'] = True
        
        # Volume considerations
        if volume_change < -30:
            conditions['volume_status'] = 'declining'
            if conditions['suitable']:
                conditions['suitable'] = False
                conditions['reason'] = 'Significantly declining volume'
        elif volume_change > 50:
            conditions['volume_status'] = 'increasing'
        else:
            conditions['volume_status'] = 'stable'
        
        # Trend strength considerations
        if trend_strength < 15:
            conditions['trend_status'] = 'weak'
            if conditions['suitable']:
                conditions['suitable'] = False
                conditions['reason'] = 'Weak trend strength'
        elif trend_strength > 40:
            conditions['trend_status'] = 'strong'
        else:
            conditions['trend_status'] = 'moderate'
        
        return conditions
    
    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate trend strength (similar to ADX)
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            period (int): Calculation period
            
        Returns:
            float: Trend strength value
        """
        try:
            # Calculate +DI and -DI
            df = df.copy()
            df['tr'] = df.apply(
                lambda x: max(
                    [
                        x['high'] - x['low'],
                        abs(x['high'] - x['close'].shift(1)),
                        abs(x['low'] - x['close'].shift(1))
                    ]
                ),
                axis=1
            )
            
            df['up_move'] = df['high'] - df['high'].shift(1)
            df['down_move'] = df['low'].shift(1) - df['low']
            
            df['+dm'] = np.where(
                (df['up_move'] > df['down_move']) & (df['up_move'] > 0),
                df['up_move'],
                0
            )
            
            df['-dm'] = np.where(
                (df['down_move'] > df['up_move']) & (df['down_move'] > 0),
                df['down_move'],
                0
            )
            
            # Calculate smoothed values
            df['tr14'] = df['tr'].rolling(window=period).sum()
            df['+dm14'] = df['+dm'].rolling(window=period).sum()
            df['-dm14'] = df['-dm'].rolling(window=period).sum()
            
            # Calculate +DI and -DI
            df['+di'] = 100 * df['+dm14'] / df['tr14']
            df['-di'] = 100 * df['-dm14'] / df['tr14']
            
            # Calculate DX and ADX
            df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
            df['adx'] = df['dx'].rolling(window=period).mean()
            
            # Return the latest ADX value
            return df['adx'].iloc[-1]
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 0
    
    def filter_signals_by_timeframe_alignment(self, signals: List[Dict], mtf_analysis: Dict) -> List[Dict]:
        """
        Filter signals based on alignment with higher timeframe bias
        
        Args:
            signals (list): List of trading signals
            mtf_analysis (dict): Multi-timeframe analysis results
            
        Returns:
            list: Filtered signals
        """
        if not signals or not mtf_analysis:
            return signals
        
        # Extract overall bias from MTF analysis
        overall_bias = mtf_analysis.get('overall_bias', 'neutral')
        bias_strength = mtf_analysis.get('bias_strength', 0)
        
        # If bias is neutral or weak, return all signals
        if overall_bias == 'neutral' or bias_strength < 30:
            return signals
        
        # Filter signals that align with the overall bias
        aligned_signals = []
        for signal in signals:
            signal_type = signal.get('type', '')
            
            # Check if signal aligns with overall bias
            if (overall_bias == 'bullish' and signal_type == 'buy') or \
               (overall_bias == 'bearish' and signal_type == 'sell'):
                # Increase strength for aligned signals
                signal['strength'] = min(100, signal.get('strength', 0) + bias_strength // 4)
                signal['reason'] += f" (Aligned with {overall_bias} bias on higher timeframes)"
                aligned_signals.append(signal)
        
        # If no aligned signals, return original signals but with reduced strength
        if not aligned_signals:
            for signal in signals:
                signal['strength'] = max(10, signal.get('strength', 0) - bias_strength // 3)
                signal['reason'] += f" (Caution: Against {overall_bias} bias on higher timeframes)"
            return signals
        
        return aligned_signals
    
    def get_best_signal(self, signals: List[Dict]) -> Optional[Dict]:
        """
        Get the best trading signal from a list of signals
        
        Args:
            signals (list): List of trading signals
            
        Returns:
            dict or None: Best signal or None if no valid signals
        """
        if not signals:
            return None
        
        # Sort by strength (descending)
        sorted_signals = sorted(signals, key=lambda x: x.get('strength', 0), reverse=True)
        
        # Get the strongest signal
        best_signal = sorted_signals[0]
        
        # Ensure minimum criteria are met
        if best_signal.get('strength', 0) < 30 or best_signal.get('risk_reward', 0) < self.min_risk_reward:
            return None
        
        return best_signal
    
    def backtest(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Backtest the SMC strategy on historical data
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Backtest results
        """
        logger.info(f"Backtesting SMC strategy on {symbol} {timeframe}")
        
        # Initialize results
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'trades': [],
            'win_rate': 0,
            'profit_factor': 0,
            'total_return': 0,
            'max_drawdown': 0
        }
        
        # Minimum required candles for analysis
        min_candles = 100
        
        # Ensure we have enough data
        if len(df) < min_candles:
            logger.warning(f"Not enough data for backtesting: {len(df)} candles")
            return results
        
        # Initialize tracking variables
        trades = []
        equity_curve = [1000]  # Starting with $1000
        max_equity = 1000
        current_drawdown = 0
        max_drawdown = 0
        
        # Process each candle (starting from min_candles to have enough history)
        for i in range(min_candles, len(df) - 1):
            # Get historical data up to current candle
            historical_data = df.iloc[:i+1].copy()
            
            # Analyze for signals
            analysis = self.analyze(historical_data, symbol, timeframe)
            signals = analysis.get('signals', [])
            
            # Check for valid signals
            if signals:
                best_signal = self.get_best_signal(signals)
                
                if best_signal:
                    # Extract signal details
                    signal_type = best_signal.get('type', '')
                    entry = best_signal.get('entry', 0)
                    stop_loss = best_signal.get('stop_loss', 0)
                    take_profit = best_signal.get('take_profit', 0)
                    
                    # Simulate trade execution in next candle
                    next_candle = df.iloc[i+1]
                    
                    # Check if signal was triggered
                    triggered = False
                    exit_price = None
                    exit_type = None
                    
                    if signal_type == 'buy':
                        # Buy signal is triggered if price goes below entry in next candle
                        if next_candle['low'] <= entry <= next_candle['high']:
                            triggered = True
                            
                            # Check if stop loss was hit
                            if next_candle['low'] <= stop_loss:
                                exit_price = stop_loss
                                exit_type = 'stop_loss'
                            # Check if take profit was hit
                            elif next_candle['high'] >= take_profit:
                                exit_price = take_profit
                                exit_type = 'take_profit'
                    
                    elif signal_type == 'sell':
                        # Sell signal is triggered if price goes above entry in next candle
                        if next_candle['low'] <= entry <= next_candle['high']:
                            triggered = True
                            
                            # Check if stop loss was hit
                            if next_candle['high'] >= stop_loss:
                                exit_price = stop_loss
                                exit_type = 'stop_loss'
                            # Check if take profit was hit
                            elif next_candle['low'] <= take_profit:
                                exit_price = take_profit
                                exit_type = 'take_profit'
                    
                    # If signal was triggered but not closed in the same candle
                    if triggered and not exit_price:
                        # Simulate trade through subsequent candles
                        for j in range(i+2, min(i+20, len(df))):  # Look ahead up to 20 candles
                            future_candle = df.iloc[j]
                            
                            if signal_type == 'buy':
                                # Check if stop loss was hit
                                if future_candle['low'] <= stop_loss:
                                    exit_price = stop_loss
                                    exit_type = 'stop_loss'
                                    break
                                # Check if take profit was hit
                                elif future_candle['high'] >= take_profit:
                                    exit_price = take_profit
                                    exit_type = 'take_profit'
                                    break
                            
                            elif signal_type == 'sell':
                                # Check if stop loss was hit
                                if future_candle['high'] >= stop_loss:
                                    exit_price = stop_loss
                                    exit_type = 'stop_loss'
                                    break
                                # Check if take profit was hit
                                elif future_candle['low'] <= take_profit:
                                    exit_price = take_profit
                                    exit_type = 'take_profit'
                                    break
                        
                        # If trade wasn't closed within the look-ahead period, close at the last candle
                        if not exit_price:
                            exit_price = df.iloc[min(i+20, len(df)-1)]['close']
                            exit_type = 'timeout'
                    
                    # If trade was triggered, record it
                    if triggered:
                        # Calculate profit/loss
                        if signal_type == 'buy':
                            profit_pct = (exit_price - entry) / entry * 100
                        else:  # sell
                            profit_pct = (entry - exit_price) / entry * 100
                        
                        # Record trade
                        trade = {
                            'entry_date': df.index[i+1] if hasattr(df.index, '__getitem__') else i+1,
                            'exit_date': df.index[j] if hasattr(df.index, '__getitem__') and 'j' in locals() else None,
                            'type': signal_type,
                            'entry': entry,
                            'exit': exit_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'exit_type': exit_type,
                            'profit_pct': profit_pct,
                            'reason': best_signal.get('reason', '')
                        }
                        trades.append(trade)
                        
                        # Update equity curve
                        last_equity = equity_curve[-1]
                        new_equity = last_equity * (1 + profit_pct / 100)
                        equity_curve.append(new_equity)
                        
                        # Update drawdown calculations
                        max_equity = max(max_equity, new_equity)
                        current_drawdown = (max_equity - new_equity) / max_equity * 100
                        max_drawdown = max(max_drawdown, current_drawdown)
                        
                        # Skip a few candles after a trade to avoid overtrading
                        i += 5
        
        # Calculate performance metrics
        if trades:
            # Win rate
            winning_trades = [t for t in trades if t['profit_pct'] > 0]
            win_rate = len(winning_trades) / len(trades) * 100
            
            # Profit factor
            gross_profit = sum([t['profit_pct'] for t in trades if t['profit_pct'] > 0])
            gross_loss = abs(sum([t['profit_pct'] for t in trades if t['profit_pct'] <= 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Total return
            total_return = (equity_curve[-1] / equity_curve[0] - 1) * 100
            
            # Update results
            results['trades'] = trades
            results['win_rate'] = win_rate
            results['profit_factor'] = profit_factor
            results['total_return'] = total_return
            results['max_drawdown'] = max_drawdown
            results['equity_curve'] = equity_curve
        
        logger.info(f"Backtest completed for {symbol} {timeframe}: {len(trades)} trades, {results['win_rate']:.2f}% win rate")
        return results
    
    def optimize_parameters(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Optimize strategy parameters based on historical data
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Optimized parameters
        """
        logger.info(f"Optimizing SMC strategy parameters for {symbol} {timeframe}")
        
        # Parameters to optimize
        min_rr_values = [1.5, 2.0, 2.5, 3.0]
        
        best_results = None
        best_params = None
        best_score = -float('inf')
        
        # Test different parameter combinations
        for min_rr in min_rr_values:
            # Set parameters
            self.min_risk_reward = min_rr
            
            # Run backtest with these parameters
            results = self.backtest(df, symbol, timeframe)
            
            # Calculate score (balance between return and drawdown)
            if results['trades']:
                score = results['total_return'] * results['win_rate'] / 100 - results['max_drawdown']
                
                # Update best parameters if score is better
                if score > best_score:
                    best_score = score
                    best_results = results
                    best_params = {'min_risk_reward': min_rr}
        
        # Restore original parameters
        self.min_risk_reward = 2.0
        
        # Return best parameters and results
        return {
            'parameters': best_params,
            'results': best_results,
            'score': best_score
        }
    
    def get_market_context(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Get broader market context for decision making
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            symbol (str): Trading symbol
            
        Returns:
            dict: Market context information
        """
        # Calculate key metrics
        current_price = df['close'].iloc[-1]
        
        # Calculate distance from key moving averages
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        
        ma20 = df['ma20'].iloc[-1]
        ma50 = df['ma50'].iloc[-1]
        ma200 = df['ma200'].iloc[-1]
        
        distance_ma20 = (current_price / ma20 - 1) * 100
        distance_ma50 = (current_price / ma50 - 1) * 100
        distance_ma200 = (current_price / ma200 - 1) * 100
        
        # Determine if price is extended from moving averages
        extended_from_ma20 = abs(distance_ma20) > 3
        extended_from_ma50 = abs(distance_ma50) > 5
        
        # Calculate recent volatility
        recent_atr = self._calculate_atr(df.iloc[-20:], 14)
        normal_atr = self._calculate_atr(df.iloc[-50:-20], 14)
        
        volatility_change = (recent_atr / normal_atr - 1) * 100 if normal_atr else 0
        
        # Determine market phase
        if ma20 > ma50 > ma200 and current_price > ma20:
            market_phase = "strong_uptrend"
        elif ma20 > ma50 and current_price > ma20:
            market_phase = "uptrend"
        elif ma20 < ma50 < ma200 and current_price < ma20:
            market_phase = "strong_downtrend"
        elif ma20 < ma50 and current_price < ma20:
            market_phase = "downtrend"
        elif abs(distance_ma50) < 1 and abs(ma50 / ma200 - 1) < 0.01:
            market_phase = "ranging_tight"
        else:
            market_phase = "ranging"
        
        # Return market context
        return {
            'symbol': symbol,
            'current_price': current_price,
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'distance_ma20': distance_ma20,
            'distance_ma50': distance_ma50,
            'distance_ma200': distance_ma200,
            'extended_from_ma20': extended_from_ma20,
            'extended_from_ma50': extended_from_ma50,
            'volatility_change': volatility_change,
            'market_phase': market_phase
        }
    
    def adjust_for_market_conditions(self, signals: List[Dict], market_context: Dict) -> List[Dict]:
        """
        Adjust signals based on broader market conditions
        
        Args:
            signals (list): List of trading signals
            market_context (dict): Market context information
            
        Returns:
            list: Adjusted signals
        """
        if not signals:
            return signals
        
        market_phase = market_context.get('market_phase', 'unknown')
        extended_from_ma20 = market_context.get('extended_from_ma20', False)
        extended_from_ma50 = market_context.get('extended_from_ma50', False)
        volatility_change = market_context.get('volatility_change', 0)
        
        adjusted_signals = []
        
        for signal in signals:
            signal_type = signal.get('type', '')
            original_strength = signal.get('strength', 50)
            
            # Adjust strength based on market conditions
            adjusted_strength = original_strength
            
            # Adjust for market phase
            if signal_type == 'buy':
                if market_phase in ['strong_uptrend', 'uptrend']:
                    adjusted_strength += 10
                    signal['reason'] += " (Aligned with uptrend)"
                elif market_phase in ['strong_downtrend', 'downtrend']:
                    adjusted_strength -= 20
                    signal['reason'] += " (Caution: Against downtrend)"
            else:  # sell
                if market_phase in ['strong_downtrend', 'downtrend']:
                    adjusted_strength += 10
                    signal['reason'] += " (Aligned with downtrend)"
                elif market_phase in ['strong_uptrend', 'uptrend']:
                    adjusted_strength -= 20
                    signal['reason'] += " (Caution: Against uptrend)"
            
            # Adjust for extended price
            if extended_from_ma20 or extended_from_ma50:
                if (signal_type == 'buy' and market_context.get('distance_ma20', 0) > 0) or \
                   (signal_type == 'sell' and market_context.get('distance_ma20', 0) < 0):
                    adjusted_strength -= 15
                    signal['reason'] += " (Caution: Extended from moving averages)"
            
            # Adjust for volatility changes
            if abs(volatility_change) > 50:
                adjusted_strength -= 10
                signal['reason'] += " (Caution: Abnormal volatility change)"
            
            # Ensure strength is within bounds
            signal['strength'] = max(10, min(100, adjusted_strength))
            
            # Add to adjusted signals if still valid
            if signal['strength'] >= 30:
                adjusted_signals.append(signal)
        
        return adjusted_signals
    
    def generate_trade_report(self, signal: Dict, market_context: Dict) -> Dict:
        """
        Generate a comprehensive trade report for a signal
        
        Args:
            signal (dict): Trading signal
            market_context (dict): Market context information
            
        Returns:
            dict: Trade report
        """
        # Extract key information
        symbol = signal.get('symbol', '')
        signal_type = signal.get('type', '')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        risk_reward = signal.get('risk_reward', 0)
        reason = signal.get('reason', '')
        strength = signal.get('strength', 0)
        
        # Calculate risk and reward percentages
        risk_pct = abs(entry - stop_loss) / entry * 100
        reward_pct = abs(entry - take_profit) / entry * 100
        
        # Create trade report
        report = {
            'symbol': symbol,
            'direction': 'LONG' if signal_type == 'buy' else 'SHORT',
            'entry_price': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward_ratio': risk_reward,
            'risk_percentage': risk_pct,
            'reward_percentage': reward_pct,
            'signal_strength': strength,
            'reason': reason,
            'market_phase': market_context.get('market_phase', 'unknown'),
            'ma20_distance': market_context.get('distance_ma20', 0),
            'ma50_distance': market_context.get('distance_ma50', 0),
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'strategy': 'SMC'
        }
        
        # Add confidence rating based on signal strength
        if strength >= 80:
            report['confidence'] = 'Very High'
        elif strength >= 65:
            report['confidence'] = 'High'
        elif strength >= 50:
            report['confidence'] = 'Medium'
        elif strength >= 35:
            report['confidence'] = 'Low'
        else:
            report['confidence'] = 'Very Low'
        
        return report
    
    def get_trade_management_plan(self, signal: Dict) -> Dict:
        """
        Generate a trade management plan for a signal
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade management plan
        """
        # Extract key information
        signal_type = signal.get('type', '')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        
        # Calculate risk in price points
        risk = abs(entry - stop_loss)
        
        # Calculate partial take profit levels
        if signal_type == 'buy':
            tp1 = entry + risk  # 1:1 R:R
            tp2 = entry + risk * 2  # 2:1 R:R
            tp3 = take_profit  # Full target
        else:  # sell
            tp1 = entry - risk  # 1:1 R:R
            tp2 = entry - risk * 2  # 2:1 R:R
            tp3 = take_profit  # Full target
        
        # Calculate position size distribution
        position_distribution = {
            'tp1': 0.3,  # 30% of position at 1:1
            'tp2': 0.4,  # 40% of position at 2:1
            'tp3': 0.3   # 30% of position at full target
        }
        
        # Calculate breakeven move
        breakeven_move = {
            'price': entry,
            'after_tp': 'tp1',
            'description': 'Move stop loss to entry after first target is hit'
        }
        
        # Calculate trailing stop parameters
        trailing_stop = {
            'activate_at': tp2,
            'trail_by_percentage': 1.0,  # Trail by 1% of price
            'description': 'Activate trailing stop after second target is hit'
        }
        
        # Create management plan
        plan = {
            'entry': entry,
            'initial_stop_loss': stop_loss,
            'take_profit_levels': {
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3
            },
            'position_distribution': position_distribution,
            'breakeven_move': breakeven_move,
            'trailing_stop': trailing_stop,
            'max_trade_duration': '5 days',
            'notes': 'Monitor price action at each take profit level. Exit full position if market structure changes against trade direction.'
        }
        
        return plan
    
    def analyze_trade_outcome(self, trade: Dict, df: pd.DataFrame) -> Dict:
        """
        Analyze the outcome of a completed trade for learning
        
        Args:
            trade (dict): Completed trade information
            df (pd.DataFrame): OHLCV dataframe covering the trade period
            
        Returns:
            dict: Trade analysis
        """
        # Extract key information
        entry_date = trade.get('entry_date')
        exit_date = trade.get('exit_date')
        trade_type = trade.get('type', '')
        entry = trade.get('entry', 0)
        exit_price = trade.get('exit', 0)
        stop_loss = trade.get('stop_loss', 0)
        take_profit = trade.get('take_profit', 0)
        exit_type = trade.get('exit_type', '')
        profit_pct = trade.get('profit_pct', 0)
        
        # Find entry and exit indices
        if isinstance(entry_date, pd.Timestamp) and isinstance(df.index, pd.DatetimeIndex):
            entry_idx = df.index.get_indexer([entry_date], method='nearest')[0]
            exit_idx = df.index.get_indexer([exit_date], method='nearest')[0] if exit_date else len(df) - 1
        else:
            # Fallback to using integers if dates aren't available
            entry_idx = entry_date if isinstance(entry_date, int) else 0
            exit_idx = exit_date if isinstance(exit_date, int) else len(df) - 1
        
        # Ensure indices are valid
        entry_idx = max(0, min(entry_idx, len(df) - 1))
        exit_idx = max(entry_idx, min(exit_idx, len(df) - 1))
        
        # Extract trade duration
        trade_duration = exit_idx - entry_idx
        
        # Calculate maximum favorable excursion (MFE)
        mfe = 0
        if trade_type == 'buy':
            max_high = df['high'].iloc[entry_idx:exit_idx+1].max()
            mfe = (max_high - entry) / entry * 100
        else:  # sell
            min_low = df['low'].iloc[entry_idx:exit_idx+1].min()
            mfe = (entry - min_low) / entry * 100
        
        # Calculate maximum adverse excursion (MAE)
        mae = 0
        if trade_type == 'buy':
            min_low = df['low'].iloc[entry_idx:exit_idx+1].min()
            mae = (entry - min_low) / entry * 100
        else:  # sell
            max_high = df['high'].iloc[entry_idx:exit_idx+1].max()
            mae = (max_high - entry) / entry * 100
        
        # Determine if stop loss was too tight
        stop_too_tight = mae > 0 and abs(entry - stop_loss) / entry * 100 < mae * 0.8
        
        # Determine if take profit was too conservative
        tp_too_conservative = mfe > 0 and abs(take_profit - entry) / entry * 100 < mfe * 0.7
        
        # Analyze market conditions during trade
        market_conditions = self.evaluate_market_conditions(df.iloc[max(0, entry_idx-20):entry_idx+1])
        
        # Determine what went right/wrong
        strengths = []
        weaknesses = []
        
        if profit_pct > 0:
            strengths.append("Trade was profitable")
            if exit_type == 'take_profit':
                strengths.append("Take profit target was reached")
            if mae < 0.5:
                strengths.append("Price moved favorably with minimal drawdown")
        else:
            weaknesses.append("Trade was unprofitable")
            if exit_type == 'stop_loss':
                weaknesses.append("Stop loss was triggered")
            if stop_too_tight:
                weaknesses.append("Stop loss may have been too tight")
        
        if tp_too_conservative and profit_pct > 0:
            weaknesses.append("Take profit may have been too conservative")
        
        if market_conditions.get('suitable', True) == False:
            weaknesses.append(f"Market conditions were not ideal: {market_conditions.get('reason', 'unknown')}")
        
        # Create analysis report
        analysis = {
            'profit_percentage': profit_pct,
            'outcome': 'win' if profit_pct > 0 else 'loss',
            'exit_type': exit_type,
            'trade_duration': trade_duration,
            'maximum_favorable_excursion': mfe,
            'maximum_adverse_excursion': mae,
            'stop_too_tight': stop_too_tight,
            'take_profit_too_conservative': tp_too_conservative,
            'market_conditions': market_conditions,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'lessons': self._generate_trade_lessons(profit_pct, exit_type, stop_too_tight, tp_too_conservative, market_conditions)
        }
        
        return analysis
    
    def _generate_trade_lessons(self, profit_pct: float, exit_type: str, stop_too_tight: bool, 
                               tp_too_conservative: bool, market_conditions: Dict) -> List[str]:
        """
        Generate lessons learned from a trade
        
        Args:
            profit_pct (float): Profit percentage
            exit_type (str): Exit type
            stop_too_tight (bool): Whether stop loss was too tight
            tp_too_conservative (bool): Whether take profit was too conservative
            market_conditions (dict): Market conditions during trade
            
        Returns:
            list: Lessons learned
        """
        lessons = []
        
        if profit_pct <= 0:
            if exit_type == 'stop_loss' and stop_too_tight:
                lessons.append("Consider using wider stops to accommodate normal market volatility")
            
            if not market_conditions.get('suitable', True):
                lessons.append(f"Avoid trading in unsuitable market conditions: {market_conditions.get('reason', 'unknown')}")
            
            if exit_type == 'timeout':
                lessons.append("Consider implementing a time-based exit strategy for trades that don't reach targets")
        
        else:  # profitable trade
            if tp_too_conservative:
                lessons.append("Consider using wider take profit targets or implementing a trailing stop to capture larger moves")
            
            if exit_type == 'take_profit' and profit_pct > 5:
                lessons.append("Strong move in favor of trade - consider scaling out of positions to let winners run")
        
        # General lessons
        if market_conditions.get('volatility', 0) > 1.5:
            lessons.append("In high volatility environments, consider wider stops and take profits")
        
        return lessons
    
    def get_strategy_performance_metrics(self, backtest_results: Dict) -> Dict:
        """
        Calculate comprehensive performance metrics for the strategy
        
        Args:
            backtest_results (dict): Results from backtest
            
        Returns:
            dict: Performance metrics
        """
        trades = backtest_results.get('trades', [])
        equity_curve = backtest_results.get('equity_curve', [1000])
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'average_profit': 0,
                'average_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'total_return': 0,
                'annualized_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_loss_ratio': 0
            }
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_pct'] > 0]
        losing_trades = [t for t in trades if t['profit_pct'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # Profit metrics
        gross_profit = sum([t['profit_pct'] for t in winning_trades])
        gross_loss = abs(sum([t['profit_pct'] for t in losing_trades]))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        average_profit = gross_profit / len(winning_trades) if winning_trades else 0
        average_loss = gross_loss / len(losing_trades) if losing_trades else 0
        
        win_loss_ratio = average_profit / average_loss if average_loss > 0 else float('inf')
        
        largest_win = max([t['profit_pct'] for t in trades]) if trades else 0
        largest_loss = min([t['profit_pct'] for t in trades]) if trades else 0
        
        # Return metrics
        total_return = (equity_curve[-1] / equity_curve[0] - 1) * 100
        
        # Estimate annualized return (assuming 252 trading days per year)
        if len(trades) >= 2:
            first_trade_date = trades[0].get('entry_date')
            last_trade_date = trades[-1].get('exit_date', trades[-1].get('entry_date'))
            
            if isinstance(first_trade_date, pd.Timestamp) and isinstance(last_trade_date, pd.Timestamp):
                days = (last_trade_date - first_trade_date).days
                years = days / 365 if days > 0 else 1
                annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
            else:
                # Fallback if dates aren't available
                annualized_return = total_return
        else:
            annualized_return = total_return
        
        # Risk metrics
        max_drawdown = backtest_results.get('max_drawdown', 0)
        
        # Calculate Sharpe ratio (simplified)
        if len(equity_curve) > 1:
            returns = [(equity_curve[i] / equity_curve[i-1] - 1) for i in range(1, len(equity_curve))]
            avg_return = sum(returns) / len(returns)
            std_return = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5
            sharpe_ratio = (avg_return * 252 ** 0.5) / (std_return * 252 ** 0.5) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Compile metrics
        metrics = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_profit': average_profit,
            'average_loss': average_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_loss_ratio': win_loss_ratio,
            'expectancy': (win_rate / 100 * average_profit) - ((100 - win_rate) / 100 * average_loss)
        }
        
        return metrics
    
    def get_strategy_summary(self) -> Dict:
        """
        Get a summary of the SMC strategy configuration and performance
        
        Returns:
            dict: Strategy summary
        """
        return {
            'name': self.name,
            'description': 'Smart Money Concepts (SMC) trading strategy based on order blocks, fair value gaps, and market structure',
            'parameters': {
                'min_risk_reward': self.min_risk_reward
            },
            'key_concepts': [
                'Order Blocks (OB)',
                'Fair Value Gaps (FVG)',
                'Market Structure Breaks (MSB)',
                'Liquidity Sweeps',
                'Higher Highs/Higher Lows (HH/HL)',
                'Lower Lows/Lower Highs (LL/LH)'
            ],
            'strengths': [
                'Identifies high-probability reversal zones',
                'Focuses on institutional order flow',
                'Provides clear entry, stop loss, and take profit levels',
                'Adaptable to multiple timeframes and markets'
            ],
            'weaknesses': [
                'Requires experience to identify patterns correctly',
                'Can generate false signals in ranging markets',
                'Subjective elements in pattern identification'
            ],
            'best_market_conditions': [
                'Trending markets with clear market structure',
                'Markets with sufficient volatility',
                'Liquid markets with institutional participation'
            ],
            'recommended_timeframes': [
                '1h', '4h', '1d'
            ],
            'version': '1.0.0'
        }
