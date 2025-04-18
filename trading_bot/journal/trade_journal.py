"""
Trade journal module for recording and tracking trades
"""

import logging
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import sqlite3
import traceback


logger = logging.getLogger(__name__)

class TradeJournal:
    """Class for recording and tracking trades"""
    
    def __init__(self, db_path=None):
        """Initialize the trade journal"""
        self.db_path = db_path or os.path.join(os.path.expanduser("~"), ".trading_bot", "trades.db")
        
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created directory for database: {db_dir}")
        
        # Create tables if they don't exist
        self._create_tables()
        
        logger.info(f"Trade journal initialized with database at {self.db_path}")

  
                
    def record_trade(self, trade_data, user_id=None):
        """
        Record a new trade in the journal
        
        Args:
            trade_data (dict): Trade data including symbol, direction, entry_price, etc.
            user_id (int, optional): User ID
            
        Returns:
            str: Trade ID
        """
        try:
            # Generate a unique trade ID if not provided
            if 'id' not in trade_data:
                from uuid import uuid4
                trade_data['id'] = str(uuid4())
                
            # Set user ID if provided
            if user_id and 'user_id' not in trade_data:
                trade_data['user_id'] = user_id
                
            # Calculate position size if not provided
            if 'position_size' not in trade_data and 'user_id' in trade_data:
                try:
                    position_info = self.calculate_position_size(
                        user_id=trade_data['user_id'],
                        symbol=trade_data['symbol'],
                        entry_price=trade_data['entry_price'],
                        stop_loss=trade_data['stop_loss']
                    )
                    trade_data['position_size'] = position_info.get('position_size', 0)
                    trade_data['risk_amount'] = position_info.get('risk_amount', 0)
                except Exception as e:
                    logger.warning(f"Error calculating position size: {e}. Using defaults.")
                    trade_data['position_size'] = 0.01  # Default position size
                    trade_data['risk_amount'] = 0      # Default risk amount
                
            # Set default values for missing fields
            now = datetime.now().isoformat()
            
            # Basic trade properties
            trade_data.setdefault('status', 'pending')
            trade_data.setdefault('entry_time', now)
            trade_data.setdefault('outcome', None)
            trade_data.setdefault('exit_time', None)
            trade_data.setdefault('exit_price', None)
            trade_data.setdefault('profit_loss', 0)
            trade_data.setdefault('profit_loss_pips', 0)
            trade_data.setdefault('created_at', now)
            trade_data.setdefault('updated_at', now)
            
            # User and trade details
            trade_data.setdefault('user_id', 0)
            trade_data.setdefault('symbol', '')
            trade_data.setdefault('timeframe', '')
            trade_data.setdefault('direction', '')
            
            # Price levels
            trade_data.setdefault('entry_price', 0.0)
            trade_data.setdefault('stop_loss', 0.0)
            trade_data.setdefault('take_profit', 0.0)
            
            # Risk and performance metrics
            trade_data.setdefault('risk_percentage', 1.0)
            trade_data.setdefault('pnl', 0.0)
            trade_data.setdefault('pnl_percentage', 0.0)
            
            # Notes and analysis
            trade_data.setdefault('reason', '')
            trade_data.setdefault('notes', '')
            
            # Calculate risk-reward ratio if not provided
            if 'risk_reward' not in trade_data and trade_data['entry_price'] > 0 and trade_data['stop_loss'] > 0 and trade_data['take_profit'] > 0:
                try:
                    if trade_data['direction'] == 'BUY':
                        risk = abs(trade_data['entry_price'] - trade_data['stop_loss'])
                        reward = abs(trade_data['take_profit'] - trade_data['entry_price'])
                    else:  # SELL
                        risk = abs(trade_data['stop_loss'] - trade_data['entry_price'])
                        reward = abs(trade_data['entry_price'] - trade_data['take_profit'])
                    
                    trade_data['risk_reward'] = reward / risk if risk > 0 else 0
                except Exception as e:
                    logger.warning(f"Error calculating risk-reward ratio: {e}. Using default.")
                    trade_data['risk_reward'] = 0
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get column names from the trades table
            cursor.execute("PRAGMA table_info(trades)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Filter trade_data to include only valid columns
            filtered_data = {k: v for k, v in trade_data.items() if k in columns}
            
            # Prepare SQL statement
            placeholders = ', '.join(['?'] * len(filtered_data))
            columns_str = ', '.join(filtered_data.keys())
            values = list(filtered_data.values())
            
            # Execute the insert
            cursor.execute(f"INSERT INTO trades ({columns_str}) VALUES ({placeholders})", values)
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded new trade: {trade_data['id']} - {trade_data['symbol']} {trade_data['direction']}")
            return trade_data['id']
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}", exc_info=True)
            return None


    def update_trade_status(self, trade_id, status, exit_price=None, exit_time=None, notes=None):
        """
        Update the status of an existing trade
        
        Args:
            trade_id (str): Trade ID
            status (str): New status (active, closed, cancelled)
            exit_price (float, optional): Exit price if closed
            exit_time (str, optional): Exit time if closed
            notes (str, optional): Additional notes
            
        Returns:
            bool: Success or failure
        """
        try:
            # Get current trade data
            trade = self.get_trade(trade_id)
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Update trade data
            now = datetime.now().isoformat()
            updates = {'status': status, 'updated_at': now}
            
            if exit_price is not None:
                updates['exit_price'] = exit_price
            
            if exit_time is not None:
                updates['exit_time'] = exit_time
            else:
                if status == 'closed':
                    updates['exit_time'] = now
            
            if notes is not None:
                updates['notes'] = notes
            
            # Calculate PnL if closed
            if status == 'closed' and exit_price is not None:
                entry_price = trade['entry_price']
                direction = trade['direction']
                position_size = trade['position_size']
                
                if direction == 'BUY':
                    pnl = (exit_price - entry_price) * position_size
                else:  # SELL
                    pnl = (entry_price - exit_price) * position_size
                
                # Calculate PnL percentage
                risk_amount = trade['risk_percentage'] * position_size / 100
                if risk_amount > 0:
                    pnl_percentage = (pnl / risk_amount) * 100
                else:
                    pnl_percentage = 0
                
                updates['pnl'] = pnl
                updates['pnl_percentage'] = pnl_percentage
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build the SQL query dynamically
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(trade_id)
            
            cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = ?", values)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated trade {trade_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trade status: {e}")
            return False
    
    def get_trade(self, trade_id):
        """
        Get a specific trade by ID
        
        Args:
            trade_id (str): Trade ID
            
        Returns:
            dict: Trade data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return dict(row)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting trade: {e}")
            return None
    
    def get_trades(self, user_id=None, status=None, symbol=None, start_date=None, end_date=None, limit=100):
        """
        Get trades with optional filtering
        
        Args:
            user_id (int, optional): Filter by user ID
            status (str, optional): Filter by status
            symbol (str, optional): Filter by symbol
            start_date (str, optional): Filter by start date
            end_date (str, optional): Filter by end date
            limit (int, optional): Limit number of results
            
        Returns:
            list: List of trade dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if status is not None:
                query += " AND status = ?"
                params.append(status)
            
            if symbol is not None:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if start_date is not None:
                query += " AND entry_time >= ?"
                params.append(start_date)
            
            if end_date is not None:
                query += " AND entry_time <= ?"
                params.append(end_date)
            
            query += " ORDER BY entry_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_active_trades(self, user_id=None):
        """
        Get active trades (pending or active status)
        
        Args:
            user_id (int, optional): Filter by user ID
            
        Returns:
            list: List of active trade dictionaries
        """
        return self.get_trades(
            user_id=user_id,
            status="active",
            limit=100
        ) + self.get_trades(
            user_id=user_id,
            status="pending",
            limit=100
        )
    
    def get_closed_trades(self, user_id=None, start_date=None, end_date=None, limit=100):
        """
        Get closed trades
        
        Args:
            user_id (int, optional): Filter by user ID
            start_date (str, optional): Filter by start date
            end_date (str, optional): Filter by end date
            limit (int, optional): Limit number of results
            
        Returns:
            list: List of closed trade dictionaries
        """
        return self.get_trades(
            user_id=user_id,
            status="closed",
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    def calculate_performance_metrics(self, user_id=None, start_date=None, end_date=None):
        """
        Calculate performance metrics for the trading account
        
        Args:
            user_id (int, optional): Filter by user ID
            start_date (str, optional): Filter by start date
            end_date (str, optional): Filter by end date
            
        Returns:
            dict: Performance metrics
        """
        try:
            # Get closed trades
            trades = self.get_closed_trades(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Get a large number for accurate metrics
            )
            
            if not trades:
                return {
                    'win_count': 0,
                    'loss_count': 0,
                    'win_rate': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'profit_factor': 0,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'trade_count': 0,
                    'total_trades': 0,  # Add this for Telegram bot
                    'net_profit': 0     # Add this for Telegram bot
                }
            
            # Calculate metrics
            win_trades = [t for t in trades if t['pnl'] > 0]
            loss_trades = [t for t in trades if t['pnl'] <= 0]
            
            win_count = len(win_trades)
            loss_count = len(loss_trades)
            trade_count = len(trades)
            
            win_rate = (win_count / trade_count) * 100 if trade_count > 0 else 0
            
            avg_win = sum([t['pnl'] for t in win_trades]) / win_count if win_count > 0 else 0
            avg_loss = sum([t['pnl'] for t in loss_trades]) / loss_count if loss_count > 0 else 0
            
            total_profit = sum([t['pnl'] for t in win_trades])
            total_loss = abs(sum([t['pnl'] for t in loss_trades]))
            
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            total_pnl = sum([t['pnl'] for t in trades])
            total_pnl_percentage = sum([t['pnl_percentage'] for t in trades])
            
            # Create metrics dictionary
            metrics = {
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'total_pnl': total_pnl,
                'total_pnl_percentage': total_pnl_percentage,
                'trade_count': trade_count,
                'total_trades': trade_count,  # Add this for Telegram bot
                'net_profit': total_pnl       # Add this for Telegram bot
            }
            
            # Save metrics to database
            self._save_trade_statistics(user_id, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            # Return a default dictionary with all required keys
            return {
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'total_pnl_percentage': 0,
                'trade_count': 0,
                'total_trades': 0,
                'net_profit': 0
            }

    
    def _save_trade_statistics(self, user_id, metrics):
        """
        Save trade statistics to database
        
        Args:
            user_id (int): User ID
            metrics (dict): Performance metrics
        """
        try:
            now = datetime.now()
            date = now.strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO trade_statistics (
                user_id, date, win_count, loss_count, win_rate, avg_win, avg_loss,
                profit_factor, total_pnl, total_pnl_percentage, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, date, metrics['win_count'], metrics['loss_count'],
                metrics['win_rate'], metrics['avg_win'], metrics['avg_loss'],
                metrics['profit_factor'], metrics['total_pnl'], metrics['total_pnl_percentage'],
                now.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving trade statistics: {e}")
    
    def get_performance_history(self, user_id=None, days=30):
        """
        Get performance history for charting
        
        Args:
            user_id (int, optional): Filter by user ID
            days (int, optional): Number of days to include
            
        Returns:
            dict: Performance history data
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get trades in date range
            trades = self.get_closed_trades(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                limit=1000
            )
            
            if not trades:
                return {
                    'dates': [],
                    'pnl': [],
                    'cumulative_pnl': [],
                    'win_rate': []
                }
            
            # Group trades by date
            trade_dates = {}
            for trade in trades:
                date = trade['exit_time'].split('T')[0]  # Extract date part
                if date not in trade_dates:
                    trade_dates[date] = []
                trade_dates[date].append(trade)
            
            # Calculate daily metrics
            dates = []
            daily_pnl = []
            cumulative_pnl = []
            win_rates = []
            
            running_pnl = 0
            running_wins = 0
            running_trades = 0
            
            # Generate all dates in range
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                dates.append(date_str)
                
                # Get trades for this date
                day_trades = trade_dates.get(date_str, [])
                
                # Calculate daily PnL
                day_pnl = sum([t['pnl'] for t in day_trades])
                daily_pnl.append(day_pnl)
                
                # Update running totals
                running_pnl += day_pnl
                cumulative_pnl.append(running_pnl)
                
                # Calculate win rate
                day_wins = len([t for t in day_trades if t['pnl'] > 0])
                running_wins += day_wins
                running_trades += len(day_trades)
                
                if running_trades > 0:
                    win_rate = (running_wins / running_trades) * 100
                else:
                    win_rate = 0
                
                win_rates.append(win_rate)
                
                # Move to next day
                current_date += timedelta(days=1)
            
            return {
                'dates': dates,
                'pnl': daily_pnl,
                'cumulative_pnl': cumulative_pnl,
                'win_rate': win_rates
            }
            
        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            return None
    
    def get_pending_trades(self):
        """
        Get all pending trades from the journal
        
        Returns:
            list: List of pending trades
        """
        # This is a wrapper around check_pending_trades for compatibility
        return self.check_pending_trades()

    def check_pending_trades(self):
        """
        Check for pending trades in the journal
        
        Returns:
            list: List of pending trades
        """
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query for pending trades
            cursor.execute(
                "SELECT * FROM trades WHERE status IN ('pending', 'open')"
            )
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            trades = []
            for row in rows:
                trade = {
                    'id': row[0],
                    'user_id': row[1],
                    'symbol': row[2],
                    'direction': row[3],
                    'entry_price': row[4],
                    'stop_loss': row[5],
                    'take_profit': row[6],
                    'status': row[7],
                    'entry_time': row[8],
                    'exit_time': row[9],
                    'profit_loss': row[10],
                    'notes': row[11],
                    'date': row[12]
                }
                trades.append(trade)
            
            # Close the connection
            conn.close()
            
            return trades
        except Exception as e:
            logger.error(f"Error checking pending trades: {e}")
            return []    
        
    def update_active_trades(self, data_processor):
        """
        Update active trades with current prices
        
        Args:
            data_processor: Data processor instance for getting current prices
            
        Returns:
            dict: Summary of updates
        """
        try:
            # Get all active trades
            active_trades = self.get_trades(status="active")
            
            if not active_trades:
                return {'closed': 0, 'updated': 0, 'total': 0}
            
            # Initialize counters
            closed = 0
            updated = 0
            
            # Process each active trade
            for trade in active_trades:
                trade_id = trade['id']
                symbol = trade['symbol']
                direction = trade['direction']
                entry_price = trade['entry_price']
                stop_loss = trade['stop_loss']
                take_profit = trade['take_profit']
                
                # Get current price
                current_price = data_processor.get_latest_price(symbol)
                
                if current_price is None:
                    logger.warning(f"Could not get current price for {symbol}")
                    continue
                
                # Check if stop loss or take profit hit
                if direction == 'BUY':
                    if current_price <= stop_loss:
                        # Stop loss hit
                        self.update_trade_status(
                            trade_id,
                            'closed',
                            exit_price=stop_loss,
                            notes='Closed at stop loss'
                        )
                        closed += 1
                    elif current_price >= take_profit:
                        # Take profit hit
                        self.update_trade_status(
                            trade_id,
                            'closed',
                            exit_price=take_profit,
                            notes='Closed at take profit'
                        )
                        closed += 1
                    else:
                        # Still active
                        updated += 1
                else:  # SELL
                    if current_price >= stop_loss:
                        # Stop loss hit
                        self.update_trade_status(
                            trade_id,
                            'closed',
                            exit_price=stop_loss,
                            notes='Closed at stop loss'
                        )
                        closed += 1
                    elif current_price <= take_profit:
                        # Take profit hit
                        self.update_trade_status(
                            trade_id,
                            'closed',
                            exit_price=take_profit,
                            notes='Closed at take profit'
                        )
                        closed += 1
                    else:
                        # Still active
                        updated += 1
            
            return {
                'closed': closed,
                'updated': updated,
                'total': len(active_trades)
            }
            
        except Exception as e:
            logger.error(f"Error updating active trades: {e}")
            return None
    
    def export_trades_to_csv(self, filepath=None, user_id=None):
        """
        Export trades to CSV file
        
        Args:
            filepath (str, optional): Path to save CSV file
            user_id (int, optional): Filter by user ID
            
        Returns:
            str: Path to CSV file
        """
        try:
            # Get all trades
            trades = self.get_trades(user_id=user_id, limit=1000)
            
            if not trades:
                logger.warning("No trades to export")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Generate filepath if not provided
            if filepath is None:
                now = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f"data/exports/trades_{now}.csv"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export to CSV
            df.to_csv(filepath, index=False)
            
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {e}")
            return None
    
    def export_trades_to_json(self, filepath=None, user_id=None):
        """
        Export trades to JSON file
        
        Args:
            filepath (str, optional): Path to save JSON file
            user_id (int, optional): Filter by user ID
            
        Returns:
            str: Path to JSON file
        """
        try:
            # Get all trades
            trades = self.get_trades(user_id=user_id, limit=1000)
            
            if not trades:
                logger.warning("No trades to export")
                return None
            
            # Generate filepath if not provided
            if filepath is None:
                now = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f"data/exports/trades_{now}.json"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export to JSON
            with open(filepath, 'w') as f:
                json.dump(trades, f, indent=2)
            
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting trades to JSON: {e}")
            return None

    def set_account_info(self, user_id, account_size, risk_per_trade, max_daily_risk=None, preferred_markets=None, preferred_timeframes=None):
        """
        Set or update account information
        
        Args:
            user_id (int): User ID
            account_size (float): Account size in base currency
            risk_per_trade (float): Risk percentage per trade
            max_daily_risk (float, optional): Maximum daily risk percentage
            preferred_markets (list, optional): List of preferred markets
            preferred_timeframes (list, optional): List of preferred timeframes
            
        Returns:
            bool: Success or failure
        """
        try:
            now = datetime.now().isoformat()
            
            # Convert lists to JSON strings
            if preferred_markets:
                preferred_markets = json.dumps(preferred_markets)
            
            if preferred_timeframes:
                preferred_timeframes = json.dumps(preferred_timeframes)
            
            # Check if user already exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing user
                cursor.execute('''
                UPDATE user_preferences SET
                    account_size = ?,
                    risk_per_trade = ?,
                    max_daily_risk = ?,
                    preferred_markets = ?,
                    preferred_timeframes = ?,
                    updated_at = ?
                WHERE user_id = ?
                ''', (
                    account_size,
                    risk_per_trade,
                    max_daily_risk or risk_per_trade * 3,  # Default to 3x risk per trade
                    preferred_markets,
                    preferred_timeframes,
                    now,
                    user_id
                ))
            else:
                # Insert new user
                cursor.execute('''
                INSERT INTO user_preferences (
                    user_id, account_size, risk_per_trade, max_daily_risk,
                    preferred_markets, preferred_timeframes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    account_size,
                    risk_per_trade,
                    max_daily_risk or risk_per_trade * 3,  # Default to 3x risk per trade
                    preferred_markets,
                    preferred_timeframes,
                    now,
                    now
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Account information set for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting account information: {e}")
            return False

    def get_account_info(self, user_id):
        """
        Get account information for a user
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Account information or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                account_info = dict(row)
                
                # Parse JSON strings back to lists
                if account_info.get('preferred_markets'):
                    try:
                        account_info['preferred_markets'] = json.loads(account_info['preferred_markets'])
                    except:
                        account_info['preferred_markets'] = []
                
                if account_info.get('preferred_timeframes'):
                    try:
                        account_info['preferred_timeframes'] = json.loads(account_info['preferred_timeframes'])
                    except:
                        account_info['preferred_timeframes'] = []
                
                return account_info
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting account information: {e}")
            return None

    def calculate_position_size(self, user_id: int, symbol: str, entry_price: float, stop_loss: float) -> dict:
        """
        Calculate position size based on account information and trade parameters
        
        Args:
            user_id (int): User ID
            symbol (str): Trading symbol
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            
        Returns:
            dict: Position sizing information
        """
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get account information
            cursor.execute("SELECT account_size, risk_percentage FROM account_info WHERE user_id = ?", (user_id,))
            account_info = cursor.fetchone()
            
            if not account_info:
                # Use default values if no account info found
                account_size = 10000.0
                risk_percentage = 1.0
            else:
                account_size = account_info[0]
                risk_percentage = account_info[1]
            
            # Calculate risk amount
            risk_amount = account_size * (risk_percentage / 100)
            
            # Calculate risk in price
            risk_price = abs(entry_price - stop_loss)
            
            # Calculate position size
            position_size = risk_amount / risk_price if risk_price > 0 else 0
            
            # Adjust position size based on symbol
            if 'JPY' in symbol:
                # For JPY pairs, divide by 100
                position_size = position_size / 100
            elif symbol in ['XAUUSD', 'GOLD']:
                # For gold, divide by 10
                position_size = position_size / 10
            elif 'BTC' in symbol:
                # For Bitcoin, divide by 1000
                position_size = position_size / 1000
            
            return {
                'account_size': account_size,
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'risk_price': risk_price,
                'position_size': position_size
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'account_size': 10000.0,
                'risk_percentage': 1.0,
                'risk_amount': 100.0,
                'risk_price': abs(entry_price - stop_loss),
                'position_size': 0
            }
        finally:
            if conn:
                conn.close()


    def _calculate_pip_value(self, symbol, price):
        """
        Calculate pip value for a symbol using account currency (USD)
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            
        Returns:
            float: Pip value in account currency (USD)
        """
        standard_lot = 100000  # Standard lot size
        
        # For pairs where USD is the quote currency (e.g., EUR/USD, GBP/USD)
        if 'USD' in symbol and symbol.index('USD') > 0:
            return 0.0001 * standard_lot  # $10 per pip for 1 standard lot
            
        # For pairs where USD is the base currency (e.g., USD/JPY, USD/CAD)
        elif 'USD' in symbol and symbol.index('USD') == 0:
            pip_value = (0.01 * standard_lot) / price  # Convert to USD based on current price
            return pip_value
            
        # For pairs where USD is neither (e.g., EUR/GBP)
        elif 'USD' not in symbol:
            # Get the USD exchange rate for the quote currency
            quote_currency = symbol[3:]
            usd_quote_rate = self._get_usd_exchange_rate(quote_currency)
            pip_value = (0.0001 * standard_lot * usd_quote_rate)
            return pip_value
            
        # For XAU/USD (Gold)
        elif symbol in ['XAUUSD', 'GOLD']:
            return 1.0  # $1 per point for 1 oz
            
        # For XAG/USD (Silver)
        elif symbol in ['XAGUSD', 'SILVER']:
            return 0.5  # $0.50 per point for 1 oz
            
        # Default fallback
        return 0.0001 * standard_lot
        
    def _get_usd_exchange_rate(self, currency):
        """
        Get the USD exchange rate for a given currency using cTrader rates
        This method should be implemented to fetch real-time rates from cTrader
        """
        try:
            # TODO: Implement actual cTrader API call to get exchange rate
            # Example: return cTrader.get_exchange_rate(f"{currency}USD")
            return 1.0  # Default to 1.0 until cTrader implementation
        except Exception as e:
            logger.error(f"Error getting exchange rate for {currency}: {e}")
            return 1.0
    
    def update_account_balance(self, user_id, profit_loss):
        """
        Update account balance after a trade
        
        Args:
            user_id (int): User ID
            profit_loss (float): Profit or loss amount
            
        Returns:
            float: New account balance
        """
        try:
            # Get current account info
            account_info = self.get_account_info(user_id)
            
            if not account_info:
                return None
            
            # Update account size
            new_balance = account_info['account_size'] + profit_loss
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE user_preferences SET
                account_size = ?,
                updated_at = ?
            WHERE user_id = ?
            ''', (
                new_balance,
                datetime.now().isoformat(),
                user_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated account balance for user {user_id}: {account_info['account_size']} -> {new_balance}")
            
            return new_balance
            
        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
            return None

    def update_trade(self, trade_id, update_data):
        """
        Update an existing trade in the journal
        
        Args:
            trade_id (str): Trade ID
            update_data (dict): Data to update
            
        Returns:
            bool: Success or failure
        """
        try:
            # Validate trade ID
            if not trade_id:
                logger.error("No trade ID provided for update")
                return False
            
            # Get current trade data
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            trade = cursor.fetchone()
            
            if not trade:
                logger.error(f"Trade not found: {trade_id}")
                conn.close()
                return False
            
            # Convert to dict
            trade_data = dict(trade)
            
            # Update with new data
            update_data['updated_at'] = datetime.now().isoformat()
            
            # If status is changing to 'closed', calculate profit/loss
            if 'status' in update_data and update_data['status'] == 'closed' and trade_data['status'] != 'closed':
                # Ensure we have exit price
                if 'exit_price' not in update_data and not trade_data['exit_price']:
                    logger.error(f"Cannot close trade {trade_id} without exit price")
                    conn.close()
                    return False
                
                exit_price = update_data.get('exit_price', trade_data['exit_price'])
                
                # Calculate profit/loss
                position_size = trade_data['position_size'] or 0
                
                if trade_data['direction'] == 'BUY':
                    profit_loss = position_size * (exit_price - trade_data['entry_price'])
                    # Calculate pips (adjust multiplier based on pair)
                    if 'JPY' in trade_data['symbol']:
                        pip_multiplier = 100
                    elif any(metal in trade_data['symbol'] for metal in ['XAU', 'GOLD']):
                        pip_multiplier = 10
                    else:
                        pip_multiplier = 10000
                    profit_loss_pips = (exit_price - trade_data['entry_price']) * pip_multiplier
                else:  # SELL
                    profit_loss = position_size * (trade_data['entry_price'] - exit_price)
                    # Calculate pips (adjust multiplier based on pair)
                    if 'JPY' in trade_data['symbol']:
                        pip_multiplier = 100
                    elif any(metal in trade_data['symbol'] for metal in ['XAU', 'GOLD']):
                        pip_multiplier = 10
                    else:
                        pip_multiplier = 10000
                    profit_loss_pips = (trade_data['entry_price'] - exit_price) * pip_multiplier
                
                # Determine outcome
                outcome = 'win' if profit_loss > 0 else 'loss' if profit_loss < 0 else 'breakeven'
                
                # Add to update data
                update_data['profit_loss'] = profit_loss
                update_data['profit_loss_pips'] = profit_loss_pips
                update_data['outcome'] = outcome
                update_data['exit_time'] = update_data.get('exit_time', datetime.now().isoformat())
                
                # Update account balance if user_id is available
                if trade_data['user_id']:
                    self.update_account_balance(trade_data['user_id'], profit_loss)
                    
                    # Record performance metrics
                    self._record_daily_performance(trade_data['user_id'])
            
            # Prepare SQL update statement
            set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values()) + [trade_id]
            
            cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = ?", values)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated trade: {trade_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return False

    def _record_daily_performance(self, user_id):
        """
        Record daily performance metrics
        
        Args:
            user_id (int): User ID
        """
        try:
            # Get today's date
            today = datetime.now().date().isoformat()
            
            # Get account info
            account_info = self.get_account_info(user_id)
            if not account_info:
                return
            
            # Get today's trades
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we already have metrics for today
            cursor.execute(
                "SELECT id FROM performance_metrics WHERE user_id = ? AND date = ?",
                (user_id, today)
            )
            existing = cursor.fetchone()
            
            # Get trade metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losing_trades,
                    SUM(profit_loss) as net_profit
                FROM trades
                WHERE user_id = ? AND status = 'closed' AND date(exit_time) = ?
            """, (user_id, today))
            
            metrics = cursor.fetchone()
            
            if metrics:
                total_trades = metrics[0] or 0
                winning_trades = metrics[1] or 0
                losing_trades = metrics[2] or 0
                net_profit = metrics[3] or 0
                
                # Calculate derived metrics
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                
                # Get total gains and losses for profit factor
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN profit_loss > 0 THEN profit_loss ELSE 0 END) as total_gains,
                        SUM(CASE WHEN profit_loss < 0 THEN ABS(profit_loss) ELSE 0 END) as total_losses
                    FROM trades
                    WHERE user_id = ? AND status = 'closed' AND date(exit_time) = ?
                """, (user_id, today))
                
                pf_metrics = cursor.fetchone()
                total_gains = pf_metrics[0] or 0
                total_losses = pf_metrics[1] or 0
                
                profit_factor = total_gains / total_losses if total_losses > 0 else (1 if total_gains > 0 else 0)
                
                # Current account balance
                account_balance = account_info['account_size']
                
                # Insert or update metrics
                now = datetime.now().isoformat()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE performance_metrics SET
                            total_trades = ?,
                            winning_trades = ?,
                            losing_trades = ?,
                            win_rate = ?,
                            profit_factor = ?,
                            net_profit = ?,
                            account_balance = ?,
                            created_at = ?
                        WHERE id = ?
                    """, (
                        total_trades,
                        winning_trades,
                        losing_trades,
                        win_rate,
                        profit_factor,
                        net_profit,
                        account_balance,
                        now,
                        existing[0]
                    ))
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO performance_metrics (
                            user_id, date, total_trades, winning_trades, losing_trades,
                            win_rate, profit_factor, net_profit, account_balance, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        today,
                        total_trades,
                        winning_trades,
                        losing_trades,
                        win_rate,
                        profit_factor,
                        net_profit,
                        account_balance,
                        now
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording daily performance: {e}")


    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        conn = None  # Initialize conn to None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table with all fields from both versions
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                risk_reward REAL,
                position_size REAL,
                risk_amount REAL,
                status TEXT,
                entry_time TEXT,
                exit_time TEXT,
                exit_price REAL,
                profit_loss REAL,
                profit_loss_pips REAL,
                outcome TEXT,
                entry_reason TEXT,
                exit_reason TEXT,
                market_conditions TEXT,
                timeframe TEXT,
                reason TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            ''')
            
            # Create user_preferences table (from first version)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                account_size REAL,
                risk_per_trade REAL,
                max_daily_risk REAL,
                preferred_markets TEXT,
                preferred_timeframes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            ''')
            
            # Create performance_metrics table (from first version)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                net_profit REAL,
                account_balance REAL,
                created_at TEXT
            )
            ''')
            
            # Create account_info table (from second version)
            # Note: This might be redundant with user_preferences, but keeping for compatibility
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_info (
                user_id INTEGER PRIMARY KEY,
                account_size REAL,
                risk_percentage REAL,
                created_at TEXT,
                updated_at TEXT
            )
            ''')
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
        finally:
            if conn:
                conn.close()





