"""
Factory for creating data providers
"""

import logging
from trading_bot.data.forex_data import ForexDataProvider
from trading_bot.data.web_data import WebDataProvider

logger = logging.getLogger(__name__)

class DataProviderFactory:
    """Factory for creating data providers"""
    
    @staticmethod
    async def get_provider(market_type, use_web_scraper=False):
        """
        Get a data provider for the specified market type
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'stocks')
            use_web_scraper (bool): Whether to use the web scraper instead of API/CSV
            
        Returns:
            object: Data provider instance
        """
        if use_web_scraper:
            provider = WebDataProvider()
            await provider.initialize()
            return provider
        
        if market_type == 'forex':
            return ForexDataProvider()
        elif market_type == 'crypto':
            # For now, use forex provider for crypto
            return ForexDataProvider()
        elif market_type == 'indices':
            # For now, use forex provider for indices
            return ForexDataProvider()
        elif market_type == 'stocks':
            # For now, use forex provider for stocks
            return ForexDataProvider()
        else:
            logger.error(f"Unknown market type: {market_type}")
            return None
