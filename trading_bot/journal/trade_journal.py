"""
Trade journaling functionality
"""

import sqlite3
import pandas as pd
import logging
import os
from datetime import datetime
import pytz

from trading_bot.utils import helpers
from trading_bot.config import settings

logger = logging.getLogger(__name__)

class TradeJournal:
    """Class for managing trade journal entries"""
    
    def __init__(self, db_path=settings.DB_PATH):
        """Initialize the trade journal"""
        self.db_path = db_path
        self._create_db_if_not_exists()
    
    def _create_db_if_not_exists(self):
        """Create database and tables if they don't exist"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    risk_reward REAL NOT NULL,
                    potential_gain REAL,
                    actual_gain REAL,
                    outcome TEXT,
                    status TEXT NOT NULL,
                    entry_reason TEXT,
                    market_conditions TEXT,
                    notes TEXT
                )
            ''')
            
            # Create user_preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    account_size REAL NOT NULL,
                    risk_percentage REAL NOT NULL,
                    trading_style TEXT NOT NULL,
                    selected_markets TEXT NOT NULL,
                    trading_pairs TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error creating database: {e}")
    
    def add_trade(self, trade_data):
        """
        Add a new trade to the journal
        
        Args:
            trade_data (dict): Trade data including symbol, direction, entry_price, etc.
        
        Returns:
            int: ID of the inserted trade, or None if failed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure required fields are present
            required_fields = ["symbol", "direction", "entry_price", "stop_loss", "take_profit"]
            for field in required_fields:
                if field not in trade_data:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Set default values for optional fields
            if "date_time" not in trade_data:
                trade_data["date_time"] = helpers.format_datetime(helpers.get_current_datetime())
            
            if "status" not in trade_data:
                trade_data["status"] = "pending"
            
            if "risk_reward" not in trade_data:
                trade_data["risk_reward"] = helpers.calculate_risk_reward(
                    trade_data["entry_price"], 
                    trade_data["stop_loss"], 
                    trade_data["take_profit"]
                )
            
            # Insert trade into database
            cursor.execute('''
                INSERT INTO trades (
                    date_time, symbol, direction, entry_price, stop_loss, take_profit,
                    risk_reward, potential_gain, status, entry_reason, market_conditions, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get("date_time", ""),
                trade_data.get("symbol", ""),
                trade_data.get("direction", ""),
                trade_data.get("entry_price", 0),
                trade_data.get("stop_loss", 0),
                trade_data.get("take_profit", 0),
                trade_data.get("risk_reward", 0),
                trade_data.get("potential_gain", 0),
                trade_data.get("status", "pending"),
                trade_data.get("entry_reason", ""),
                trade_data.get("market_conditions", ""),
                trade_data.get("notes", "")
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Added trade {trade_id} for {trade_data['symbol']}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            return None
    
    def update_trade_status(self, trade_id, current_price, status=None, notes=None):
        """
        Update the status of a trade based on current price
        
        Args:
            trade_id (int): ID of the trade to update
            current_price (float): Current price of the symbol
            status (str, optional): Manual status override
            notes (str, optional): Additional notes
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get trade details
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            trade = cursor.fetchone()
            
            if not trade:
                logger.error(f"Trade with ID {trade_id} not found")
                return False
            
            # Convert to dict for easier access
            columns = [col[0] for col in cursor.description]
            trade_dict = {columns[i]: trade[i] for i in range(len(columns))}
            
            # Calculate outcome if not provided
            if not status:
                direction = trade_dict["direction"]
                entry_price = trade_dict["entry_price"]
                stop_loss = trade_dict["stop_loss"]
                take_profit = trade_dict["take_profit"]
                
                if direction == "BUY":
                    if current_price <= stop_loss:
                        status = "stopped"
                        actual_gain = (stop_loss - entry_price) / entry_price * 100
                    elif current_price >= take_profit:
                        status = "target_reached"
                        actual_gain = (take_profit - entry_price) / entry_price * 100
                    else:
                        status = "open"
                        actual_gain = (current_price - entry_price) / entry_price * 100
                else:  # SELL
                    if current_price >= stop_loss:
                        status = "stopped"
                        actual_gain = (entry_price - stop_loss) / entry_price * 100
                    elif current_price <= take_profit:
                        status = "target_reached"
                        actual_gain = (entry_price - take_profit) / entry_price * 100
                    else:
                        status = "open"
                        actual_gain = (entry_price - current_price) / entry_price * 100
            else:
                actual_gain = trade_dict.get("actual_gain", 0)
            
            # Update trade in database
            cursor.execute('''
                UPDATE trades
                SET status = ?, actual_gain = ?, notes = ?
                WHERE id = ?
            ''', (
                status,
                actual_gain,
                notes if notes else trade_dict.get("notes", ""),
                trade_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated trade {trade_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trade status: {e}")
            return False
    
    def get_trades(self, limit=10, status=None):
        """
        Get recent trades from the journal
        
        Args:
            limit (int): Maximum number of trades to return
            status (str, optional): Filter by status
            
        Returns:
            list: List of trade dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY date_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            trades = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_pending_trades(self):
        """Get all pending trades that need status updates"""
        return self.get_trades(limit=100, status="pending")
    
    def get_trade_statistics(self):
        """
        Calculate trading statistics
        
        Returns:
            dict: Dictionary with statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total number of trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status != 'pending'")
            total_trades = cursor.fetchone()[0]
            
            if total_trades == 0:
                return {
                    "total_trades": 0,
                    "win_rate": 0,
                    "average_rr": 0,
                    "profit_factor": 0,
                    "total_return": 0,
                    "best_pair": None,
                    "worst_pair": None
                }
            
            # Get winning trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'target_reached'")
            winning_trades = cursor.fetchone()[0]
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Get average risk-reward ratio
            cursor.execute("SELECT AVG(risk_reward) FROM trades WHERE status != 'pending'")
            average_rr = cursor.fetchone()[0] or 0
            
            # Calculate total return
            cursor.execute("SELECT SUM(actual_gain) FROM trades WHERE status != 'pending'")
            total_return = cursor.fetchone()[0] or 0
            
            # Get profit factor (sum of profits / sum of losses)
            cursor.execute("SELECT SUM(actual_gain) FROM trades WHERE actual_gain > 0")
            total_profit = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(ABS(actual_gain)) FROM trades WHERE actual_gain < 0")
            total_loss = cursor.fetchone()[0] or 0
            
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Get best performing pair
            cursor.execute("""
                SELECT symbol, SUM(actual_gain) as total_gain
                FROM trades
                WHERE status != 'pending'
                GROUP BY symbol
                ORDER BY total_gain DESC
                LIMIT 1
            """)
            best_pair_result = cursor.fetchone()
            best_pair = {"symbol": best_pair_result[0], "gain": best_pair_result[1]} if best_pair_result else None
            
            # Get worst performing pair
            cursor.execute("""
                SELECT symbol, SUM(actual_gain) as total_gain
                FROM trades
                WHERE status != 'pending'
                GROUP BY symbol
                ORDER BY total_gain ASC
                LIMIT 1
            """)
            worst_pair_result = cursor.fetchone()
            worst_pair = {"symbol": worst_pair_result[0], "gain": worst_pair_result[1]} if worst_pair_result else None
            
            conn.close()
            
            return {
                "total_trades": total_trades,
                "win_rate": win_rate,
                "average_rr": average_rr,
                "profit_factor": profit_factor,
                "total_return": total_return,
                "best_pair": best_pair,
                "worst_pair": worst_pair
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}
    
    def save_user_preferences(self, user_id, preferences):
        """
        Save user trading preferences
        
        Args:
            user_id (int): Telegram user ID
            preferences (dict): User preferences
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert list values to strings for storage
            if "selected_markets" in preferences and isinstance(preferences["selected_markets"], list):
                preferences["selected_markets"] = ",".join(preferences["selected_markets"])
            
            if "trading_pairs" in preferences and isinstance(preferences["trading_pairs"], list):
                preferences["trading_pairs"] = ",".join(preferences["trading_pairs"])
            
            # Check if user already exists
            cursor.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing preferences
                cursor.execute('''
                    UPDATE user_preferences
                    SET account_size = ?, risk_percentage = ?, trading_style = ?,
                        selected_markets = ?, trading_pairs = ?, last_updated = ?
                    WHERE user_id = ?
                ''', (
                    preferences.get("account_size", 0),
                    preferences.get("risk_percentage", 1.0),
                    preferences.get("trading_style", ""),
                    preferences.get("selected_markets", ""),
                    preferences.get("trading_pairs", ""),
                    helpers.format_datetime(helpers.get_current_datetime()),
                    user_id
                ))
            else:
                # Insert new preferences
                cursor.execute('''
                    INSERT INTO user_preferences (
                        user_id, account_size, risk_percentage, trading_style,
                        selected_markets, trading_pairs, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    preferences.get("account_size", 0),
                    preferences.get("risk_percentage", 1.0),
                    preferences.get("trading_style", ""),
                    preferences.get("selected_markets", ""),
                    preferences.get("trading_pairs", ""),
                    helpers.format_datetime(helpers.get_current_datetime())
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            return False
    
    def get_user_preferences(self, user_id):
        """
        Get user trading preferences
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            dict: User preferences or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return None
            
            preferences = dict(result)
            
            # Convert string lists back to actual lists
            if "selected_markets" in preferences and preferences["selected_markets"]:
                preferences["selected_markets"] = preferences["selected_markets"].split(",")
            
            if "trading_pairs" in preferences and preferences["trading_pairs"]:
                preferences["trading_pairs"] = preferences["trading_pairs"].split(",")
            
            conn.close()
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    def update_pending_trades(self):
        """
        Update all pending trades at end of day
        
        Returns:
            int: Number of trades updated
        """
        try:
            # Get all pending trades
            pending_trades = self.get_pending_trades()
            
            if not pending_trades:
                logger.info("No pending trades to update")
                return 0
            
            updated_count = 0
            
            # Update each trade
            for trade in pending_trades:
                # Here you would get the current price from your data provider
                # For now, we'll use a dummy value
                current_price = trade["entry_price"]  # Placeholder
                
                # Update trade status
                success = self.update_trade_status(
                    trade["id"],
                    current_price,
                    notes="Automatically updated at end of day"
                )
                
                if success:
                    updated_count += 1
            
            logger.info(f"Updated {updated_count} pending trades")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating pending trades: {e}")
            return 0

    # Add to trading_bot/journal/trade_journal.py

    def get_active_trades(self, user_id=None):
        """
        Get active trades (pending or open)
        
        Args:
            user_id (int, optional): Filter by user ID
            
        Returns:
            list: List of active trades
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE status IN ('pending', 'open')"
            params = []
            
            if user_id is not None:
                # If the trades table has a user_id column
                if self._has_column('trades', 'user_id'):
                    query += " AND user_id = ?"
                    params.append(user_id)
            
            cursor.execute(query, params)
            trades = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error getting active trades: {e}")
            return []
        
    def get_recent_trades(self, user_id=None, limit=10):
        """
        Get recent trades regardless of status
        
        Args:
            user_id (int, optional): Filter by user ID
            limit (int): Maximum number of trades to return
            
        Returns:
            list: List of recent trades
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades"
            params = []
            
            if user_id is not None:
                # If the trades table has a user_id column
                if self._has_column('trades', 'user_id'):
                    query += " WHERE user_id = ?"
                    params.append(user_id)
            
            query += " ORDER BY date_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            trades = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []


    def get_account_statistics(self, user_id=None):
        """
        Get account statistics
        
        Args:
            user_id (int, optional): User ID for filtering trades
            
        Returns:
            dict: Account statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Base query parts
            where_clause = ""
            params = []
            
            # Add user_id filter if provided and column exists
            if user_id is not None and self._has_column('trades', 'user_id'):
                where_clause = " WHERE user_id = ?"
                params.append(user_id)
            
            # Get total completed trades
            completed_query = "SELECT COUNT(*) FROM trades"
            if where_clause:
                completed_query += where_clause + " AND status != 'pending'"
            else:
                completed_query += " WHERE status != 'pending'"
            
            cursor.execute(completed_query, params)
            total_trades = cursor.fetchone()[0]
            
            # Get winning trades
            winning_query = "SELECT COUNT(*) FROM trades"
            if where_clause:
                winning_query += where_clause + " AND status = 'target_reached'"
            else:
                winning_query += " WHERE status = 'target_reached'"
            
            cursor.execute(winning_query, params)
            winning_trades = cursor.fetchone()[0]
            
            # Get total profit/loss
            profit_query = "SELECT SUM(actual_gain) FROM trades"
            if where_clause:
                profit_query += where_clause + " AND status != 'pending'"
            else:
                profit_query += " WHERE status != 'pending'"
            
            cursor.execute(profit_query, params)
            total_profit_loss = cursor.fetchone()[0] or 0
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Get user preferences for account size
            account_size = 10000  # Default
            if user_id is not None:
                prefs = self.get_user_preferences(user_id)
                if prefs:
                    account_size = prefs.get('account_size', 10000)
            
            # Calculate current drawdown (simplified)
            current_drawdown = 0
            if total_profit_loss < 0:
                current_drawdown = abs(total_profit_loss) / account_size * 100
            
            conn.close()
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_profit_loss': total_profit_loss,
                'account_size': account_size,
                'current_drawdown': current_drawdown
            }
            
        except Exception as e:
            logger.error(f"Error getting account statistics: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit_loss': 0,
                'account_size': account_size,
                'current_drawdown': 0
            }


    def _has_column(self, table, column):
        """
        Check if a table has a specific column
        
        Args:
            table (str): Table name
            column (str): Column name
            
        Returns:
            bool: True if column exists, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            conn.close()
            
            return column in columns
            
        except Exception as e:
            logger.error(f"Error checking column existence: {e}")
            return False
