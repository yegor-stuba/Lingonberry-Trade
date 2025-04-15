"""
Backtesting engine for trading strategies
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Optional, Tuple, Union

from trading_bot.analysis.smc import SMCAnalyzer
from trading_bot.risk.management import RiskManager
from trading_bot.config import settings
from trading_bot.utils import helpers, visualization

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Engine for backtesting trading strategies on historical data
    """
    
    def __init__(self):
        """Initialize the backtest engine"""
        self.smc_analyzer = SMCAnalyzer()
        self.risk_manager = RiskManager()
        self.charts_dir = Path(settings.BASE_DIR).parent / "charts"
        
    async def run_backtest(self, 
                          market_type: str,
                          symbol: str, 
                          timeframe: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          initial_capital: float = 10000.0,
                          risk_per_trade: float = 1.0,
                          strategy_params: Optional[Dict] = None) -> Dict:
        """
        Run a backtest for a specific symbol and timeframe
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframe (str): Timeframe for analysis
            start_date (str, optional): Start date for backtest (YYYY-MM-DD)
            end_date (str, optional): End date for backtest (YYYY-MM-DD)
            initial_capital (float): Initial capital for the backtest
            risk_per_trade (float): Risk percentage per trade
            strategy_params (dict, optional): Additional strategy parameters
            
        Returns:
            dict: Backtest results
        """
        try:
            # Load historical data
            df = self._load_historical_data(market_type, symbol, timeframe)
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': f"Failed to load historical data for {symbol} {timeframe}"
                }
            
            # Filter data by date range if provided
            if start_date:
                start_dt = pd.to_datetime(start_date)
                df = df[df.index >= start_dt]
            
            if end_date:
                end_dt = pd.to_datetime(end_date)
                df = df[df.index <= end_dt]
            
            if df.empty:
                return {
                    'success': False,
                    'message': f"No data available for the specified date range"
                }
            
            # Set default strategy parameters if not provided
            if strategy_params is None:
                strategy_params = {
                    'min_strength': 70,
                    'min_rr': 2.0,
                    'use_market_structure': True,
                    'use_order_blocks': True,
                    'use_liquidity_levels': True,
                    'use_fair_value_gaps': True
                }
            
            # Run the backtest using the SMCAnalyzer
            backtest_results = self.smc_analyzer.backtest(
                df=df,
                initial_capital=initial_capital,
                risk_per_trade=risk_per_trade,
                strategy_params=strategy_params
            )
            
            # Calculate additional performance metrics
            performance_metrics = self._calculate_performance_metrics(backtest_results)
            
            # Generate equity curve chart
            equity_curve_buffer = self._generate_equity_curve(backtest_results)
            
            # Generate trade distribution chart
            trade_distribution_buffer = self._generate_trade_distribution(backtest_results)
            
            # Generate drawdown chart
            drawdown_buffer = self._generate_drawdown_chart(backtest_results)
            
            # Generate monthly returns chart
            monthly_returns_buffer = self._generate_monthly_returns(backtest_results)
            
            # Prepare the final results
            results = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': df.index[0].strftime('%Y-%m-%d'),
                'end_date': df.index[-1].strftime('%Y-%m-%d'),
                'initial_capital': initial_capital,
                'risk_per_trade': risk_per_trade,
                'final_capital': backtest_results.get('final_capital', initial_capital),
                'total_return_pct': ((backtest_results.get('final_capital', initial_capital) / initial_capital) - 1) * 100,
                'trades': backtest_results.get('trades', []),
                'trade_count': len(backtest_results.get('trades', [])),
                'win_rate': performance_metrics.get('win_rate', 0),
                'profit_factor': performance_metrics.get('profit_factor', 0),
                'average_win': performance_metrics.get('average_win', 0),
                'average_loss': performance_metrics.get('average_loss', 0),
                'max_drawdown': performance_metrics.get('max_drawdown', 0),
                'max_drawdown_pct': performance_metrics.get('max_drawdown_pct', 0),
                'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0),
                'sortino_ratio': performance_metrics.get('sortino_ratio', 0),
                'equity_curve': backtest_results.get('equity_curve', []),
                'drawdowns': backtest_results.get('drawdowns', []),
                'monthly_returns': performance_metrics.get('monthly_returns', {}),
                'charts': {
                    'equity_curve': equity_curve_buffer,
                    'trade_distribution': trade_distribution_buffer,
                    'drawdown': drawdown_buffer,
                    'monthly_returns': monthly_returns_buffer
                },
                'strategy_params': strategy_params
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {
                'success': False,
                'message': f"Error running backtest: {str(e)}"
            }
    
    def _load_historical_data(self, market_type: str, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Load historical data from CSV files
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframe (str): Timeframe for analysis
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        try:
            # Map timeframe to CSV file suffix
            timeframe_map = {
                '1m': '1',
                '5m': '5',
                '15m': '15',
                '30m': '30',
                '1h': '60',
                '4h': '240',
                '1d': '1440',
                '1w': '10080'
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            csv_suffix = timeframe_map[timeframe]
            
            # Construct CSV file path
            if market_type.lower() == 'forex':
                csv_path = self.charts_dir / "forex" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'crypto':
                csv_path = self.charts_dir / "crypto" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'indices':
                csv_path = self.charts_dir / "indeces" / f"{symbol}{csv_suffix}.csv"
            elif market_type.lower() == 'metals':
                csv_path = self.charts_dir / "metals" / f"{symbol}{csv_suffix}.csv"
            else:
                logger.error(f"Unsupported market type: {market_type}")
                return None
            
            if not csv_path.exists():
                logger.error(f"CSV file not found: {csv_path}")
                return None
            
            # Read CSV file
            df = pd.read_csv(csv_path, sep='\t', header=None)
            
            # Rename columns
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # Convert datetime
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Set datetime as index
            df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return None
    
    def _calculate_performance_metrics(self, backtest_results: Dict) -> Dict:
        """
        Calculate additional performance metrics from backtest results
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            dict: Performance metrics
        """
        try:
            trades = backtest_results.get('trades', [])
            equity_curve = backtest_results.get('equity_curve', [])
            
            if not trades or not equity_curve:
                return {}
            
            # Calculate win rate
            winning_trades = [t for t in trades if t.get('profit', 0) > 0]
            win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
            
            # Calculate profit factor
            total_profit = sum(t.get('profit', 0) for t in trades if t.get('profit', 0) > 0)
            total_loss = abs(sum(t.get('profit', 0) for t in trades if t.get('profit', 0) < 0))
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Calculate average win and loss
            average_win = total_profit / len(winning_trades) if winning_trades else 0
            average_loss = total_loss / (len(trades) - len(winning_trades)) if len(trades) > len(winning_trades) else 0
            
            # Calculate max drawdown
            max_drawdown = backtest_results.get('max_drawdown', 0)
            max_drawdown_pct = backtest_results.get('max_drawdown_pct', 0)
            
            # Calculate Sharpe ratio (assuming risk-free rate of 0)
            if len(equity_curve) > 1:
                returns = [(equity_curve[i] / equity_curve[i-1]) - 1 for i in range(1, len(equity_curve))]
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate Sortino ratio (using only negative returns for denominator)
            if len(equity_curve) > 1:
                negative_returns = [r for r in returns if r < 0]
                downside_std = np.std(negative_returns) if negative_returns else 0
                sortino_ratio = (avg_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
            else:
                sortino_ratio = 0
            
            # Calculate monthly returns
            if len(trades) > 0:
                # Convert trade dates to datetime if they're strings
                for trade in trades:
                    if isinstance(trade.get('exit_date'), str):
                        trade['exit_date'] = pd.to_datetime(trade['exit_date'])
                
                # Group trades by month and calculate returns
                monthly_returns = {}
                for trade in trades:
                    exit_date = trade.get('exit_date')
                    if exit_date:
                        month_key = exit_date.strftime('%Y-%m')
                        if month_key not in monthly_returns:
                            monthly_returns[month_key] = 0
                        monthly_returns[month_key] += trade.get('profit', 0)
            else:
                monthly_returns = {}
            
            return {
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'average_win': average_win,
                'average_loss': average_loss,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'monthly_returns': monthly_returns
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def _generate_equity_curve(self, backtest_results: Dict) -> Optional[io.BytesIO]:
        """
        Generate equity curve chart
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            io.BytesIO: PNG image data
        """
        try:
            equity_curve = backtest_results.get('equity_curve', [])
            trades = backtest_results.get('trades', [])
            
            if not equity_curve:
                return None
            
            # Create figure
            plt.figure(figsize=(10, 6))
            plt.style.use(settings.CHART_STYLE)
            
            # Plot equity curve
            plt.plot(equity_curve, 'g-', linewidth=2)
            
            # Add trade markers
            for i, trade in enumerate(trades):
                idx = trade.get('exit_index')
                if idx is not None and idx < len(equity_curve):
                    if trade.get('profit', 0) > 0:
                        plt.plot(idx, equity_curve[idx], 'go', markersize=6)
                    else:
                        plt.plot(idx, equity_curve[idx], 'ro', markersize=6)
            
            # Add labels and title
            plt.title('Equity Curve')
            plt.xlabel('Trade Number')
            plt.ylabel('Account Balance')
            plt.grid(True, alpha=0.3)
            
            # Add horizontal line at initial capital
            plt.axhline(y=equity_curve[0], color='r', linestyle='--', alpha=0.5)
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error generating equity curve: {e}")
            return None
    
    def _generate_trade_distribution(self, backtest_results: Dict) -> Optional[io.BytesIO]:
        """
        Generate trade distribution chart
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            io.BytesIO: PNG image data
        """
        try:
            trades = backtest_results.get('trades', [])
            
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
            logger.error(f"Error generating trade distribution chart: {e}")
            return None
    
    def _generate_drawdown_chart(self, backtest_results: Dict) -> Optional[io.BytesIO]:
        """
        Generate drawdown chart
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            io.BytesIO: PNG image data
        """
        try:
            drawdowns = backtest_results.get('drawdowns', [])
            
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
            logger.error(f"Error generating drawdown chart: {e}")
            return None
    
    def _generate_monthly_returns(self, backtest_results: Dict) -> Optional[io.BytesIO]:
        """
        Generate monthly returns chart
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            io.BytesIO: PNG image data
        """
        try:
            trades = backtest_results.get('trades', [])
            
            if not trades:
                return None
            
            # Group trades by month
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
            logger.error(f"Error generating monthly returns chart: {e}")
            return None
    
    async def optimize_strategy(self, 
                               market_type: str,
                               symbol: str, 
                               timeframe: str,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               initial_capital: float = 10000.0,
                               param_grid: Optional[Dict] = None) -> Dict:
        """
        Optimize strategy parameters using grid search
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            timeframe (str): Timeframe for analysis
            start_date (str, optional): Start date for backtest (YYYY-MM-DD)
            end_date (str, optional): End date for backtest (YYYY-MM-DD)
            initial_capital (float): Initial capital for the backtest
            param_grid (dict, optional): Parameter grid for optimization
            
        Returns:
            dict: Optimization results
        """
        try:
            # Load historical data
            df = self._load_historical_data(market_type, symbol, timeframe)
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': f"Failed to load historical data for {symbol} {timeframe}"
                }
            
            # Filter data by date range if provided
            if start_date:
                start_dt = pd.to_datetime(start_date)
                df = df[df.index >= start_dt]
            
            if end_date:
                end_dt = pd.to_datetime(end_date)
                df = df[df.index <= end_dt]
            
            if df.empty:
                return {
                    'success': False,
                    'message': f"No data available for the specified date range"
                }
            
            # Set default parameter grid if not provided
            if param_grid is None:
                param_grid = {
                    'min_strength': [60, 70, 80],
                    'min_rr': [1.5, 2.0, 2.5],
                    'risk_per_trade': [0.5, 1.0, 2.0]
                }
            
            # Generate all parameter combinations
            param_combinations = self._generate_param_combinations(param_grid)
            
            # Run backtest for each parameter combination
            results = []
            
            for params in param_combinations:
                # Extract risk_per_trade from params
                risk_per_trade = params.pop('risk_per_trade', 1.0)
                
                # Run backtest with these parameters
                backtest_results = self.smc_analyzer.backtest(
                    df=df,
                    initial_capital=initial_capital,
                    risk_per_trade=risk_per_trade,
                    strategy_params=params
                )
                
                # Calculate key metrics
                total_return = ((backtest_results.get('final_capital', initial_capital) / initial_capital) - 1) * 100
                win_rate = (backtest_results.get('win_count', 0) / backtest_results.get('trade_count', 1)) * 100 if backtest_results.get('trade_count', 0) > 0 else 0
                max_drawdown = backtest_results.get('max_drawdown_pct', 0)
                
                # Calculate Sharpe ratio
                equity_curve = backtest_results.get('equity_curve', [])
                sharpe_ratio = 0
                
                if len(equity_curve) > 1:
                    returns = [(equity_curve[i] / equity_curve[i-1]) - 1 for i in range(1, len(equity_curve))]
                    avg_return = np.mean(returns)
                    std_return = np.std(returns)
                    sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
                
                # Store results
                results.append({
                    'params': {**params, 'risk_per_trade': risk_per_trade},
                    'total_return': total_return,
                    'win_rate': win_rate,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'trade_count': backtest_results.get('trade_count', 0)
                })
            
            # Sort results by total return (descending)
            results.sort(key=lambda x: x['total_return'], reverse=True)
            
            # Generate optimization chart
            optimization_chart = self._generate_optimization_chart(results)
            
            return {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': df.index[0].strftime('%Y-%m-%d'),
                'end_date': df.index[-1].strftime('%Y-%m-%d'),
                'initial_capital': initial_capital,
                'param_grid': param_grid,
                'results': results,
                'best_params': results[0]['params'] if results else None,
                'best_return': results[0]['total_return'] if results else None,
                'optimization_chart': optimization_chart
            }
            
        except Exception as e:
            logger.error(f"Error optimizing strategy: {e}")
            return {
                'success': False,
                'message': f"Error optimizing strategy: {str(e)}"
            }
    
    def _generate_param_combinations(self, param_grid: Dict) -> List[Dict]:
        """
        Generate all combinations of parameters from the grid
        
        Args:
            param_grid (dict): Parameter grid
            
        Returns:
            list: List of parameter dictionaries
        """
        import itertools
        
        # Get all parameter names and values
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        # Generate all combinations
        combinations = list(itertools.product(*param_values))
        
        # Convert to list of dictionaries
        result = []
        for combo in combinations:
            param_dict = {param_names[i]: combo[i] for i in range(len(param_names))}
            result.append(param_dict)
        
        return result
    
    def _generate_optimization_chart(self, results: List[Dict]) -> Optional[io.BytesIO]:
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
            
            # Create figure
            plt.figure(figsize=(12, 8))
            plt.style.use(settings.CHART_STYLE)
            
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
            logger.error(f"Error generating optimization chart: {e}")
            return None

