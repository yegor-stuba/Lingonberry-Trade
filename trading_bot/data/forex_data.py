"""
Forex data provider module
Fetches forex data from various sources including local CSV files and MT4
"""

import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import asyncio
import json

from trading_bot.config import settings, credentials

logger = logging.getLogger(__name__)

class ForexDataProvider:
    """
    Provides forex market data from various sources
    Supports both online (API) and offline (CSV) data
    """
    
    def __init__(self):
        """Initialize the forex data provider"""
        self.base_dir = settings.BASE_DIR
        self.charts_dir = Path(self.base_dir).parent / "charts" / "forex"
        
        # Initialize MT4 ZeroMQ bridge client
        self.mt4_bridge = None
        self.mt4_bridge_connected = False
        
        # Try to connect to MT4 bridge
        self._init_mt4_bridge()
    
    def _init_mt4_bridge(self):
        """Initialize the MT4 ZeroMQ bridge"""
        try:
            from trading_bot.bridges.mt4.client import MT4ZeroMQClient
            
            self.mt4_bridge = MT4ZeroMQClient()
            self.mt4_bridge_connected = self.mt4_bridge.connect()
            
            if self.mt4_bridge_connected:
                logger.info("Connected to MT4 ZeroMQ bridge")
            else:
                logger.warning("Failed to connect to MT4 ZeroMQ bridge. Will use alternative data sources.")
        except Exception as e:
            logger.error(f"Error connecting to MT4 ZeroMQ bridge: {e}")
            self.mt4_bridge_connected = False
    
    async def get_ohlcv(self, symbol, timeframe, count=100, source='auto'):
        """
        Get OHLCV data for a forex pair
        
        Args:
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            source (str): Data source ('mt4', 'csv', 'api', 'auto')
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        # Map timeframe string to MT4 timeframe and CSV filename suffix
        timeframe_map = {
            '1m': ('M1', '1'),
            '5m': ('M5', '5'),
            '15m': ('M15', '15'),
            '30m': ('M30', '30'),
            '1h': ('H1', '60'),
            '4h': ('H4', '240'),
            '1d': ('D1', '1440'),
            '1w': ('W1', '10080')
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None
        
        mt4_timeframe, csv_suffix = timeframe_map[timeframe]
        
        # Try different data sources based on preference and availability
        if source == 'auto':
            # Create a list of data sources to try in order
            data_sources = []
            
            # If MT4 bridge is connected, try it first
            if self.mt4_bridge_connected:
                data_sources.append('mt4')
            
            # Always try CSV and API as fallbacks
            data_sources.extend(['csv', 'api'])
            
            # Try each data source until we get data
            for src in data_sources:
                logger.info(f"Trying to get {symbol} {timeframe} data from {src}")
                
                if src == 'mt4':
                    df = await self._get_mt4_data(symbol, mt4_timeframe, count)
                    if df is not None and not df.empty:
                        logger.info(f"Successfully got {symbol} {timeframe} data from MT4")
                        return df
                    logger.warning(f"Failed to get {symbol} {timeframe} data from MT4")
                
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
        
        elif source == 'mt4':
            if not self.mt4_bridge_connected:
                logger.error("MT4 bridge is not connected")
                return None
                
            return await self._get_mt4_data(symbol, mt4_timeframe, count)
        
        elif source == 'api':
            return await self._get_api_data(symbol, timeframe, count)
        
        else:
            logger.error(f"Invalid data source: {source}")
            return None
    
    async def _get_mt4_data(self, symbol, mt4_timeframe, count=100):
        """
        Get OHLCV data from MT4 via the ZeroMQ bridge
        
        Args:
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            mt4_timeframe (str): MT4 timeframe (e.g., 'H1')
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            if not self.mt4_bridge_connected:
                return None
                
            # Request data from MT4
            data = await self.mt4_bridge.get_historical_data(symbol, mt4_timeframe, count)
            
            if data is None:
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns if needed
            if 'time' in df.columns:
                df.rename(columns={'time': 'datetime'}, inplace=True)
            
            # Convert datetime
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting MT4 data: {e}")
            return None
    
    def _get_csv_data(self, symbol, timeframe_suffix, count=100):
        """
        Get OHLCV data from local CSV files
        
        Args:
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            timeframe_suffix (str): Timeframe suffix for CSV filename
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Construct CSV filename
            csv_path = self.charts_dir / f"{symbol}{timeframe_suffix}.csv"
            
            if not csv_path.exists():
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
    
    async def _get_api_data(self, symbol, timeframe, count=100):
        """
        Get OHLCV data from external API (Alpha Vantage)
        
        Args:
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Use Alpha Vantage API for forex data
            api_key = credentials.ALPHA_VANTAGE_API_KEY
            
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
            
            # Split symbol into from_currency and to_currency
            if len(symbol) != 6:
                logger.error(f"Invalid forex symbol: {symbol}")
                return None
            
            from_currency = symbol[:3]
            to_currency = symbol[3:]
            
            # Construct API URL
            base_url = "https://www.alphavantage.co/query"
            
            if timeframe in ['1d', '1w']:
                function = 'FX_' + interval_map[timeframe].upper()
                url = f"{base_url}?function={function}&from_symbol={from_currency}&to_symbol={to_currency}&apikey={api_key}"
            else:
                function = 'FX_INTRADAY'
                url = f"{base_url}?function={function}&from_symbol={from_currency}&to_symbol={to_currency}&interval={interval_map[timeframe]}&apikey={api_key}"
            
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
                        time_series_key = f"Time Series FX ({interval_map[timeframe].capitalize()})"
                    else:
                        time_series_key = f"Time Series FX ({interval_map[timeframe]})"
                    
                    if time_series_key not in data:
                        logger.error(f"Time series data not found in API response")
                        return None
                    
                    time_series = data[time_series_key]
                    
                    # Convert to DataFrame
                    df = pd.DataFrame.from_dict(time_series, orient='index')
                    
                    # Rename columns
                    df.columns = [col.split('. ')[1] for col in df.columns]
                    df.rename(columns={
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume'
                    }, inplace=True)
                    
                    # Convert to numeric
                    for col in ['open', 'high', 'low', 'close', 'volume']:
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
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            period (str): Time period ('1m', '3m', '6m', '1y', '2y', '5y')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            source (str): Data source ('mt4', 'csv', 'api', 'auto')
            
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
        Get the latest price for a forex pair
        
        Args:
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            source (str): Data source ('mt4', 'csv', 'api', 'auto')
            
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
            symbol (str): Forex pair symbol (e.g., 'EURUSD')
            timeframes (list): List of timeframes (e.g., ['1h', '4h', '1d'])
            count (int): Number of candles to fetch
            source (str): Data source ('mt4', 'csv', 'api', 'auto')
            
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
    
    async def get_forex_pairs(self, source='auto'):
        """
        Get a list of available forex pairs
        
        Args:
            source (str): Data source ('mt4', 'csv', 'auto')
            
        Returns:
            list: List of available forex pairs
        """
        pairs = []
        
        if source in ['auto', 'mt4'] and self.mt4_bridge_connected:
            # Try to get pairs from MT4 bridge
            try:
                pairs = await self.mt4_bridge.get_symbols()
                if pairs:
                    logger.info(f"Got {len(pairs)} forex pairs from MT4")
                    return pairs
            except Exception as e:
                logger.error(f"Error getting forex pairs from MT4 bridge: {e}")
        
        if not pairs and source in ['auto', 'csv']:
            # Try to get pairs from CSV files
            try:
                # Get all CSV files in the forex directory
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
                logger.error(f"Error getting forex pairs from CSV files: {e}")
        
        # If still no pairs, return default list
        if not pairs:
            pairs = settings.FOREX_PAIRS
        
        return pairs
    
    async def get_forex_timeframes(self, source='auto'):
        """
        Get a list of available timeframes
        
        Args:
            source (str): Data source ('mt4', 'csv', 'api', 'auto')
            
        Returns:
            list: List of available timeframes
        """
        # Return standard timeframes
        return ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    
    async def close(self):
        """Close connections and clean up resources"""
        if self.mt4_bridge:
            await self.mt4_bridge.close()
            logger.info("Closed MT4 bridge connection")
