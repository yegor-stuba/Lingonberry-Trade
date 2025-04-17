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

logger = logging.getLogger(__name__)

class TradeJournal:
    """Class for recording and tracking trades"""
    
    def __init__(self, db_path=None):
        """Initialize the trade journal"""
        self.db_path = db_path or Path("data/trade_journal.db")
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure the database exists and has the required tables"""
        # Create directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trades table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            symbol TEXT,
            timeframe TEXT,
            direction TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            risk_percentage REAL,
            position_size REAL,
            entry_time TEXT,
            exit_time TEXT,
            exit_price REAL,
            status TEXT,
            pnl REAL,
            pnl_percentage REAL,
            reason TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        # Create user preferences table
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
        
        # Create trade statistics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            win_count INTEGER,
            loss_count INTEGER,
            win_rate REAL,
            avg_win REAL,
            avg_loss REAL,
            profit_factor REAL,
            total_pnl REAL,
            total_pnl_percentage REAL,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Trade journal database initialized at {self.db_path}")
    
    def record_trade(self, trade_data):
        """
        Record a new trade in the journal
        
        Args:
            trade_data (dict): Trade data including symbol, direction, entry, etc.
            
        Returns:
            str: Trade ID
        """
        try:
            # Generate a unique ID for the trade
            trade_id = str(uuid.uuid4())
            
            # Set default values
            now = datetime.now().isoformat()
            
            # Prepare trade data
            trade = {
                'id': trade_id,
                'user_id': trade_data.get('user_id', 0),
                'symbol': trade_data.get('symbol', ''),
                'timeframe': trade_data.get('timeframe', ''),
                'direction': trade_data.get('direction', ''),
                'entry_price': trade_data.get('entry_price', 0.0),
                'stop_loss': trade_data.get('stop_loss', 0.0),
                'take_profit': trade_data.get('take_profit', 0.0),
                'risk_percentage': trade_data.get('risk_percentage', 1.0),
                'position_size': trade_data.get('position_size', 0.0),
                'entry_time': trade_data.get('entry_time', now),
                'exit_time': None,
                'exit_price': None,
                'status': 'pending',  # pending, active, closed, cancelled
                'pnl': 0.0,
                'pnl_percentage': 0.0,
                'reason': trade_data.get('reason', ''),
                'notes': trade_data.get('notes', ''),
                'created_at': now,
                'updated_at': now
            }
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO trades (
                id, user_id, symbol, timeframe, direction, entry_price, stop_loss, take_profit,
                risk_percentage, position_size, entry_time, exit_time, exit_price, status,
                pnl, pnl_percentage, reason, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['id'], trade['user_id'], trade['symbol'], trade['timeframe'],
                trade['direction'], trade['entry_price'], trade['stop_loss'], trade['take_profit'],
                trade['risk_percentage'], trade['position_size'], trade['entry_time'],
                trade['exit_time'], trade['exit_price'], trade['status'],
                trade['pnl'], trade['pnl_percentage'], trade['reason'], trade['notes'],
                trade['created_at'], trade['updated_at']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded new trade {trade_id} for {trade['symbol']}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
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
                    'trade_count': 0
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
                'trade_count': trade_count
            }
            
            # Save metrics to database
            self._save_trade_statistics(user_id, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return None
    
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
    
    def check_pending_trades(self):
        """
        Check pending trades to see if they should be activated or cancelled
        
        Returns:
            dict: Summary of updates
        """
        try:
            # Get all pending trades
            pending_trades = self.get_trades(status="pending")
            
            if not pending_trades:
                return {'activated': 0, 'cancelled': 0, 'total': 0}
            
            # Initialize counters
            activated = 0
            cancelled = 0
            
            # Current time
            now = datetime.now()
            
            # Process each pending trade
            for trade in pending_trades:
                trade_id = trade['id']
                symbol = trade['symbol']
                direction = trade['direction']
                entry_price = trade['entry_price']
                
                # Check if trade is too old (more than 24 hours)
                entry_time = datetime.fromisoformat(trade['entry_time'])
                if (now - entry_time).total_seconds() > 24 * 60 * 60:
                    # Cancel trade
                    self.update_trade_status(
                        trade_id,
                        'cancelled',
                        notes='Cancelled due to timeout (24 hours)'
                    )
                    cancelled += 1
                    continue
                
                # TODO: Check current price to see if trade should be activated
                # This requires integration with your data provider
                # For now, we'll just leave trades pending
                
            return {
                'activated': activated,
                'cancelled': cancelled,
                'total': len(pending_trades)
            }
            
        except Exception as e:
            logger.error(f"Error checking pending trades: {e}")
            return None
    
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
