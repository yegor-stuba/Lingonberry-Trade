"""
Configuration settings for the trading bot
"""

import os
import logging
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Database settings
DB_PATH = BASE_DIR / "data" / "trading_bot.db"

# Telegram bot settings
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

# Trading preferences
TRADING_STYLES = ["Intraday", "Intraweek", "Position"]
MARKETS = ["Forex", "Crypto", "Metals", "Indices"]
DEFAULT_RISK_PERCENTAGE = 1.0  
MIN_RISK_REWARD_RATIO = 2.0
DEFAULT_ACCOUNT_SIZE = 10000.0

# Timeframes
TIMEFRAMES = {
    "Intraday": ["5m", "15m", "1h", "4h"],
    "Intraweek": ["1h", "4h", "1d"],
    "Position": ["4h", "1d", "1w"]
}

# Analysis settings
ANALYSIS_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]  # Multiple timeframes for analysis
FINAL_TIMEFRAME = "15m"  # Final timeframe for trade suggestion

# Common currency pairs
FOREX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", 
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY"
]

CRYPTO_PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "LINK/USDT"
]

INDICES = ["US30", "US500", "USTEC", "UK100", "GER40", "JPN225"]
METALS = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"]

# Combine all trading pairs into one list for convenience
TRADING_PAIRS = FOREX_PAIRS + [p.replace('/', '') for p in CRYPTO_PAIRS] + INDICES + METALS

# Journal settings
JOURNAL_UPDATE_TIME = "00:00"  # Time to update trade status (GMT+1)
JOURNAL_FIELDS = [
    "date_time", "symbol", "direction", "entry_price", "stop_loss", "take_profit", 
    "risk_reward", "potential_gain", "outcome", "entry_reason", "market_conditions"
]

# Database settings
DB_PATH = "trading_bot/data/trading_journal.db"

# Visualization settings
CHART_STYLE = "dark_background"
CHART_DPI = 100
CHART_SIZE = (10, 6)

# API settings
# CCXT settings for crypto
CCXT_EXCHANGE = os.environ.get("CCXT_EXCHANGE", "binance")
CCXT_API_KEY = os.environ.get("CCXT_API_KEY", "")
CCXT_API_SECRET = os.environ.get("CCXT_API_SECRET", "")

# OANDA settings for forex
OANDA_API_KEY = os.environ.get("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID", "")

# MetaTrader settings
MT5_USERNAME = os.environ.get("MT5_USERNAME", "")
MT5_PASSWORD = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER = os.environ.get("MT5_SERVER", "")

# News API settings
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# Logging settings
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOG_DIR / "trading_bot.log"

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Daily review settings
DAILY_REVIEW_TIME = "00:00"  # GMT+1
WEEKLY_REVIEW_DAY = "Friday"

# Trade journal settings
JOURNAL_EXPORT_FORMATS = ["csv", "json", "xlsx"]

# SMC Analysis settings
SMC_ORDER_BLOCK_WINDOW = 5
SMC_LIQUIDITY_WINDOW = 10
SMC_MIN_STRENGTH = 70  # Minimum strength for trade setups

# Risk management settings
MAX_RISK_PER_TRADE = 2.0  # Maximum risk percentage per trade
MAX_OPEN_TRADES = 5  # Maximum number of open trades at once
MAX_DAILY_RISK = 5.0  # Maximum daily risk percentage
MAX_DRAWDOWN_PERCENTAGE = 10.0  # Maximum drawdown percentage before reducing risk

# Backtesting settings
BACKTEST_DEFAULT_PERIOD = "1y"  # Default period for backtesting (1 year)
BACKTEST_COMMISSION = 0.1  # Default commission percentage

# Web scraper settings
WEB_SCRAPER_CACHE_DURATION = 300  # 5 minutes
WEB_SCRAPER_REQUEST_INTERVAL = 2  # 2 seconds between requests to the same site
PROXIES = []  # List of proxy servers to use
GENERATE_SYNTHETIC_DATA = True  # Generate synthetic data when web scraping fails
