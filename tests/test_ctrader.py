"""
Test script for cTrader data functionality
Tests the CTraderData class from trading_bot.data.ctrader_data
"""

import os
import sys
import time
import unittest
import logging
from datetime import datetime
import pandas as pd
from pathlib import Path
import argparse

# Add the parent directory to the path so we can import from trading_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.data.ctrader_data import CTraderData, TIMEFRAME_PERIODS, SYMBOL_IDS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestCTraderData(unittest.TestCase):
    """Test cases for CTraderData class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.data_provider = CTraderData()
        cls.test_symbol = "BTCUSD"
        cls.test_timeframe = "M5"
        cls.data_dir = Path("data")
        cls.data_dir.mkdir(exist_ok=True)
        
        # Connect to cTrader API
        cls.data_provider.connect()
        
        # Wait for authentication to complete (with timeout)
        timeout = 10  # seconds
        start_time = time.time()
        
        while not cls.data_provider.authenticated and time.time() - start_time < timeout:
            time.sleep(0.5)
            logger.info("Waiting for authentication...")
        
        cls.connected = cls.data_provider.authenticated
        
        if not cls.connected:
            logger.warning("Could not authenticate with cTrader API within timeout")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        if hasattr(cls, 'data_provider'):
            cls.data_provider.disconnect()
    
    def test_connection(self):
        """Test connection to cTrader API"""
        self.assertTrue(self.__class__.connected, "Not connected to cTrader API")
        logger.info("Connection test passed")
    
    def test_get_historical_data(self):
        """Test fetching historical data"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Get historical data
        df = self.__class__.data_provider.get_historical_data(self.__class__.test_symbol, self.__class__.test_timeframe, 10)
        
        # Check if data was fetched
        self.assertFalse(df.empty, f"No data fetched for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        self.assertGreaterEqual(len(df), 1, f"Not enough data fetched for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        
        # Check if data was saved to CSV
        csv_file = self.__class__.data_dir / f"{self.__class__.test_symbol}_{self.__class__.test_timeframe}.csv"
        self.assertTrue(csv_file.exists(), f"CSV file not created: {csv_file}")
        
        logger.info(f"Historical data test passed: Got {len(df)} bars for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
    
    def test_multiple_timeframes(self):
        """Test fetching data for multiple timeframes"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Test timeframes
        timeframes = ["M1", "M5", "H1"]
        
        for timeframe in timeframes:
            # Get historical data
            df = self.__class__.data_provider.get_historical_data(self.__class__.test_symbol, timeframe, 5)
            
            # Check if data was fetched
            self.assertFalse(df.empty, f"No data fetched for {self.__class__.test_symbol} {timeframe}")
            self.assertGreaterEqual(len(df), 1, f"Not enough data fetched for {self.__class__.test_symbol} {timeframe}")
            
            # Check if data was saved to CSV
            csv_file = self.__class__.data_dir / f"{self.__class__.test_symbol}_{timeframe}.csv"
            self.assertTrue(csv_file.exists(), f"CSV file not created: {csv_file}")
            
            logger.info(f"Got {len(df)} bars for {self.__class__.test_symbol} {timeframe}")
        
        logger.info("Multiple timeframes test passed")
    
    def test_multiple_symbols(self):
        """Test fetching data for multiple symbols"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Test symbols (use only a few to keep test time reasonable)
        symbols = ["BTCUSD", "EURUSD"]
        
        for symbol in symbols:
            if symbol not in SYMBOL_IDS:
                logger.warning(f"Symbol {symbol} not in SYMBOL_IDS, skipping")
                continue
                
            # Get historical data
            df = self.__class__.data_provider.get_historical_data(symbol, self.__class__.test_timeframe, 5)
            
            # Check if data was fetched
            self.assertFalse(df.empty, f"No data fetched for {symbol} {self.__class__.test_timeframe}")
            self.assertGreaterEqual(len(df), 1, f"Not enough data fetched for {symbol} {self.__class__.test_timeframe}")
            
            # Check if data was saved to CSV
            csv_file = self.__class__.data_dir / f"{symbol}_{self.__class__.test_timeframe}.csv"
            self.assertTrue(csv_file.exists(), f"CSV file not created: {csv_file}")
            
            logger.info(f"Got {len(df)} bars for {symbol} {self.__class__.test_timeframe}")
        
        logger.info("Multiple symbols test passed")
    
    def test_load_data(self):
        """Test loading data from CSV"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # First, ensure we have data to load
        self.__class__.data_provider.get_historical_data(self.__class__.test_symbol, self.__class__.test_timeframe, 10)
        
        # Now load the data
        df = self.__class__.data_provider.load_data(self.__class__.test_symbol, self.__class__.test_timeframe)
        
        # Check if data was loaded
        self.assertFalse(df.empty, f"No data loaded for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        self.assertGreaterEqual(len(df), 1, f"Not enough data loaded for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        
        # Check if required columns exist
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, df.columns, f"Column {col} not found in loaded data")
        
        logger.info(f"Loaded {len(df)} rows for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        logger.info("Load data test passed")
    
    def test_update_data(self):
        """Test updating data"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Update data
        df = self.__class__.data_provider.update_data(self.__class__.test_symbol, self.__class__.test_timeframe, 10)
        
        # Check if data was updated
        self.assertFalse(df.empty, f"No data updated for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        self.assertGreaterEqual(len(df), 1, f"Not enough data updated for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        
        logger.info(f"Updated data with {len(df)} rows for {self.__class__.test_symbol} {self.__class__.test_timeframe}")
        logger.info("Update data test passed")
    
    def test_live_data_subscription(self):
        """Test subscribing to live data"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Create a callback to verify live data
        live_data_received = [False]
        
        def live_data_callback(data):
            logger.info(f"Received live data: {data}")
            live_data_received[0] = True
        
        # Subscribe to live data
        self.__class__.data_provider.subscribe_to_live_data(self.__class__.test_symbol, self.__class__.test_timeframe, live_data_callback)
        
        # Wait for live data (with timeout)
        timeout = 10  # seconds
        start_time = time.time()
        
        logger.info(f"Waiting up to {timeout} seconds for live data...")
        
        while not live_data_received[0] and time.time() - start_time < timeout:
            time.sleep(1)
        
        # Check if live data was received
        if not live_data_received[0]:
            logger.warning("No live data received within timeout period")
            # This is not a failure as live data depends on market activity
        else:
            logger.info("Live data received successfully")
        
        logger.info("Live data subscription test completed")

    def test_update_symbol_ids(self):
        """Test updating symbol IDs"""
        # Skip if not connected
        if not self.__class__.connected:
            self.skipTest("Not connected to cTrader API")
        
        # Get symbol IDs from the broker
        symbol_ids = self.__class__.data_provider.get_symbol_ids()
        
        # Check if we got any symbol IDs
        self.assertGreater(len(symbol_ids), 0, "No symbol IDs retrieved")
        
        # Print the symbol IDs for important symbols
        important_symbols = ["BTCUSD", "EURUSD", "GBPJPY", "NAS100", "US30", "US500", "USTEC", "XAUUSD"]
        found_symbols = {}
        
        for symbol_name, symbol_id in symbol_ids.items():
            # Check for exact matches
            if symbol_name in important_symbols:
                found_symbols[symbol_name] = symbol_id
            # Check for partial matches (for symbols that might have different naming)
            else:
                for important in important_symbols:
                    if important in symbol_name:
                        found_symbols[important] = symbol_id
                        logger.info(f"Found partial match: {symbol_name} -> {important} (ID: {symbol_id})")
        
        # Print the found symbols
        logger.info("Found symbol IDs:")
        for symbol, symbol_id in found_symbols.items():
            logger.info(f"  {symbol}: {symbol_id}")
        
        # Check if we found NAS100
        self.assertIn("NAS100", found_symbols, "NAS100 symbol not found")
        
        # Update the SYMBOL_IDS dictionary with the correct values
        updated_ids = {}
        for symbol in SYMBOL_IDS:
            if symbol in found_symbols:
                updated_ids[symbol] = found_symbols[symbol]
            else:
                updated_ids[symbol] = SYMBOL_IDS[symbol]
        
        # Print the updated SYMBOL_IDS dictionary
        logger.info("Updated SYMBOL_IDS dictionary:")
        logger.info(str(updated_ids))
        
        # Save the updated SYMBOL_IDS to a file for reference
        with open("updated_symbol_ids.py", "w") as f:
            f.write("SYMBOL_IDS = {\n")
            # Group by category
            categories = {
                "Crypto": ["BTCUSD", "ETHUSD", "XRPUSD", "ADAUSD"],
                "Forex": ["EURUSD", "GBPUSD", "GBPJPY", "USDJPY", "AUDUSD", "USDCAD"],
                "Indices": ["US30", "US500", "USTEC", "NAS100", "SPX500"],
                "Metals": ["XAUUSD", "XAGUSD"]
            }
            
            for category, symbols in categories.items():
                f.write(f"    # {category}\n")
                for symbol in symbols:
                    if symbol in updated_ids:
                        f.write(f"    '{symbol}': {updated_ids[symbol]},\n")
                    else:
                        f.write(f"    # '{symbol}': None,  # Not found\n")
            
            f.write("}\n")
        
        logger.info("Updated symbol IDs saved to updated_symbol_ids.py")


def run_specific_test(test_name=None):
    """Run a specific test or all tests"""
    if test_name:
        suite = unittest.TestSuite()
        suite.addTest(TestCTraderData(test_name))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCTraderData)
    
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test cTrader data functionality')
    parser.add_argument('--test', type=str, help='Specific test to run')
    parser.add_argument('--list', action='store_true', help='List available tests')
    args = parser.parse_args()
    
    if args.list:
        # List available tests
        test_names = [method for method in dir(TestCTraderData) if method.startswith('test_')]
        print("Available tests:")
        for test in test_names:
            print(f"  {test}")
    elif args.test:
        # Run specific test
        run_specific_test(args.test)
    else:
        # Run all tests
        unittest.main()
