"""Test the trade suggestion service"""
import asyncio
import logging
from trading_bot.services.trade_suggestion import TradeSuggestionService
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_suggestion_service():
    """Test the trade suggestion service"""
    service = TradeSuggestionService()
    
    # Test forex suggestion
    logger.info("Testing forex suggestion for EURUSD...")
    forex_result = await service.get_trade_suggestions(
        market_type='forex',
        symbol='EURUSD',
        timeframes=['1h', '4h', '1d'],
        account_size=10000,
        risk_percentage=1.0
    )
    
    if forex_result['success']:
        logger.info(f"Got {len(forex_result['suggestions'])} suggestions for EURUSD")
        if forex_result['suggestions']:
            logger.info("First suggestion:")
            pprint(forex_result['suggestions'][0])
    else:
        logger.error(f"Error: {forex_result['message']}")
    
    # Test crypto suggestion
    logger.info("\nTesting crypto suggestion for BTCUSDT...")
    crypto_result = await service.get_trade_suggestions(
        market_type='crypto',
        symbol='BTCUSDT',
        timeframes=['1h', '4h', '1d'],
        account_size=10000,
        risk_percentage=1.0
    )
    
    if crypto_result['success']:
        logger.info(f"Got {len(crypto_result['suggestions'])} suggestions for BTCUSDT")
        if crypto_result['suggestions']:
            logger.info("First suggestion:")
            pprint(crypto_result['suggestions'][0])
    else:
        logger.error(f"Error: {crypto_result['message']}")
    
    # Test market scanner
    logger.info("\nTesting market scanner for forex...")
    scan_results = await service.get_market_scanner_results('forex')
    logger.info(f"Found {len(scan_results)} potential opportunities")
    for i, result in enumerate(scan_results[:3]):  # Show top 3
        logger.info(f"Opportunity {i+1}: {result['symbol']} - Bias: {result['bias']} - Score: {result['score']}")
    
    # Test trade acceptance
    if forex_result['success'] and forex_result['suggestions']:
        suggestion = forex_result['suggestions'][0]
        logger.info("\nTesting trade acceptance...")
        
        # Simulate user accepting the trade
        accepted = await service.process_trade_decision(
            user_id=12345,  # Test user ID
            suggestion=suggestion,
            decision='accept',
            notes="Test trade acceptance"
        )
        
        if accepted:
            logger.info("Trade successfully recorded in journal")
        else:
            logger.error("Failed to record trade in journal")

if __name__ == '__main__':
    asyncio.run(test_suggestion_service())
