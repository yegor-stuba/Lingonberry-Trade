"""
Journal analytics and statistics
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import logging
from datetime import datetime, timedelta

from trading_bot.config import settings
from trading_bot.journal.trade_journal import TradeJournal
from trading_bot.utils import helpers

logger = logging.getLogger(__name__)

class JournalAnalytics:
    """Class for analyzing trading journal data"""
    
    def __init__(self, journal=None):
        """Initialize the analytics module"""
        self.journal = journal or TradeJournal()
    
    def get_performance_summary(self):
        """
        Get performance summary statistics
        
        Returns:
            dict: Performance statistics
        """
        return self.journal.get_trade_statistics()
    
    def get_trades_as_dataframe(self, limit=100):
        """
        Get trades as a pandas DataFrame for analysis
        
        Returns:
            pandas.DataFrame: DataFrame with trade data
        """
        try:
            trades = self.journal.get_trades(limit=limit)
            
            if not trades:
                return pd.DataFrame()
            
            df = pd.DataFrame(trades)
            
            # Convert date_time to datetime
            df['date_time'] = pd.to_datetime(df['date_time'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error converting trades to DataFrame: {e}")
            return pd.DataFrame()
    
    def generate_equity_curve(self):
        """
        Generate equity curve chart
        
        Returns:
            bytes: PNG image data
        """
        try:
            df = self.get_trades_as_dataframe()
            
            if df.empty:
                logger.warning("No trade data available for equity curve")
                return None
            
            # Sort by date
            df = df.sort_values('date_time')
            
            # Calculate cumulative return
            df['cumulative_return'] = df['actual_gain'].cumsum()
            
            # Create the plot
            plt.figure(figsize=settings.CHART_SIZE, dpi=settings.CHART_DPI)
            plt.style.use(settings.CHART_STYLE)
            
            plt.plot(df['date_time'], df['cumulative_return'], 'g-', linewidth=2)
            plt.title('Equity Curve')
            plt.xlabel('Date')
            plt.ylabel('Cumulative Return (%)')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.gcf().autofmt_xdate()
            
            # Add horizontal line at y=0
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating equity curve: {e}")
            return None
    
    def generate_win_loss_chart(self):
        """
        Generate win/loss pie chart
        
        Returns:
            bytes: PNG image data
        """
        try:
            stats = self.get_performance_summary()
            
            if not stats or stats.get('total_trades', 0) == 0:
                logger.warning("No trade data available for win/loss chart")
                return None
            
            # Calculate values
            total_trades = stats['total_trades']
            win_rate = stats['win_rate']
            loss_rate = 100 - win_rate
            
            # Create the plot
            plt.figure(figsize=(8, 8), dpi=settings.CHART_DPI)
            plt.style.use(settings.CHART_STYLE)
            
            # Create pie chart
            labels = ['Wins', 'Losses']
            sizes = [win_rate, loss_rate]
            colors = ['green', 'red']
            explode = (0.1, 0)  # explode the 1st slice (Wins)
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=90)
            plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            plt.title(f'Win/Loss Distribution (Total Trades: {total_trades})')
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating win/loss chart: {e}")
            return None
    
    def generate_pair_performance_chart(self):
        """
        Generate chart showing performance by trading pair
        
        Returns:
            bytes: PNG image data
        """
        try:
            df = self.get_trades_as_dataframe()
            
            if df.empty:
                logger.warning("No trade data available for pair performance chart")
                return None
            
            # Group by symbol and calculate statistics
            pair_stats = df.groupby('symbol').agg({
                'actual_gain': ['sum', 'mean', 'count'],
                'id': 'count'  # Total trades per pair
            })
            
            # Flatten the multi-index columns
            pair_stats.columns = ['total_gain', 'avg_gain', 'gain_count', 'trade_count']
            pair_stats = pair_stats.reset_index()
            
            # Sort by total gain
            pair_stats = pair_stats.sort_values('total_gain', ascending=False)
            
            # Take top 10 pairs by trade count
            top_pairs = pair_stats.nlargest(10, 'trade_count')
            
            # Create the plot
            plt.figure(figsize=(12, 8), dpi=settings.CHART_DPI)
            plt.style.use(settings.CHART_STYLE)
            
            # Create bar chart
            bars = plt.bar(top_pairs['symbol'], top_pairs['total_gain'], color='skyblue')
            
            # Color bars based on gain (green for positive, red for negative)
            for i, bar in enumerate(bars):
                if top_pairs.iloc[i]['total_gain'] < 0:
                    bar.set_color('red')
                else:
                    bar.set_color('green')
            
            plt.title('Performance by Trading Pair')
            plt.xlabel('Trading Pair')
            plt.ylabel('Total Gain (%)')
            plt.grid(True, alpha=0.3, axis='y')
            
            # Add trade count as text on top of bars
            for i, bar in enumerate(bars):
                count = top_pairs.iloc[i]['trade_count']
                plt.text(bar.get_x() + bar.get_width()/2, 
                         bar.get_height() + (1 if bar.get_height() >= 0 else -3),
                         f'{count} trades', 
                         ha='center', va='bottom', rotation=0)
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating pair performance chart: {e}")
            return None
    
    def generate_monthly_performance_chart(self):
        """
        Generate chart showing monthly performance
        
        Returns:
            bytes: PNG image data
        """
        try:
            df = self.get_trades_as_dataframe()
            
            if df.empty:
                logger.warning("No trade data available for monthly performance chart")
                return None
            
            # Extract month from date_time
            df['month'] = df['date_time'].dt.to_period('M')
            
            # Group by month and calculate sum of gains
            monthly_performance = df.groupby('month')['actual_gain'].sum().reset_index()
            monthly_performance['month_str'] = monthly_performance['month'].dt.strftime('%Y-%m')
            
            # Create the plot
            plt.figure(figsize=(12, 6), dpi=settings.CHART_DPI)
            plt.style.use(settings.CHART_STYLE)
            
            # Create bar chart
            bars = plt.bar(monthly_performance['month_str'], monthly_performance['actual_gain'], color='skyblue')
            
            # Color bars based on gain (green for positive, red for negative)
            for i, bar in enumerate(bars):
                if monthly_performance.iloc[i]['actual_gain'] < 0:
                    bar.set_color('red')
                else:
                    bar.set_color('green')
            
            plt.title('Monthly Performance')
            plt.xlabel('Month')
            plt.ylabel('Total Gain (%)')
            plt.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45, ha='right')
            
            # Add horizontal line at y=0
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            
            plt.tight_layout()
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating monthly performance chart: {e}")
            return None
    
    def generate_performance_report(self):
        """
        Generate a comprehensive performance report with multiple charts
        
        Returns:
            dict: Dictionary with report data and charts
        """
        try:
            stats = self.get_performance_summary()
            
            # Generate charts
            equity_curve = self.generate_equity_curve()
            win_loss_chart = self.generate_win_loss_chart()
            pair_performance = self.generate_pair_performance_chart()
            monthly_performance = self.generate_monthly_performance_chart()
            
            report = {
                "statistics": stats,
                "charts": {
                    "equity_curve": equity_curve,
                    "win_loss": win_loss_chart,
                    "pair_performance": pair_performance,
                    "monthly_performance": monthly_performance
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return None
        


        # Add to trading_bot/journal/analytics.py

    def get_user_statistics(self, user_id):
        """
        Get comprehensive statistics for a user
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: User statistics
        """
        try:
            # Get basic account statistics
            account_stats = self.journal.get_account_statistics(user_id)
            
            # Get all trades for this user
            df = self.get_trades_as_dataframe(limit=1000)
            
            # Filter by user_id if the column exists
            if 'user_id' in df.columns:
                df = df[df['user_id'] == user_id]
            
            if df.empty:
                return account_stats
            
            # Calculate additional statistics
            
            # Average profit/loss
            winning_trades = df[df['actual_gain'] > 0]
            losing_trades = df[df['actual_gain'] < 0]
            
            avg_profit = winning_trades['actual_gain'].mean() if not winning_trades.empty else 0
            avg_loss = losing_trades['actual_gain'].mean() if not losing_trades.empty else 0
            
            # Profit factor
            total_profit = winning_trades['actual_gain'].sum() if not winning_trades.empty else 0
            total_loss = abs(losing_trades['actual_gain'].sum()) if not losing_trades.empty else 0
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Best and worst trades
            best_trade = df.loc[df['actual_gain'].idxmax()].to_dict() if not df.empty else None
            worst_trade = df.loc[df['actual_gain'].idxmin()].to_dict() if not df.empty else None
            
            # Average risk-reward ratio
            avg_rr = df['risk_reward'].mean() if 'risk_reward' in df.columns else 0
            
            # Symbol performance
            symbol_stats = {}
            for symbol, group in df.groupby('symbol'):
                wins = len(group[group['actual_gain'] > 0])
                losses = len(group[group['actual_gain'] < 0])
                total = len(group)
                win_rate = (wins / total * 100) if total > 0 else 0
                
                symbol_stats[symbol] = {
                    'trades': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'profit_loss': group['actual_gain'].sum()
                }
            
            # Monthly performance
            if 'date_time' in df.columns:
                df['month'] = pd.to_datetime(df['date_time']).dt.strftime('%Y-%m')
                monthly_stats = {}
                
                for month, group in df.groupby('month'):
                    wins = len(group[group['actual_gain'] > 0])
                    losses = len(group[group['actual_gain'] < 0])
                    total = len(group)
                    win_rate = (wins / total * 100) if total > 0 else 0
                    
                    monthly_stats[month] = {
                        'trades': total,
                        'wins': wins,
                        'losses': losses,
                        'win_rate': win_rate,
                        'profit_loss': group['actual_gain'].sum()
                    }
            else:
                monthly_stats = {}
            
            # Return enhanced statistics
            return {
                **account_stats,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'avg_risk_reward': avg_rr,
                'symbol_performance': symbol_stats,
                'monthly_performance': monthly_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit_loss': 0,
                'account_size': 10000,
                'current_drawdown': 0,
                'error': str(e)
            }
