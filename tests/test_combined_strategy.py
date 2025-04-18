"""
Test the combined strategy implementation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.strategy.combined_strategy import CombinedStrategy
from trading_bot.strategy.signal_generator import SignalGenerator

class TestCombinedStrategy(unittest.TestCase):
    """Test cases for the combined strategy"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data
        dates = [datetime.now() - timedelta(days=i) for i in range(300, 0, -1)]
        
        # Create a trending market
        close = np.linspace(100, 150, 300) + np.random.normal(0, 1, 300)
        high = close + np.random.uniform(0, 2, 300)
        low = close - np.random.uniform(0, 2, 300)
        open_prices = close - np.random.uniform(-1, 1, 300)
        volume = np.random.uniform(1000, 5000, 300)
        
        # Create DataFrame
        self.df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        
        # Create multi-timeframe data
        self.mtf_data = {
            '1h': self.df,
            '4h': self.df.resample('4H').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna(),
            '1d': self.df.resample('D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        }
        
        # Initialize strategy
        self.strategy = CombinedStrategy()
        self.signal_generator = SignalGenerator()
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        self.assertIsNotNone(self.strategy)
        self.assertIsNotNone(self.strategy.smc_strategy)
        self.assertIsNotNone(self.strategy.ict_strategy)
        self.assertIsNotNone(self.strategy.technical_analyzer)
        self.assertIsNotNone(self.strategy.sentiment_analyzer)
    
    def test_analyze_method(self):
        """Test the analyze method"""
        analysis = self.strategy.analyze(self.df, 'EURUSD', '1h')
        
        # Check basic structure
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis['symbol'], 'EURUSD')
        self.assertEqual(analysis['timeframe'], '1h')
        self.assertIn('bias', analysis)
        self.assertIn('signals', analysis)
        self.assertIn('trade_setups', analysis)
        
        # Check that we have analysis from each component
        self.assertIn('smc_analysis', analysis)
        self.assertIn('ict_analysis', analysis)
        self.assertIn('technical_analysis', analysis)
    
    def test_multi_timeframe_analysis(self):
        """Test multi-timeframe analysis"""
        mtf_analysis = self.strategy.get_multi_timeframe_analysis(self.mtf_data, 'EURUSD')
        
        # Check basic structure
        self.assertIsNotNone(mtf_analysis)
        self.assertEqual(mtf_analysis['symbol'], 'EURUSD')
        self.assertIn('timeframes', mtf_analysis)
        self.assertIn('htf_poi', mtf_analysis)
        self.assertIn('ltf_entries', mtf_analysis)
        self.assertIn('overall_bias', mtf_analysis)
        
        # Check that we have analysis for each timeframe
        for tf in self.mtf_data.keys():
            self.assertIn(tf, mtf_analysis['timeframes'])
    
    def test_signal_generator_integration(self):
        """Test integration with signal generator"""
        signals = self.signal_generator.generate_signals('EURUSD', self.df, '1h')
        
        # Check that we get signals
        self.assertIsInstance(signals, list)
        
        # Filter for high-quality signals
        filtered_signals = self.signal_generator.filter_signals(signals, min_risk_reward=3.0, min_strength=70)
        
        # Check that filtering works
        for signal in filtered_signals:
            self.assertGreaterEqual(signal.get('risk_reward', 0), 3.0)
            self.assertGreaterEqual(signal.get('strength', 0), 70)
    
    def test_trade_setup_generation(self):
        """Test trade setup generation"""
        # Get a sample signal
        analysis = self.strategy.analyze(self.df, 'EURUSD', '1h')
        signals = analysis.get('signals', [])
        
        if signals:
            # Get the best signal
            best_signal = max(signals, key=lambda x: x.get('strength', 0))
            
            # Get trade setup
            trade_setup = self.strategy.get_trade_setup(best_signal)
            
            # Check trade setup structure
            self.assertIsNotNone(trade_setup)
            self.assertIn('symbol', trade_setup)
            self.assertIn('direction', trade_setup)
            self.assertIn('entry_price', trade_setup)
            self.assertIn('stop_loss', trade_setup)
            self.assertIn('take_profit', trade_setup)
            self.assertIn('risk_reward', trade_setup)
            self.assertIn('position_size', trade_setup)

if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCombinedStrategy)
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(suite)
