"""
Web data provider for fetching market data from websites
"""

import asyncio
import logging
import random
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from trading_bot.config import settings

logger = logging.getLogger(__name__)

class WebDataProvider:
    """Web data provider for fetching market data from websites"""
    
    def __init__(self):
        """Initialize the web data provider"""
        self.initialized = False
        self.playwright = None
        self.browser = None
        self.context = None
        
        # Cache settings
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_duration = getattr(settings, 'WEB_SCRAPER_CACHE_DURATION', 300)  # 5 minutes default
        
        # Create cache directory
        self.cache_dir = Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        
        # Site configurations
        self.site_configs = {
            'tradingview': {
                'url_template': {
                    'forex': 'https://www.tradingview.com/symbols/{symbol}/',
                    'crypto': 'https://www.tradingview.com/symbols/{symbol}/',
                    'indices': 'https://www.tradingview.com/symbols/{symbol}/',
                    'metals': 'https://www.tradingview.com/symbols/OANDA-{symbol}/'
                },
                'price_selector': '.tv-symbol-price-quote__value',
                'chart_selector': '#tv-chart-container'
            },
            'investing': {
                'url_template': {
                    'forex': 'https://www.investing.com/currencies/{symbol}',
                    'crypto': 'https://www.investing.com/crypto/{symbol}',
                    'indices': 'https://www.investing.com/indices/{symbol}',
                    'metals': 'https://www.investing.com/commodities/{symbol}'
                },
                'price_selector': '.text-2xl',
                'chart_selector': '#chart_container'
            },
            'yahoo': {
                'url_template': {
                    'forex': 'https://finance.yahoo.com/quote/{symbol}=X',
                    'crypto': 'https://finance.yahoo.com/quote/{symbol}-USD',
                    'indices': 'https://finance.yahoo.com/quote/%5E{symbol}',
                    'metals': 'https://finance.yahoo.com/quote/{symbol}=F'
                },
                'price_selector': 'fin-streamer[data-field="regularMarketPrice"]',
                'chart_selector': '#chart-container'
            }
        }
        
        # Site order (priority)
        self.site_order = ['tradingview', 'investing', 'yahoo']
        
        # Site failure tracking
        self.site_failures = {site: 0 for site in self.site_configs}
        self.max_failures = 3
        
        # Rate limiting
        self.last_request_time = {site: 0 for site in self.site_configs}
        self.request_interval = getattr(settings, 'WEB_SCRAPER_REQUEST_INTERVAL', 2)  # 2 seconds default
        
        # Proxy support
        self.proxies = self._load_proxies()
        self.current_proxy_index = 0
        self.proxy_health = {}  # Track proxy health
        self.proxy_rotation_interval = getattr(settings, 'PROXY_ROTATION_INTERVAL', 10)  # Rotate every 10 requests
        self.request_count = 0
        
        # Symbol normalization mappings
        self.symbol_mappings = {
            'forex': {
                'EURUSD': 'EUR-USD',
                'GBPUSD': 'GBP-USD',
                'USDJPY': 'USD-JPY',
                'AUDUSD': 'AUD-USD',
                'USDCAD': 'USD-CAD',
                'USDCHF': 'USD-CHF',
                'NZDUSD': 'NZD-USD'
            },
            'crypto': {
                'BTCUSDT': 'BTCUSD',
                'ETHUSDT': 'ETHUSD',
                'BNBUSDT': 'BNBUSD',
                'ADAUSDT': 'ADAUSD',
                'XRPUSDT': 'XRPUSD'
            },
            'indices': {
                'US30': 'DJI',
                'US500': 'SPX',
                'USTEC': 'NDX',
                'UK100': 'UKX',
                'GER40': 'DAX'
            },
            'metals': {
                'XAUUSD': 'GOLD',
                'XAGUSD': 'SILVER'
            }
        }
    
    def _load_proxies(self):
        """
        Load proxies from settings or from a proxy file
        
        Returns:
            list: List of proxy URLs
        """
        # First check if proxies are defined in settings
        proxies = getattr(settings, 'PROXIES', [])
        
        # If no proxies in settings, try to load from file
        if not proxies:
            proxy_file = Path('proxies.txt')
            if proxy_file.exists():
                try:
                    with open(proxy_file, 'r') as f:
                        proxies = [line.strip() for line in f if line.strip()]
                    logger.info(f"Loaded {len(proxies)} proxies from proxies.txt")
                except Exception as e:
                    logger.error(f"Error loading proxies from file: {e}")
        
        # If still no proxies, try to load from free proxy API
        if not proxies:
            try:
                proxies = self._fetch_free_proxies()
                logger.info(f"Fetched {len(proxies)} free proxies")
            except Exception as e:
                logger.error(f"Error fetching free proxies: {e}")
        
        return proxies
    
    def _fetch_free_proxies(self):
        """
        Fetch free proxies from public APIs
        
        Returns:
            list: List of proxy URLs
        """
        import requests
        
        proxies = []
        
        # Try to fetch from free-proxy-list.net
        try:
            response = requests.get('https://www.free-proxy-list.net/', timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                
                if table:
                    for row in table.find_all('tr')[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 7:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            https = cols[6].text.strip()
                            
                            if https == 'yes':
                                proxies.append(f"https://{ip}:{port}")
                            else:
                                proxies.append(f"http://{ip}:{port}")
        except Exception as e:
            logger.error(f"Error fetching proxies from free-proxy-list.net: {e}")
        
        # Try to fetch from sslproxies.org
        try:
            response = requests.get('https://www.sslproxies.org/', timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                
                if table:
                    for row in table.find_all('tr')[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 7:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            proxies.append(f"https://{ip}:{port}")
        except Exception as e:
            logger.error(f"Error fetching proxies from sslproxies.org: {e}")
        
        return proxies
    
    async def initialize(self):
        """Initialize the web data provider"""
        if self.initialized:
            return True
        
        try:
            # Initialize playwright
            self.playwright = await async_playwright().start()
            
            # Set up browser options
            browser_type = getattr(settings, 'WEB_SCRAPER_BROWSER', 'chromium')
            browser_options = {
                'headless': True,
                'timeout': 30000
            }
            
            # Add proxy if available
            if self.proxies and len(self.proxies) > 0:
                current_proxy = self.proxies[self.current_proxy_index]
                logger.info(f"Using proxy: {current_proxy}")
                
                # Parse proxy URL to get protocol, host, port, username, password
                proxy_config = self._parse_proxy_url(current_proxy)
                
                browser_options['proxy'] = proxy_config
            
            # Launch browser based on type
            if browser_type.lower() == 'edge':
                # Use Chromium with Edge user agent
                self.browser = await self.playwright.chromium.launch(**browser_options)
                edge_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
                
                # Create context with Edge user agent
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent=edge_ua
                )
            elif browser_type.lower() == 'firefox':
                self.browser = await self.playwright.firefox.launch(**browser_options)
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800}
                )
            else:
                # Default to Chromium
                self.browser = await self.playwright.chromium.launch(**browser_options)
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800}
                )
            
            # Initialize proxies if available
            if self.proxies:
                await self._initialize_proxies()
            
            self.initialized = True
            logger.info(f"Web data provider initialized with {browser_type} browser")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing web data provider: {e}")
            await self.close()
            return False

    
    def _parse_proxy_url(self, proxy_url):
        """
        Parse proxy URL into components for Playwright
        
        Args:
            proxy_url (str): Proxy URL (e.g., http://user:pass@host:port)
            
        Returns:
            dict: Proxy configuration for Playwright
        """
        # Default proxy config
        proxy_config = {
            'server': proxy_url
        }
        
        # Try to parse URL for auth info
        try:
            if '@' in proxy_url:
                # Extract auth info
                auth_part = proxy_url.split('@')[0].split('://')[1]
                if ':' in auth_part:
                    username, password = auth_part.split(':')
                    proxy_config['username'] = username
                    proxy_config['password'] = password
        except Exception as e:
            logger.warning(f"Error parsing proxy URL: {e}")
        
        return proxy_config
    
    async def close(self):
        """Close the web data provider"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            self.initialized = False
            logger.info("Web data provider closed")
            
        except Exception as e:
            logger.error(f"Error closing web data provider: {e}")
    
    async def get_latest_price(self, symbol, market_type='forex'):
        """
        Get the latest price for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            float: Latest price or None if error
        """
        # Check if we need to rotate proxy
        await self._check_proxy_rotation()
        
        # Check cache first
        cache_key = f"{symbol}_{market_type}_price"
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.cache_duration:
                return self.cache[cache_key]
        
        # Try to load from cache file with a short max age (1 minute)
        cached_price = self._load_from_cache_file(symbol, market_type, max_age=60)
        if cached_price is not None:
            # Update in-memory cache
            self.cache[cache_key] = cached_price
            self.cache_timestamps[cache_key] = time.time()
            return cached_price
        
        # Function to extract price from a site
        async def extract_price(site_name, site_config, url):
            try:
                # Respect rate limits
                await self._respect_rate_limit(site_name)
                
                # Create a new page
                page = await self.context.new_page()
                
                try:
                    # Set a shorter timeout for price fetching
                    page.set_default_timeout(15000)
                    
                    # Add stealth mode to avoid detection
                    await self._apply_stealth_mode(page)
                    
                    # Navigate to the page
                    await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    
                    # Wait for the price selector
                    price_selector = site_config['price_selector']
                    await page.wait_for_selector(price_selector, timeout=10000)
                    
                    # Extract price
                    price_element = await page.query_selector(price_selector)
                    price_text = await price_element.text_content()
                    
                    # Clean up price text
                    price_text = price_text.strip().replace(',', '')
                    price = float(re.search(r'[\d.]+', price_text).group())
                    
                    # Close the page
                    await page.close()
                    
                    # Reset failure count on success
                    self.site_failures[site_name] = 0
                    
                    # Update cache
                    self.cache[cache_key] = price
                    self.cache_timestamps[cache_key] = time.time()
                    
                    # Save to cache file
                    self._save_to_cache_file(symbol, market_type, price)
                    
                    return price
                    
                except Exception as e:
                    # Close the page in case of error
                    await page.close()
                    
                    # Increment failure count
                    self.site_failures[site_name] += 1
                    logger.error(f"Error extracting price from {site_name} for {symbol}: {e}")
                    
                    # If using a proxy, mark it as potentially bad
                    if self.proxies:
                        self._mark_proxy_health(self.current_proxy_index, False)
                    
                    return None
                    
            except Exception as e:
                logger.error(f"Error accessing {site_name} for {symbol} price: {e}")
                self.site_failures[site_name] += 1
                return None
        
        # Normalize symbol for different sites
        normalized_symbol = self._normalize_symbol(symbol, market_type)
        
        # Try each site in order until we get a price
        for site_name in self.site_order:
            # Skip sites with too many failures
            if self.site_failures[site_name] >= self.max_failures:
                logger.warning(f"Skipping {site_name} due to too many failures")
                continue
            
            site_config = self.site_configs[site_name]
            url_template = site_config['url_template'][market_type]
            url = url_template.replace('{symbol}', normalized_symbol)
            
            price = await extract_price(site_name, site_config, url)
            if price is not None:
                return price
        
        # If all sites fail, return None
        logger.error(f"Failed to get price for {symbol} from any site")
        return None
    
    async def get_ohlcv(self, symbol, timeframe, count=100, market_type='forex'):
        """
        Get OHLCV data for a symbol
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            pd.DataFrame: OHLCV data or None if error
        """
        # Check if we need to rotate proxy
        await self._check_proxy_rotation()
        
        # Check cache first
        cache_key = f"{symbol}_{market_type}_{timeframe}_{count}"
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.cache_duration:
                return self.cache[cache_key]
        
        # Try to load from cache file
        cached_df = self._load_from_cache_file(symbol, market_type, timeframe=timeframe)
        if cached_df is not None and len(cached_df) >= count:
            # Update in-memory cache
            self.cache[cache_key] = cached_df.tail(count)
            self.cache_timestamps[cache_key] = time.time()
            return cached_df.tail(count)
        
        # Try to extract chart data from websites
        df = await self._extract_chart_data(symbol, timeframe, count, market_type)
        
        # If web extraction fails, try to load from CSV files
        if df is None or df.empty:
            df = self._load_from_csv(symbol, timeframe, count, market_type)
        
        # If still no data, generate synthetic data for testing
        if df is None or df.empty:
            logger.warning(f"Generating synthetic data for {symbol} {timeframe}")
            df = self._generate_synthetic_data(symbol, timeframe, count)
        
        # Update cache if we have data
        if df is not None and not df.empty:
            self.cache[cache_key] = df
            self.cache_timestamps[cache_key] = time.time()
            
            # Save to cache file
            self._save_to_cache_file(symbol, market_type, df, timeframe=timeframe)
        
        return df
    
    async def _extract_chart_data(self, symbol, timeframe, count, market_type):
        """
        Extract chart data from websites
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            pd.DataFrame: OHLCV data or None if error
        """
        # Normalize symbol for different sites
        normalized_symbol = self._normalize_symbol(symbol, market_type)
        
        # Try TradingView first (best source for chart data)
        try:
            # Respect rate limits
            await self._respect_rate_limit('tradingview')
            
            # Create a new page
            page = await self.context.new_page()
            
            try:
                # Set a longer timeout for chart data
                page.set_default_timeout(30000)
                
                # Add stealth mode to avoid detection
                await self._apply_stealth_mode(page)
                
                # Construct URL for TradingView
                url_template = self.site_configs['tradingview']['url_template'][market_type]
                url = url_template.replace('{symbol}', normalized_symbol)
                
                # Navigate to the page
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for the chart to load
                chart_selector = self.site_configs['tradingview']['chart_selector']
                await page.wait_for_selector(chart_selector, timeout=20000)
                
                # Wait a bit for the chart to fully render
                await asyncio.sleep(3)
                
                # Execute JavaScript to extract chart data
                # This is a simplified example - actual implementation would be more complex
                # and specific to TradingView's chart structure
                script = """
                () => {
                    // This is a placeholder - actual implementation would need to access
                    // TradingView's internal chart data which is complex
                    // For now, we'll return an empty array
                    return [];
                }
                """
                
                # For now, we'll return None as this requires a more complex implementation
                # specific to each website's chart structure
                await page.close()
                return None
                
            except Exception as e:
                # Close the page in case of error
                await page.close()
                logger.error(f"Error extracting chart data from TradingView for {symbol}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing TradingView for chart data: {e}")
            return None
    
    def _load_from_csv(self, symbol, timeframe, count, market_type):
        """
        Load OHLCV data from CSV files
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to fetch
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            pd.DataFrame: OHLCV data or None if error
        """
        try:
            # Map timeframe to CSV suffix
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
            
            # Construct CSV path
            base_dir = Path(__file__).resolve().parent.parent.parent
            csv_path = base_dir / "charts" / market_type / f"{symbol}{csv_suffix}.csv"
            
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
    
    def _generate_synthetic_data(self, symbol, timeframe, count):
        """
        Generate synthetic OHLCV data for testing
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            count (int): Number of candles to generate
            
        Returns:
            pd.DataFrame: Synthetic OHLCV data
        """
        try:
            # Get current time
            now = datetime.now()
            
            # Map timeframe to timedelta
            timeframe_map = {
                '1m': timedelta(minutes=1),
                '5m': timedelta(minutes=5),
                '15m': timedelta(minutes=15),
                '30m': timedelta(minutes=30),
                '1h': timedelta(hours=1),
                '4h': timedelta(hours=4),
                '1d': timedelta(days=1),
                '1w': timedelta(weeks=1)
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            delta = timeframe_map[timeframe]
            
            # Generate dates
            dates = [now - delta * i for i in range(count, 0, -1)]
            
            # Generate random price data
            if 'USD' in symbol:
                # Forex or crypto with USD
                base_price = 1.0 if 'EUR' in symbol else (50000.0 if 'BTC' in symbol else 100.0)
            else:
                # Other instrument
                base_price = 100.0
            
            # Add some randomness
            np.random.seed(hash(symbol) % 10000)
            
            # Generate OHLCV data
            data = []
            current_price = base_price
            
            for date in dates:
                # Random price movement
                change_pct = np.random.normal(0, 0.01)  # 1% standard deviation
                
                # Calculate OHLC
                close = current_price * (1 + change_pct)
                high = close * (1 + abs(np.random.normal(0, 0.005)))
                low = close * (1 - abs(np.random.normal(0, 0.005)))
                open_price = current_price
                
                # Random volume
                volume = int(np.random.normal(1000000, 500000))
                if volume < 0:
                    volume = 1000000
                
                data.append({
                    'datetime': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume
                })
                
                current_price = close
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            return None
    
    def _normalize_symbol(self, symbol, market_type):
        """
        Normalize symbol for different websites
        
        Args:
            symbol (str): Symbol (e.g., 'EURUSD', 'BTCUSDT')
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            str: Normalized symbol
        """
        # Check if we have a mapping for this symbol
        if market_type in self.symbol_mappings and symbol in self.symbol_mappings[market_type]:
            return self.symbol_mappings[market_type][symbol]
        
        # Default normalization
        if market_type == 'forex':
            # Convert EURUSD to EUR-USD
            if len(symbol) == 6:
                return f"{symbol[:3]}-{symbol[3:]}"
        elif market_type == 'crypto':
            # Convert BTCUSDT to BTCUSD
            if symbol.endswith('USDT'):
                return symbol[:-4] + 'USD'
        
        return symbol
    
    async def _respect_rate_limit(self, site_name):
        """
        Respect rate limits for websites
        
        Args:
            site_name (str): Site name
        """
        current_time = time.time()
        last_request = self.last_request_time.get(site_name, 0)
        
        # If we've made a request recently, wait
        if current_time - last_request < self.request_interval:
            wait_time = self.request_interval - (current_time - last_request)
            await asyncio.sleep(wait_time)
        
        # Update last request time
        self.last_request_time[site_name] = time.time()
    
    async def _apply_stealth_mode(self, page):
        """
        Apply stealth mode to avoid detection
        
        Args:
            page: Playwright page
        """
        # Execute stealth mode script
        await page.evaluate("""
        () => {
            // Overwrite the `languages` property to use a custom getter
            Object.defineProperty(navigator, 'languages', {
                get: function() {
                    return ['en-US', 'en'];
                },
            });
            
            // Overwrite the `plugins` property to use a custom getter
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    return [1, 2, 3, 4, 5];
                },
            });
            
            // Pass the Webdriver test
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Pass the Chrome Test
            window.chrome = {
                runtime: {},
            };
            
            // Pass the Permissions Test
            window.navigator.permissions = {
                query: () => Promise.resolve({ state: 'granted' }),
            };
        }
        """)
    
    def _save_to_cache_file(self, symbol, market_type, data, timeframe=None):
        """
        Save data to cache file
        
        Args:
            symbol (str): Symbol
            market_type (str): Market type
            data: Data to save (price or DataFrame)
            timeframe (str, optional): Timeframe for OHLCV data
        """
        try:
            # Create cache directory if it doesn't exist
            cache_dir = self.cache_dir / market_type
            cache_dir.mkdir(exist_ok=True)
            
            # Construct cache file path
            if timeframe:
                cache_file = cache_dir / f"{symbol}_{timeframe}.json"
            else:
                cache_file = cache_dir / f"{symbol}_price.json"
            
            # Prepare data for saving
            cache_data = {
                'timestamp': time.time(),
                'symbol': symbol,
                'market_type': market_type
            }
            
            if isinstance(data, pd.DataFrame):
                # Convert DataFrame to dict for JSON serialization
                cache_data['type'] = 'ohlcv'
                cache_data['timeframe'] = timeframe
                cache_data['data'] = data.reset_index().to_dict(orient='records')
            else:
                # Save price data
                cache_data['type'] = 'price'
                cache_data['data'] = data
            
            # Save to file
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            logger.error(f"Error saving to cache file: {e}")
    
    def _load_from_cache_file(self, symbol, market_type, timeframe=None, max_age=None):
        """
        Load data from cache file
        
        Args:
            symbol (str): Symbol
            market_type (str): Market type
            timeframe (str, optional): Timeframe for OHLCV data
            max_age (int, optional): Maximum age of cache in seconds
            
        Returns:
            Data from cache or None if not found or expired
        """
        try:
            # Construct cache file path
            cache_dir = self.cache_dir / market_type
            
            if timeframe:
                cache_file = cache_dir / f"{symbol}_{timeframe}.json"
            else:
                cache_file = cache_dir / f"{symbol}_price.json"
            
            # Check if file exists
            if not cache_file.exists():
                return None
            
            # Load data from file
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check timestamp
            timestamp = cache_data.get('timestamp', 0)
            current_time = time.time()
            
            # Use provided max_age or default cache duration
            if max_age is None:
                max_age = self.cache_duration
            
            # Check if cache is expired
            if current_time - timestamp > max_age:
                return None
            
            # Return data based on type
            if cache_data.get('type') == 'ohlcv':
                # Convert dict back to DataFrame
                df = pd.DataFrame(cache_data['data'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                return df
            else:
                # Return price data
                return cache_data['data']
                
        except Exception as e:
            logger.error(f"Error loading from cache file: {e}")
            return None
    
    async def _initialize_proxies(self):
        """Initialize and test proxies"""
        if not self.proxies:
            return
        
        logger.info(f"Testing {len(self.proxies)} proxies...")
        
        # Test each proxy
        for i, proxy in enumerate(self.proxies):
            try:
                # Create a new context with this proxy
                proxy_config = self._parse_proxy_url(proxy)
                
                # Test the proxy with a simple request
                test_context = await self.browser.new_context(proxy=proxy_config)
                test_page = await test_context.new_page()
                
                try:
                    await test_page.goto('https://www.google.com', timeout=10000)
                    title = await test_page.title()
                    
                    # If we get here, the proxy is working
                    self._mark_proxy_health(i, True)
                    logger.info(f"Proxy {proxy} is working")
                    
                except Exception as e:
                    # Proxy failed
                    self._mark_proxy_health(i, False)
                    logger.warning(f"Proxy {proxy} failed: {e}")
                
                finally:
                    await test_page.close()
                    await test_context.close()
                    
            except Exception as e:
                # Proxy failed to initialize
                self._mark_proxy_health(i, False)
                logger.warning(f"Failed to initialize proxy {proxy}: {e}")
        
        # Filter out bad proxies
        good_proxies = [proxy for i, proxy in enumerate(self.proxies) if self.proxy_health.get(i, False)]
        
        if good_proxies:
            logger.info(f"Found {len(good_proxies)} working proxies")
            self.proxies = good_proxies
        else:
            logger.warning("No working proxies found. Will continue without proxies.")
            self.proxies = []
    
    def _mark_proxy_health(self, index, is_healthy):
        """
        Mark proxy health
        
        Args:
            index (int): Proxy index
            is_healthy (bool): Whether the proxy is healthy
        """
        self.proxy_health[index] = is_healthy
    
    async def _check_proxy_rotation(self):
        """Check if we need to rotate proxy"""
        if not self.proxies:
            return
        
        # Increment request count
        self.request_count += 1
        
        # Check if we need to rotate
        if self.request_count >= self.proxy_rotation_interval:
            # Reset request count
            self.request_count = 0
            
            # Rotate to next proxy
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            # Get the new proxy
            current_proxy = self.proxies[self.current_proxy_index]
            logger.info(f"Rotating to proxy: {current_proxy}")
            
            # Close existing browser and context
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            
            # Create new browser with the new proxy
            proxy_config = self._parse_proxy_url(current_proxy)
            
            # Launch browser with new proxy
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                timeout=30000,
                proxy=proxy_config
            )
            
            # Create new context
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )

    # Add these methods to the WebDataProvider class in web_data.py

    async def get_forex_price_exchange_rate(self, symbol):
        """
        Get forex price using ExchangeRate-API
        
        Args:
            symbol (str): Forex symbol (e.g., 'EURUSD')
        
        Returns:
            float: Price or None if error
        """
        try:
            # Format symbol
            if len(symbol) == 6:
                base = symbol[:3]
                quote = symbol[3:]
            else:
                parts = symbol.split('/')
                base = parts[0]
                quote = parts[1] if len(parts) > 1 else 'USD'
            
            # Construct URL
            url = f"https://open.er-api.com/v6/latest/{base}"
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching forex data: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if not data or not data.get('rates') or quote not in data['rates']:
                        logger.error("No forex data returned")
                        return None
                    
                    # Extract price
                    rate = data['rates'][quote]
                    
                    return rate
            
        except Exception as e:
            logger.error(f"Error getting forex price for {symbol}: {e}")
            return None

    async def get_crypto_price_ccxt(self, symbol):
        """
        Get cryptocurrency price using CCXT
        
        Args:
            symbol (str): Crypto symbol (e.g., 'BTC/USDT' or 'BTCUSDT')
        
        Returns:
            float: Price or None if error
        """
        try:
            import ccxt.async_support as ccxt
            
            # Format symbol for CCXT
            if 'USDT' in symbol and '/' not in symbol:
                formatted_symbol = f"{symbol.replace('USDT', '')}/USDT"
            elif 'USD' in symbol and '/' not in symbol and 'USDT' not in symbol:
                formatted_symbol = f"{symbol.replace('USD', '')}/USD"
            else:
                formatted_symbol = symbol
            
            # Initialize exchange
            exchange = ccxt.binance({
                'enableRateLimit': True,
            })
            
            try:
                # Fetch ticker
                ticker = await exchange.fetch_ticker(formatted_symbol)
                
                # Close exchange
                await exchange.close()
                
                if not ticker:
                    logger.error(f"No ticker data returned for {formatted_symbol}")
                    return None
                
                # Extract price
                price = ticker['last']
                
                return price
                
            except Exception as e:
                # Make sure to close the exchange
                await exchange.close()
                raise e
            
        except Exception as e:
            logger.error(f"Error getting crypto price for {symbol} with CCXT: {e}")
            return None
