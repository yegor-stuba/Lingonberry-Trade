"""
Test for the ExchangeRate API and CCXT integration
"""

import logging
import asyncio
import aiohttp
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_forex_price(symbol):
    """
    Get forex price using ExchangeRate-API
    
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
                
                # Return price information
                return {
                    'symbol': symbol,
                    'price': rate,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'exchangerate-api.com'
                }
        
    except Exception as e:
        logger.error(f"Error getting forex price for {symbol}: {e}")
        return None

async def get_crypto_price(symbol):
    """
    Get cryptocurrency price using CCXT
    
    Args:
        symbol (str): Crypto symbol (e.g., 'BTC/USDT' or 'BTCUSDT')
    
    Returns:
        dict: Price information or None if error
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
            logger.info(f"Fetching ticker for {formatted_symbol} from Binance")
            
            # Fetch ticker
            ticker = await exchange.fetch_ticker(formatted_symbol)
            
            # Close exchange
            await exchange.close()
            
            if not ticker:
                logger.error(f"No ticker data returned for {formatted_symbol}")
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
                'source': f"ccxt.binance"
            }
            
        except Exception as e:
            # Make sure to close the exchange
            await exchange.close()
            raise e
        
    except Exception as e:
        logger.error(f"Error getting crypto price for {symbol} with CCXT: {e}")
        return None

async def test_apis():
    """Test the ExchangeRate API and CCXT"""
    # Test forex
    forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    logger.info("Testing forex data with ExchangeRate API...")
    forex_results = {}
    
    for symbol in forex_symbols:
        logger.info(f"Getting price for {symbol}...")
        result = await get_forex_price(symbol)
        
        if result:
            logger.info(f"{symbol}: {result['price']} (from {result['source']})")
            forex_results[symbol] = result
        else:
            logger.error(f"Failed to get price for {symbol}")
    
    # Test crypto
    crypto_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
    
    logger.info("Testing crypto data with CCXT...")
    crypto_results = {}
    
    for symbol in crypto_symbols:
        logger.info(f"Getting price for {symbol}...")
        result = await get_crypto_price(symbol)
        
        if result:
            logger.info(f"{symbol}: {result['price']} (from {result['source']})")
            crypto_results[symbol] = result
        else:
            logger.error(f"Failed to get price for {symbol}")
    
    # Save results to file
    all_results = {**forex_results, **crypto_results}
    
    if all_results:
        with open('api_test_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        
        logger.info(f"Saved results to api_test_results.json")

if __name__ == "__main__":
    logger.info("Starting API test...")
    asyncio.run(test_apis())
    logger.info("API test completed")
