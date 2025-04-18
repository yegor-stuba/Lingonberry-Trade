"""
Test the credentials module
"""

import unittest
import os
import sys
import importlib
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCredentials(unittest.TestCase):
    """Test cases for the credentials module"""
    
    def setUp(self):
        """Set up test environment"""
        # Import the module
        self.credentials = importlib.import_module('trading_bot.config.credentials')
    
    def test_telegram_token_exists(self):
        """Test that Telegram token exists"""
        self.assertTrue(hasattr(self.credentials, 'TELEGRAM_TOKEN'))
        self.assertIsInstance(self.credentials.TELEGRAM_TOKEN, str)
        self.assertGreater(len(self.credentials.TELEGRAM_TOKEN), 0)
    
    def test_alpha_vantage_api_key_exists(self):
        """Test that Alpha Vantage API key exists"""
        self.assertTrue(hasattr(self.credentials, 'ALPHA_VANTAGE_API_KEY'))
        self.assertIsInstance(self.credentials.ALPHA_VANTAGE_API_KEY, str)
        self.assertGreater(len(self.credentials.ALPHA_VANTAGE_API_KEY), 0)
    
    def test_news_api_key_exists(self):
        """Test that News API key exists"""
        self.assertTrue(hasattr(self.credentials, 'NEWS_API_KEY'))
        self.assertIsInstance(self.credentials.NEWS_API_KEY, str)
        self.assertGreater(len(self.credentials.NEWS_API_KEY), 0)
    
    def test_ctrader_credentials_exist(self):
        """Test that cTrader credentials exist"""
        self.assertTrue(hasattr(self.credentials, 'CTRADER_CLIENT_ID'))
        self.assertTrue(hasattr(self.credentials, 'CTRADER_CLIENT_SECRET'))
        self.assertTrue(hasattr(self.credentials, 'CTRADER_ACCOUNT_ID'))
        self.assertTrue(hasattr(self.credentials, 'CTRADER_ACCESS_TOKEN'))
        
        self.assertIsInstance(self.credentials.CTRADER_CLIENT_ID, str)
        self.assertIsInstance(self.credentials.CTRADER_CLIENT_SECRET, str)
        self.assertIsInstance(self.credentials.CTRADER_ACCOUNT_ID, int)
        self.assertIsInstance(self.credentials.CTRADER_ACCESS_TOKEN, str)
        
        self.assertGreater(len(self.credentials.CTRADER_CLIENT_ID), 0)
        self.assertGreater(len(self.credentials.CTRADER_CLIENT_SECRET), 0)
        self.assertGreater(self.credentials.CTRADER_ACCOUNT_ID, 0)
        self.assertGreater(len(self.credentials.CTRADER_ACCESS_TOKEN), 0)
    
    def test_mt5_credentials_exist(self):
        """Test that MT5 credentials exist"""
        self.assertTrue(hasattr(self.credentials, 'MT5_CREDENTIALS'))
        self.assertIsInstance(self.credentials.MT5_CREDENTIALS, dict)
        self.assertGreater(len(self.credentials.MT5_CREDENTIALS), 0)
        
        # Check structure of MT5 credentials
        for server, creds in self.credentials.MT5_CREDENTIALS.items():
            self.assertIsInstance(server, str)
            self.assertIsInstance(creds, dict)
            self.assertIn('server', creds)
            self.assertIn('login', creds)
            self.assertIn('password', creds)

if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCredentials)
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(suite)
