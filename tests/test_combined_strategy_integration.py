"""
Integration test for the combined strategy
Tests the entire pipeline from data loading to signal generation
"""

import unittest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import logging

from trading_bot.data.data_processor import DataProcessor
from trading_bot.strategy.combined_strategy import CombinedStrategy
from trading_bot.strategy.signal_generator import SignalGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCombinedStrategyIntegration(unittest.TestCase):
    """Test the combined strategy integration with data processor"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.data_processor = DataProcessor()
        cls.combined_strategy = CombinedStrategy()
        cls.signal_generator = SignalGenerator()
        
        # Load test data
        cls.test_data = {}
        
        # Run async setup
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls._async_setup())
    
    @classmethod
    async def _async_setup(cls):
        """Async setup to load test data"""
        # Load data for different symbols and timeframes
        symbols = ["EURUSD", "GBPUSD", "BTCUSDT", "XAUUSD"]
        timeframes = ["H1", "H4"]
        
        for symbol in symbols:
            cls.test_data[symbol] = {}
            for timeframe in timeframes:
                try:
                    # Try to load from CSV first (faster for testing)
                    source = "csv"
                    df = await cls.data_processor.get_data(symbol, timeframe, bars=100, source=source)
                    
                    if df is None or df.empty:
                        # If CSV fails, try appropriate source based on symbol
                        if symbol in ["BTCUSDT", "ETHUSDT"]:
                            source = "crypto"
                        else:
                            source = "ctrader"
                        
                        df = await cls.data_processor.get_data(symbol, timeframe, bars=100, source=source)
                    
                    cls.test_data[symbol][timeframe] = df
                    logger.info(f"Loaded {len(df) if df is not None else 0} rows for {symbol} {timeframe}")
                except Exception as e:
                    logger.error(f"Error loading data for {symbol} {timeframe}: {e}")
                    cls.test_data[symbol][timeframe] = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up resources"""
        cls.data_processor.close()
    
    def test_data_loading(self):
        """Test that data was loaded correctly"""
        for symbol in self.test_data:
            for timeframe in self.test_data[symbol]:
                df = self.test_data[symbol][timeframe]
                if df is not None:
                    self.assertFalse(df.empty, f"Data for {symbol} {timeframe} should not be empty")
                    self.assertIn("open", df.columns, f"Data for {symbol} {timeframe} should have 'open' column")
                    self.assertIn("high", df.columns, f"Data for {symbol} {timeframe} should have 'high' column")
                    self.assertIn("low", df.columns, f"Data for {symbol} {timeframe} should have 'low' column")
                    self.assertIn("close", df.columns, f"Data for {symbol} {timeframe} should have 'close' column")
                    self.assertIn("volume", df.columns, f"Data for {symbol} {timeframe} should have 'volume' column")
    
    def test_combined_strategy_analysis(self):
        """Test the combined strategy analysis"""
        for symbol in self.test_data:
            for timeframe in self.test_data[symbol]:
                df = self.test_data[symbol][timeframe]
                if df is not None and not df.empty:
                    # Run analysis
                    analysis = self.combined_strategy.analyze(df, symbol, timeframe)
                    
                    # Check analysis structure
                    self.assertIsNotNone(analysis, f"Analysis for {symbol} {timeframe} should not be None")
                    self.assertIn('symbol', analysis, f"Analysis for {symbol} {timeframe} should have 'symbol' key")
                    self.assertIn('timeframe', analysis, f"Analysis for {symbol} {timeframe} should have 'timeframe' key")
                    self.assertIn('bias', analysis, f"Analysis for {symbol} {timeframe} should have 'bias' key")
                    self.assertIn('signals', analysis, f"Analysis for {symbol} {timeframe} should have 'signals' key")
                    
                    # Check bias value
                    self.assertIn(analysis['bias'], ['bullish', 'bearish', 'neutral'], 
                                 f"Bias for {symbol} {timeframe} should be bullish, bearish, or neutral")
                    
                    # Log analysis results
                    logger.info(f"Analysis for {symbol} {timeframe}: bias={analysis['bias']}, "
                               f"signals={len(analysis['signals'])}, "
                               f"trade_setups={len(analysis.get('trade_setups', []))}")
    
    def test_signal_generation(self):
        """Test signal generation from the combined strategy"""
        for symbol in self.test_data:
            for timeframe in self.test_data[symbol]:
                df = self.test_data[symbol][timeframe]
                if df is not None and not df.empty:
                    # Generate signals
                    signals = self.combined_strategy.generate_signals(symbol, df, timeframe)
                    
                    # Check signals structure
                    self.assertIsNotNone(signals, f"Signals for {symbol} {timeframe} should not be None")
                    self.assertIsInstance(signals, list, f"Signals for {symbol} {timeframe} should be a list")
                    
                    # Log signals
                    logger.info(f"Generated {len(signals)} signals for {symbol} {timeframe}")
                    
                    # Check individual signals if any exist
                    for signal in signals:
                        self.assertIsInstance(signal, dict, f"Signal for {symbol} {timeframe} should be a dictionary")
                        if 'type' in signal:
                            self.assertIn(signal['type'], ['bullish', 'bearish', 'entry', 'exit', 'neutral'], 
                                         f"Signal type for {symbol} {timeframe} should be valid")
    
    def test_multi_timeframe_analysis(self):
        """Test multi-timeframe analysis"""
        # Test only for symbols that have data for multiple timeframes
        for symbol in self.test_data:
            if len(self.test_data[symbol]) >= 2:
                # Create a dictionary of dataframes for different timeframes
                dfs = self.test_data[symbol]
                
                # Determine market type
                if 'USD' in symbol:
                    if symbol.startswith('XAU'):
                        market_type = 'metals'
                    elif symbol in ['BTCUSDT', 'ETHUSDT']:
                        market_type = 'crypto'
                    else:
                        market_type = 'forex'
                else:
                    market_type = 'indices'
                
                # Run multi-timeframe analysis
                mtf_analysis = self.combined_strategy.get_multi_timeframe_analysis(dfs, symbol, market_type)
                
                # Check analysis structure
                self.assertIsNotNone(mtf_analysis, f"MTF analysis for {symbol} should not be None")
                self.assertIn('symbol', mtf_analysis, f"MTF analysis for {symbol} should have 'symbol' key")
                self.assertIn('timeframes', mtf_analysis, f"MTF analysis for {symbol} should have 'timeframes' key")
                self.assertIn('overall_bias', mtf_analysis, f"MTF analysis for {symbol} should have 'overall_bias' key")
                
                # Check bias value
                self.assertIn(mtf_analysis['overall_bias'], ['bullish', 'bearish', 'neutral'], 
                             f"Overall bias for {symbol} should be bullish, bearish, or neutral")
                
                # Log analysis results
                logger.info(f"MTF analysis for {symbol}: overall_bias={mtf_analysis['overall_bias']}, "
                           f"timeframes={list(mtf_analysis['timeframes'].keys())}, "
                           f"htf_poi={len(mtf_analysis.get('htf_poi', []))}, "
                           f"ltf_entries={len(mtf_analysis.get('ltf_entries', []))}")
    
    def test_trade_setup_generation(self):
        """Test trade setup generation"""
        for symbol in self.test_data:
            for timeframe in self.test_data[symbol]:
                df = self.test_data[symbol][timeframe]
                if df is not None and not df.empty:
                    # Generate signals
                    signals = self.combined_strategy.generate_signals(symbol, df, timeframe)
                    
                    # If we have signals, test trade setup generation
                    if signals:
                        # Get the best signal
                        best_signal = max(signals, key=lambda x: x.get('strength', 0)) if signals else None
                        
                        if best_signal:
                            # Generate trade setup
                            trade_setup = self.combined_strategy.get_trade_setup(best_signal)
                            
                            # Check trade setup structure
                            self.assertIsNotNone(trade_setup, f"Trade setup for {symbol} {timeframe} should not be None")
                            self.assertIn('symbol', trade_setup, f"Trade setup for {symbol} {timeframe} should have 'symbol' key")
                            self.assertIn('direction', trade_setup, f"Trade setup for {symbol} {timeframe} should have 'direction' key")
                            self.assertIn('entry_price', trade_setup, f"Trade setup for {symbol} {timeframe} should have 'entry_price' key")
                            self.assertIn('stop_loss', trade_setup, f"Trade setup for {symbol} {timeframe} should have 'stop_loss' key")
                            self.assertIn('take_profit', trade_setup, f"Trade setup for {symbol} {timeframe} should have 'take_profit' key")
                            
                            # Check direction value
                            self.assertIn(trade_setup['direction'], ['BUY', 'SELL'], 
                                         f"Direction for {symbol} {timeframe} should be BUY or SELL")
                            
                            # Check risk-reward ratio
                            if 'risk_reward' in trade_setup:
                                self.assertGreater(trade_setup['risk_reward'], 0, 
                                                 f"Risk-reward for {symbol} {timeframe} should be positive")
                            
                            # Log trade setup
                            logger.info(f"Trade setup for {symbol} {timeframe}: direction={trade_setup['direction']}, "
                                       f"entry={trade_setup['entry_price']:.5f}, "
                                       f"sl={trade_setup['stop_loss']:.5f}, "
                                       f"tp={trade_setup['take_profit']:.5f}, "
                                       f"rr={trade_setup.get('risk_reward', 0):.2f}")
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis integration"""
        # Only test for a few symbols to avoid long test times
        test_symbols = ["EURUSD", "BTCUSDT"]
        
        for symbol in test_symbols:
            if symbol in self.test_data and "H1" in self.test_data[symbol]:
                df = self.test_data[symbol]["H1"]
                if df is not None and not df.empty:
                    # Determine market type
                    if symbol in ["BTCUSDT", "ETHUSDT"]:
                        market_type = 'crypto'
                    elif symbol in ["XAUUSD", "XAGUSD"]:
                        market_type = 'metals'
                    elif symbol in ["US30", "US500", "USTEC"]:
                        market_type = 'indices'
                    else:
                        market_type = 'forex'
                    
                    # Run sentiment analysis
                    loop = asyncio.get_event_loop()
                    analysis = loop.run_until_complete(
                        self.combined_strategy.analyze_with_sentiment(df, symbol, "H1", market_type)
                    )
                    
                    # Check analysis structure
                    self.assertIsNotNone(analysis, f"Sentiment analysis for {symbol} should not be None")
                    self.assertIn('sentiment', analysis, f"Sentiment analysis for {symbol} should have 'sentiment' key")
                    
                    # Log sentiment results
                    if 'sentiment' in analysis and analysis['sentiment']:
                        sentiment_data = analysis['sentiment']
                        logger.info(f"Sentiment for {symbol}: sentiment={sentiment_data.get('sentiment', 'unknown')}, "
                                   f"score={sentiment_data.get('sentiment_score', 0):.2f}, "
                                   f"confidence={sentiment_data.get('confidence', 0):.2f}")
    
    def test_position_sizing(self):
        """Test position sizing calculations"""
        # Test parameters
        account_size = 10000.0
        risk_percentage = 1.0
        
        # Test for different symbols and entry/stop combinations
        test_cases = [
            {"symbol": "EURUSD", "entry": 1.10000, "stop": 1.09800},
            {"symbol": "BTCUSDT", "entry": 50000.0, "stop": 49500.0},
            {"symbol": "XAUUSD", "entry": 1900.0, "stop": 1890.0}
        ]
        
        for case in test_cases:
            # Calculate position size
            position_size = self.combined_strategy.calculate_position_size(
                account_size, risk_percentage, case["entry"], case["stop"], case["symbol"]
            )
            
            # Check position size
            self.assertIsNotNone(position_size, f"Position size for {case['symbol']} should not be None")
            self.assertGreater(position_size, 0, f"Position size for {case['symbol']} should be positive")
            
            # Calculate risk amount
            risk_amount = abs(case["entry"] - case["stop"]) * position_size
            
            # Check risk amount is close to expected (account_size * risk_percentage / 100)
            expected_risk = account_size * risk_percentage / 100
            self.assertAlmostEqual(risk_amount, expected_risk, delta=expected_risk*0.1,
                                  msg=f"Risk amount for {case['symbol']} should be close to {expected_risk}")
            
            # Log position sizing results
            logger.info(f"Position sizing for {case['symbol']}: "
                       f"entry={case['entry']:.5f}, stop={case['stop']:.5f}, "
                       f"position_size={position_size:.5f}, risk_amount=${risk_amount:.2f}")


if __name__ == "__main__":
    unittest.main()

