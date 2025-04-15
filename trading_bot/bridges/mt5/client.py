"""Client for the MT5 bridge server"""
import requests
import pandas as pd
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

class MT5BridgeClient:
    """Client for the MT5 bridge server"""
    
    def __init__(self, server_url="http://localhost:5555"):
        """
        Initialize the MT5 bridge client
        
        Args:
            server_url (str): URL of the bridge server
        """
        self.server_url = server_url
        self.connected = False

        
    def connect(self):
        """
        Connect to the bridge server
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Try multiple times with increasing timeouts
            for attempt in range(3):
                try:
                    timeout = 5 * (attempt + 1)  # 5, 10, 15 seconds
                    logger.info(f"Connecting to MT5 bridge server (attempt {attempt+1}, timeout {timeout}s)...")
                    response = requests.get(f"{self.server_url}/status", timeout=timeout)
                    
                    if response.status_code == 200:
                        self.connected = True
                        logger.info(f"Connected to MT5 bridge server: {response.json()}")
                        return True
                    else:
                        logger.error(f"Failed to connect to MT5 bridge server: {response.status_code} - {response.text}")
                except requests.exceptions.Timeout:
                    logger.warning(f"Connection timeout (attempt {attempt+1})")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error (attempt {attempt+1})")
                
                # Wait before retrying
                time.sleep(2)
            
            logger.error("Failed to connect to MT5 bridge server after multiple attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to MT5 bridge server: {e}")
            return False
    
    def get_forex_data(self, symbol, timeframe, count):
        """
        Get forex data from MT5 via the bridge server
        
        Args:
            symbol (str): Forex symbol (e.g., 'EURUSD')
            timeframe (str): Timeframe (e.g., 'H1')
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: Forex data
        """
        if not self.connected:
            if not self.connect():
                logger.error("Not connected to MT5 bridge server")
                return None
        
        # Prepare the request
        request = f"GET_RATES|{symbol}|{timeframe}|{count}"
        
        try:
            # Send the request with multiple retries
            for attempt in range(3):
                try:
                    timeout = 30 * (attempt + 1)  # 30, 60, 90 seconds
                    logger.info(f"Sending request to MT5 bridge (attempt {attempt+1}, timeout {timeout}s)...")
                    
                    response = requests.post(
                        f"{self.server_url}/send_request", 
                        json={'request': request},
                        timeout=timeout
                    )
                    
                    if response.status_code == 200:
                        # Get the result
                        result = response.json().get('result')
                        
                        if not result or not result.startswith('RATES'):
                            logger.error(f"Error: Invalid result format - {result}")
                            continue  # Try again
                        
                        # Parse the result
                        parts = result.split('|')
                        count = int(parts[1])
                        
                        # Parse the rates data
                        rates = []
                        for i in range(2, 2 + count):
                            if i < len(parts):
                                rate_parts = parts[i].split(',')
                                rates.append({
                                    'datetime': datetime.fromtimestamp(int(rate_parts[0])),
                                    'open': float(rate_parts[1]),
                                    'high': float(rate_parts[2]),
                                    'low': float(rate_parts[3]),
                                    'close': float(rate_parts[4]),
                                    'volume': int(rate_parts[5])
                                })
                        
                        # Create DataFrame
                        df = pd.DataFrame(rates)
                        
                        # Set datetime as index
                        if not df.empty:
                            df.set_index('datetime', inplace=True)
                        
                        return df
                    else:
                        logger.error(f"Error: {response.status_code} - {response.text}")
                
                except requests.exceptions.Timeout:
                    logger.warning(f"Request timeout (attempt {attempt+1})")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error (attempt {attempt+1})")
                
                # Wait before retrying
                time.sleep(2)
            
            logger.error("Failed to get forex data after multiple attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error getting forex data: {e}")
            return None

    
    def get_available_symbols(self):
        """
        Get a list of all available symbols in MT5
        
        Returns:
            list: List of available symbols
        """
        if not self.connected:
            if not self.connect():
                logger.error("Not connected to MT5 bridge server")
                return None
        
        # Prepare the request
        request = "GET_SYMBOLS"
        
        try:
            # Send the request
            response = requests.post(f"{self.server_url}/send_request", 
                                    json={'request': request},
                                    timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Error: {response.status_code} - {response.text}")
                return None
            
            # Get the result
            result = response.json().get('result')
            
            if not result or not result.startswith('SYMBOLS'):
                logger.error(f"Error: Invalid result format - {result}")
                return None
            
            # Parse the result
            parts = result.split('|')
            symbols = parts[1:]
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return None
    
    def get_open_charts(self):
        """
        Get a list of all open charts in MT5
        
        Returns:
            list: List of open charts with their timeframes
        """
        if not self.connected:
            if not self.connect():
                logger.error("Not connected to MT5 bridge server")
                return None
        
        # Prepare the request
        request = "GET_OPEN_CHARTS"
        
        try:
            # Send the request
            response = requests.post(f"{self.server_url}/send_request", 
                                    json={'request': request},
                                    timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Error: {response.status_code} - {response.text}")
                return None
            
            # Get the result
            result = response.json().get('result')
            
            if not result or not result.startswith('CHARTS'):
                logger.error(f"Error: Invalid result format - {result}")
                return None
            
            # Parse the result
            parts = result.split('|')
            charts = []
            
            for i in range(1, len(parts)):
                if parts[i]:
                    chart_parts = parts[i].split(',')
                    if len(chart_parts) >= 2:
                        charts.append({
                            'symbol': chart_parts[0],
                            'timeframe': chart_parts[1]
                        })
            
            return charts
            
        except Exception as e:
            logger.error(f"Error getting open charts: {e}")
            return None

