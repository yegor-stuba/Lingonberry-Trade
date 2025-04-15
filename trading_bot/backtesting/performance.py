"""
Performance metrics for backtesting
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

def calculate_metrics(equity_curve: List[float], trades: List[Dict]) -> Dict:
    """
    Calculate performance metrics from equity curve and trades
    
    Args:
        equity_curve (list): List of equity values
        trades (list): List of trade dictionaries
        
    Returns:
        dict: Performance metrics
    """
    try:
        if not equity_curve or not trades:
            return {}
        
        # Basic metrics
        initial_capital = equity_curve[0]
        final_capital = equity_curve[-1]
        total_return = ((final_capital / initial_capital) - 1) * 100
        
        # Trade metrics
        winning_trades = [t for t in trades if t.get('profit', 0) > 0]
        losing_trades = [t for t in trades if t.get('profit', 0) < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_trades = len(trades)
        
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        
        # Profit metrics
        total_profit = sum(t.get('profit', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('profit', 0) for t in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        average_win = total_profit / win_count if win_count > 0 else 0
        average_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # Calculate drawdown
        max_equity = initial_capital
        drawdown = 0
        max_drawdown = 0
        drawdown_series = []
        
        for equity in equity_curve:
            if equity > max_equity:
                max_equity = equity
                drawdown = 0
            else:
                drawdown = (max_equity - equity) / max_equity * 100
            
            drawdown_series.append(drawdown)
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] / equity_curve[i-1]) - 1
            returns.append(ret)
        
        # Risk metrics
        if returns:
            annual_return = total_return / (len(equity_curve) / 252)  # Assuming 252 trading days per year
            volatility = np.std(returns) * np.sqrt(252)
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0
            
            # Sortino ratio (using only negative returns)
            negative_returns = [r for r in returns if r < 0]
            downside_deviation = np.std(negative_returns) * np.sqrt(252) if negative_returns else 0
            sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else 0
            
            # Calmar ratio
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        else:
            annual_return = 0
            volatility = 0
            sharpe_ratio = 0
            sortino_ratio = 0
            calmar_ratio = 0
        
        # Calculate monthly returns
        monthly_returns = {}
        for trade in trades:
            exit_date = trade.get('exit_date')
            if exit_date:
                # Convert to datetime if it's a string
                if isinstance(exit_date, str):
                    exit_date = pd.to_datetime(exit_date)
                
                month_key = exit_date.strftime('%Y-%m')
                if month_key not in monthly_returns:
                    monthly_returns[month_key] = 0
                
                monthly_returns[month_key] += trade.get('profit', 0)
        
        # Calculate consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        current_streak = 0
        for trade in trades:
            if trade.get('profit', 0) > 0:
                if current_streak > 0:
                    current_streak += 1
                else:
                    current_streak = 1
                max_consecutive_wins = max(max_consecutive_wins, current_streak)
            else:
                if current_streak < 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                max_consecutive_losses = max(max_consecutive_losses, abs(current_streak))
        
        return {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_win': average_win,
            'average_loss': average_loss,
            'max_drawdown': max_drawdown,
            'drawdown_series': drawdown_series,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'monthly_returns': monthly_returns,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {}

def calculate_trade_statistics(trades: List[Dict]) -> Dict:
    """
    Calculate statistics about trade characteristics
    
    Args:
        trades (list): List of trade dictionaries
        
    Returns:
        dict: Trade statistics
    """
    try:
        if not trades:
            return {}
        
        # Trade durations
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
        
        avg_duration = np.mean(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Trade types
        buy_trades = [t for t in trades if t.get('direction', '').upper() == 'BUY']
        sell_trades = [t for t in trades if t.get('direction', '').upper() == 'SELL']
        
        buy_count = len(buy_trades)
        sell_count = len(sell_trades)
        
        buy_win_rate = (len([t for t in buy_trades if t.get('profit', 0) > 0]) / buy_count) * 100 if buy_count > 0 else 0
        sell_win_rate = (len([t for t in sell_trades if t.get('profit', 0) > 0]) / sell_count) * 100 if sell_count > 0 else 0
        
        # Risk-reward ratios
        risk_reward_ratios = []
        for trade in trades:
            entry = trade.get('entry_price', 0)
            stop = trade.get('stop_loss', 0)
            target = trade.get('take_profit', 0)
            
            if entry and stop and target:
                if trade.get('direction', '').upper() == 'BUY':
                    risk = entry - stop
                    reward = target - entry
                else:  # SELL
                    risk = stop - entry
                    reward = entry - target
                
                if risk > 0:
                    rr = reward / risk
                    risk_reward_ratios.append(rr)
        
        avg_rr = np.mean(risk_reward_ratios) if risk_reward_ratios else 0
        
        return {
            'avg_duration': avg_duration,
            'max_duration': max_duration,
            'min_duration': min_duration,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'buy_win_rate': buy_win_rate,
            'sell_win_rate': sell_win_rate,
            'avg_risk_reward': avg_rr
        }
        
    except Exception as e:
        logger.error(f"Error calculating trade statistics: {e}")
        return {}
