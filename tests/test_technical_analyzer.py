"""
Test the technical analyzer implementation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.analysis.technical import TechnicalAnalyzer

class TestTechnicalAnalyzer(unittest.TestCase):
    """Test cases for the technical analyzer implementation"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data
        dates = [datetime.now() - timedelta(days=i) for i in range(200, 0, -1)]
        
        # Create a trending market
        close = np.linspace(100, 150, 200) + np.random.normal(0, 1, 200)
        high = close + np.random.uniform(0, 2, 200)
        low = close - np.random.uniform(0, 2, 200)
        open_prices = close - np.random.uniform(-1, 1, 200)
        volume = np.random.uniform(1000, 5000, 200)
        
        # Create DataFrame
        self.df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        
        # Initialize analyzer
        self.analyzer = TechnicalAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer)
    
    def test_analyze_chart(self):
        """Test the analyze_chart method"""
        analysis = self.analyzer.analyze_chart(self.df, 'EURUSD')
        
        # Check basic structure
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis['symbol'], 'EURUSD')
        self.assertIn('indicators', analysis)
        self.assertIn('signals', analysis)
        self.assertIn('bias', analysis)
        self.assertIn('key_levels', analysis)
        self.assertIn('patterns', analysis)
        self.assertIn('volatility', analysis)
        self.assertIn('trend_strength', analysis)
    
    def test_calculate_indicators(self):
        """Test indicator calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        
        # Check that we have all expected indicators
        self.assertIn('sma20', indicators)
        self.assertIn('sma50', indicators)
        self.assertIn('sma200', indicators)
        self.assertIn('ema20', indicators)
        self.assertIn('bb_upper', indicators)
        self.assertIn('bb_lower', indicators)
        self.assertIn('rsi', indicators)
        self.assertIn('macd', indicators)
        self.assertIn('stoch_k', indicators)
        self.assertIn('atr', indicators)
    
    def test_generate_signals(self):
        """Test signal generation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        signals = self.analyzer.generate_signals(self.df, indicators)
        
        # Check that we get signals
        self.assertIsInstance(signals, list)
        
        # Check signal structure if any signals are generated
        if signals:
            signal = signals[0]
            self.assertIn('type', signal)
            self.assertIn('indicator', signal)
            self.assertIn('description', signal)
            self.assertIn('strength', signal)
    
    def test_identify_key_levels(self):
        """Test key level identification"""
        key_levels = self.analyzer.identify_key_levels(self.df)
        
        # Check that we get key levels
        self.assertIsInstance(key_levels, list)
        
        # Check key level structure if any are found
        if key_levels:
            level = key_levels[0]
            self.assertIn('type', level)
            self.assertIn('price', level)
            self.assertIn('strength', level)
    
    def test_identify_patterns(self):
        """Test pattern identification"""
        patterns = self.analyzer.identify_patterns(self.df)
        
        # Check that we get patterns
        self.assertIsInstance(patterns, list)
        
        # Check pattern structure if any are found
        if patterns:
            pattern = patterns[0]
            self.assertIn('type', pattern)
            self.assertIn('index', pattern)
            self.assertIn('significance', pattern)
    
    def test_calculate_volatility(self):
        """Test volatility calculation"""
        volatility = self.analyzer.calculate_volatility(self.df)
        
        # Check volatility metrics
        self.assertIn('atr', volatility)
        self.assertIn('atr_percent', volatility)
        self.assertIn('daily_volatility', volatility)
        self.assertIn('annualized_volatility', volatility)
        self.assertIn('bollinger_width', volatility)
        self.assertIn('trend', volatility)
    
    def test_calculate_trend_strength(self):
        """Test trend strength calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        trend = self.analyzer.calculate_trend_strength(self.df, indicators)
        
        # Check trend metrics
        self.assertIn('adx', trend)
        self.assertIn('strength', trend)
        self.assertIn('direction', trend)
    
    def test_find_trade_setups(self):
        """Test trade setup finding"""
        setups = self.analyzer.find_trade_setups(self.df)
        
        # Check that we get setups
        self.assertIsInstance(setups, list)
        
        # Check setup structure if any are found
        if setups:
            setup = setups[0]
            self.assertIn('direction', setup)
            self.assertIn('entry', setup)
            self.assertIn('stop_loss', setup)
            self.assertIn('take_profit', setup)
            self.assertIn('risk_reward', setup)
    
    def test_calculate_optimal_position_size(self):
        """Test position size calculation"""
        position_sizing = self.analyzer.calculate_optimal_position_size(
            account_size=10000,
            risk_percentage=1.0,
            entry_price=100.0,
            stop_loss=99.0
        )
        
        # Check position sizing
        self.assertIn('position_size', position_sizing)
        self.assertIn('risk_amount', position_sizing)
        self.assertIn('pip_risk', position_sizing)
        self.assertIn('risk_reward', position_sizing)
        
        # Check calculations
        self.assertEqual(position_sizing['risk_amount'], 100.0)  # 1% of 10000
        self.assertEqual(position_sizing['pip_risk'], 1.0)  # 100 - 99
        
        # Position size should be risk_amount / pip_risk
        self.assertEqual(position_sizing['position_size'], 100.0)
    
    def test_determine_bias(self):
        """Test bias determination"""
        indicators = self.analyzer.calculate_indicators(self.df)
        signals = self.analyzer.generate_signals(self.df, indicators)
        bias = self.analyzer.determine_bias(self.df, indicators, signals)
        
        # Check bias structure
        self.assertIn('direction', bias)
        self.assertIn('strength', bias)
        self.assertIn('confidence', bias)
        
        # Direction should be one of: bullish, bearish, neutral
        self.assertIn(bias['direction'], ['bullish', 'bearish', 'neutral'])
        
        # Strength should be between 0 and 1
        self.assertGreaterEqual(bias['strength'], 0)
        self.assertLessEqual(bias['strength'], 1)
        
        # Confidence should be between 0 and 1
        self.assertGreaterEqual(bias['confidence'], 0)
        self.assertLessEqual(bias['confidence'], 1)
    
    def test_sma_calculation(self):
        """Test SMA calculation"""
        sma20 = self.analyzer._calculate_sma(self.df, 20)
        
        # Check that SMA is calculated correctly
        self.assertEqual(len(sma20), len(self.df))
        self.assertTrue(pd.isna(sma20.iloc[0]))  # First 19 values should be NaN
        self.assertFalse(pd.isna(sma20.iloc[20]))  # 20th value should not be NaN
        
        # Check a manual calculation
        manual_sma = self.df['close'].iloc[0:20].mean()
        self.assertAlmostEqual(sma20.iloc[19], manual_sma, places=4)
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        ema20 = self.analyzer._calculate_ema(self.df, 20)
        
        # Check that EMA is calculated correctly
        self.assertEqual(len(ema20), len(self.df))
        
        # EMA should be different from SMA
        sma20 = self.analyzer._calculate_sma(self.df, 20)
        self.assertNotEqual(ema20.iloc[-1], sma20.iloc[-1])
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        
        # Check that Bollinger Bands are calculated correctly
        self.assertIn('bb_upper', indicators)
        self.assertIn('bb_middle', indicators)
        self.assertIn('bb_lower', indicators)
        
        # Upper band should be higher than middle band
        self.assertTrue((indicators['bb_upper'] > indicators['bb_middle']).all())
        
        # Lower band should be lower than middle band
        self.assertTrue((indicators['bb_lower'] < indicators['bb_middle']).all())
        
        # Middle band should be equal to SMA20
        np.testing.assert_array_almost_equal(
            indicators['bb_middle'].values, 
            indicators['sma20'].values
        )
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        
        # Check that RSI is calculated correctly
        self.assertIn('rsi', indicators)
        
        # RSI should be between 0 and 100
        self.assertTrue((indicators['rsi'] >= 0).all())
        self.assertTrue((indicators['rsi'] <= 100).all())
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        
        # Check that MACD is calculated correctly
        self.assertIn('macd', indicators)
        self.assertIn('macd_signal', indicators)
        self.assertIn('macd_histogram', indicators)
        
        # MACD histogram should be MACD - Signal
        np.testing.assert_array_almost_equal(
            indicators['macd_histogram'].values,
            (indicators['macd'] - indicators['macd_signal']).values
        )
    
    def test_atr_calculation(self):
        """Test ATR calculation"""
        indicators = self.analyzer.calculate_indicators(self.df)
        
        # Check that ATR is calculated correctly
        self.assertIn('atr', indicators)
        
        # ATR should be positive
        self.assertTrue((indicators['atr'] > 0).all())
    
    def test_support_resistance_levels(self):
        """Test support and resistance level identification"""
        key_levels = self.analyzer.identify_key_levels(self.df)
        
        # Group levels by type
        support_levels = [level for level in key_levels if level['type'] == 'support']
        resistance_levels = [level for level in key_levels if level['type'] == 'resistance']
        
        # Check that we have both support and resistance levels
        self.assertTrue(len(support_levels) > 0)
        self.assertTrue(len(resistance_levels) > 0)
        
        # Support levels should be below current price
        current_price = self.df['close'].iloc[-1]
        for level in support_levels:
            self.assertLessEqual(level['price'], current_price)
        
        # Resistance levels should be above current price
        for level in resistance_levels:
            self.assertGreaterEqual(level['price'], current_price)
    
    def test_candlestick_pattern_recognition(self):
        """Test candlestick pattern recognition"""
        patterns = self.analyzer.identify_patterns(self.df)
        
        # Check that patterns are identified
        self.assertIsInstance(patterns, list)
        
        # Create a dataframe with known patterns
        pattern_df = self.df.copy()
        
        # Create a doji pattern
        pattern_df.iloc[-5]['open'] = 120.0
        pattern_df.iloc[-5]['close'] = 120.1
        pattern_df.iloc[-5]['high'] = 122.0
        pattern_df.iloc[-5]['low'] = 118.0
        
        # Create a hammer pattern
        pattern_df.iloc[-10]['open'] = 115.0
        pattern_df.iloc[-10]['close'] = 118.0
        pattern_df.iloc[-10]['high'] = 118.5
        pattern_df.iloc[-10]['low'] = 110.0
        
        # Identify patterns in the modified dataframe
        new_patterns = self.analyzer.identify_patterns(pattern_df)
        
        # Check that we have more patterns in the modified dataframe
        self.assertGreater(len(new_patterns), len(patterns))

if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTechnicalAnalyzer)
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(suite)
