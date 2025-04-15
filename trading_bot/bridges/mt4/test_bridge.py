"""Test the MT4 ZeroMQ bridge connection"""
import asyncio
import pandas as pd
import logging
from trading_bot.bridges.mt4.client import MT4ZeroMQClient
from trading_bot.data.forex_data import ForexDataProvider

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_bridge():
    """Test the MT4 ZeroMQ bridge connection"""
    logger.info("Testing MT4 ZeroMQ bridge connection...")
    
    # Test direct bridge client
    client = MT4ZeroMQClient()
    if client.connect():
        logger.info("Connected to MT4 ZeroMQ bridge server")
        
        # Test getting symbols
        symbols = await client.get_symbols()
        if symbols:
            logger.info(f"Received {len(symbols)} symbols")
            logger.info(f"Sample symbols: {symbols[:5]}")
        else:
            logger.error("Failed to get symbols")
        
        # Test getting EURUSD data
        df = await client.get_historical_data('EURUSD', 'H1', 10)
        if df is not None:
            logger.info(f"Received {len(df)} candles for EURUSD H1")
            logger.info(f"Data sample:\n{df.head()}")
        else:
            logger.error("Failed to get EURUSD data")
        
        # Test getting account info
        account_info = await client.get_account_info()
        if account_info:
            logger.info(f"Account info: {account_info}")
        else:
            logger.error("Failed to get account info")
        
        # Close the connection
        await client.close()
    else:
        logger.error("Failed to connect to MT4 ZeroMQ bridge server")
    
    # Test through ForexDataProvider
    provider = ForexDataProvider()
    
    # Test getting EURUSD data
    df = await provider.get_ohlcv('EURUSD', '1h', 10, source='mt4')
    if df is not None:
        logger.info(f"ForexDataProvider: Received {len(df)} candles for EURUSD 1h")
        logger.info(f"Data sample:\n{df.head()}")
    else:
        logger.error("ForexDataProvider: Failed to get EURUSD data")
    
    # Test getting data from CSV
    df = await provider.get_ohlcv('EURUSD', '1h', 10, source='csv')
    if df is not None:
        logger.info(f"ForexDataProvider (CSV): Received {len(df)} candles for EURUSD 1h")
        logger.info(f"Data sample:\n{df.head()}")
    else:
        logger.error("ForexDataProvider: Failed to get EURUSD data from CSV")
    
    # Test getting data from API
    df = await provider.get_ohlcv('EURUSD', '1h', 10, source='api')
    if df is not None:
        logger.info(f"ForexDataProvider (API): Received {len(df)} candles for EURUSD 1h")
        logger.info(f"Data sample:\n{df.head()}")
    else:
        logger.error("ForexDataProvider: Failed to get EURUSD data from API")

if __name__ == '__main__':
    asyncio.run(test_bridge())
