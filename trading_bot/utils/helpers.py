"""
Helper functions for the trading bot
"""

import datetime
import pytz

def get_current_datetime():
    """Get current datetime in GMT+1 timezone"""
    utc_now = datetime.datetime.now(pytz.utc)
    gmt1 = pytz.timezone('Europe/London')  # Close enough to GMT+1
    return utc_now.astimezone(gmt1)

def format_datetime(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def calculate_risk_amount(account_size, risk_percentage):
    """Calculate risk amount based on account size and risk percentage"""
    return account_size * (risk_percentage / 100)

def calculate_position_size(account_size, risk_percentage, entry_price, stop_loss, pair_type="forex"):
    """
    Calculate position size based on risk parameters
    
    Args:
        account_size (float): Account size in base currency
        risk_percentage (float): Risk percentage per trade
        entry_price (float): Entry price
        stop_loss (float): Stop loss price
        pair_type (str): Type of pair (forex, crypto, etc.)
        
    Returns:
        float: Position size
    """
    risk_amount = calculate_risk_amount(account_size, risk_percentage)
    
    if pair_type.lower() == "forex":
        # For forex, calculate in lots
        pip_value = 0.0001  # Standard pip value for most pairs
        pips_at_risk = abs(entry_price - stop_loss) / pip_value
        # Assuming 1 standard lot = 100,000 units and 1 pip = $10 for standard lot
        lot_size = risk_amount / (pips_at_risk * 10)
        return lot_size
    
    elif pair_type.lower() == "crypto":
        # For crypto, calculate in units
        price_difference = abs(entry_price - stop_loss)
        units = risk_amount / price_difference
        return units
    
    else:
        # Generic calculation
        price_difference = abs(entry_price - stop_loss)
        units = risk_amount / price_difference
        return units

def calculate_risk_reward(entry_price, stop_loss, take_profit):
    """Calculate risk-reward ratio"""
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    
    if risk == 0:
        return 0
    
    return reward / risk

def is_trading_time():
    """Check if current time is within trading hours"""
    now = get_current_datetime()
    
    # Define trading hours (e.g., weekdays 8:00-22:00)
    weekday = now.weekday()
    hour = now.hour
    
    # Weekend check (5=Saturday, 6=Sunday)
    if weekday >= 5:
        return False
    
    # Hour check (8:00-22:00)
    if hour < 8 or hour >= 22:
        return False
    
    return True

def get_end_of_day_time():
    """Get the end of day time (00:00 GMT+1)"""
    now = get_current_datetime()
    tomorrow = now.date() + datetime.timedelta(days=1)
    return datetime.datetime.combine(tomorrow, datetime.time.min, tzinfo=now.tzinfo)

def format_price(price, decimals=5):
    """Format price with appropriate number of decimal places"""
    return f"{price:.{decimals}f}"

def format_percentage(value):
    """Format percentage value"""
    return f"{value:.2f}%"

def get_market_type(symbol):
    """Determine market type from symbol"""
    symbol = symbol.upper()
    
    # Forex pairs typically have 6 characters (e.g., EURUSD)
    if len(symbol) == 6 and symbol.isalpha():
        return "forex"
    
    # Crypto pairs typically end with USDT, BTC, ETH, etc.
    if "USDT" in symbol or "BTC" in symbol or "ETH" in symbol:
        return "crypto"
    
    # Indices typically start with a country code
    if symbol in ["US30", "US500", "USTEC", "UK100", "GER40", "JPN225"]:
        return "indices"
    
    # Metals typically start with X
    if symbol.startswith("XAU") or symbol.startswith("XAG"):
        return "metals"
    
    # Default
    return "unknown"

def validate_symbol(symbol):
    """Validate if a symbol is properly formatted"""
    if not symbol:
        return False
    
    # Basic validation
    if len(symbol) < 3:
        return False
    
    return True
