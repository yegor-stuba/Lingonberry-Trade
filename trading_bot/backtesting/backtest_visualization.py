"""
Visualization utilities for backtesting
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import io
from typing import Dict, List, Optional, Tuple, Union
import logging

from trading_bot.config import settings

logger = logging.getLogger(__name__)

def plot_equity_curve(equity_curve: List[float], trades: Optional[List[Dict]] = None, timestamp: Optional[str] = None) -> io.BytesIO:
    """
    Generate equity curve chart
    
    Args:
        equity_curve (list): List of equity values
        trades (list, optional): List of trade dictionaries
        timestamp (str, optional): Timestamp of when the backtest was performed
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not equity_curve:
            return None
        
        # Create figure
        plt.figure(figsize=(10, 6))
        plt.style.use('grayscale')  # Use grayscale style for black and white
        
        # Plot equity curve
        plt.plot(equity_curve, 'k-', linewidth=2)
        
        # Add trade markers if provided
        if trades:
            for i, trade in enumerate(trades):
                idx = trade.get('exit_index')
                if idx is not None and idx < len(equity_curve):
                    if trade.get('profit', 0) > 0:
                        plt.plot(idx, equity_curve[idx], 'ko', markersize=6)
                    else:
                        plt.plot(idx, equity_curve[idx], 'ko', markerfacecolor='white', markersize=6)
        
        # Add labels and title
        title = 'Equity Curve'
        if timestamp:
            title += f' (Backtest: {timestamp})'
        plt.title(title)
        plt.xlabel('Trade Number')
        plt.ylabel('Account Balance')
        plt.grid(True, alpha=0.3)
        
        # Add horizontal line at initial capital
        plt.axhline(y=equity_curve[0], color='k', linestyle='--', alpha=0.5)
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting equity curve: {e}")
        return None

def plot_drawdown_chart(drawdowns: List[float]) -> io.BytesIO:
    """
    Generate drawdown chart
    
    Args:
        drawdowns (list): List of drawdown values
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not drawdowns:
            return None
        
        # Create figure
        plt.figure(figsize=(10, 6))
        plt.style.use(settings.CHART_STYLE)
        
        # Plot drawdowns
        plt.plot(drawdowns, 'r-', linewidth=2)
        
        # Add labels and title
        plt.title('Drawdown Chart')
        plt.xlabel('Trade Number')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting drawdown chart: {e}")
        return None

def plot_monthly_returns(monthly_returns: Dict[str, float]) -> io.BytesIO:
    """
    Generate monthly returns chart
    
    Args:
        monthly_returns (dict): Dictionary of monthly returns
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not monthly_returns:
            return None
        
        # Sort by date
        sorted_months = sorted(monthly_returns.keys())
        returns = [monthly_returns[month] for month in sorted_months]
        
        # Create figure
        plt.figure(figsize=(12, 6))
        plt.style.use(settings.CHART_STYLE)
        
        # Create bar chart
        bars = plt.bar(sorted_months, returns, alpha=0.7)
        
        # Color bars based on return (green for positive, red for negative)
        for i, bar in enumerate(bars):
            if returns[i] >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        # Add labels and title
        plt.title('Monthly Returns')
        plt.xlabel('Month')
        plt.ylabel('Return')
        plt.grid(True, alpha=0.3, axis='y')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting monthly returns: {e}")
        return None

def plot_trade_distribution(trades: List[Dict]) -> io.BytesIO:
    """
    Generate trade profit distribution chart
    
    Args:
        trades (list): List of trade dictionaries
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not trades:
            return None
        
        # Extract profit values
        profits = [t.get('profit', 0) for t in trades]
        
        # Create figure
        plt.figure(figsize=(10, 6))
        plt.style.use(settings.CHART_STYLE)
        
        # Create histogram
        plt.hist(profits, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        
        # Add labels and title
        plt.title('Trade Profit Distribution')
        plt.xlabel('Profit/Loss')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        # Add vertical line at zero
        plt.axvline(x=0, color='r', linestyle='--', alpha=0.5)
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting trade distribution: {e}")
        return None

def plot_win_loss_chart(trades: List[Dict]) -> io.BytesIO:
    """
    Generate win/loss pie chart
    
    Args:
        trades (list): List of trade dictionaries
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not trades:
            return None
        
        # Count winning and losing trades
        winning_trades = len([t for t in trades if t.get('profit', 0) > 0])
        losing_trades = len([t for t in trades if t.get('profit', 0) < 0])
        
        # Create figure
        plt.figure(figsize=(8, 8))
        plt.style.use(settings.CHART_STYLE)
        
        # Create pie chart
        labels = ['Wins', 'Losses']
        sizes = [winning_trades, losing_trades]
        colors = ['green', 'red']
        explode = (0.1, 0)  # explode the 1st slice (Wins)
        
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title(f'Win/Loss Distribution (Total Trades: {len(trades)})')
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting win/loss chart: {e}")
        return None

def plot_trade_duration_chart(trades: List[Dict]) -> io.BytesIO:
    """
    Generate trade duration chart
    
    Args:
        trades (list): List of trade dictionaries
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not trades:
            return None
        
        # Calculate trade durations
        durations = []
        for trade in trades:
            entry_date = trade.get('entry_date')
            exit_date = trade.get('exit_date')
            
            if entry_date and exit_date:
                # Convert to datetime if they're strings
                if isinstance(entry_date, str):
                    entry_date = pd.to_datetime(entry_date)
                if isinstance(exit_date, str):
                    exit_date = pd.to_datetime(exit_date)
                
                duration = (exit_date - entry_date).total_seconds() / 3600  # Duration in hours
                durations.append(duration)
        
        if not durations:
            return None
        
        # Create figure
        plt.figure(figsize=(10, 6))
        plt.style.use(settings.CHART_STYLE)
        
        # Create histogram
        plt.hist(durations, bins=20, alpha=0.7, color='purple', edgecolor='black')
        
        # Add labels and title
        plt.title('Trade Duration Distribution')
        plt.xlabel('Duration (hours)')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting trade duration chart: {e}")
        return None

def plot_optimization_results(results: List[Dict]) -> io.BytesIO:
    """
    Generate chart showing optimization results
    
    Args:
        results (list): Optimization results
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not results:
            return None
        
        # Extract data for plotting
        returns = [r['total_return'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        drawdowns = [r['max_drawdown'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        
        # Create subplots
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        plt.style.use(settings.CHART_STYLE)
        
        # Plot total returns
        axs[0, 0].bar(range(len(returns)), returns, alpha=0.7, color='green')
        axs[0, 0].set_title('Total Returns (%)')
        axs[0, 0].set_xlabel('Parameter Set')
        axs[0, 0].set_ylabel('Return (%)')
        axs[0, 0].grid(True, alpha=0.3)
        
        # Plot win rates
        axs[0, 1].bar(range(len(win_rates)), win_rates, alpha=0.7, color='blue')
        axs[0, 1].set_title('Win Rates (%)')
        axs[0, 1].set_xlabel('Parameter Set')
        axs[0, 1].set_ylabel('Win Rate (%)')
        axs[0, 1].grid(True, alpha=0.3)
        
        # Plot max drawdowns
        axs[1, 0].bar(range(len(drawdowns)), drawdowns, alpha=0.7, color='red')
        axs[1, 0].set_title('Max Drawdowns (%)')
        axs[1, 0].set_xlabel('Parameter Set')
        axs[1, 0].set_ylabel('Drawdown (%)')
        axs[1, 0].grid(True, alpha=0.3)
        
        # Plot Sharpe ratios
        axs[1, 1].bar(range(len(sharpe_ratios)), sharpe_ratios, alpha=0.7, color='purple')
        axs[1, 1].set_title('Sharpe Ratios')
        axs[1, 1].set_xlabel('Parameter Set')
        axs[1, 1].set_ylabel('Sharpe Ratio')
        axs[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error plotting optimization results: {e}")
        return None

def create_performance_summary(metrics: Dict) -> io.BytesIO:
    """
    Create a visual performance summary
    
    Args:
        metrics (dict): Performance metrics
        
    Returns:
        io.BytesIO: PNG image data
    """
    try:
        if not metrics:
            return None
        
        # Create figure
        plt.figure(figsize=(10, 8))
        plt.style.use(settings.CHART_STYLE)
        
        # No actual plotting, just text
        plt.axis('off')
        
        # Title
        plt.text(0.5, 0.95, 'BACKTEST PERFORMANCE SUMMARY', 
                 horizontalalignment='center', fontsize=16, fontweight='bold')
        
        # Returns section
        plt.text(0.05, 0.85, 'RETURNS', fontsize=14, fontweight='bold')
        plt.text(0.05, 0.80, f"Total Return: {metrics.get('total_return', 0):.2f}%")
        plt.text(0.05, 0.77, f"Annual Return: {metrics.get('annual_return', 0):.2f}%")
        plt.text(0.05, 0.74, f"Final Capital: ${metrics.get('final_capital', 0):,.2f}")
        
        # Trade statistics section
        plt.text(0.05, 0.65, 'TRADE STATISTICS', fontsize=14, fontweight='bold')
        plt.text(0.05, 0.60, f"Total Trades: {metrics.get('total_trades', 0)}")
        plt.text(0.05, 0.57, f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
        plt.text(0.05, 0.54, f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        plt.text(0.05, 0.51, f"Average Win: ${metrics.get('average_win', 0):,.2f}")
        plt.text(0.05, 0.48, f"Average Loss: ${metrics.get('average_loss', 0):,.2f}")
        
        # Risk metrics section
        plt.text(0.05, 0.39, 'RISK METRICS', fontsize=14, fontweight='bold')
        plt.text(0.05, 0.34, f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
        plt.text(0.05, 0.31, f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        plt.text(0.05, 0.28, f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
        plt.text(0.05, 0.25, f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}")
        
        # Streak information
        plt.text(0.05, 0.16, 'STREAKS', fontsize=14, fontweight='bold')
        plt.text(0.05, 0.11, f"Max Consecutive Wins: {metrics.get('max_consecutive_wins', 0)}")
        plt.text(0.05, 0.08, f"Max Consecutive Losses: {metrics.get('max_consecutive_losses', 0)}")
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error creating performance summary: {e}")
        return None

def create_backtest_summary(backtest_results, symbol, period, timestamp=None):
    """
    Create a backtest summary chart
    
    Args:
        backtest_results (dict): Backtest results
        symbol (str): Trading symbol
        period (str): Backtest period
        timestamp (str, optional): Timestamp of when the backtest was performed
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Create figure with multiple subplots
        fig, axs = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
        plt.style.use('grayscale')  # Use grayscale style for black and white
        
        # Get equity curve and trades
        equity_curve = backtest_results.get('equity_curve', [])
        trades = backtest_results.get('trades', [])
        
        if not equity_curve:
            return None
        
        # Plot equity curve
        axs[0].plot(equity_curve, 'k-', linewidth=2)
        axs[0].set_title('Equity Curve')
        axs[0].set_xlabel('Trade Number')
        axs[0].set_ylabel('Account Balance')
        axs[0].grid(True, alpha=0.3)
        axs[0].axhline(y=equity_curve[0], color='k', linestyle='--', alpha=0.5)
        
        # Plot trade results (win/loss)
        wins = [t for t in trades if t.get('profit', 0) > 0]
        losses = [t for t in trades if t.get('profit', 0) <= 0]
        
        axs[1].bar(['Wins', 'Losses'], [len(wins), len(losses)], color=['white', 'black'], edgecolor='black')
        axs[1].set_title('Trade Results')
        axs[1].set_ylabel('Count')
        axs[1].grid(True, alpha=0.3, axis='y')
        
        # Plot profit distribution
        profits = [t.get('profit_percentage', 0) for t in trades]
        axs[2].hist(profits, bins=20, color='lightgray', edgecolor='black')
        axs[2].set_title('Profit Distribution')
        axs[2].set_xlabel('Profit (%)')
        axs[2].set_ylabel('Frequency')
        axs[2].grid(True, alpha=0.3)
        
        # Add overall title
        title = f'Backtest Results: {symbol} ({period})'
        if timestamp:
            title += f' - {timestamp}'
        fig.suptitle(title, fontsize=16)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust layout to make room for suptitle
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error creating backtest summary: {e}")
        return None
