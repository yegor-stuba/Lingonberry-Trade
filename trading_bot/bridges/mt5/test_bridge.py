"""Test the MT5 bridge connection"""
import asyncio
import pandas as pd
import logging
from trading_bot.bridges.mt5.client import MT5BridgeClient
from trading_bot.data.forex_data import ForexDataProvider

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Reduce timeout for testing
MT5_TIMEOUT = 10  # seconds

async def test_bridge():
    """Test the MT5 bridge connection"""
    logger.info("Testing MT5 bridge connection...")
    
    # Test direct bridge client
    client = MT5BridgeClient()
    mt5_available = client.connect()
    
    if mt5_available:
        logger.info("Connected to MT5 bridge server")
        
        # Get available symbols
        symbols = client.get_available_symbols()
        if symbols:
            logger.info(f"Available symbols in MT5: {symbols[:10]}...")  # Show first 10
        else:
            logger.warning("Failed to get available symbols")
            mt5_available = False
        
        # Get open charts
        if mt5_available:
            charts = client.get_open_charts()
            if charts:
                logger.info(f"Open charts in MT5: {charts}")
                
                # Test getting data for first open chart only
                if len(charts) > 0:
                    chart = charts[0]
                    symbol = chart['symbol']
                    timeframe = chart['timeframe']
                    
                    logger.info(f"Testing data retrieval for {symbol} {timeframe}")
                    df = client.get_forex_data(symbol, timeframe, 10)
                    if df is not None:
                        logger.info(f"Received {len(df)} candles for {symbol} {timeframe}")
                        logger.info(f"Data sample:\n{df.head(3)}")
                    else:
                        logger.error(f"Failed to get {symbol} {timeframe} data")
                        mt5_available = False
            else:
                logger.warning("No open charts found or failed to get open charts")
                mt5_available = False
    else:
        logger.error("Failed to connect to MT5 bridge server")
    
    # Test through ForexDataProvider
    provider = ForexDataProvider()
    
    # Test pairs to check from different sources
    test_pairs = [
        {'symbol': 'EURUSD', 'timeframe': '1h', 'source': 'csv'},
        {'symbol': 'GBPUSD', 'timeframe': '4h', 'source': 'mt5'},
        {'symbol': 'BTCUSD', 'timeframe': '5m', 'source': 'auto'}
    ]
    
    # Only test MT5 if it's available
    if mt5_available:
        test_pairs.insert(0, {'symbol': 'EURUSD', 'timeframe': '30m', 'source': 'mt5'})
    
    for pair in test_pairs:
        logger.info(f"Testing {pair['symbol']} {pair['timeframe']} from {pair['source']}")
        df = await provider.get_ohlcv(pair['symbol'], pair['timeframe'], 10, source=pair['source'])
        if df is not None:
            logger.info(f"ForexDataProvider ({pair['source']}): Received {len(df)} candles for {pair['symbol']} {pair['timeframe']}")
            logger.info(f"Data sample:\n{df.head(3)}")
        else:
            logger.error(f"ForexDataProvider: Failed to get {pair['symbol']} {pair['timeframe']} data from {pair['source']}")
    
    # Test getting available pairs
    pairs = await provider.get_forex_pairs()
    logger.info(f"Available forex pairs: {pairs}")
    
    # Test getting available timeframes
    timeframes = await provider.get_forex_timeframes()
    logger.info(f"Available timeframes: {timeframes}")
    
    # Test multi-timeframe data with auto source
    multi_tf_data = await provider.get_multi_timeframe_data('EURUSD', ['1h', '4h', '1d'], 10)
    if multi_tf_data:
        for tf, data in multi_tf_data.items():
            logger.info(f"Multi-timeframe data for EURUSD {tf}: {len(data)} candles")
            logger.info(f"Sample:\n{data.head(2)}")
    else:
        logger.error("Failed to get multi-timeframe data")

if __name__ == '__main__':
    asyncio.run(test_bridge())
