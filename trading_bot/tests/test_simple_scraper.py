"""
Simple test script for web scraping forex data and using CCXT for crypto
"""

import requests
import logging
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_forex_price_yahoo(symbol):
    """
    Get forex price from Yahoo Finance
    
    Args:
        symbol (str): Forex symbol (e.g., 'EURUSD')
        
    Returns:
        dict: Price information or None if error
    """
    try:
        # Format symbol for Yahoo Finance
        if len(symbol) == 6:
            formatted_symbol = f"{symbol[:3]}{symbol[3:]}=X"
        else:
            formatted_symbol = f"{symbol}=X"
        
        # Construct URL
        url = f"https://finance.yahoo.com/quote/{formatted_symbol}"
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Send request
        logger.info(f"Sending request to {url}")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Error fetching data: {response.status_code}")
            return None
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the price element - try different selectors
        price_element = None
        selectors = [
            'fin-streamer[data-field="regularMarketPrice"]',
            'fin-streamer[data-symbol="' + formatted_symbol + '"][data-field="regularMarketPrice"]',
            'span[data-reactid="32"]',
            'div[data-test="quote-header-info"] span'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                price_element = elements[0]
                break
        
        if not price_element:
            logger.error("Price element not found")
            return None
        
        # Extract price
        price_text = price_element.get('value')
        if not price_text:
            price_text = price_element.text.strip()
        
        if not price_text:
            logger.error("Price text is empty")
            return None
        
        price = float(price_text.replace(',', ''))
        
        # Return price information
        return {
            'symbol': symbol,
            'price': price,
            'timestamp': datetime.now().isoformat(),
            'source': 'finance.yahoo.com'
        }
        
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def get_forex_price_exchangerate(symbol):
    """
    Get forex price from ExchangeRate-API
    
    Args:
        symbol (str): Forex symbol (e.g., 'EURUSD')
        
    Returns:
        dict: Price information or None if error
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
        logger.info(f"Sending request to {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Error fetching data: {response.status_code}")
            return None
        
        # Parse JSON response
        data = response.json()
        
        if not data or not data.get('rates') or quote not in data['rates']:
            logger.error("No data returned")
            return None
        
        # Extract price
        rate = data['rates'][quote]
        
        # Return price information
        return {
            'symbol': symbol,
            'price': rate,
            'timestamp': datetime.now().isoformat(),
            'source': 'exchangerate-api.com'
        }
        
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def get_crypto_price_ccxt(symbol):
    """
    Get cryptocurrency price using CCXT
    
    Args:
        symbol (str): Crypto symbol (e.g., 'BTC/USDT')
        
    Returns:
        dict: Price information or None if error
    """
    try:
        # Import ccxt
        import ccxt
        
        # Format symbol for CCXT
        if 'USDT' in symbol and '/' not in symbol:
            formatted_symbol = f"{symbol.replace('USDT', '')}/USDT"
        elif 'USD' in symbol and '/' not in symbol:
            formatted_symbol = f"{symbol.replace('USD', '')}/USD"
        else:
            formatted_symbol = symbol
        
        # Initialize exchange
        exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        
        logger.info(f"Fetching ticker for {formatted_symbol} from Binance")
        
        # Fetch ticker
        ticker = exchange.fetch_ticker(formatted_symbol)
        
        if not ticker:
            logger.error(f"No ticker data returned for {formatted_symbol}")
            
            # Try with Coinbase Pro as fallback
            logger.info(f"Trying Coinbase Pro for {formatted_symbol}")
            exchange = ccxt.coinbasepro({
                'enableRateLimit': True,
            })
            ticker = exchange.fetch_ticker(formatted_symbol)
            
            if not ticker:
                logger.error(f"No ticker data returned from Coinbase Pro for {formatted_symbol}")
                return None
        
        # Extract price
        price = ticker['last']
        
        # Return price information
        return {
            'symbol': symbol,
            'price': price,
            'bid': ticker.get('bid'),
            'ask': ticker.get('ask'),
            'volume': ticker.get('volume'),
            'timestamp': datetime.now().isoformat(),
            'source': f"ccxt.{exchange.id}"
        }
        
    except Exception as e:
        logger.error(f"Error getting price for {symbol} with CCXT: {e}")
        
        # Try another exchange as fallback
        try:
            import ccxt
            
            # Format symbol for CCXT
            if 'USDT' in symbol and '/' not in symbol:
                formatted_symbol = f"{symbol.replace('USDT', '')}/USDT"
            elif 'USD' in symbol and '/' not in symbol:
                formatted_symbol = f"{symbol.replace('USD', '')}/USD"
            else:
                formatted_symbol = symbol
            
            # Try with Kraken as another fallback
            logger.info(f"Trying Kraken for {formatted_symbol}")
            exchange = ccxt.kraken({
                'enableRateLimit': True,
            })
            ticker = exchange.fetch_ticker(formatted_symbol)
            
            if not ticker:
                logger.error(f"No ticker data returned from Kraken for {formatted_symbol}")
                return None
            
            # Extract price
            price = ticker['last']
            
            # Return price information
            return {
                'symbol': symbol,
                'price': price,
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'volume': ticker.get('volume'),
                'timestamp': datetime.now().isoformat(),
                'source': f"ccxt.{exchange.id}"
            }
            
        except Exception as e2:
            logger.error(f"Error getting price for {symbol} with fallback exchange: {e2}")
            return None

def test_scrapers():
    """Test all scrapers with common symbols"""
    # Test forex scrapers
    forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    logger.info("Testing forex scrapers...")
    
    for symbol in forex_symbols:
        # Test Yahoo Finance
        logger.info(f"Testing Yahoo Finance for {symbol}...")
        result = get_forex_price_yahoo(symbol)
        
        if result:
            logger.info(f"Yahoo Finance result for {symbol}: {result}")
        else:
            logger.error(f"Yahoo Finance failed for {symbol}")
        
        # Test ExchangeRate-API
        logger.info(f"Testing ExchangeRate-API for {symbol}...")
        result = get_forex_price_exchangerate(symbol)
        
        if result:
            logger.info(f"ExchangeRate-API result for {symbol}: {result}")
        else:
            logger.error(f"ExchangeRate-API failed for {symbol}")
        
        # Sleep to avoid rate limiting
        time.sleep(2)
    
    # Test crypto scrapers
    crypto_symbols = ['BTC/USDT', 'ETH/USDT', 'BTCUSDT', 'ETHUSDT']
    
    logger.info("Testing crypto scrapers with CCXT...")
    
    for symbol in crypto_symbols:
        # Test CCXT
        logger.info(f"Testing CCXT for {symbol}...")
        result = get_crypto_price_ccxt(symbol)
        
        if result:
            logger.info(f"CCXT result for {symbol}: {result}")
        else:
            logger.error(f"CCXT failed for {symbol}")
        
        # Sleep to avoid rate limiting
        time.sleep(2)

if __name__ == "__main__":
    logger.info("Starting simple scraper test...")
    
    # Check if ccxt is installed
    try:
        import ccxt
        logger.info("CCXT is installed")
    except ImportError:
        logger.error("CCXT is not installed. Please install it with: pip install ccxt")
        logger.info("Continuing with forex tests only...")
    
    test_scrapers()
    logger.info("Simple scraper test completed")
