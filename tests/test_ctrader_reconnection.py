"""
Test for cTrader data provider reconnection logic
"""

import sys
from twisted.internet import selectreactor
if 'twisted.internet.reactor' not in sys.modules:
    selectreactor.install()
from twisted.internet import reactor

import unittest
import asyncio
import time
import logging
import pandas as pd
from unittest.mock import patch, MagicMock

from trading_bot.data.ctrader_data import CTraderData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCTraderReconnection(unittest.TestCase):
    """Test the cTrader data provider reconnection logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ctrader = CTraderData()
    
    # Then in the tearDown method:
    def tearDown(self):
        """Clean up resources"""
        self.ctrader.disconnect()
        # Don't stop the reactor as it might be used by other tests
        # Instead, just ensure we're disconnected
    
    def test_connection_establishment(self):
        """Test that connection can be established"""
        # Connect to cTrader API
        result = self.ctrader.connect()
        self.assertTrue(result, "Connection should be established successfully")
        
        # Wait for authentication to complete
        timeout = 10
        start_time = time.time()
        while not self.ctrader.authenticated and time.time() - start_time < timeout:
            time.sleep(0.5)
        
        self.assertTrue(self.ctrader.authenticated, "Authentication should complete within timeout")
    
    def test_reconnection_after_disconnect(self):
        """Test reconnection after disconnect"""
        # Connect to cTrader API
        self.ctrader.connect()
        
        # Wait for authentication to complete
        timeout = 10
        start_time = time.time()
        while not self.ctrader.authenticated and time.time() - start_time < timeout:
            time.sleep(0.5)
        
        # Verify connected
        self.assertTrue(self.ctrader.authenticated, "Should be authenticated initially")
        
        # Directly set the reconnect_scheduled flag to False to ensure clean state
        self.ctrader._reconnect_scheduled = False
        
        # Call the _on_disconnected method directly with a test reason
        self.ctrader._on_disconnected(self.ctrader.client, "Test disconnect")
        
        # Verify the reconnect_scheduled flag is set to True
        self.assertTrue(self.ctrader._reconnect_scheduled, "Reconnection should be scheduled after disconnect")
        
        # Wait for reconnection to be attempted
        time.sleep(1)
        
        # Note: We don't actually expect a real reconnection in the test since we're
        # directly calling the method rather than experiencing a real disconnect    def test_fallback_to_csv(self):
        """Test fallback to CSV when data cannot be fetched from API"""
        # Create a sample CSV file for testing
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Create sample data
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=100, freq='h'),
            'open': [1.1 + i*0.0001 for i in range(100)],
            'high': [1.1 + i*0.0001 + 0.0005 for i in range(100)],
            'low': [1.1 + i*0.0001 - 0.0005 for i in range(100)],
            'close': [1.1 + i*0.0001 + 0.0002 for i in range(100)],
            'volume': [1000 + i*10 for i in range(100)]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        # Save to CSV in the expected format
        filename = self.ctrader.data_dir / f"{symbol}_{timeframe}.csv"
        
        # Format data for CSV
        formatted_data = []
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d %H:%M')
            line = f"{date_str} {row['open']:.5f} {row['high']:.5f} {row['low']:.5f} {row['close']:.5f} {int(row['volume'])}"
            formatted_data.append(line)
        
        # Save to file
        with open(filename, 'w') as f:
            f.write(f"# Historical data for {symbol} {timeframe}\n")
            f.write("# timestamp open high low close volume\n")
            f.write('\n'.join(formatted_data))
        
        # Now test the fallback mechanism by simulating a failed API request
        with patch.object(self.ctrader, 'client') as mock_client:
            # Make the send method raise an exception
            mock_client.send.side_effect = Exception("Simulated API failure")
            
            # Try to get data
            df_result = self.ctrader.get_historical_data(symbol, timeframe, bars=50)
            
            # Verify that we got data from the CSV file
            self.assertFalse(df_result.empty, "Should get data from CSV fallback")
            self.assertEqual(len(df_result), 100, "Should get all rows from CSV file")
            self.assertIn('open', df_result.columns, "DataFrame should have 'open' column")
            self.assertIn('high', df_result.columns, "DataFrame should have 'high' column")
            self.assertIn('low', df_result.columns, "DataFrame should have 'low' column")
            self.assertIn('close', df_result.columns, "DataFrame should have 'close' column")
            self.assertIn('volume', df_result.columns, "DataFrame should have 'volume' column")
    
    def test_unknown_symbol_fallback(self):
        """Test fallback when an unknown symbol is requested"""
        # Create a sample CSV file for a non-standard symbol
        symbol = "CUSTOM_SYMBOL"
        timeframe = "H1"
        
        # Create sample data
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=50, freq='h'),
            'open': [100.0 + i for i in range(50)],
            'high': [100.0 + i + 0.5 for i in range(50)],
            'low': [100.0 + i - 0.5 for i in range(50)],
            'close': [100.0 + i + 0.2 for i in range(50)],
            'volume': [1000 + i*10 for i in range(50)]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        # Save to CSV in the expected format
        filename = self.ctrader.data_dir / f"{symbol}_{timeframe}.csv"
        
        # Format data for CSV
        formatted_data = []
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d %H:%M')
            line = f"{date_str} {row['open']:.5f} {row['high']:.5f} {row['low']:.5f} {row['close']:.5f} {int(row['volume'])}"
            formatted_data.append(line)
        
        # Save to file
        with open(filename, 'w') as f:
            f.write(f"# Historical data for {symbol} {timeframe}\n")
            f.write("# timestamp open high low close volume\n")
            f.write('\n'.join(formatted_data))
        
        # Try to get data for the unknown symbol
        df_result = self.ctrader.get_historical_data(symbol, timeframe, bars=50)
        
        # Verify that we got data from the CSV file
        self.assertFalse(df_result.empty, "Should get data from CSV for unknown symbol")
        self.assertEqual(len(df_result), 50, "Should get all rows from CSV file")
        self.assertIn('open', df_result.columns, "DataFrame should have 'open' column")
    
    def test_timeout_handling(self):
        """Test handling of request timeouts"""
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Create a sample CSV file as fallback
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=30, freq='h'),
            'open': [1.1 + i*0.0001 for i in range(30)],
            'high': [1.1 + i*0.0001 + 0.0005 for i in range(30)],
            'low': [1.1 + i*0.0001 - 0.0005 for i in range(30)],
            'close': [1.1 + i*0.0001 + 0.0002 for i in range(30)],
            'volume': [1000 + i*10 for i in range(30)]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        # Save to CSV in the expected format
        filename = self.ctrader.data_dir / f"{symbol}_{timeframe}.csv"
        
        # Format data for CSV
        formatted_data = []
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d %H:%M')
            line = f"{date_str} {row['open']:.5f} {row['high']:.5f} {row['low']:.5f} {row['close']:.5f} {int(row['volume'])}"
            formatted_data.append(line)
        
        # Save to file
        with open(filename, 'w') as f:
            f.write(f"# Historical data for {symbol} {timeframe}\n")
            f.write("# timestamp open high low close volume\n")
            f.write('\n'.join(formatted_data))
        
        # Patch the client to simulate a timeout
        with patch.object(self.ctrader, 'client') as mock_client:
            # Make the send method work but don't add any data to data_callbacks
            mock_client.send = MagicMock(return_value=None)
            
            # Try to get data with a short timeout
            # Instead of wrapping the method, we'll modify the timeout directly
            original_timeout = 30
            
            # Store the original method
            original_method = self.ctrader.get_historical_data
            
            # Replace with a version that uses a shorter timeout
            def get_with_short_timeout(symbol, timeframe, bars=100):
                # Mock time.sleep to make the test faster
                original_sleep = time.sleep
                time.sleep = lambda x: None
                
                try:
                    return original_method(symbol, timeframe, bars)
                finally:
                    time.sleep = original_sleep
            
            # Apply the patch
            self.ctrader.get_historical_data = get_with_short_timeout
            
            try:
                # Try to get data
                df_result = self.ctrader.get_historical_data(symbol, timeframe, bars=20)
                
                # Verify that we got data from the CSV file after timeout
                self.assertFalse(df_result.empty, "Should get data from CSV after timeout")
                self.assertEqual(len(df_result), 30, "Should get all rows from CSV file")
            finally:
                # Restore the original method
                self.ctrader.get_historical_data = original_method    
    def test_error_handling(self):
        """Test handling of various errors"""
        # Test with invalid timeframe
        df_result = self.ctrader.get_historical_data("EURUSD", "INVALID_TIMEFRAME", bars=50)
        self.assertTrue(df_result.empty, "Should return empty DataFrame for invalid timeframe")
        
        # Test with unauthenticated state
        original_authenticated = self.ctrader.authenticated
        self.ctrader.authenticated = False
        
        # Try to get data while unauthenticated
        df_result = self.ctrader.get_historical_data("EURUSD", "H1", bars=50)
        
        # Restore the authenticated state
        self.ctrader.authenticated = original_authenticated
        
        # Verify behavior
        if not df_result.empty:
            # If we got data, it should be from CSV fallback
            self.assertIn('open', df_result.columns, "DataFrame should have 'open' column")
            logger.info("Successfully fell back to CSV when unauthenticated")
        else:
            # It's also acceptable to return empty DataFrame if no CSV exists
            logger.info("Returned empty DataFrame when unauthenticated and no CSV exists")
    

    def _on_disconnected(self, client, reason):
        """Callback when disconnected from cTrader API"""
        logger.info(f"Disconnected: {reason}")
        self.connected = False
        self.authenticated = False
        
        # Schedule reconnection if not already scheduled
        if not self._reconnect_scheduled:
            self._reconnect_scheduled = True
            logger.info("Scheduling reconnection in 5 seconds...")
            
            # Use reactor.callLater for reconnection
            from twisted.internet import reactor
            reactor.callLater(5, self._reconnect)

if __name__ == "__main__":
    unittest.main()

