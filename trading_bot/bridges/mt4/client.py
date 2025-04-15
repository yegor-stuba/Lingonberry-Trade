"""
ZeroMQ client for MetaTrader 4
Based on the DWX ZeroMQ Connector
"""

import zmq
import time
import json
import logging
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from trading_bot.config import credentials

logger = logging.getLogger(__name__)

class MT4ZeroMQClient:
    """
    Client for the MT4 ZeroMQ bridge
    Connects to the DWX ZeroMQ Server running in MetaTrader 4
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 protocol: str = "tcp", 
                 push_port: int = 5555,
                 pull_port: int = 5556,
                 sub_port: int = 5557,
                 context: Optional[zmq.Context] = None,
                 poll_timeout: int = 1000,
                 sleep_delay: float = 0.001,
                 verbose: bool = False):
        """
        Initialize the MT4 ZeroMQ client
        
        Args:
            host (str): Host address
            protocol (str): Protocol (tcp, ipc, etc.)
            push_port (int): Port for push socket (client -> server)
            pull_port (int): Port for pull socket (server -> client)
            sub_port (int): Port for subscribe socket (market data)
            context (zmq.Context): ZeroMQ context
            poll_timeout (int): Polling timeout in milliseconds
            sleep_delay (float): Sleep delay between operations
            verbose (bool): Verbose logging
        """
        self.host = host
        self.protocol = protocol
        self.push_port = push_port
        self.pull_port = pull_port
        self.sub_port = sub_port
        
        self.context = context or zmq.Context.instance()
        self.poll_timeout = poll_timeout
        self.sleep_delay = sleep_delay
        self.verbose = verbose
        
        # Socket to send commands to MT4
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket_connection = f"{protocol}://{host}:{push_port}"
        
        # Socket to receive responses from MT4
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket_connection = f"{protocol}://{host}:{pull_port}"
        
        # Socket to receive market data from MT4
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket_connection = f"{protocol}://{host}:{sub_port}"
        
        # Set up the poller
        self.poller = zmq.Poller()
        self.poller.register(self.pull_socket, zmq.POLLIN)
        
        # Market data storage
        self.market_data = {}
        
        # Connection status
        self.connected = False
        
        # MT4 account credentials
        self.account = credentials.MT4_CREDENTIALS.get("BlackBullMarkets-Demo", {})
    
    def connect(self) -> bool:
        """
        Connect to the MT4 ZeroMQ server
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Connect sockets
            self.push_socket.connect(self.push_socket_connection)
            self.pull_socket.connect(self.pull_socket_connection)
            self.sub_socket.connect(self.sub_socket_connection)
            
            # Subscribe to all messages
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            
            # Test connection by sending a status request
            self._send_request("STATUS")
            response = self._receive_response(timeout=5000)
            
            if response and "status" in response:
                self.connected = True
                logger.info(f"Connected to MT4 ZeroMQ server: {response}")
                return True
            else:
                logger.error("Failed to connect to MT4 ZeroMQ server: No valid response")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MT4 ZeroMQ server: {e}")
            return False
    
    def _send_request(self, request: str) -> None:
        """
        Send a request to the MT4 server
        
        Args:
            request (str): Request string
        """
        try:
            self.push_socket.send_string(request)
            if self.verbose:
                logger.debug(f"Sent request: {request}")
        except Exception as e:
            logger.error(f"Error sending request: {e}")
    
    def _receive_response(self, timeout: int = None) -> Optional[Dict]:
        """
        Receive a response from the MT4 server
        
        Args:
            timeout (int): Timeout in milliseconds
            
        Returns:
            dict: Response data or None if timeout
        """
        try:
            timeout = timeout or self.poll_timeout
            sockets = dict(self.poller.poll(timeout))
            
            if self.pull_socket in sockets:
                response = self.pull_socket.recv_string()
                
                if self.verbose:
                    logger.debug(f"Received response: {response}")
                
                # Parse JSON response
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error receiving response: {e}")
            return None
    
    async def get_historical_data(self, 
                                 symbol: str, 
                                 timeframe: str, 
                                 count: int = 100) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data from MT4
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD')
            timeframe (str): Timeframe (e.g., 'H1')
            count (int): Number of candles
            
        Returns:
            pd.DataFrame: OHLCV data or None if error
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return None
        
        try:
            # Construct request
            request = f"GET_RATES|{symbol}|{timeframe}|{count}"
            
            # Send request
            self._send_request(request)
            
            # Wait for response
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 30:  # 30 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'RATES':
                    break
            
            if not response or response.get('_action') != 'RATES':
                logger.error(f"Failed to get historical data for {symbol} {timeframe}")
                return None
            
            # Parse rates data
            rates_data = response.get('_data', [])
            
            if not rates_data:
                logger.warning(f"No historical data returned for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates_data)
            
            # Convert timestamp to datetime
            if 'time' in df.columns:
                df['datetime'] = pd.to_datetime(df['time'], unit='s')
                df.drop('time', axis=1, inplace=True)
            
            # Set datetime as index
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col])
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """
        Get available symbols from MT4
        
        Returns:
            list: List of available symbols
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return []
        
        try:
            # Send request
            self._send_request("GET_SYMBOLS")
            
            # Wait for response
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 10:  # 10 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'SYMBOLS':
                    break
            
            if not response or response.get('_action') != 'SYMBOLS':
                logger.error("Failed to get symbols from MT4")
                return []
            
            # Parse symbols data
            symbols = response.get('_data', [])
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []
    
    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        """
        Get current price for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD')
            
        Returns:
            dict: Price data with bid, ask, etc.
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return None
        
        try:
            # Send request
            self._send_request(f"GET_PRICE|{symbol}")
            
            # Wait for response
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 5:  # 5 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'PRICE' and response.get('_symbol') == symbol:
                    break
            
            if not response or response.get('_action') != 'PRICE':
                logger.error(f"Failed to get price for {symbol}")
                return None
            
            # Parse price data
            price_data = {
                'symbol': symbol,
                'bid': response.get('_bid', 0),
                'ask': response.get('_ask', 0),
                'time': response.get('_time', datetime.now().timestamp())
            }
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    async def subscribe_to_prices(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time price updates for symbols
        
        Args:
            symbols (list): List of symbols to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return False
        
        try:
            # Send subscription request
            symbols_str = ",".join(symbols)
            self._send_request(f"SUBSCRIBE|{symbols_str}")
            
            # Wait for confirmation
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 5:  # 5 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'SUBSCRIBE_CONFIRM':
                    break
            
            if not response or response.get('_action') != 'SUBSCRIBE_CONFIRM':
                logger.error(f"Failed to subscribe to symbols: {symbols}")
                return False
            
            logger.info(f"Successfully subscribed to symbols: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to prices: {e}")
            return False
    
    async def place_order(self, 
                         symbol: str, 
                         order_type: str, 
                         volume: float, 
                         price: Optional[float] = None,
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None,
                         comment: str = "",
                         magic: int = 0) -> Optional[Dict]:
        """
        Place a trading order
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD')
            order_type (str): Order type ('BUY', 'SELL', 'BUYLIMIT', 'SELLLIMIT', etc.)
            volume (float): Order volume in lots
            price (float): Order price (for limit/stop orders)
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            comment (str): Order comment
            magic (int): Magic number
            
        Returns:
            dict: Order result with ticket number, etc.
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return None
        
        try:
            # Construct order request
            order_params = {
                "_action": "TRADE",
                "_type": order_type,
                "_symbol": symbol,
                "_volume": volume
            }
            
            if price is not None:
                order_params["_price"] = price
            
            if stop_loss is not None:
                order_params["_sl"] = stop_loss
            
            if take_profit is not None:
                order_params["_tp"] = take_profit
            
            if comment:
                order_params["_comment"] = comment
            
            if magic:
                order_params["_magic"] = magic
            
            # Send order request
            self._send_request(json.dumps(order_params))
            
            # Wait for order confirmation
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 10:  # 10 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'TRADE_CONFIRM':
                    break
            
            if not response or response.get('_action') != 'TRADE_CONFIRM':
                logger.error(f"Failed to place order for {symbol}")
                return None
            
            # Parse order result
            order_result = {
                'ticket': response.get('_ticket', 0),
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'price': response.get('_price', 0),
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': comment,
                'magic': magic,
                'time': response.get('_time', datetime.now().timestamp())
            }
            
            logger.info(f"Order placed successfully: Ticket #{order_result['ticket']}")
            return order_result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def close_order(self, ticket: int) -> bool:
        """
        Close an open order
        
        Args:
            ticket (int): Order ticket number
            
        Returns:
            bool: True if order closed successfully
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return False
        
        try:
            # Send close order request
            self._send_request(f"CLOSE_ORDER|{ticket}")
            
            # Wait for confirmation
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 10:  # 10 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'CLOSE_CONFIRM' and response.get('_ticket') == ticket:
                    break
            
            if not response or response.get('_action') != 'CLOSE_CONFIRM':
                logger.error(f"Failed to close order #{ticket}")
                return False
            
            logger.info(f"Order #{ticket} closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error closing order: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict]:
        """
        Get account information
        
        Returns:
            dict: Account information
        """
        if not self.connected:
            logger.error("Not connected to MT4 ZeroMQ server")
            return None
        
        try:
            # Send request
            self._send_request("GET_ACCOUNT_INFO")
            
            # Wait for response
            response = None
            start_time = time.time()
            
            while time.time() - start_time < 5:  # 5 second timeout
                # Use asyncio.sleep to avoid blocking
                await asyncio.sleep(0.1)
                
                response = self._receive_response()
                if response and response.get('_action') == 'ACCOUNT_INFO':
                    break
            
            if not response or response.get('_action') != 'ACCOUNT_INFO':
                logger.error("Failed to get account information")
                return None
            
            # Parse account info
            account_info = {
                'balance': response.get('_balance', 0),
                'equity': response.get('_equity', 0),
                'margin': response.get('_margin', 0),
                'free_margin': response.get('_free_margin', 0),
                'leverage': response.get('_leverage', 1),
                'currency': response.get('_currency', 'USD')
            }
            
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def close(self) -> None:
        """Close the connection and clean up resources"""
        try:
            if self.connected:
                # Unsubscribe from all symbols
                self._send_request("UNSUBSCRIBE|ALL")
                
                # Wait a moment for the server to process
                await asyncio.sleep(0.5)
                
                # Close sockets
                self.push_socket.close()
                self.pull_socket.close()
                self.sub_socket.close()
                
                self.connected = False
                logger.info("Closed connection to MT4 ZeroMQ server")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
