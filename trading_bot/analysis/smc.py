"""
Trade suggestion service
Integrates market data, SMC analysis, and risk management
to generate trade suggestions
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from trading_bot.data.forex_data import ForexDataProvider
from trading_bot.data.crypto_data import CryptoDataProvider
from trading_bot.data.web_data import WebDataProvider  # Add this import
from trading_bot.risk.management import RiskManager
from trading_bot.config import settings
from trading_bot.journal.trade_journal import TradeJournal

logger = logging.getLogger(__name__)

class TradeSuggestionService:
    """Service for generating trade suggestions"""
    
    def __init__(self):
        """Initialize the trade suggestion service"""
        self.forex_provider = ForexDataProvider()
        self.crypto_provider = CryptoDataProvider()
        self.web_provider = None  # Will be initialized on demand
        self.risk_manager = RiskManager()
        self.journal = TradeJournal()
        self.use_web_scraper = settings.USE_WEB_SCRAPER if hasattr(settings, 'USE_WEB_SCRAPER') else False
        pass
        
    async def _ensure_web_provider(self):
        """Ensure web provider is initialized"""
        if self.web_provider is None:
            self.web_provider = WebDataProvider()
            await self.web_provider.initialize()
        
    async def get_trade_suggestions(self, 
                                market_type: str, 
                                symbol: str, 
                                timeframes: List[str] = None,
                                user_id: int = None,
                                account_size: float = None,
                                risk_percentage: float = None,
                                use_web_scraper: bool = None) -> Dict:
        """
        Generate trade suggestions for a specific symbol
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframes (list): List of timeframes to analyze
            user_id (int): User ID for risk checking
            account_size (float): Account size for position sizing
            risk_percentage (float): Risk percentage for position sizing
            use_web_scraper (bool): Whether to use web scraping for data
            
        Returns:
            dict: Trade suggestion details
        """
        try:
            # Set default timeframes if not provided
            if timeframes is None:
                timeframes = settings.ANALYSIS_TIMEFRAMES
            
            # Get user preferences if user_id is provided
            user_preferences = None
            if user_id:
                user_preferences = self.journal.get_user_preferences(user_id)
                if user_preferences:
                    if account_size is None:
                        account_size = user_preferences.get('account_size', settings.DEFAULT_ACCOUNT_SIZE)
                    if risk_percentage is None:
                        risk_percentage = user_preferences.get('risk_percentage', settings.DEFAULT_RISK_PERCENTAGE)
            
            # Set defaults if still not set
            if account_size is None:
                account_size = settings.DEFAULT_ACCOUNT_SIZE
            if risk_percentage is None:
                risk_percentage = settings.DEFAULT_RISK_PERCENTAGE
            
            # Determine whether to use web scraper
            if use_web_scraper is None:
                use_web_scraper = self.use_web_scraper
            
            # Get multi-timeframe data
            data_frames = await self._get_market_data(market_type, symbol, timeframes, use_web_scraper)
            if not data_frames:
                return {
                    'success': False,
                    'message': f"Failed to get data for {symbol}",
                    'suggestions': []
                }
            
            # Log which data provider was used
            data_source = 'WebDataProvider' if use_web_scraper else (
                'CryptoDataProvider' if market_type.lower() == 'crypto' else 'ForexDataProvider'
            )
            logger.info(f"Analyzing {symbol} using data from {data_source}")
            
            # Perform multi-timeframe analysis
            analysis_result = self.smc_analyzer.multi_timeframe_analysis(data_frames)
            
            # Extract trade setups
            trade_setups = analysis_result.get('trade_setups', [])
            
            # Apply risk management to each setup
            suggestions = []
            for setup in trade_setups:
                # Calculate position size
                position_info = self.risk_manager.calculate_position_size(
                    account_size=account_size,
                    risk_percentage=risk_percentage,
                    entry_price=setup['entry'],
                    stop_loss=setup['stop_loss'],
                    symbol=symbol
                )
                
                # Check risk limits if user_id is provided
                risk_check = None
                if user_id:
                    trade_info = {
                        'symbol': symbol,
                        'direction': setup['type'],
                        'entry_price': setup['entry'],
                        'stop_loss': setup['stop_loss'],
                        'take_profit': setup['take_profit'],
                        'risk_percentage': risk_percentage
                    }
                    risk_check = self.risk_manager.check_risk_limits(user_id, trade_info)
                
                # Adjust for correlation if user_id is provided
                if user_id:
                    trade_info = {
                        'symbol': symbol,
                        'direction': setup['type'],
                        'entry_price': setup['entry'],
                        'stop_loss': setup['stop_loss'],
                        'take_profit': setup['take_profit'],
                        'risk_percentage': risk_percentage,
                        'position_size': position_info.get('position_size', 0),
                        'position_info': position_info
                    }
                    adjusted_trade = self.risk_manager.adjust_position_for_correlation(user_id, trade_info)
                    position_info = {
                        'position_size': adjusted_trade.get('position_size', position_info.get('position_size', 0)),
                        'position_info': adjusted_trade.get('position_info', position_info),
                        'risk_amount': position_info.get('risk_amount', 0),
                        'risk_percentage': risk_percentage,
                        'correlation_adjustment': adjusted_trade.get('correlation_adjustment')
                    }
                
                # Create suggestion
                suggestion = {
                    'symbol': symbol,
                    'market_type': market_type,
                    'direction': setup['type'],
                    'entry': setup['entry'],
                    'stop_loss': setup['stop_loss'],
                    'take_profit': setup['take_profit'],
                    'risk_reward': setup['risk_reward'],
                    'strength': setup['strength'],
                    'reason': setup['reason'],
                    'position_info': position_info,
                    'risk_check': risk_check,
                    'timestamp': datetime.now().isoformat(),
                    'timeframes_analyzed': list(data_frames.keys()),
                    'bias': analysis_result.get('bias', 'neutral'),
                    'data_source': data_source  # Add information about the data source used
                }
                
                suggestions.append(suggestion)
            
            # Return results
            return {
                'success': True,
                'symbol': symbol,
                'market_type': market_type,
                'suggestions': suggestions,
                'market_bias': analysis_result.get('bias', 'neutral'),
                'analysis_timestamp': datetime.now().isoformat(),
                'timeframes_analyzed': list(data_frames.keys()),
                'data_source': data_source  # Add information about the data source used
            }
            
        except Exception as e:
            logger.error(f"Error generating trade suggestions: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'suggestions': []
            }

    
    async def _get_market_data(self, market_type: str, symbol: str, timeframes: List[str], use_web_scraper: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Get market data for multiple timeframes
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframes (list): List of timeframes
            use_web_scraper (bool): Whether to use web scraping for data
            
        Returns:
            dict: Dictionary of dataframes for each timeframe
        """
        try:
            data_frames = {}
            
            # Use web scraper if requested
            if use_web_scraper:
                await self._ensure_web_provider()
                logger.info(f"Using WebDataProvider for {symbol} ({market_type})")
                
                for tf in timeframes:
                    df = await self.web_provider.get_ohlcv(symbol, tf, count=100, market_type=market_type)
                    if df is not None and not df.empty:
                        data_frames[tf] = df
                    else:
                        logger.warning(f"Failed to get {tf} data for {symbol} from web provider")
                
                # If web scraper failed for all timeframes, fall back to traditional providers
                if not data_frames:
                    logger.warning(f"Web scraper failed for all timeframes. Falling back to traditional providers.")
                    use_web_scraper = False
            
            if not use_web_scraper:
                # Log which data provider we're using
                logger.info(f"Getting data for {symbol} ({market_type}) using {'crypto' if market_type.lower() == 'crypto' else 'forex'} data provider")
                
                if market_type.lower() in ['forex', 'indices', 'metals']:
                    # Use forex data provider for forex, indices, and metals
                    logger.info(f"Using ForexDataProvider for {symbol} ({market_type})")
                    for tf in timeframes:
                        df = await self.forex_provider.get_ohlcv(symbol, tf, count=100, source='auto')
                        if df is not None and not df.empty:
                            data_frames[tf] = df
                        else:
                            logger.warning(f"Failed to get {tf} data for {symbol} from forex provider")
                
                elif market_type.lower() == 'crypto':
                    # Use crypto data provider for crypto
                    logger.info(f"Using CryptoDataProvider for {symbol} ({market_type})")
                    for tf in timeframes:
                        df = await self.crypto_provider.get_ohlcv(symbol, tf, count=100, source='auto')
                        if df is not None and not df.empty:
                            data_frames[tf] = df
                        else:
                            logger.warning(f"Failed to get {tf} data for {symbol} from crypto provider")
                
                else:
                    logger.error(f"Unsupported market type: {market_type}")
                    return {}
            
            # Check if we got data for all timeframes
            if not data_frames:
                logger.error(f"Could not get any data for {symbol} ({market_type})")
                return {}
            
            missing_timeframes = set(timeframes) - set(data_frames.keys())
            if missing_timeframes:
                logger.warning(f"Missing data for timeframes: {missing_timeframes} for {symbol}")
            
            return data_frames
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol} ({market_type}): {e}")
            return {}

    
    async def get_market_scanner_results(self, market_type: str, symbols: List[str] = None, use_web_scraper: bool = None) -> List[Dict]:
        """
        Scan multiple symbols for trade opportunities
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbols (list): List of symbols to scan (if None, use default list)
            use_web_scraper (bool): Whether to use web scraping for data
            
        Returns:
            list: List of scan results with potential trade opportunities
        """
        try:
            # Determine whether to use web scraper
            if use_web_scraper is None:
                use_web_scraper = self.use_web_scraper
                
            # Get symbols to scan
            if symbols is None:
                if market_type.lower() == 'forex':
                    symbols = settings.FOREX_PAIRS
                elif market_type.lower() == 'crypto':
                    symbols = [pair.replace('/', '') for pair in settings.CRYPTO_PAIRS]
                elif market_type.lower() == 'indices':
                    symbols = settings.INDICES
                elif market_type.lower() == 'metals':
                    symbols = settings.METALS
                else:
                    logger.error(f"Unsupported market type: {market_type}")
                    return []
            
            # Use a subset of timeframes for scanning (for efficiency)
            scan_timeframes = ['1h', '4h', '1d']
            
            # Scan each symbol
            scan_results = []
            for symbol in symbols:
                try:
                    # Get data for this symbol
                    data_frames = await self._get_market_data(market_type, symbol, scan_timeframes, use_web_scraper)
                    if not data_frames:
                        continue
                    
                    # Analyze the highest timeframe available
                    highest_tf = max(data_frames.keys(), key=lambda x: self._timeframe_to_minutes(x))
                    df = data_frames[highest_tf]
                    
                    # Perform basic analysis
                    market_structure = self.smc_analyzer.identify_market_structure(df)
                    order_blocks = self.smc_analyzer.identify_order_blocks(df)
                    
                    # Check if there are strong order blocks near current price
                    current_price = df.iloc[-1]['close']
                    strong_obs = [ob for ob in order_blocks if ob['strength'] > 70]
                    
                    # Filter for order blocks within 2% of current price
                    nearby_obs = [ob for ob in strong_obs if 
                                 abs(ob['top'] - current_price) / current_price < 0.02 or
                                 abs(ob['bottom'] - current_price) / current_price < 0.02]
                    
                    # If we have nearby strong order blocks or clear market structure, add to results
                    if nearby_obs or market_structure['trend'] != 'neutral':
                        scan_results.append({
                            'symbol': symbol,
                            'market_type': market_type,
                            'current_price': current_price,
                            'bias': market_structure['trend'],
                            'has_strong_ob': len(nearby_obs) > 0,
                            'ob_count': len(nearby_obs),
                            'timeframe': highest_tf,
                            'score': len(nearby_obs) * 10 + (10 if market_structure['trend'] != 'neutral' else 0),
                            'data_source': 'WebDataProvider' if use_web_scraper else (
                                                             'CryptoDataProvider' if market_type.lower() == 'crypto' else 'ForexDataProvider'
                            )
                        })
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
                    continue
            
            # Sort results by score (descending)
            scan_results.sort(key=lambda x: x['score'], reverse=True)
            
            return scan_results
            
        except Exception as e:
            logger.error(f"Error in market scanner: {e}")
            return []
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe string to minutes
        
        Args:
            timeframe (str): Timeframe string (e.g., '1h', '4h', '1d')
            
        Returns:
            int: Timeframe in minutes
        """
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 60 * 24
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 60 * 24 * 7
        else:
            return 0
    
    async def close(self):
        """Close all data providers"""
        if self.web_provider:
            await self.web_provider.close()
        
        if hasattr(self.forex_provider, 'close'):
            self.forex_provider.close()
        
        if hasattr(self.crypto_provider, 'close'):
            self.crypto_provider.close()

