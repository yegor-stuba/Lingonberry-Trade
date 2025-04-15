"""
Main backtesting module for the trading bot
"""

import logging
from typing import Dict, List, Optional, Union

from trading_bot.backtesting.engine import BacktestEngine
from trading_bot.backtesting.data_loader import DataLoader
from trading_bot.backtesting.performance import calculate_metrics, calculate_trade_statistics
from trading_bot.backtesting.backtest_visualization import (
    plot_equity_curve, plot_drawdown_chart, plot_monthly_returns,
    plot_trade_distribution, plot_win_loss_chart, plot_trade_duration_chart,
    create_performance_summary
)

logger = logging.getLogger(__name__)

class Backtester:
    """
    Main backtesting class for the trading bot
    """
    
    def __init__(self):
        """Initialize the backtester"""
        self.engine = BacktestEngine()
        self.data_loader = DataLoader()
    
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
            # Run the backtest using the engine
            results = await self.engine.run_backtest(
                market_type=market_type,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                risk_per_trade=risk_per_trade,
                strategy_params=strategy_params
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {
                'success': False,
                'message': f"Error running backtest: {str(e)}"
            }
    
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
            # Run optimization using the engine
            results = await self.engine.optimize_strategy(
                market_type=market_type,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                param_grid=param_grid
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing strategy: {e}")
            return {
                'success': False,
                'message': f"Error optimizing strategy: {str(e)}"
            }
    
    def get_available_symbols(self, market_type: str) -> List[str]:
        """
        Get list of available symbols for a market type
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            list: List of available symbols
        """
        return self.data_loader.get_available_symbols(market_type)
    
    def get_available_timeframes(self, market_type: str, symbol: str) -> List[str]:
        """
        Get list of available timeframes for a symbol
        
        Args:
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            symbol (str): Trading symbol
            
        Returns:
            list: List of available timeframes
        """
        return self.data_loader.get_available_timeframes(market_type, symbol)
    
    def generate_report(self, backtest_results: Dict) -> Dict:
        """
        Generate a comprehensive backtest report
        
        Args:
            backtest_results (dict): Results from the backtest
            
        Returns:
            dict: Report with charts and metrics
        """
        try:
            if not backtest_results.get('success', False):
                return backtest_results
            
            # Extract data from results
            equity_curve = backtest_results.get('equity_curve', [])
            trades = backtest_results.get('trades', [])
            drawdowns = backtest_results.get('drawdowns', [])
            
            # Calculate additional metrics
            metrics = calculate_metrics(equity_curve, trades)
            trade_stats = calculate_trade_statistics(trades)
            
            # Generate charts
            equity_chart = plot_equity_curve(equity_curve, trades)
            drawdown_chart = plot_drawdown_chart(drawdowns)
            monthly_chart = plot_monthly_returns(metrics.get('monthly_returns', {}))
            distribution_chart = plot_trade_distribution(trades)
            win_loss_chart = plot_win_loss_chart(trades)
            duration_chart = plot_trade_duration_chart(trades)
            summary_chart = create_performance_summary({**metrics, **trade_stats})
            
            # Combine everything into a report
            report = {
                'success': True,
                'symbol': backtest_results.get('symbol'),
                'timeframe': backtest_results.get('timeframe'),
                'start_date': backtest_results.get('start_date'),
                'end_date': backtest_results.get('end_date'),
                'initial_capital': backtest_results.get('initial_capital'),
                'final_capital': backtest_results.get('final_capital'),
                'total_return': backtest_results.get('total_return_pct'),
                'metrics': {**metrics, **trade_stats},
                'charts': {
                    'equity_curve': equity_chart,
                    'drawdown': drawdown_chart,
                    'monthly_returns': monthly_chart,
                    'trade_distribution': distribution_chart,
                    'win_loss': win_loss_chart,
                    'trade_duration': duration_chart,
                    'summary': summary_chart
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating backtest report: {e}")
            return {
                'success': False,
                'message': f"Error generating backtest report: {str(e)}"
            }
