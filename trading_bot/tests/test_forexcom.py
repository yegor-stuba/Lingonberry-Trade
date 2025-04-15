"""
Test script for forexcom package
"""

import logging
import sys
import time
from datetime import datetime
import pandas as pd
from pathlib import Path

# Set up logging
logging.basicConfig(
    stream=sys.stdout, 
    format='%(asctime)s %(levelname)-7s %(threadName)-15s %(message)s', 
    level=logging.INFO
)
log = logging.getLogger()

try:
    from forexcom import ForexComClient, Position
except ImportError:
    log.error("forexcom package not installed. Install with: pip install forexcom")
    sys.exit(1)

class ForexComDataProvider:
    """Data provider using forexcom package"""
    
    def __init__(self, username, password, app_key):
        """
        Initialize the ForexCom data provider
        
        Args:
            username (str): ForexCom username
            password (str): ForexCom password
            app_key (str): ForexCom app key
        """
        self.username = username
        self.password = password
        self.app_key = app_key
        self.client = None
        self.subscriptions = {}
        self.price_data = {}
        self.connected = False
    
    def connect(self):
        """
        Connect to ForexCom API
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            log.info("Connecting to ForexCom API...")
            self.client = ForexComClient(self.username, self.password, self.app_key)
            self.connected = self.client.connect()
            
            if self.connected:
                log.info("Connected to ForexCom API")
                
                # Get account info
                account_info = self.client.get_account_info()
                log.info(f"Account info: {account_info}")
                
                return True
            else:
                log.error("Failed to connect to ForexCom API")
                return False
                
        except Exception as e:
            log.error(f"Error connecting to ForexCom API: {e}")
            return False
    
    def subscribe_to_symbol(self, symbol):
        """
        Subscribe to price updates for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EUR/USD')
            
        Returns:
            bool: True if subscribed, False otherwise
        """
        if not self.connected:
            log.error("Not connected to ForexCom API")
            return False
        
        try:
            # Initialize price data for this symbol
            self.price_data[symbol] = {
                'bid': None,
                'ask': None,
                'low': None,
                'high': None,
                'price': None,
                'timestamp': None
            }
            
            # Define callback function
            def price_callback(price):
                self.price_data[symbol] = {
                    'bid': price.bid,
                    'ask': price.offer,
                    'low': price.low,
                    'high': price.high,
                    'price': price.price,
                    'timestamp': datetime.now().isoformat()
                }
                log.info(f"Price update for {symbol}: {self.price_data[symbol]}")
            
            # Subscribe to price updates
            subscription_id = self.client.price_symbol_subscribe(symbol, price_callback)
            self.subscriptions[symbol] = subscription_id
            
            log.info(f"Subscribed to {symbol}")
            return True
            
        except Exception as e:
            log.error(f"Error subscribing to {symbol}: {e}")
            return False
    
    def unsubscribe_from_symbol(self, symbol):
        """
        Unsubscribe from price updates for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EUR/USD')
            
        Returns:
            bool: True if unsubscribed, False otherwise
        """
        if not self.connected:
            log.error("Not connected to ForexCom API")
            return False
        
        try:
            if symbol in self.subscriptions:
                self.client.unsubscribe_listener(self.subscriptions[symbol])
                del self.subscriptions[symbol]
                log.info(f"Unsubscribed from {symbol}")
                return True
            else:
                log.warning(f"Not subscribed to {symbol}")
                return False
                
        except Exception as e:
            log.error(f"Error unsubscribing from {symbol}: {e}")
            return False
    
    def get_latest_price(self, symbol):
        """
        Get the latest price for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EUR/USD')
            
        Returns:
            dict: Price information or None if error
        """
        if not self.connected:
            log.error("Not connected to ForexCom API")
            return None
        
        try:
            # Check if we're subscribed to this symbol
            if symbol not in self.price_data:
                # Subscribe to the symbol
                if not self.subscribe_to_symbol(symbol):
                    return None
                
                # Wait for price data
                for _ in range(5):
                    if self.price_data[symbol]['price'] is not None:
                        break
                    time.sleep(1)
            
            # Return price data
            return self.price_data[symbol]
            
        except Exception as e:
            log.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def close(self):
        """Close the connection"""
        try:
            if self.connected:
                # Unsubscribe from all symbols
                for symbol in list(self.subscriptions.keys()):
                    self.unsubscribe_from_symbol(symbol)
                
                # Disconnect
                self.client = None
                self.connected = False
                log.info("Disconnected from ForexCom API")
                
        except Exception as e:
            log.error(f"Error closing connection: {e}")

def test_forexcom():
    """Test the ForexCom data provider"""
    # Replace with your ForexCom credentials
    username = '<USERNAME>'  # Replace with your username
    password = '<PASSWORD>'  # Replace with your password
    app_key = '<APP_KEY>'    # Replace with your app key
    
    # Check if credentials are provided
    if username == '<USERNAME>' or password == '<PASSWORD>' or app_key == '<APP_KEY>':
        log.error("Please replace the placeholder credentials with your ForexCom credentials")
        return
    
    provider = ForexComDataProvider(username, password, app_key)
    
    try:
        # Connect to ForexCom API
        if not provider.connect():
            log.error("Failed to connect to ForexCom API")
            return
        
        # Subscribe to symbols
        symbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD']
        
        for symbol in symbols:
            provider.subscribe_to_symbol(symbol)
        
        # Wait for price updates
        log.info("Waiting for price updates (30 seconds)...")
        time.sleep(30)
        
        # Get latest prices
        for symbol in symbols:
            price_info = provider.get_latest_price(symbol)
            log.info(f"Latest price for {symbol}: {price_info}")
        
        # Save price data to CSV
        data_dir = Path('trading_bot/data/forexcom')
        data_dir.mkdir(exist_ok=True, parents=True)
        
        for symbol in symbols:
            price_info = provider.get_latest_price(symbol)
            if price_info:
                # Create DataFrame
                df = pd.DataFrame([price_info])
                
                # Save to CSV
                csv_path = data_dir / f"{symbol.replace('/', '')}_price.csv"
                df.to_csv(csv_path, index=False)
                log.info(f"Saved price data for {symbol} to {csv_path}")
        
    finally:
        # Close the connection
        provider.close()

if __name__ == "__main__":
    test_forexcom()
