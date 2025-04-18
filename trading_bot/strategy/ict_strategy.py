"""
ICT (Inner Circle Trader) strategy implementation
Uses ICT concepts like market structure, liquidity, and order blocks
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

from trading_bot.strategy.strategy_base import Strategy
from trading_bot.analysis.smc_analyzer import SMCAnalyzer

logger = logging.getLogger(__name__)

class ICTStrategy(Strategy):
    """
    ICT (Inner Circle Trader) trading strategy
    Implements trading logic based on ICT principles
    """
    
    def __init__(self):
        """Initialize the ICT strategy"""
        super().__init__("Inner Circle Trader")
        self.analyzer = SMCAnalyzer()  # Reuse the SMC analyzer which has ICT methods
        self.min_risk_reward = 2.0
        self.last_analysis = None
        
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """
        Analyze market data using ICT principles
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            dict: Analysis results
        """
        logger.info(f"Analyzing {symbol} on {timeframe} timeframe using ICT strategy")
        
        # Use the SMC analyzer to analyze the chart
        smc_analysis = self.analyzer.analyze_chart(df, symbol)
        
        # Add ICT-specific analysis
        ict_concepts = self.analyzer.identify_ict_concepts(df)
        
        # Combine SMC and ICT analysis
        analysis = {**smc_analysis, 'ict_concepts': ict_concepts}
        
        # Add timeframe information
        analysis['timeframe'] = timeframe
        
        # Store the last price for signal generation
        if not df.empty:
            analysis['current_price'] = df['close'].iloc[-1]
            # Store the original dataframe for reference
            self.last_analysis = analysis
        
        # Generate signals based on the analysis
        signals = self.generate_signals(analysis)
        analysis['signals'] = signals
        
        logger.info(f"ICT analysis for {symbol} on {timeframe} complete. Found {len(signals)} signals.")
        
        return analysis
    
    def generate_signals(self, analysis: Dict) -> List[Dict]:
        """
        Generate trading signals from ICT analysis
        
        Args:
            analysis (dict): ICT analysis results
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Extract key components from analysis
        symbol = analysis.get('symbol', '')
        ict_concepts = analysis.get('ict_concepts', {})
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
        
        # Signal 1: OTE (Optimal Trade Entry) Zones
        signals.extend(self._generate_ote_signals(
            symbol, ict_concepts.get('ote_zones', []), bias, current_price
        ))
        
        # Signal 2: Breaker Blocks
        signals.extend(self._generate_breaker_signals(
            symbol, ict_concepts.get('breaker_blocks', []), bias, current_price
        ))
        
        # Signal 3: Kill Zone Setups (London/NY session)
        signals.extend(self._generate_kill_zone_signals(
            symbol, ict_concepts.get('kill_zones', {}), bias, current_price
        ))
        
        # Signal 4: Fair Value Gap + Order Block
        signals.extend(self._generate_fvg_ob_signals(
            symbol, fair_value_gaps, order_blocks, bias, current_price
        ))
        
        # Filter signals by risk-reward ratio
        valid_signals = [s for s in signals if s.get('risk_reward', 0) >= self.min_risk_reward]
        
        # Sort by strength (descending)
        valid_signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        return valid_signals
    
    def _generate_ote_signals(self, symbol: str, ote_zones: List[Dict], 
                             bias: str, current_price: float) -> List[Dict]:
        """Generate signals based on Optimal Trade Entry zones"""
        signals = []
        
        # Filter for recent OTE zones (less than 20 candles old)
        recent_otes = [ote for ote in ote_zones if ote.get('age', 100) < 20]
        
        for ote in recent_otes:
            ote_type = ote.get('type', '')
            ote_top = ote.get('top', 0)
            ote_bottom = ote.get('bottom', 0)
            ote_strength = ote.get('strength', 50)
            
            # Check if price is near the OTE zone
            if ote_type == 'bullish' and current_price <= ote_top * 1.01 and current_price >= ote_bottom * 0.99:
                # Bullish signal
                stop_loss = ote_bottom * 0.995  # Just below the OTE zone
                
                # Calculate take profit - handle the case where df might be None
                try:
                    take_profit, risk_reward = self.analyzer.find_optimal_take_profit(
                        None,  # We don't have the df here, but the method can handle it
                        current_price,
                        stop_loss,
                        'buy',
                        min_rr=2.0
                    )
                except (TypeError, AttributeError) as e:
                    # If the method fails, calculate a simple 1:2 risk-reward ratio
                    logger.warning(f"Error finding optimal take profit: {e}. Using simple calculation.")
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * 2)
                    risk_reward = 2.0
                
                signals.append({
                    'symbol': symbol,
                    'type': 'buy',
                    'entry': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'risk_reward': risk_reward,
                    'strength': ote_strength,
                    'reason': f"ICT Bullish OTE Zone: {ote_bottom:.5f}-{ote_top:.5f}"
                })
            
            elif ote_type == 'bearish' and current_price >= ote_bottom * 0.99 and current_price <= ote_top * 1.01:
                # Bearish signal
                stop_loss = ote_top * 1.005  # Just above the OTE zone
                
                # Calculate take profit - handle the case where df might be None
                try:
                    take_profit, risk_reward = self.analyzer.find_optimal_take_profit(
                        None,  # We don't have the df here, but the method can handle it
                        current_price,
                        stop_loss,
                        'sell',
                        min_rr=2.0
                    )
                except (TypeError, AttributeError):
                    # If the method fails, calculate a simple 1:2 risk-reward ratio
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * 2)
                    risk_reward = 2.0
                
                signals.append({
                    'symbol': symbol,
                    'type': 'sell',
                    'entry': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'risk_reward': risk_reward,
                    'strength': ote_strength,
                    'reason': f"ICT Bearish OTE Zone: {ote_bottom:.5f}-{ote_top:.5f}"
                })
        
        return signals
    
    def _generate_breaker_signals(self, symbol: str, breaker_blocks: List[Dict],
                                bias: str, current_price: float) -> List[Dict]:
        """
        Generate signals based on Breaker Blocks
        
        Args:
            symbol (str): Trading symbol
            breaker_blocks (list): Breaker blocks
            bias (str): Market bias
            current_price (float): Current price
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Filter for recent breaker blocks (less than 20 candles old)
        recent_blocks = [block for block in breaker_blocks if block.get('age', 100) < 20]
        
        for block in recent_blocks:
            block_type = block.get('type', '')
            block_top = block.get('top', 0)
            block_bottom = block.get('bottom', 0)
            
            # Check if price is near the block
            price_near_block = (
                (block_type == 'bullish' and current_price < block_top * 1.02) or
                (block_type == 'bearish' and current_price > block_bottom * 0.98)
            )
            
            if price_near_block:
                # Generate signal based on block type
                if block_type == 'bullish' and (bias == 'bullish' or bias == 'neutral'):
                    # Bullish signal
                    stop_loss = block_bottom * 0.995  # Just below the block
                    
                    # Take profit at a 1:3 risk-reward ratio
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * 3)
                    
                    signals.append({
                        'symbol': symbol,
                        'type': 'buy',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': 3.0,
                        'strength': block.get('strength', 65),
                        'reason': f"ICT Bullish Breaker Block at {block_bottom:.5f}-{block_top:.5f}"
                    })
                
                elif block_type == 'bearish' and (bias == 'bearish' or bias == 'neutral'):
                    # Bearish signal
                    stop_loss = block_top * 1.005  # Just above the block
                    
                    # Take profit at a 1:3 risk-reward ratio
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * 3)
                    
                    signals.append({
                        'symbol': symbol,
                        'type': 'sell',
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': 3.0,
                        'strength': block.get('strength', 65),
                        'reason': f"ICT Bearish Breaker Block at {block_bottom:.5f}-{block_top:.5f}"
                    })
        
        return signals
    
    def _generate_kill_zone_signals(self, symbol: str, kill_zones: Dict,
                                  bias: str, current_price: float) -> List[Dict]:
        """
        Generate signals based on Kill Zones (London/NY sessions)
        
        Args:
            symbol (str): Trading symbol
            kill_zones (dict): Kill zones analysis
            bias (str): Market bias
            current_price (float): Current price
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Check London session
        london = kill_zones.get('london', {})
        london_bias = london.get('bias', 'neutral')
        london_strength = london.get('strength', 0)
        
        # Check New York session
        new_york = kill_zones.get('new_york', {})
        ny_bias = new_york.get('bias', 'neutral')
        ny_strength = new_york.get('strength', 0)
        
        # Generate signals if session bias is strong and aligns with overall bias
        if london_bias == 'bullish' and london_strength > 70 and (bias == 'bullish' or bias == 'neutral'):
            # Bullish London session signal
            # Calculate stop loss based on average range
            avg_range = london.get('avg_range', 0.5)
            stop_loss = current_price * (1 - avg_range / 100)
            
            # Take profit at a 1:2 risk-reward ratio
            risk = current_price - stop_loss
            take_profit = current_price + (risk * 2)
            
            signals.append({
                'symbol': symbol,
                'type': 'buy',
                'entry': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': 2.0,
                'strength': london_strength,
                'reason': f"ICT London Kill Zone: Strong bullish bias ({london_strength}%)"
            })
        
        elif london_bias == 'bearish' and london_strength > 70 and (bias == 'bearish' or bias == 'neutral'):
            # Bearish London session signal
            # Calculate stop loss based on average range
            avg_range = london.get('avg_range', 0.5)
            stop_loss = current_price * (1 + avg_range / 100)
            
            # Take profit at a 1:2 risk-reward ratio
            risk = stop_loss - current_price
            take_profit = current_price - (risk * 2)
            
            signals.append({
                'symbol': symbol,
                'type': 'sell',
                'entry': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': 2.0,
                'strength': london_strength,
                'reason': f"ICT London Kill Zone: Strong bearish bias ({london_strength}%)"
            })
        
        # Similar logic for New York session
        if ny_bias == 'bullish' and ny_strength > 70 and (bias == 'bullish' or bias == 'neutral'):
            # Bullish New York session signal
            # Calculate stop loss based on average range
            avg_range = new_york.get('avg_range', 0.5)
            stop_loss = current_price * (1 - avg_range / 100)
            
            # Take profit at a 1:2 risk-reward ratio
            risk = current_price - stop_loss
            take_profit = current_price + (risk * 2)
            
            signals.append({
                'symbol': symbol,
                'type': 'buy',
                'entry': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': 2.0,
                'strength': ny_strength,
                'reason': f"ICT New York Kill Zone: Strong bullish bias ({ny_strength}%)"
            })
        
        elif ny_bias == 'bearish' and ny_strength > 70 and (bias == 'bearish' or bias == 'neutral'):
            # Bearish New York session signal
            # Calculate stop loss based on average range
            avg_range = new_york.get('avg_range', 0.5)
            stop_loss = current_price * (1 + avg_range / 100)
            
            # Take profit at a 1:2 risk-reward ratio
            risk = stop_loss - current_price
            take_profit = current_price - (risk * 2)
            
            signals.append({
                'symbol': symbol,
                'type': 'sell',
                'entry': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward': 2.0,
                'strength': ny_strength,
                'reason': f"ICT New York Kill Zone: Strong bearish bias ({ny_strength}%)"
            })
        
        return signals
    
    def _generate_fvg_ob_signals(self, symbol: str, fair_value_gaps: List[Dict], 
                               order_blocks: List[Dict], bias: str, 
                               current_price: float) -> List[Dict]:
        """
        Generate signals based on Fair Value Gaps and Order Blocks
        
        Args:
            symbol (str): Trading symbol
            fair_value_gaps (list): Fair value gaps
            order_blocks (list): Order blocks
            bias (str): Market bias
            current_price (float): Current price
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Filter for recent fair value gaps (less than 30 candles old)
        recent_fvgs = [fvg for fvg in fair_value_gaps if fvg.get('age', 100) < 30]
        
        # Filter for recent order blocks (less than 20 candles old)
        recent_obs = [ob for ob in order_blocks if ob.get('age', 100) < 20]
        
        # Look for alignments between FVGs and OBs
        for fvg in recent_fvgs:
            fvg_type = fvg.get('type', '')
            fvg_top = fvg.get('top', 0)
            fvg_bottom = fvg.get('bottom', 0)
            
            # Find matching order blocks
            matching_obs = []
            for ob in recent_obs:
                ob_type = ob.get('type', '')
                ob_top = ob.get('top', 0)
                ob_bottom = ob.get('bottom', 0)
                
                # Check if the OB and FVG are aligned (same direction and close to each other)
                if ob_type == fvg_type:
                    # For bullish setups, OB should be below FVG
                    if ob_type == 'bullish' and ob_top <= fvg_bottom * 1.01:
                        matching_obs.append(ob)
                    # For bearish setups, OB should be above FVG
                    elif ob_type == 'bearish' and ob_bottom >= fvg_top * 0.99:
                        matching_obs.append(ob)
            
            # If we have matching OBs, generate signals
            for ob in matching_obs:
                ob_top = ob.get('top', 0)
                ob_bottom = ob.get('bottom', 0)
                
                # Calculate combined strength
                combined_strength = (fvg.get('strength', 50) + ob.get('strength', 50)) / 2
                
                if fvg_type == 'bullish' and (bias == 'bullish' or bias == 'neutral'):
                    # Bullish signal
                    # Entry at current price if it's near the FVG
                    if current_price <= fvg_top * 1.01:
                        stop_loss = ob_bottom * 0.995  # Just below the order block
                        
                        # Calculate take profit using the analyzer's method
                        take_profit, risk_reward = self.analyzer.find_optimal_take_profit(
                            None,  # We don't have the df here, but the method can handle it
                            current_price,
                            stop_loss,
                            'buy',
                            min_rr=2.5
                        )
                        
                        signals.append({
                            'symbol': symbol,
                            'type': 'buy',
                            'entry': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': combined_strength,
                            'reason': f"ICT Bullish FVG+OB Setup: FVG({fvg_bottom:.5f}-{fvg_top:.5f}), OB({ob_bottom:.5f}-{ob_top:.5f})"
                        })
                
                elif fvg_type == 'bearish' and (bias == 'bearish' or bias == 'neutral'):
                    # Bearish signal
                    # Entry at current price if it's near the FVG
                    if current_price >= fvg_bottom * 0.99:
                        stop_loss = ob_top * 1.005  # Just above the order block
                        
                        # Calculate take profit using the analyzer's method
                        take_profit, risk_reward = self.analyzer.find_optimal_take_profit(
                            None,  # We don't have the df here, but the method can handle it
                            current_price,
                            stop_loss,
                            'sell',
                            min_rr=2.5
                        )
                        
                        signals.append({
                            'symbol': symbol,
                            'type': 'sell',
                            'entry': current_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': combined_strength,
                            'reason': f"ICT Bearish FVG+OB Setup: FVG({fvg_bottom:.5f}-{fvg_top:.5f}), OB({ob_bottom:.5f}-{ob_top:.5f})"
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
            'strategy': 'ICT',
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return trade_setup
