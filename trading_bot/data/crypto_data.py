"""
Crypto data provider module
Fetches cryptocurrency data from various sources including local CSV files and APIs
"""

import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import asyncio
import ccxt.async_support as ccxt

from trading_bot.config import settings, credentials

logger = logging.getLogger(__name__)

class CryptoDataProvider:
    """
    Provides cryptocurrency market data from various sources
    Supports both online (API) and offline (CSV) data
    """
    
    def __init__(self, exchange_id=None):
        """
        Initialize the crypto data provider
        
        Args:
            exchange_id (str): CCXT exchange ID (default: from settings)
        """
        self.base_dir = settings.BASE_DIR
        self.charts_dir = Path(self.base_dir).parent / "charts" / "crypto"
        
        # Initialize CCXT exchange
        self.exchange_id = exchange_id or getattr(settings, 'CCXT_EXCHANGE', 'binance')
        self.exchange = None
        self.exchange_connected = False
        
        # Try to connect to exchange
        self._init_exchange()
    
    def _init_exchange(self):
        """Initialize the CCXT exchange"""
        try:
            # Create exchange instance
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': getattr(credentials, f'{self.exchange_id.upper()}_API_KEY', ''),
                'secret': getattr(credentials, f'{self.exchange_id.upper()}_API_SECRET', ''),
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Mark as connected (actual connection test will happen on first request)
            self.exchange_connected = True
            logger.info(f"Initialized {self.exchange_id} exchange connection")
        except Exception as e:
            logger.error(f"Error initializing {self.exchange_id} exchange: {e}")
            self.exchange_connected = False
    
    async def get_ohlcv(self, symbol, timeframe, count=100, source='auto'):
        """
        Get OHLCV data for a cryptocurrency pair
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            source (str): Data source ('ccxt', 'csv', 'api', 'auto')
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        # Normalize symbol format
        symbol = self._normalize_symbol(symbol)
        
        # Map timeframe string to CSV filename suffix
        timeframe_map = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '4h': '240',
            '1d': '1440',
            '1w': '10080'
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None
        
        csv_suffix = timeframe_map[timeframe]
        
        # Try different data sources based on preference and availability
        if source == 'auto':
            # Create a list of data sources to try in order
            data_sources = []
            
            # If exchange is initialized, include it
            if self.exchange_connected:
                data_sources.append('ccxt')
            
            # Always try CSV and API as fallbacks
            data_sources.extend(['csv', 'api'])
            
            # Try each data source until we get data
            for src in data_sources:
                logger.info(f"Trying to get {symbol} {timeframe} data from {src}")
                
                if src == 'ccxt':
                    df = await self._get_ccxt_data(symbol, timeframe, count)
                    if df is not None and not df.empty:
                        logger.info(f"Successfully got {symbol} {timeframe} data from CCXT")
                        return df
                    logger.warning(f"Failed to get {symbol} {timeframe} data from CCXT")
                
                elif src == 'csv':
                    df = self._get_csv_data(symbol, csv_suffix, count)
                    if df is not None and not df.empty:
                        logger.info(f"Successfully got {symbol} {timeframe} data from CSV")
                        return df
                    logger.warning(f"Failed to get {symbol} {timeframe} data from CSV")
                
                elif src == 'api':
                    df = await self._get_api_data(symbol, timeframe, count)
                    if df is not None and not df.empty:
                        logger.info(f"Successfully got {symbol} {timeframe} data from API")
                        return df
                    logger.warning(f"Failed to get {symbol} {timeframe} data from API")
            
            # If we get here, all data sources failed
            logger.error(f"All data sources failed for {symbol} {timeframe}")
            return None
        
        elif source == 'csv':
            return self._get_csv_data(symbol, csv_suffix, count)
        
        elif source == 'ccxt':
            if not self.exchange_connected:
                logger.error(f"{self.exchange_id} exchange is not connected")
                return None
            return await self._get_ccxt_data(symbol, timeframe, count)
        
        elif source == 'api':
            return await self._get_api_data(symbol, timeframe, count)
        
        else:
            logger.error(f"Invalid data source: {source}")
            return None
    
    def _normalize_symbol(self, symbol):
        """
        Normalize symbol format for consistency
        
        Args:
            symbol (str): Symbol in various formats (e.g., 'BTC/USDT', 'BTCUSDT')
            
        Returns:
            str: Normalized symbol
        """
        # Remove '/' if present
        symbol = symbol.replace('/', '')
        
        # Convert to uppercase
        return symbol.upper()
    
    def _get_csv_data(self, symbol, timeframe_suffix, count=100):
        """
        Get OHLCV data from local CSV files
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            timeframe_suffix (str): Timeframe suffix for CSV filename
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Construct CSV filename
            csv_path = self.charts_dir / f"{symbol}{timeframe_suffix}.csv"
            
            if not csv_path.exists():
                # Try alternative locations
                alternative_paths = [
                    Path(self.base_dir).parent / "charts" / "crypto" / f"{symbol}{timeframe_suffix}.csv",
                    Path(self.base_dir).parent / "data" / "crypto" / f"{symbol}{timeframe_suffix}.csv",
                    Path(self.base_dir) / "data" / "crypto" / f"{symbol}{timeframe_suffix}.csv"
                ]
                
                for alt_path in alternative_paths:
                    if alt_path.exists():
                        csv_path = alt_path
                        logger.info(f"Found CSV file at alternative location: {csv_path}")
                        break
                else:
                    logger.warning(f"CSV file not found: {csv_path}")
                    return None
            
            # Read CSV file
            df = pd.read_csv(csv_path, sep='\t', header=None)
            
            # Rename columns
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # Convert datetime
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            # Return the last 'count' rows
            return df.tail(count)
            
        except Exception as e:
            logger.error(f"Error reading CSV data for {symbol}: {e}")
            return None
    
    async def _get_ccxt_data(self, symbol, timeframe, count=100):
        """
        Get OHLCV data from cryptocurrency exchange via CCXT
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Format symbol for CCXT
            ccxt_symbol = self._format_for_ccxt(symbol)
            
            # Load markets if not already loaded
            if not self.exchange.markets:
                await self.exchange.load_markets()
            
            # Check if symbol is available
            if ccxt_symbol not in self.exchange.markets:
                logger.warning(f"Symbol {ccxt_symbol} not available on {self.exchange_id}")
                
                # Try alternative symbol formats
                alternatives = [
                    symbol.replace('USDT', '/USDT'),
                    symbol.replace('USD', '/USD'),
                    f"{symbol[:3]}/{symbol[3:]}"
                ]
                
                for alt in alternatives:
                    if alt in self.exchange.markets:
                        ccxt_symbol = alt
                        logger.info(f"Using alternative symbol format: {ccxt_symbol}")
                        break
                else:
                    logger.error(f"No valid symbol format found for {symbol}")
                    return None
            
            # Fetch OHLCV data
            ohlcv = await self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=count)
            
            if not ohlcv or len(ohlcv) == 0:
                logger.warning(f"No CCXT data for {ccxt_symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.drop('timestamp', axis=1, inplace=True)
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching CCXT data for {symbol}: {e}")
            return None
    
    def _format_for_ccxt(self, symbol):
        """
        Format symbol for CCXT
        
        Args:
            symbol (str): Symbol to format (e.g., 'BTCUSDT')
            
        Returns:
            str: Formatted symbol (e.g., 'BTC/USDT')
        """
        # If already in CCXT format, return as is
        if '/' in symbol:
            return symbol
        
        # Handle common quote currencies
        if symbol.endswith('USDT'):
            return f"{symbol[:-4]}/USDT"
        elif symbol.endswith('USD'):
            return f"{symbol[:-3]}/USD"
        elif symbol.endswith('BTC'):
            return f"{symbol[:-3]}/BTC"
        elif symbol.endswith('ETH'):
            return f"{symbol[:-3]}/ETH"
        
        # Default case: assume 3-letter base and quote
        return f"{symbol[:3]}/{symbol[3:]}"
    
    async def _get_api_data(self, symbol, timeframe, count=100):
        """
        Get OHLCV data from external API (Alpha Vantage)
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Use Alpha Vantage API for crypto data
            api_key = getattr(credentials, 'ALPHA_VANTAGE_API_KEY', None)
            
            if not api_key:
                logger.error("Alpha Vantage API key not found")
                return None
            
            # Map timeframe to Alpha Vantage interval
            interval_map = {
                '1m': '1min',
                '5m': '5min',
                '15m': '15min',
                '30m': '30min',
                '1h': '60min',
                '4h': 'NONE',  # Not directly supported
                '1d': 'daily',
                '1w': 'weekly'
            }
            
            if timeframe not in interval_map or interval_map[timeframe] == 'NONE':
                logger.warning(f"Timeframe {timeframe} not supported by Alpha Vantage API")
                return None
            
            # Extract base currency and quote currency
            if symbol.endswith('USDT'):
                base_currency = symbol[:-4]
                quote_currency = 'USD'  # Alpha Vantage uses USD instead of USDT
            elif symbol.endswith('USD'):
                base_currency = symbol[:-3]
                quote_currency = 'USD'
            else:
                # Default assumption for other formats
                base_currency = symbol[:3]
                quote_currency = symbol[3:]
            
            # Construct API URL
            base_url = "https://www.alphavantage.co/query"
            
            if timeframe in ['1d', '1w']:
                function = 'DIGITAL_CURRENCY_' + interval_map[timeframe].upper()
                url = f"{base_url}?function={function}&symbol={base_currency}&market={quote_currency}&apikey={api_key}"
            else:
                function = 'CRYPTO_INTRADAY'
                url = f"{base_url}?function={function}&symbol={base_currency}&market={quote_currency}&interval={interval_map[timeframe]}&apikey={api_key}"
            
            # Fetch data from API
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Check for error messages
                    if 'Error Message' in data:
                        logger.error(f"API error: {data['Error Message']}")
                        return None
                    
                    # Extract time series data
                    if timeframe in ['1d', '1w']:
                        time_series_key = f"Time Series (Digital Currency {interval_map[timeframe].capitalize()})"
                    else:
                        time_series_key = f"Time Series Crypto ({interval_map[timeframe]})"
                    
                    if time_series_key not in data:
                        logger.error(f"Time series data not found in API response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Handle different column naming conventions
                    if timeframe in ['1d', '1w']:
                        # Daily/weekly data has different column names
                        price_columns = {
                            f'1a. open ({quote_currency})': 'open',
                            f'2a. high ({quote_currency})': 'high',
                            f'3a. low ({quote_currency})': 'low',
                            f'4a. close ({quote_currency})': 'close',
                            f'5. volume': 'volume'
                        }
                    else:
                        # Intraday data
                        price_columns = {
                            '1. open': 'open',
                            '2. high': 'high',
                            '3. low': 'low',
                            '4. close': 'close',
                            '5. volume': 'volume'
                        }
                    
                    # Rename columns
                    df = df.rename(columns=price_columns)
                    
                    # Keep only the columns we need
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    # Convert to numeric
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col])
                    
                    # Convert index to datetime
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'datetime'
                    
                    # Sort by datetime
                    df.sort_index(inplace=True)
                    
                    # Return the last 'count' rows
                    return df.tail(count)
            
        except Exception as e:
            logger.error(f"Error fetching API data for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol, period='1y', timeframe='1d', source='auto'):
        """
        Get historical OHLCV data for backtesting
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            period (str): Time period ('1m', '3m', '6m', '1y', '2y', '5y')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            source (str): Data source ('ccxt', 'csv', 'api', 'auto')
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        # Map period to number of candles based on timeframe
        period_map = {
            '1m': {'1h': 24 * 30, '4h': 6 * 30, '1d': 30},
            '3m': {'1h': 24 * 90, '4h': 6 * 90, '1d': 90},
            '6m': {'1h': 24 * 180, '4h': 6 * 180, '1d': 180},
            '1y': {'1h': 24 * 365, '4h': 6 * 365, '1d': 365},
            '2y': {'1h': 24 * 730, '4h': 6 * 730, '1d': 730},
            '5y': {'1h': 24 * 1825, '4h': 6 * 1825, '1d': 1825}
        }
        
        if period not in period_map:
            logger.error(f"Invalid period: {period}")
            return None
        
        if timeframe not in period_map[period]:
            logger.error(f"Invalid timeframe for period: {timeframe}")
            return None
        
        count = period_map[period][timeframe]
        
        # Get OHLCV data
        return await self.get_ohlcv(symbol, timeframe, count, source)
    
    async def get_latest_price(self, symbol, source='auto'):
        """
        Get the latest price for a cryptocurrency pair
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            source (str): Data source ('ccxt', 'csv', 'api', 'auto')
            
        Returns:
            float: Latest price (close)
        """
        # Get the latest candle
        df = await self.get_ohlcv(symbol, '1m', 1, source)
        
        if df is None or df.empty:
            logger.error(f"Failed to get latest price for {symbol}")
            return None
        
        # Return the close price
        return df['close'].iloc[-1]
    
    async def get_multi_timeframe_data(self, symbol, timeframes=None, count=100, source='auto'):
        """
        Get OHLCV data for multiple timeframes
        
        Args:
            symbol (str): Crypto pair symbol (e.g., 'BTCUSDT')
            timeframes (list): List of timeframes (e.g., ['1h', '4h', '1d'])
            count (int): Number of candles to fetch
            source (str): Data source ('ccxt', 'csv', 'api', 'auto')
            
        Returns:
            dict: Dictionary of dataframes for each timeframe
        """
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']
        
        result = {}
        
        # Fetch data for each timeframe
        for tf in timeframes:
            df = await self.get_ohlcv(symbol, tf, count, source)
            if df is not None:
                result[tf] = df
            else:
                logger.warning(f"Failed to get data for {symbol} on {tf} timeframe")
        
        return result
    
    async def get_crypto_pairs(self, source='auto'):
        """
        Get a list of available cryptocurrency pairs
        
        Args:
            source (str): Data source ('ccxt', 'csv', 'auto')
            
        Returns:
            list: List of available cryptocurrency pairs
        """
        pairs = []
        
        if source in ['auto', 'ccxt'] and self.exchange_connected:
            # Try to get pairs from CCXT
            try:
                if not self.exchange.markets:
                    await self.exchange.load_markets()
                
                # Filter for USDT pairs
                usdt_pairs = [
                    symbol.replace('/', '') 
                    for symbol in self.exchange.markets.keys() 
                    if '/USDT' in symbol
                ]
                
                # Sort by volume if available
                if hasattr(self.exchange, 'fetch_tickers'):
                    tickers = await self.exchange.fetch_tickers(usdt_pairs)
                    # Sort by volume
                    sorted_pairs = sorted(
                        [(symbol, ticker['quoteVolume'] if 'quoteVolume' in ticker else 0) 
                         for symbol, ticker in tickers.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )
                    pairs = [pair[0].replace('/', '') for pair in sorted_pairs]
                else:
                    pairs = usdt_pairs
                
                # Limit to top 50 pairs
                pairs = pairs[:50]
                
            except Exception as e:
                logger.error(f"Error getting crypto pairs from CCXT: {e}")
        
        if not pairs and source in ['auto', 'csv']:
            # Try to get pairs from CSV files
            try:
                # Get all CSV files in the crypto directory
                csv_files = list(self.charts_dir.glob('*.csv'))
                
                # Extract pair names from filenames
                for file in csv_files:
                    # Extract the pair name (remove the timeframe suffix)
                    pair = file.stem
                    # Remove digits from the end (timeframe)
                    pair = ''.join([c for c in pair if not c.isdigit()])
                    if pair not in pairs:
                        pairs.append(pair)
            except Exception as e:
                logger.error(f"Error getting crypto pairs from CSV files: {e}")
        
        # If still no pairs, return default list
        if not pairs:
            pairs = [p.replace('/', '') for p in settings.CRYPTO_PAIRS]
        
        return pairs
    
    async def get_crypto_timeframes(self, source='auto'):
        """
        Get a list of available timeframes
        
        Args:
            source (str): Data source ('ccxt', 'csv', 'api', 'auto')
            
        Returns:
            list: List of available timeframes
        """
        # Return standard timeframes
        return ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    
    async def close(self):
        """Close connections and clean up resources"""
        if self.exchange:
            await self.exchange.close()
            logger.info(f"Closed connection to {self.exchange_id} exchange")

