"""
cTrader data provider module
Handles connection to cTrader API, fetching historical and live data
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union
import pandas as pd
import asyncio
from pathlib import Path

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAAccountAuthReq,
    ProtoOAGetTrendbarsReq,
    ProtoOASubscribeSpotsReq,
    ProtoOASubscribeLiveTrendbarReq,
    ProtoOASymbolsListReq
)
from twisted.internet import reactor, defer
from twisted.internet.task import LoopingCall

from trading_bot.config.credentials import (
    CTRADER_CLIENT_ID,
    CTRADER_CLIENT_SECRET,
    CTRADER_ACCOUNT_ID,
    CTRADER_ACCESS_TOKEN
)

# Configure logging
logger = logging.getLogger(__name__)

# Symbol mapping (updated based on broker's actual values)
SYMBOL_IDS = {
    # Crypto
    'BTCUSD': 101,  # Updated from test results
    'BTCUSDT': 101, # Alias for BTCUSD
    'ETHUSD': 102,  
    'ETHUSDT': 102, # Alias for ETHUSD
    'XRPUSD': 2592,
    'ADAUSD': 2597,
    # Forex
    'EURUSD': 2596, # Updated from test results
    'GBPUSD': 2,
    'GBPJPY': 4410,
    'USDJPY': 4,
    'AUDUSD': 5,
    'USDCAD': 8,
    # Indices
    'US30': 193,    # Updated from test results
    'US500': 2600,  # Updated from test results
    'USTEC': 2552,  # Updated from test results
    'NAS100': 185,  # Updated from test results
    'SPX500': 2600, # Alias for US500
    # Metals
    'XAUUSD': 2469, # Updated from test results
    'XAGUSD': 42,
}

# Timeframe mapping
TIMEFRAME_PERIODS = {
    "M1": 1,    # 1 minute
    "M2": 2,    # 2 minutes
    "M3": 3,    # 3 minutes
    "M4": 4,    # 4 minutes
    "M5": 5,    # 5 minutes
    "M10": 6,   # 10 minutes
    "M15": 7,   # 15 minutes
    "M30": 8,   # 30 minutes
    "H1": 9,    # 1 hour
    "H4": 10,   # 4 hours
    "H12": 11,  # 12 hours
    "D1": 12,   # 1 day
    "W1": 13,   # 1 week
    "MN1": 14   # 1 month
}

_instance = None

class CTraderData:
    _initialized = False # Class variable to track initialization
    """
    Class for handling cTrader data operations (Singleton pattern)
    """
    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super(CTraderData, cls).__new__(cls)
            _instance._initialized = False
        return _instance
        
    def __init__(self):
        """Initialize the cTrader data provider (only once)"""
        if CTraderData._initialized:  # Use class name to access class variable
            return
            
        self.client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
        self.connected = False
        self.authenticated = False
        self.symbols_loaded = False
        self.symbol_list = []
        self.live_data_subscriptions = set()
        self.data_callbacks = {}
        self.pending_requests = {}
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self._reconnect_scheduled = False
        
        # Set up callbacks
        self.client.setConnectedCallback(self._on_connected)
        self.client.setDisconnectedCallback(self._on_disconnected)
        self.client.setMessageReceivedCallback(self._on_message_received)
        
        # Add keepalive mechanism
        self._keepalive_call = None
        
        CTraderData._initialized = True  # Set class variable

    def connect(self) -> bool:
        """
        Connect to cTrader API
        
        Returns:
            bool: True if connection was initiated successfully
        """
        logger.info("Connecting to cTrader API...")
        
        # Start the client service
        self.client.startService()
        
        # Start the reactor if it's not running
        if not reactor.running:
            # Run the reactor in a separate thread
            import threading
            try:
                reactor_thread = threading.Thread(target=lambda: reactor.run(installSignalHandlers=False))
                reactor_thread.daemon = True
                reactor_thread.start()
            except Exception as e:
                logger.error(f"Error starting reactor: {e}")
        
        # Give it a moment to connect
        time.sleep(2)
        
        return True

    def disconnect(self):
        """Disconnect from cTrader API"""
        logger.info("Disconnecting from cTrader API...")
        
        # Stop the client service
        self.client.stopService()
        
        # Don't stop the reactor, as it might be used by other instances
        # Just mark as disconnected
        self.connected = False
        self.authenticated = False
        logger.info("Disconnected from cTrader API")


    def get_historical_data(self, symbol: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """
        Get historical data for a symbol and timeframe
        
        Args:
            symbol (str): Trading symbol (e.g., "EURUSD")
            timeframe (str): Timeframe (e.g., "M1", "H1")
            bars (int): Number of bars to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            if not self.authenticated:
                logger.error("Not authenticated with cTrader API")
                logger.info("Attempting to load data from CSV as fallback")
                return self.load_data(symbol, timeframe)
            
            if timeframe not in TIMEFRAME_PERIODS:
                logger.error(f"Invalid timeframe: {timeframe}")
                logger.info("Available timeframes: {list(TIMEFRAME_PERIODS.keys())}")
                return pd.DataFrame()
            
            # Normalize symbol name (remove .P, .F, etc. suffixes if present)
            normalized_symbol = symbol.split('.')[0].upper()
            
            symbol_id = SYMBOL_IDS.get(normalized_symbol)
            if not symbol_id:
                logger.error(f"Unknown symbol: {symbol}")
                logger.info(f"Available symbols: {list(SYMBOL_IDS.keys())}")
                
                # Try to load from file as fallback
                logger.info(f"Attempting to load {symbol} data from CSV file")
                df = self.load_data(symbol, timeframe)
                if not df.empty:
                    logger.info(f"Loaded {len(df)} rows from file for {symbol} {timeframe}")
                    return df
                    
                return pd.DataFrame()
            
            # Calculate period in minutes for timestamp calculation
            period_minutes = self._get_period_minutes(timeframe)
            
            now = int(time.time() * 1000)  # Current time in milliseconds
            from_timestamp = now - (period_minutes * bars * 60 * 1000)  # Calculate start time
            
            logger.info(f"Requesting {bars} {timeframe} historical bars for {symbol}...")
            logger.info(f"From: {datetime.fromtimestamp(from_timestamp/1000)}")
            logger.info(f"To: {datetime.fromtimestamp(now/1000)}")
            
            # Create a deferred for this request
            d = defer.Deferred()
            request_id = f"{symbol}_{timeframe}_{int(time.time())}"
            self.pending_requests[request_id] = {
                "deferred": d,
                "symbol": symbol,
                "timeframe": timeframe
            }
            
            # Send the request
            trendbars_req = ProtoOAGetTrendbarsReq()
            trendbars_req.ctidTraderAccountId = CTRADER_ACCOUNT_ID
            trendbars_req.symbolId = symbol_id
            trendbars_req.period = TIMEFRAME_PERIODS[timeframe]
            trendbars_req.fromTimestamp = from_timestamp
            trendbars_req.toTimestamp = now
            
            # Send the request and wait for response
            self.client.send(trendbars_req)
            
            # Wait for the response with a timeout
            timeout = 30  # seconds
            start_time = time.time()
            result = None
            
            while request_id in self.pending_requests and time.time() - start_time < timeout:
                time.sleep(0.1)
                if request_id in self.data_callbacks:
                    result = self.data_callbacks.pop(request_id)
                    self.pending_requests.pop(request_id, None)
                    break
            
            if not result:
                logger.error(f"Timeout waiting for historical data for {symbol} {timeframe}")
                self.pending_requests.pop(request_id, None)
                
                # Try to load from file as fallback
                logger.info(f"Attempting to load {symbol} data from CSV file after timeout")
                df = self.load_data(symbol, timeframe)
                if not df.empty:
                    logger.info(f"Loaded {len(df)} rows from file for {symbol} {timeframe}")
                    return df
                    
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = self._convert_to_dataframe(result, symbol, timeframe)
            
            # Save to CSV
            self._save_to_csv(df, symbol, timeframe)
            
            return df
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol} {timeframe}: {e}", exc_info=True)
            # Try to load from file as fallback
            logger.info(f"Attempting to load {symbol} data from CSV file after error")
            df = self.load_data(symbol, timeframe)
            if not df.empty:
                logger.info(f"Loaded {len(df)} rows from file for {symbol} {timeframe}")
                return df
            return pd.DataFrame()


    def subscribe_to_live_data(self, symbol: str, timeframe: str, callback=None):
        """
        Subscribe to live data for a symbol and timeframe
        
        Args:
            symbol (str): Trading symbol (e.g., "EURUSD")
            timeframe (str): Timeframe (e.g., "M1", "H1")
            callback (callable, optional): Callback function for live data updates
        """
        if not self.authenticated:
            logger.error("Not authenticated with cTrader API")
            return
        
        if timeframe not in TIMEFRAME_PERIODS:
            logger.error(f"Invalid timeframe: {timeframe}")
            return
        
        # Normalize symbol name
        normalized_symbol = symbol.split('.')[0].upper()
        
        symbol_id = SYMBOL_IDS.get(normalized_symbol)
        if not symbol_id:
            logger.error(f"Unknown symbol: {symbol}")
            return
        
        # Check if already subscribed
        subscription_key = f"{symbol}_{timeframe}"
        if subscription_key in self.live_data_subscriptions:
            logger.info(f"Already subscribed to {symbol} {timeframe}")
            return
        
        logger.info(f"Subscribing to live {timeframe} data for {symbol}...")
        
        # First subscribe to spots
        spot_sub_req = ProtoOASubscribeSpotsReq()
        spot_sub_req.ctidTraderAccountId = CTRADER_ACCOUNT_ID
        spot_sub_req.symbolId.append(symbol_id)
        self.client.send(spot_sub_req)
        
        # Then subscribe to live trend bars
        trendbar_sub_req = ProtoOASubscribeLiveTrendbarReq()
        trendbar_sub_req.ctidTraderAccountId = CTRADER_ACCOUNT_ID
        trendbar_sub_req.symbolId = symbol_id
        trendbar_sub_req.period = TIMEFRAME_PERIODS[timeframe]
        self.client.send(trendbar_sub_req)
        
        # Store the subscription
        self.live_data_subscriptions.add(subscription_key)
        
        # Store the callback if provided
        if callback:
            self.data_callbacks[subscription_key + "_live"] = callback
        
        logger.info(f"Subscribed to live {timeframe} data for {symbol}")

    def get_available_symbols(self) -> List[Dict]:
        """
        Get list of available symbols
        
        Returns:
            List[Dict]: List of available symbols with their details
        """
        if not self.authenticated:
            logger.error("Not authenticated with cTrader API")
            return []
        
        if self.symbols_loaded:
            return self.symbol_list
        
        logger.info("Requesting symbol list...")
        
        # Create a deferred for this request
        d = defer.Deferred()
        request_id = f"symbols_{int(time.time())}"
        self.pending_requests[request_id] = {
            "deferred": d,
            "type": "symbols"
        }
        
        # Send the request
        symbols_req = ProtoOASymbolsListReq()
        symbols_req.ctidTraderAccountId = CTRADER_ACCOUNT_ID
        self.client.send(symbols_req)
        
        # Wait for the response with a timeout
        timeout = 10  # seconds
        start_time = time.time()
        
        while request_id in self.pending_requests and time.time() - start_time < timeout:
            time.sleep(0.1)
            if request_id in self.data_callbacks:
                self.symbol_list = self.data_callbacks.pop(request_id)
                self.pending_requests.pop(request_id, None)
                self.symbols_loaded = True
                break
        
        if not self.symbols_loaded:
            logger.error("Timeout waiting for symbol list")
            self.pending_requests.pop(request_id, None)
            return []
        
        return self.symbol_list

    def get_available_timeframes(self) -> Dict[str, int]:
        """
        Get list of available timeframes
        
        Returns:
            Dict[str, int]: Dictionary of available timeframes and their values
        """
        return TIMEFRAME_PERIODS.copy()

    def get_symbol_ids(self) -> Dict[str, int]:
        """
        Get accurate symbol IDs from the broker
        
        Returns:
            Dict[str, int]: Dictionary mapping symbol names to their IDs
        """
        if not self.authenticated:
            logger.error("Not authenticated with cTrader API")
            return {}
        
        # Request symbol list if not already loaded
        symbols = self.get_available_symbols()
        
        if not symbols:
            logger.error("Failed to get symbol list")
            return {}
        
        # Create a mapping of symbol names to IDs
        symbol_ids = {}
        for symbol_info in symbols:
            if 'name' in symbol_info and 'id' in symbol_info:
                symbol_ids[symbol_info['name']] = symbol_info['id']
        
        logger.info(f"Retrieved {len(symbol_ids)} symbol IDs from broker")
        return symbol_ids

    def _on_connected(self, client):
        """Callback when connected to cTrader API"""
        self.connected = True
        logger.info("Connected to cTrader Open API")
        
        # Application authentication
        app_auth_req = ProtoOAApplicationAuthReq()
        app_auth_req.clientId = CTRADER_CLIENT_ID
        app_auth_req.clientSecret = CTRADER_CLIENT_SECRET
        d = client.send(app_auth_req)
        d.addCallback(self._on_app_auth_response)
        d.addErrback(self._on_error)
        
        # Remove the call to _start_keepalive() that's causing the error
        # self._start_keepalive()  # <-- Comment out or remove this line


    def _on_app_auth_response(self, response):
        """Callback when application authentication is complete"""
        logger.info("Application authenticated successfully")
        
        # Account authentication
        account_auth_req = ProtoOAAccountAuthReq()
        account_auth_req.ctidTraderAccountId = CTRADER_ACCOUNT_ID
        account_auth_req.accessToken = CTRADER_ACCESS_TOKEN
        d = self.client.send(account_auth_req)
        d.addCallback(self._on_account_auth_response)
        d.addErrback(self._on_error)

    def _on_account_auth_response(self, response):
        """Callback when account authentication is complete"""
        logger.info("Account authenticated successfully")
        self.authenticated = True

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

    def _reconnect(self):
        """Attempt to reconnect to cTrader API with exponential backoff"""
        self._reconnect_scheduled = False
        
        if not self.connected:
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries and not self.connected:
                try:
                    logger.info(f"Connecting to cTrader API (attempt {retry_count+1}/{max_retries})...")
                    self.client.startService()
                    # Wait a bit to see if connection succeeds
                    time.sleep(5)
                    
                    if self.connected:
                        logger.info("Successfully reconnected to cTrader API")
                        break
                        
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 5 * (2 ** retry_count)  # Exponential backoff
                        logger.info(f"Reconnection attempt failed. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"Error during reconnection attempt: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 5 * (2 ** retry_count)
                        logger.info(f"Reconnection attempt failed. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
            
            if not self.connected and retry_count >= max_retries:
                logger.error("Maximum reconnection attempts reached. Giving up on cTrader connection.")


    def _on_message_received(self, client, message):
        """Callback when a message is received from cTrader API"""
        try:
            # Extract the message
            extracted_message = Protobuf.extract(message)
            message_type = type(extracted_message).__name__
            
            # Check if it's a trendbar response
            if hasattr(extracted_message, 'trendbar') and len(extracted_message.trendbar) > 0:
                # This is a trendbar update (historical or live)
                period = getattr(extracted_message, 'period', None)
                
                # Process the trendbars
                trendbars = []
                for trendbar in extracted_message.trendbar:
                    trendbars.append(self._process_trendbar(trendbar, period))
                
                # Find the matching request or subscription
                for request_id, request_info in list(self.pending_requests.items()):
                    if 'timeframe' in request_info and TIMEFRAME_PERIODS.get(request_info['timeframe']) == period:
                        # This is a response to a historical data request
                        self.data_callbacks[request_id] = trendbars
                        break
                
                # Check if this is a live update for a subscription
                if period is not None:
                    # Find the matching timeframe
                    timeframe = next((tf for tf, p in TIMEFRAME_PERIODS.items() if p == period), f"Period{period}")
                    
                    # Check for live data subscriptions
                    for symbol in SYMBOL_IDS:
                        subscription_key = f"{symbol}_{timeframe}"
                        if subscription_key in self.live_data_subscriptions:
                            # This is a live update for a subscription
                            callback_key = subscription_key + "_live"
                            if callback_key in self.data_callbacks:
                                # Call the callback with the new data
                                self.data_callbacks[callback_key](trendbars)
                            
                            # Update the CSV file with the new data
                            self._append_live_data_to_csv(trendbars, symbol, timeframe)
            
            # Check if it's a symbols list response
            elif hasattr(extracted_message, 'symbol') and len(extracted_message.symbol) > 0:
                symbols = []
                for symbol in extracted_message.symbol:
                    if hasattr(symbol, 'symbolName') and hasattr(symbol, 'symbolId'):
                        symbols.append({
                            'name': symbol.symbolName,
                            'id': symbol.symbolId
                        })
                
                # Find the matching request
                for request_id, request_info in list(self.pending_requests.items()):
                    if request_info.get('type') == 'symbols':
                        self.data_callbacks[request_id] = symbols
                        break
            
            # Check if it's a spot price update
            elif hasattr(extracted_message, 'symbolId') and hasattr(extracted_message, 'bid') and hasattr(extracted_message, 'ask'):
                # This is a spot price update
                symbol_id = extracted_message.symbolId
                bid = extracted_message.bid / 100000
                ask = extracted_message.ask / 100000
                
                # Find the matching symbol
                for symbol, sid in SYMBOL_IDS.items():
                    if sid == symbol_id:
                        # Check for spot data subscriptions
                        subscription_key = f"{symbol}_SPOT"
                        if subscription_key in self.live_data_subscriptions:
                            callback_key = subscription_key + "_live"
                            if callback_key in self.data_callbacks:
                                # Call the callback with the new data
                                self.data_callbacks[callback_key]({
                                    'symbol': symbol,
                                    'bid': bid,
                                    'ask': ask,
                                    'timestamp': datetime.now()
                                })
                        break
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()

    def _on_error(self, failure):
        """Callback when an error occurs"""
        logger.error(f"Error: {failure}")
        # Print more detailed error information
        if hasattr(failure, 'value'):
            logger.error(f"Error value: {failure.value}")
        if hasattr(failure, 'type'):
            logger.error(f"Error type: {failure.type}")

    def _process_trendbar(self, bar, period=None) -> Dict:
        """
        Process a trendbar into a dictionary
        
        Args:
            bar: The trendbar object
            period: The period value (optional)
            
        Returns:
            Dict: Processed trendbar data
        """
        # Get the timestamp in seconds
        bar_timestamp = bar.utcTimestampInMinutes * 60
        timestamp = datetime.fromtimestamp(bar_timestamp)
        date_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # Convert prices from points to actual prices (divide by 100000)
        # Check which fields are available
        if hasattr(bar, 'low') and hasattr(bar, 'deltaOpen') and hasattr(bar, 'deltaHigh') and hasattr(bar, 'deltaClose'):
            # Using delta format
            low_price = bar.low / 100000
            open_price = (bar.low + bar.deltaOpen) / 100000
            high_price = (bar.low + bar.deltaHigh) / 100000
            close_price = (bar.low + bar.deltaClose) / 100000
        else:
            # Try direct access
            try:
                low_price = getattr(bar, 'low', 0) / 100000
                open_price = getattr(bar, 'open', low_price) / 100000
                high_price = getattr(bar, 'high', low_price) / 100000
                close_price = getattr(bar, 'close', low_price) / 100000
            except AttributeError:
                logger.error(f"Error: Unable to access price fields in trendbar")
                low_price = open_price = high_price = close_price = 0
        
        volume = getattr(bar, 'volume', 0)
        
        # Return as dictionary
        return {
            'timestamp': timestamp,
            'date_str': date_str,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }

    def _convert_to_dataframe(self, trendbars: List[Dict], symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Convert trendbars to a pandas DataFrame
        
        Args:
            trendbars (List[Dict]): List of processed trendbars
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        if not trendbars:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(trendbars)
        
        # Set timestamp as index
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
        
        # Ensure all required columns exist
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                df[col] = 0
        
        # Sort by index
        df.sort_index(inplace=True)
        
        return df

    def _save_to_csv(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """
        Save DataFrame to CSV file
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
        """
        if df.empty:
            logger.warning(f"No data to save for {symbol} {timeframe}")
            return
        
        # Format data for CSV
        formatted_data = []
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d %H:%M')
            line = f"{date_str} {row['open']:.5f} {row['high']:.5f} {row['low']:.5f} {row['close']:.5f} {int(row['volume'])}"
            formatted_data.append(line)
        
        # Save to file
        filename = self.data_dir / f"{symbol}_{timeframe}.csv"
        
        with open(filename, 'w') as f:
            f.write(f"# Historical data for {symbol} {timeframe}\n")
            f.write("# timestamp open high low close volume\n")
            f.write('\n'.join(formatted_data))
        
        logger.info(f"Historical data saved to {filename}")

    def _append_live_data_to_csv(self, trendbars: List[Dict], symbol: str, timeframe: str):
        """
        Append live data to CSV file
        
        Args:
            trendbars (List[Dict]): List of processed trendbars
            symbol (str): Trading symbol
            timeframe (str): Timeframe
        """
        if not trendbars:
            return
        
        # Format data for CSV
        formatted_data = []
        for bar in trendbars:
            line = f"{bar['date_str']} {bar['open']:.5f} {bar['high']:.5f} {bar['low']:.5f} {bar['close']:.5f} {int(bar['volume'])}"
            formatted_data.append(line)
        
        # Append to file
        filename = self.data_dir / f"{symbol}_{timeframe}_live.csv"
        
        # Create file with headers if it doesn't exist
        if not filename.exists():
            with open(filename, 'w') as f:
                f.write(f"# Live data for {symbol} {timeframe}\n")
                f.write("# timestamp open high low close volume\n")
        
        # Append data
        with open(filename, 'a') as f:
            f.write('\n'.join(formatted_data) + '\n')

    def _get_period_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe to minutes for timestamp calculation
        
        Args:
            timeframe (str): Timeframe (e.g., "M1", "H1")
            
        Returns:
            int: Period in minutes
        """
        if timeframe == 'M1':
            return 1
        elif timeframe == 'M2':
            return 2
        elif timeframe == 'M3':
            return 3
        elif timeframe == 'M4':
            return 4
        elif timeframe == 'M5':
            return 5
        elif timeframe == 'M10':
            return 10
        elif timeframe == 'M15':
            return 15
        elif timeframe == 'M30':
            return 30
        elif timeframe == 'H1':
            return 60
        elif timeframe == 'H4':
            return 240
        elif timeframe == 'H12':
            return 720
        elif timeframe == 'D1':
            return 1440
        elif timeframe == 'W1':
            return 10080
        elif timeframe == 'MN1':
            return 43200
        else:
            return 1  # Default to 1 minute

    # Enhance the load_data method to be more robust
    def load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Load data from CSV file
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        # Try multiple file patterns
        possible_filenames = [
            self.data_dir / f"{symbol}_{timeframe}.csv",
            self.data_dir / f"{symbol.replace('/', '')}_{timeframe}.csv",  # Try without slash for crypto
            self.data_dir / f"{symbol.split('.')[0]}_{timeframe}.csv"  # Try without suffix
        ]
        
        for filename in possible_filenames:
            if filename.exists():
                try:
                    # Skip the first two lines (headers)
                    df = pd.read_csv(filename, skiprows=2, header=None, sep=' ')
                    
                    # Set column names
                    if len(df.columns) >= 7:
                        df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
                        
                        # Combine date and time
                        df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
                        df.drop(['date', 'time'], axis=1, inplace=True)
                        
                        # Set timestamp as index
                        df.set_index('timestamp', inplace=True)
                        
                        logger.info(f"Loaded {len(df)} rows from {filename}")
                        return df
                    else:
                        logger.warning(f"CSV file {filename} has incorrect format")
                except Exception as e:
                    logger.error(f"Error loading data from {filename}: {e}")
        
        # If we get here, none of the files worked
        logger.warning(f"No data file found for {symbol} {timeframe}")
        return pd.DataFrame()

    def get_latest_price(self, symbol):
        """
        Get the latest price for a symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            float: Latest price or None if not available
        """
        try:
            # Normalize symbol name
            normalized_symbol = symbol.split('.')[0].upper()
            
            # Try to get from historical data
            df = self.get_historical_data(normalized_symbol, "M1", bars=1)
            if df is not None and not df.empty:
                return df['close'].iloc[-1]
            
            # If that fails, try to load from file
            df = self.load_data(normalized_symbol, "M1")
            if df is not None and not df.empty:
                return df['close'].iloc[-1]
            
            return None
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None


    def update_data(self, symbol: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """
        Update data for a symbol and timeframe
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            bars (int): Number of bars to fetch
            
        Returns:
            pd.DataFrame: Updated OHLCV data
        """
        # Get historical data
        df = self.get_historical_data(symbol, timeframe, bars)
        
        if df.empty:
            # Try to load from file
            df = self.load_data(symbol, timeframe)
        
        return df
