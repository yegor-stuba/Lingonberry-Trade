"""
Data processor module
Provides a unified interface for fetching and processing market data from various sources
"""

import os
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import asyncio

from trading_bot.data.ctrader_data import CTraderData
from trading_bot.data.crypto_data import CryptoDataProvider
from trading_bot.utils.helpers import get_market_type

# Configure logging
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Unified interface for fetching and processing market data
    Supports multiple data sources and provides consistent data format
    """
    
    def __init__(self, use_live_data=True, data_dir="data"):
        """
        Initialize the data processor
        
        Args:
            use_live_data (bool): Whether to use live data when available
            data_dir (str): Directory for data storage
        """
        self.use_live_data = use_live_data
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize data providers
        self.ctrader = CTraderData()
        self.crypto_provider = CryptoDataProvider()
        
        # Connect to cTrader if using live data
        if self.use_live_data:
            self.ctrader.connect()
            logger.info("Connecting to cTrader for live data")
        
        # Cache for loaded data
        self.data_cache = {}
    
    async def _get_crypto_data_async(self, symbol: str, timeframe: str, bars: int = 100):
        """
        Get crypto data asynchronously
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            bars (int): Number of bars to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Convert timeframe format for crypto provider
            crypto_timeframe = self._convert_to_crypto_timeframe(timeframe)
            return await self.crypto_provider.get_ohlcv(symbol, crypto_timeframe, bars)
        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")
            return pd.DataFrame()

    async def get_data(self, symbol: str, timeframe: str, bars: int = 100, 
                      source: str = 'auto') -> pd.DataFrame:
        """
        Get market data for a symbol and timeframe
        
        Args:
            symbol (str): Trading symbol (e.g., "EURUSD", "BTCUSDT")
            timeframe (str): Timeframe (e.g., "M1", "H1", "1h", "4h")
            bars (int): Number of bars to fetch
            source (str): Data source ('ctrader', 'crypto', 'csv', 'auto')
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        # Normalize symbol and timeframe
        symbol = symbol.upper()
        timeframe = self._normalize_timeframe(timeframe)
        
        # Create cache key
        cache_key = f"{symbol}_{timeframe}_{bars}_{source}"
        
        # Check cache first
        if cache_key in self.data_cache:
            logger.info(f"Using cached data for {symbol} {timeframe}")
            return self.data_cache[cache_key]
        
        # Determine market type
        market_type = get_market_type(symbol)
        
        # Determine data source if auto
        if source == 'auto':
            if market_type == 'crypto':
                source = 'crypto'
            else:
                source = 'ctrader'
        
        # Get data from appropriate source
        df = None
        
        if source == 'ctrader':
            if self.use_live_data and self.ctrader.authenticated:
                logger.info(f"Fetching live data from cTrader for {symbol} {timeframe}")
                df = self.ctrader.update_data(symbol, timeframe, bars)
            else:
                logger.info(f"Loading data from CSV for {symbol} {timeframe}")
                df = self._load_from_csv(symbol, timeframe)
        
        elif source == 'crypto':
            if self.use_live_data:
                logger.info(f"Fetching live data from crypto provider for {symbol} {timeframe}")
                # Directly await the async function since we're in an async context
                df = await self._get_crypto_data_async(symbol, timeframe, bars)
            else:
                logger.info(f"Loading data from CSV for {symbol} {timeframe}")
                df = self._load_from_csv(symbol, timeframe)
        
        elif source == 'csv':
            logger.info(f"Loading data from CSV for {symbol} {timeframe}")
            df = self._load_from_csv(symbol, timeframe)
        
        else:
            logger.error(f"Invalid data source: {source}")
            return pd.DataFrame()
        
        # If data is still empty, try CSV as a fallback
        if df is None or df.empty:
            logger.warning(f"Failed to get data from {source}, trying CSV fallback")
            df = self._load_from_csv(symbol, timeframe)
        
        # Cache the result
        if df is not None and not df.empty:
            self.data_cache[cache_key] = df
        
        return df if df is not None else pd.DataFrame()
    
    def get_data_sync(self, symbol: str, timeframe: str, bars: int = 100, 
                 source: str = 'auto') -> pd.DataFrame:
        """
        Synchronous version of get_data
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            bars (int): Number of bars to fetch
            source (str): Data source ('crypto', 'ctrader', 'csv', 'auto')
        
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async method
        if loop.is_running():
            # If loop is already running, create a future task
            future = asyncio.run_coroutine_threadsafe(
                self.get_data(symbol, timeframe, bars, source), loop
            )
            return future.result(timeout=30)  # Add timeout to prevent hanging
        else:
            # If loop is not running, use run_until_complete
            return loop.run_until_complete(self.get_data(symbol, timeframe, bars, source))
    
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
        # Clear cache for this symbol/timeframe
        cache_key_prefix = f"{symbol}_{timeframe}"
        for key in list(self.data_cache.keys()):
            if key.startswith(cache_key_prefix):
                del self.data_cache[key]
        
        # Get fresh data
        return self.get_data(symbol, timeframe, bars, 'auto')
    
    def get_available_symbols(self, market_type: str = None) -> List[str]:
        """
        Get list of available symbols
        
        Args:
            market_type (str, optional): Filter by market type ('forex', 'crypto', etc.)
            
        Returns:
            List[str]: List of available symbols
        """
        symbols = []
        
        # Get symbols from cTrader
        if self.use_live_data and self.ctrader.authenticated:
            try:
                ctrader_symbols = self.ctrader.get_available_symbols()
                symbols.extend([s['name'] for s in ctrader_symbols])
            except Exception as e:
                logger.error(f"Error getting cTrader symbols: {e}")
        
        # Get symbols from crypto provider
        if market_type in [None, 'crypto']:
            try:
                # Try to get symbols from CSV files first (as a reliable fallback)
                csv_symbols = self._get_crypto_symbols_from_csv()
                if csv_symbols:
                    logger.info(f"Loaded {len(csv_symbols)} crypto symbols from CSV files")
                    symbols.extend(csv_symbols)
                else:
                    # Only use default list if CSV loading failed
                    default_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 
                                     'SOLUSDT', 'BNBUSDT', 'DOGEUSDT', 'MATICUSDT']
                    logger.info(f"Using default list of {len(default_symbols)} crypto symbols")
                    symbols.extend(default_symbols)
            except Exception as e:
                logger.error(f"Error getting crypto symbols: {e}")
                # Fallback to common crypto symbols
                symbols.extend(['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT'])
        
        # Filter by market type if specified
        if market_type:
            symbols = [s for s in symbols if get_market_type(s) == market_type]
        
        # Remove duplicates and sort
        symbols = sorted(list(set(symbols)))
        
        return symbols
    
    def _get_crypto_symbols_from_csv(self) -> List[str]:
        """
        Get crypto symbols from CSV files in the data directory
        
        Returns:
            List[str]: List of crypto symbols
        """
        symbols = []
        
        # Check data directory for crypto symbol files
        for file_path in self.data_dir.glob("*.csv"):
            filename = file_path.stem
            # Look for common crypto naming patterns
            if any(token in filename.upper() for token in ['BTC', 'ETH', 'USDT', 'USD']):
                # Extract symbol from filename
                symbol = filename.split('_')[0].upper()
                if not symbol.endswith('USDT') and not symbol.endswith('USD'):
                    # Add USDT suffix for standard format
                    if 'USDT' in filename.upper():
                        symbol = f"{symbol}USDT"
                    elif 'USD' in filename.upper():
                        symbol = f"{symbol}USD"
        
                symbols.append(symbol)
        
        # Also check charts directory if it exists
        charts_dir = Path("charts") / "crypto"
        if charts_dir.exists():
            for file_path in charts_dir.glob("*.csv"):
                filename = file_path.stem
                # Extract symbol from filename
                if any(token in filename.upper() for token in ['BTC', 'ETH', 'USDT', 'USD']):
                    # Clean up symbol name - remove numeric parts
                    symbol = ''.join([c for c in filename.upper() if not c.isdigit()])
                    
                    # Remove common suffixes that might be part of the filename
                    for suffix in ['MIN', 'HOUR', 'DAY', 'WEEK']:
                        symbol = symbol.replace(suffix, '')
                    
                    # Ensure proper format
                    if not symbol.endswith('USDT') and not symbol.endswith('USD'):
                        if 'USDT' in filename.upper():
                            symbol = f"{symbol}USDT"
                        elif 'USD' in filename.upper():
                            symbol = f"{symbol}USD"
                    
                    symbols.append(symbol)
        
        # If no symbols found, use default list
        if not symbols:
            symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT']
        
        # Clean up duplicates and malformed symbols
        clean_symbols = []
        for symbol in symbols:
            # Remove any remaining numeric parts
            clean_symbol = ''.join([c for c in symbol if not c.isdigit()])
            
            # Ensure we don't have double USDT/USD
            if 'USDTUSDT' in clean_symbol:
                clean_symbol = clean_symbol.replace('USDTUSDT', 'USDT')
            if 'USDUSD' in clean_symbol:
                clean_symbol = clean_symbol.replace('USDUSD', 'USD')
            
            clean_symbols.append(clean_symbol)
        
        return list(set(clean_symbols))
    
    def get_available_timeframes(self, source: str = 'all') -> List[str]:
        """
        Get list of available timeframes
        
        Args:
            source (str): Data source ('ctrader', 'crypto', 'all')
            
        Returns:
            List[str]: List of available timeframes
        """
        timeframes = []
        
        if source in ['ctrader', 'all']:
            ctrader_timeframes = list(self.ctrader.get_available_timeframes().keys())
            timeframes.extend(ctrader_timeframes)
        
        if source in ['crypto', 'all']:
            crypto_timeframes = asyncio.run(self.crypto_provider.get_crypto_timeframes())
            # Convert to cTrader format
            crypto_timeframes = [self._normalize_timeframe(tf) for tf in crypto_timeframes]
            timeframes.extend(crypto_timeframes)
        
        # Remove duplicates and sort
        timeframes = sorted(list(set(timeframes)))
        
        return timeframes
    
    def _load_from_csv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Load data from CSV file with flexible format detection
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        # Try different file naming conventions
        potential_files = [
            self.data_dir / f"{symbol}_{timeframe}.csv",
            self.data_dir / f"{symbol}{self._timeframe_to_minutes(timeframe)}.csv",
            Path("charts") / get_market_type(symbol) / f"{symbol}{self._timeframe_to_minutes(timeframe)}.csv",
            Path("charts") / get_market_type(symbol) / f"{symbol}_{timeframe}.csv"
        ]
        
        for file_path in potential_files:
            if file_path.exists():
                try:
                    # First check if it's a standard format with headers
                    with open(file_path, 'r') as f:
                        first_line = f.readline().strip()                    
                    if "Historical data" in first_line:
                        # Skip the first two lines (headers)
                        df = pd.read_csv(file_path, skiprows=2, header=None, sep=' ')
                        df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
                        
                        # Combine date and time
                        df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
                        df.drop(['date', 'time'], axis=1, inplace=True)
                    else:
                        # Try to detect separator (tab or space)
                        sep = '\t' if '\t' in first_line else ' '
                        
                        # Try different formats
                        try:
                            # First try with header
                            df = pd.read_csv(file_path, sep=sep)
                            
                            # Check if we have the expected columns
                            required_cols = ['open', 'high', 'low', 'close']
                            if not all(col.lower() in [c.lower() for c in df.columns] for col in required_cols):
                                raise ValueError("Missing required columns")
                            
                        except Exception:
                            # If that fails, try without header
                            df = pd.read_csv(file_path, header=None, sep=sep)
                            
                            # Handle different formats based on column count
                            if len(df.columns) == 6:  # Date and time combined
                                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                            elif len(df.columns) == 7:  # Date and time separate
                                df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
                                df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
                                df.drop(['date', 'time'], axis=1, inplace=True)
                            else:
                                raise ValueError(f"Unexpected number of columns: {len(df.columns)}")
                    
                    # Ensure timestamp is the index
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                    
                    # Ensure all columns are lowercase
                    df.columns = [col.lower() for col in df.columns]
                    
                    logger.info(f"Loaded {len(df)} rows from {file_path}")
                    return df
                
                except Exception as e:
                    logger.warning(f"Error with standard format for {file_path}: {str(e)}")
                    # Continue to try other formats
        
        logger.warning(f"No data file found for {symbol} {timeframe}")
        return pd.DataFrame()
    
    def _normalize_timeframe(self, timeframe: str) -> str:
        """
        Normalize timeframe format
        
        Args:
            timeframe (str): Timeframe in various formats
            
        Returns:
            str: Normalized timeframe
        """
        # Convert common formats to cTrader format
        if timeframe == '1m':
            return 'M1'
        elif timeframe == '5m':
            return 'M5'
        elif timeframe == '15m':
            return 'M15'
        elif timeframe == '30m':
            return 'M30'
        elif timeframe == '1h':
            return 'H1'
        elif timeframe == '4h':
            return 'H4'
        elif timeframe == '1d':
            return 'D1'
        elif timeframe == '1w':
            return 'W1'
        
        # If already in cTrader format, return as is
        if timeframe in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
            return timeframe
        
        # Default case
        logger.warning(f"Unknown timeframe format: {timeframe}, using H1 as default")
        return 'H1'
    
    def _convert_to_crypto_timeframe(self, timeframe: str) -> str:
        """
        Convert cTrader timeframe to crypto provider format
        
        Args:
            timeframe (str): Timeframe in cTrader format
            
        Returns:
            str: Timeframe in crypto provider format
        """
        # Convert cTrader format to crypto format
        if timeframe == 'M1':
            return '1m'
        elif timeframe == 'M5':
            return '5m'
        elif timeframe == 'M15':
            return '15m'
        elif timeframe == 'M30':
            return '30m'
        elif timeframe == 'H1':
            return '1h'
        elif timeframe == 'H4':
            return '4h'
        elif timeframe == 'D1':
            return '1d'
        elif timeframe == 'W1':
            return '1w'
        
        # If already in crypto format, return as is
        if timeframe in ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']:
            return timeframe
        
        # Default case
        logger.warning(f"Unknown timeframe format for crypto: {timeframe}, using 1h as default")
        return '1h'
    
    def _timeframe_to_minutes(self, timeframe: str) -> str:
        """
        Convert timeframe to minutes for CSV filename
        
        Args:
            timeframe (str): Timeframe
            
        Returns:
            str: Minutes as string
        """
        if timeframe == 'M1':
            return '1'
        elif timeframe == 'M5':
            return '5'
        elif timeframe == 'M15':
            return '15'
        elif timeframe == 'M30':
            return '30'
        elif timeframe == 'H1':
            return '60'
        elif timeframe == 'H4':
            return '240'
        elif timeframe == 'D1':
            return '1440'
        elif timeframe == 'W1':
            return '10080'
        
        # Default case
        return '60'  # Default to 1 hour
    
    def get_multi_timeframe_data(self, symbol: str, timeframes: List[str] = None, 
                                bars: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple timeframes
        
        Args:
            symbol (str): Trading symbol
            timeframes (list): List of timeframes
            bars (int): Number of bars to fetch
            
        Returns:
            dict: Dictionary of dataframes for each timeframe
        """
        if timeframes is None:
            timeframes = ['H1', 'H4', 'D1']
        
        result = {}
        
        for tf in timeframes:
            df = self.get_data(symbol, tf, bars)
            if df is not None and not df.empty:
                result[tf] = df
        
        return result
    
    def get_latest_price(self, symbol: str) -> float:
        """
        Get the latest price for a symbol
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            float: Latest price
        """
        # Determine market type
        market_type = get_market_type(symbol)
        
        # Try to get live price if available
        if self.use_live_data:
            if market_type == 'crypto':
                # Use crypto provider for crypto symbols
                price = asyncio.run(self.crypto_provider.get_latest_price(symbol))
                if price is not None:
                    return price
            elif self.ctrader.authenticated:
                # TODO: Implement getting latest price from cTrader
                pass
        
        # Fallback to latest price from data
        df = self.get_data(symbol, 'H1', 1)
        if df is not None and not df.empty:
            return df['close'].iloc[-1]
        
        return None
    
    def close(self):
        """Close connections and clean up resources"""
        if self.use_live_data:
            # Close cTrader connection
            self.ctrader.disconnect()
        
            # Close crypto provider connection using a new event loop
            try:
                # Check if there's a running event loop
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        logger.info("Using existing event loop for cleanup")
                        asyncio.run_coroutine_threadsafe(self.crypto_provider.close(), loop)
                    else:
                        # Create a new event loop for cleanup
                        logger.info("Creating new event loop for cleanup")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.crypto_provider.close())
                        loop.close()
                except RuntimeError:
                    # No running event loop
                    logger.info("No running event loop, creating new one for cleanup")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.crypto_provider.close())
                    loop.close()
            except Exception as e:
                logger.error(f"Error closing crypto provider: {e}")
        
            logger.info("Closed all data provider connections")
