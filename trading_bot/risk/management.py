"""
Risk management module for the trading bot
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from trading_bot.config import settings
from trading_bot.journal.trade_journal import TradeJournal

logger = logging.getLogger(__name__)

class RiskManager:
    """Class for managing trading risk"""
    
    def __init__(self, journal=None):
        """Initialize the risk manager"""
        self.journal = journal or TradeJournal()
    
    def calculate_position_size(self, account_size: float, risk_percentage: float, 
                               entry_price: float, stop_loss: float, symbol: str) -> Dict:
        """
        Calculate position size based on risk parameters
        
        Args:
            account_size (float): Account size in base currency
            risk_percentage (float): Risk percentage per trade
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            symbol (str): Trading symbol
            
        Returns:
            dict: Position sizing information
        """
        try:
            # Validate inputs
            if risk_percentage > settings.MAX_RISK_PER_TRADE:
                risk_percentage = settings.MAX_RISK_PER_TRADE
                logger.warning(f"Risk percentage capped at {settings.MAX_RISK_PER_TRADE}%")
            
            # Calculate risk amount in account currency
            risk_amount = account_size * (risk_percentage / 100)
            
            # Calculate pip/point risk
            if entry_price > stop_loss:  # Long position
                pip_risk = entry_price - stop_loss
                direction = "BUY"
            else:  # Short position
                pip_risk = stop_loss - entry_price
                direction = "SELL"
            
            # Calculate position size
            position_size = risk_amount / pip_risk
            
            # Adjust position size based on symbol
            # For forex pairs, we need to consider lot sizes
            if any(symbol.startswith(currency) for currency in ["EUR", "GBP", "AUD", "NZD"]):
                # Standard lot = 100,000 units
                # Mini lot = 10,000 units
                # Micro lot = 1,000 units
                standard_lots = position_size / 100000
                mini_lots = position_size / 10000
                micro_lots = position_size / 1000
                
                position_info = {
                    'standard_lots': standard_lots,
                    'mini_lots': mini_lots,
                    'micro_lots': micro_lots,
                    'recommended': f"{micro_lots:.2f} micro lots"
                }
            elif symbol.endswith("USDT"):  # Crypto
                position_info = {
                    'units': position_size,
                    'recommended': f"{position_size:.4f} {symbol.replace('USDT', '')}"
                }
            else:  # Other instruments
                position_info = {
                    'units': position_size,
                    'recommended': f"{position_size:.2f} units"
                }
            
            return {
                'direction': direction,
                'risk_amount': risk_amount,
                'risk_percentage': risk_percentage,
                'pip_risk': pip_risk,
                'position_size': position_size,
                'position_info': position_info
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'direction': "UNKNOWN",
                'risk_amount': 0,
                'risk_percentage': 0,
                'pip_risk': 0,
                'position_size': 0,
                'position_info': {'recommended': "Error calculating position size"}
            }
    
    def check_risk_limits(self, user_id: int, new_trade: Dict) -> Dict:
        """
        Check if a new trade would exceed risk limits
        
        Args:
            user_id (int): User ID
            new_trade (dict): New trade details
            
        Returns:
            dict: Risk check results
        """
        try:
            # Get user preferences
            preferences = self.journal.get_user_preferences(user_id)
            if not preferences:
                return {
                    'allowed': False,
                    'reason': "User preferences not found. Please set up your account first."
                }
            
            # Get active trades
            active_trades = self.journal.get_active_trades(user_id)
            
            # Check maximum open trades
            if len(active_trades) >= settings.MAX_OPEN_TRADES:
                return {
                    'allowed': False,
                    'reason': f"Maximum number of open trades ({settings.MAX_OPEN_TRADES}) reached."
                }
            
            # Calculate current risk exposure
            current_risk = sum(trade.get('risk_percentage', 0) for trade in active_trades)
            
            # Calculate new total risk
            new_risk = current_risk + new_trade.get('risk_percentage', 0)
            
            # Check daily risk limit
            if new_risk > settings.MAX_DAILY_RISK:
                return {
                    'allowed': False,
                    'reason': f"This trade would exceed your daily risk limit of {settings.MAX_DAILY_RISK}%."
                }
            
            # Check drawdown
            account_stats = self.journal.get_account_statistics(user_id)
            current_drawdown = account_stats.get('current_drawdown', 0)
            
            if current_drawdown > settings.MAX_DRAWDOWN_PERCENTAGE:
                # Reduce risk when in drawdown
                max_risk = settings.MAX_RISK_PER_TRADE * (1 - (current_drawdown / 100))
                
                if new_trade.get('risk_percentage', 0) > max_risk:
                    return {
                        'allowed': False,
                        'reason': f"Risk too high during drawdown. Maximum allowed: {max_risk:.2f}%"
                    }
            
            # All checks passed
            return {
                'allowed': True,
                'current_risk': current_risk,
                'new_total_risk': new_risk,
                'remaining_risk': settings.MAX_DAILY_RISK - new_risk
            }
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {
                'allowed': False,
                'reason': f"Error checking risk limits: {e}"
            }
    
    def calculate_risk_reward(self, entry_price: float, stop_loss: float, take_profit: float) -> Dict:
        """
        Calculate risk-reward ratio for a trade
        
        Args:
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            
        Returns:
            dict: Risk-reward information
        """
        try:
            # Determine direction
            if entry_price > stop_loss:  # Long position
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
                direction = "BUY"
            else:  # Short position
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
                direction = "SELL"
            
            # Calculate R:R ratio
            if risk > 0:
                risk_reward_ratio = reward / risk
            else:
                risk_reward_ratio = 0
            
            return {
                'direction': direction,
                'risk_points': risk,
                'reward_points': reward,
                'risk_reward_ratio': risk_reward_ratio,
                'meets_minimum': risk_reward_ratio >= settings.MIN_RISK_REWARD_RATIO
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio: {e}")
            return {
                'direction': "UNKNOWN",
                'risk_points': 0,
                'reward_points': 0,
                'risk_reward_ratio': 0,
                'meets_minimum': False
            }
    
    def adjust_position_for_correlation(self, user_id: int, new_trade: Dict) -> Dict:
        """
        Adjust position size based on correlation with existing trades
        
        Args:
            user_id (int): User ID
            new_trade (dict): New trade details
            
        Returns:
            dict: Adjusted position information
        """
        try:
            # Get active trades
            active_trades = self.journal.get_active_trades(user_id)
            
            # If no active trades, no adjustment needed
            if not active_trades:
                return new_trade
            
            # Check for correlated pairs
            correlated_trades = []
            new_symbol = new_trade.get('symbol', '')
            
            # Simple correlation rules (can be expanded with actual correlation data)
            for trade in active_trades:
                trade_symbol = trade.get('symbol', '')
                
                # Check for direct correlation
                if (new_symbol.startswith('EUR') and trade_symbol.startswith('EUR')) or \
                   (new_symbol.startswith('GBP') and trade_symbol.startswith('GBP')) or \
                   (new_symbol.startswith('USD') and trade_symbol.startswith('USD')) or \
                   (new_symbol.startswith('BTC') and trade_symbol.startswith('BTC')):
                    correlated_trades.append(trade)
            
            # If correlated trades found, adjust risk
            if correlated_trades:
                # Calculate correlation factor (simple version)
                correlation_factor = 1 - (0.2 * len(correlated_trades))  # Reduce by 20% per correlated trade
                correlation_factor = max(0.5, correlation_factor)  # Don't reduce below 50%
                
                # Adjust risk percentage
                original_risk = new_trade.get('risk_percentage', 1.0)
                adjusted_risk = original_risk * correlation_factor
                
                # Recalculate position size
                preferences = self.journal.get_user_preferences(user_id)
                account_size = preferences.get('account_size', settings.DEFAULT_ACCOUNT_SIZE)
                
                position_info = self.calculate_position_size(
                    account_size=account_size,
                    risk_percentage=adjusted_risk,
                    entry_price=new_trade.get('entry_price', 0),
                    stop_loss=new_trade.get('stop_loss', 0),
                    symbol=new_symbol
                )
                
                # Update trade with adjusted values
                new_trade.update({
                    'risk_percentage': adjusted_risk,
                    'position_size': position_info.get('position_size', 0),
                    'position_info': position_info.get('position_info', {}),
                    'correlation_adjustment': {
                        'original_risk': original_risk,
                        'adjusted_risk': adjusted_risk,
                        'correlation_factor': correlation_factor,
                        'correlated_symbols': [trade.get('symbol') for trade in correlated_trades]
                    }
                })
            
            return new_trade
            
        except Exception as e:
            logger.error(f"Error adjusting position for correlation: {e}")
            return new_trade
