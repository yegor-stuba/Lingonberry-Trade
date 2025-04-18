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

from trading_bot.analysis.smc_analyzer import SMCAnalyzer
from trading_bot.risk.management import RiskManager
from trading_bot.config import settings
from trading_bot.utils import helpers, visualization
from trading_bot.data.data_processor import DataProcessor
from trading_bot.strategy.combined_strategy import CombinedStrategy


logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Engine for backtesting trading strategies on historical data
    """
    
    def __init__(self):
        """Initialize the backtest engine"""
        self.data_processor = DataProcessor()
        self.smc_analyzer = SMCAnalyzer()
        self.risk_manager = RiskManager()
        self.combined_strategy = CombinedStrategy()
        self.results = {}
        
    async def load_data(self, symbol: str, timeframe: str, period: str = '1y', market_type: str = 'forex') -> pd.DataFrame:
        """
        Load historical data for backtesting
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            period (str): Time period ('1m', '3m', '6m', '1y', '2y', '5y')
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        try:
            logger.info(f"Loading historical data for {symbol} ({timeframe}, {period})")
            
            # Get appropriate data provider based on market type
            if market_type.lower() == 'crypto':
                data_provider = self.data_provider_factory.get_provider('crypto')
            else:
                # Use cTrader for forex, indices, and metals
                data_provider = self.data_provider_factory.get_provider('ctrader')
            
            # Get historical data
            df = await data_provider.get_historical_data(symbol, period, timeframe)
            
            if df is None or df.empty:
                logger.error(f"Failed to load data for {symbol} ({timeframe}, {period})")
                return None
            
            logger.info(f"Loaded {len(df)} candles for {symbol} ({timeframe}, {period})")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            return None
    
    async def run_backtest(self, symbol: str, timeframe: str, period: str = '1y', 
                          market_type: str = 'forex', initial_capital: float = 10000.0,
                          risk_per_trade: float = 1.0, strategy: str = 'smc') -> Dict:
        """
        Run a backtest on historical data
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe (e.g., '1h', '4h', '1d')
            period (str): Time period ('1m', '3m', '6m', '1y', '2y', '5y')
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            initial_capital (float): Initial capital
            risk_per_trade (float): Risk percentage per trade
            strategy (str): Strategy to use ('smc', 'technical', 'combined')
            
        Returns:
            dict: Backtest results
        """
        try:
            # Load historical data
            df = await self.load_data(symbol, timeframe, period, market_type)
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': f"Failed to load data for {symbol} ({timeframe}, {period})"
                }
            
            # Initialize backtest variables
            equity = [initial_capital]
            trades = []
            current_position = None
            
            # Run the backtest based on the selected strategy
            if strategy.lower() == 'smc':
                trades, equity = self._run_smc_backtest(df, initial_capital, risk_per_trade)
            elif strategy.lower() == 'technical':
                trades, equity = self._run_technical_backtest(df, initial_capital, risk_per_trade)
            elif strategy.lower() == 'combined':
                trades, equity = self._run_combined_backtest(df, initial_capital, risk_per_trade)
            else:
                return {
                    'success': False,
                    'message': f"Unknown strategy: {strategy}"
                }
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(trades, equity, initial_capital)
            
            # Store results
            self.results = {
                'success': True,
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'market_type': market_type,
                'initial_capital': initial_capital,
                'risk_per_trade': risk_per_trade,
                'strategy': strategy,
                'trades': trades,
                'equity': equity,
                'metrics': metrics
            }
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error running backtest for {symbol}: {e}")
            return {
                'success': False,
                'message': f"Error running backtest: {str(e)}"
            }
    
    def _run_smc_backtest(self, df: pd.DataFrame, initial_capital: float, risk_per_trade: float) -> Tuple[List[Dict], List[float]]:
        """
        Run a backtest using SMC strategy
        
        Args:
            df (pd.DataFrame): Historical OHLCV data
            initial_capital (float): Initial capital
            risk_per_trade (float): Risk percentage per trade
            
        Returns:
            tuple: (trades, equity)
        """
        trades = []
        equity = [initial_capital]
        current_equity = initial_capital
        
        # We need at least 100 candles for proper analysis
        if len(df) < 100:
            logger.warning(f"Not enough data for SMC analysis: {len(df)} candles")
            return trades, equity
        
        # Analyze each candle (starting from the 100th)
        for i in range(100, len(df)):
            # Get data up to current candle (excluding current)
            analysis_df = df.iloc[:i].copy()
            
            # Run SMC analysis
            trade_setups = self.smc_analyzer.find_trade_setups(analysis_df)
            
            # Check for valid trade setups
            if trade_setups:
                for setup in trade_setups:
                    # Check if we should enter a trade
                    entry_price = setup['entry']
                    stop_loss = setup['stop_loss']
                    take_profit = setup['take_profit']
                    trade_type = setup['type']  # 'BUY' or 'SELL'
                    
                    # Current candle
                    current_candle = df.iloc[i]
                    
                    # Check if entry was triggered
                    entry_triggered = False
                    if trade_type == 'BUY' and current_candle['low'] <= entry_price <= current_candle['high']:
                        entry_triggered = True
                    elif trade_type == 'SELL' and current_candle['low'] <= entry_price <= current_candle['high']:
                        entry_triggered = True
                    
                    if entry_triggered:
                        # Calculate position size based on risk
                        risk_amount = current_equity * (risk_per_trade / 100)
                        pip_risk = abs(entry_price - stop_loss)
                        position_size = risk_amount / pip_risk
                        
                        # Record the trade
                        trade = {
                            'entry_date': df.index[i],
                            'symbol': 'BACKTEST',
                            'type': trade_type,
                            'entry': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size,
                            'risk_amount': risk_amount,
                            'exit_date': None,
                            'exit_price': None,
                            'profit_loss': None,
                            'status': 'OPEN'
                        }
                        
                        trades.append(trade)
            
            # Check if any open trades were closed
            for trade in [t for t in trades if t['status'] == 'OPEN']:
                # Current candle
                current_candle = df.iloc[i]
                
                # Check if stop loss was hit
                sl_hit = False
                if trade['type'] == 'BUY' and current_candle['low'] <= trade['stop_loss']:
                    sl_hit = True
                    exit_price = trade['stop_loss']
                elif trade['type'] == 'SELL' and current_candle['high'] >= trade['stop_loss']:
                    sl_hit = True
                    exit_price = trade['stop_loss']
                
                # Check if take profit was hit
                tp_hit = False
                if trade['type'] == 'BUY' and current_candle['high'] >= trade['take_profit']:
                    tp_hit = True
                    exit_price = trade['take_profit']
                elif trade['type'] == 'SELL' and current_candle['low'] <= trade['take_profit']:
                    tp_hit = True
                    exit_price = trade['take_profit']
                
                # If either SL or TP was hit, close the trade
                if sl_hit or tp_hit:
                    trade['exit_date'] = df.index[i]
                    trade['exit_price'] = exit_price
                    
                    # Calculate profit/loss
                    if trade['type'] == 'BUY':
                        pip_profit = exit_price - trade['entry']
                    else:  # SELL
                        pip_profit = trade['entry'] - exit_price
                    
                    trade['profit_loss'] = pip_profit * trade['position_size']
                    trade['status'] = 'CLOSED'
                    
                    # Update equity
                    current_equity += trade['profit_loss']
                    equity.append(current_equity)
        
        return trades, equity
    
    def _run_technical_backtest(self, df: pd.DataFrame, initial_capital: float, risk_per_trade: float) -> Tuple[List[Dict], List[float]]:
        """
        Run a backtest using technical analysis strategy
        
        Args:
            df (pd.DataFrame): Historical OHLCV data
            initial_capital (float): Initial capital
            risk_per_trade (float): Risk percentage per trade
            
        Returns:
            tuple: (trades, equity)
        """
        # Placeholder for technical analysis backtest
        # This would be implemented with specific technical indicators
        return [], [initial_capital]
    
    def _run_combined_backtest(self, df: pd.DataFrame, initial_capital: float, risk_per_trade: float) -> Tuple[List[Dict], List[float]]:
        """
        Run a backtest using combined SMC and technical analysis
        
        Args:
            df (pd.DataFrame): Historical OHLCV data
            initial_capital (float): Initial capital
            risk_per_trade (float): Risk percentage per trade
            
        Returns:
            tuple: (trades, equity)
        """
        # Initialize the combined strategy
        combined_strategy = CombinedStrategy()
        
        # Initialize backtest variables
        equity = [initial_capital]
        trades = []
        current_position = None
        capital = initial_capital
        
        # Ensure DataFrame has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("DataFrame index is not DatetimeIndex, attempting to convert")
            try:
                if 'datetime' in df.columns:
                    df = df.set_index('datetime')
                else:
                    df = df.set_index(pd.DatetimeIndex(df.index))
            except Exception as e:
                logger.error(f"Failed to convert index to DatetimeIndex: {e}")
                return [], [initial_capital]
        
        # Ensure column names are lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Minimum required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"DataFrame missing required columns. Available: {df.columns.tolist()}")
            return [], [initial_capital]
        
        # Iterate through each candle (starting from enough history for indicators)
        start_idx = 200  # Allow enough data for indicators
        
        for i in range(start_idx, len(df)):
            # Get current date and price
            current_date = df.index[i]
            current_price = df.iloc[i]['close']
            
            # Update equity
            if current_position:
                # Calculate current value of position
                if current_position['type'] == 'BUY':
                    position_value = current_position['size'] * current_price
                else:  # SELL
                    position_value = current_position['size'] * (2 * current_position['entry'] - current_price)
                
                # Update equity with position value
                equity.append(capital + position_value - current_position['value'])
            else:
                equity.append(capital)
            
            # Check for exit conditions if in a position
            if current_position:
                # For long positions
                if current_position['type'] == 'BUY':
                    # Check if take profit hit
                    if df.iloc[i]['high'] >= current_position['take_profit']:
                        # Calculate profit
                        profit = current_position['size'] * (current_position['take_profit'] - current_position['entry'])
                        capital += profit
                        
                        # Record trade
                        trades.append({
                            'entry_date': current_position['date'],
                            'exit_date': current_date,
                            'type': current_position['type'],
                            'entry': current_position['entry'],
                            'exit': current_position['take_profit'],
                            'size': current_position['size'],
                            'profit': profit,
                            'profit_pct': (profit / current_position['value']) * 100,
                            'exit_reason': 'take_profit'
                        })
                        
                        # Reset position
                        current_position = None
                        continue
                    
                    # Check if stop loss hit
                    if df.iloc[i]['low'] <= current_position['stop_loss']:
                        # Calculate loss
                        loss = current_position['size'] * (current_position['stop_loss'] - current_position['entry'])
                        capital += loss
                        
                        # Record trade
                        trades.append({
                            'entry_date': current_position['date'],
                            'exit_date': current_date,
                            'type': current_position['type'],
                            'entry': current_position['entry'],
                            'exit': current_position['stop_loss'],
                            'size': current_position['size'],
                            'profit': loss,
                            'profit_pct': (loss / current_position['value']) * 100,
                            'exit_reason': 'stop_loss'
                        })
                        
                        # Reset position
                        current_position = None
                        continue
                
                # For short positions
                else:  # SELL
                    # Check if take profit hit
                    if df.iloc[i]['low'] <= current_position['take_profit']:
                        # Calculate profit
                        profit = current_position['size'] * (current_position['entry'] - current_position['take_profit'])
                        capital += profit
                        
                        # Record trade
                        trades.append({
                            'entry_date': current_position['date'],
                            'exit_date': current_date,
                            'type': current_position['type'],
                            'entry': current_position['entry'],
                            'exit': current_position['take_profit'],
                            'size': current_position['size'],
                            'profit': profit,
                            'profit_pct': (profit / current_position['value']) * 100,
                            'exit_reason': 'take_profit'
                        })
                        
                        # Reset position
                        current_position = None
                        continue
                    
                    # Check if stop loss hit
                    if df.iloc[i]['high'] >= current_position['stop_loss']:
                        # Calculate loss
                        loss = current_position['size'] * (current_position['entry'] - current_position['stop_loss'])
                        capital += loss
                        
                        # Record trade
                        trades.append({
                            'entry_date': current_position['date'],
                            'exit_date': current_date,
                            'type': current_position['type'],
                            'entry': current_position['entry'],
                            'exit': current_position['stop_loss'],
                            'size': current_position['size'],
                            'profit': loss,
                            'profit_pct': (loss / current_position['value']) * 100,
                            'exit_reason': 'stop_loss'
                        })
                        
                        # Reset position
                        current_position = None
                        continue
            
            # Only look for new trades if not in a position
            if not current_position:
                # Get historical data up to current candle
                historical_df = df.iloc[:i+1].copy()
                
                # Analyze with combined strategy
                analysis = combined_strategy.analyze(historical_df, 'BACKTEST', 'BACKTEST')
                
                # Get trade setups
                trade_setups = analysis.get('trade_setups', [])
                
                # Filter for high-quality setups (RR >= 3)
                quality_setups = [setup for setup in trade_setups if setup.get('risk_reward', 0) >= 3]
                
                if quality_setups:
                    # Take the highest RR setup
                    setup = max(quality_setups, key=lambda x: x.get('risk_reward', 0))
                    
                    # Calculate position size based on risk
                    risk_amount = capital * (risk_per_trade / 100)
                    
                    if setup['direction'] == 'BUY':
                        # Calculate risk per unit
                        risk_per_unit = setup['entry'] - setup['stop_loss']
                        
                        if risk_per_unit > 0:
                            # Calculate position size
                            position_size = risk_amount / risk_per_unit
                            position_value = position_size * setup['entry']
                            
                            # Enter long position
                            current_position = {
                                'date': current_date,
                                'type': 'BUY',
                                'entry': setup['entry'],
                                'stop_loss': setup['stop_loss'],
                                'take_profit': setup['take_profit'],
                                'size': position_size,
                                'value': position_value,
                                'risk': risk_amount
                            }
                    
                    elif setup['direction'] == 'SELL':
                        # Calculate risk per unit
                        risk_per_unit = setup['stop_loss'] - setup['entry']
                        
                        if risk_per_unit > 0:
                            # Calculate position size
                            position_size = risk_amount / risk_per_unit
                            position_value = position_size * setup['entry']
                            
                            # Enter short position
                            current_position = {
                                'date': current_date,
                                'type': 'SELL',
                                'entry': setup['entry'],
                                'stop_loss': setup['stop_loss'],
                                'take_profit': setup['take_profit'],
                                'size': position_size,
                                'value': position_value,
                                'risk': risk_amount
                            }
        
        # Close any open position at the end of the backtest
        if current_position:
            final_price = df.iloc[-1]['close']
            
            if current_position['type'] == 'BUY':
                profit = current_position['size'] * (final_price - current_position['entry'])
            else:  # SELL
                profit = current_position['size'] * (current_position['entry'] - final_price)
            
            capital += profit
            
            # Record trade
            trades.append({
                'entry_date': current_position['date'],
                'exit_date': df.index[-1],
                'type': current_position['type'],
                'entry': current_position['entry'],
                'exit': final_price,
                'size': current_position['size'],
                'profit': profit,
                'profit_pct': (profit / current_position['value']) * 100,
                'exit_reason': 'end_of_test'
            })
            
            # Update final equity
            equity[-1] = capital
        
        return trades, equity
    
    def _calculate_performance_metrics(self, trades: List[Dict], equity: List[float], initial_capital: float) -> Dict:
        """
        Calculate performance metrics from backtest results
        
        Args:
            trades (list): List of trades
            equity (list): Equity curve
            initial_capital (float): Initial capital
            
        Returns:
            dict: Performance metrics
        """
        # Filter closed trades
        closed_trades = [t for t in trades if t['status'] == 'CLOSED']
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'net_profit': 0,
                'net_profit_percentage': 0,
                'max_drawdown': 0,
                'max_drawdown_percentage': 0,
                'sharpe_ratio': 0,
                'average_win': 0,
                'average_loss': 0,
                'largest_win': 0,
                'largest_loss': 0
            }
        
        # Calculate basic metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t['profit_loss'] > 0]
        losing_trades = [t for t in closed_trades if t['profit_loss'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Calculate profit metrics
        total_profit = sum(t['profit_loss'] for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t['profit_loss'] for t in losing_trades)) if losing_trades else 0
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        net_profit = total_profit - total_loss
        net_profit_percentage = (net_profit / initial_capital) * 100
        
        # Calculate drawdown
        max_equity = initial_capital
        max_drawdown = 0
        
        for eq in equity:
            if eq > max_equity:
                max_equity = eq
            drawdown = max_equity - eq
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        max_drawdown_percentage = (max_drawdown / max_equity) * 100 if max_equity > 0 else 0
        
        # Calculate average win/loss
        average_win = total_profit / win_count if win_count > 0 else 0
        average_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # Calculate largest win/loss
        largest_win = max([t['profit_loss'] for t in winning_trades]) if winning_trades else 0
        largest_loss = min([t['profit_loss'] for t in losing_trades]) if losing_trades else 0
        
        # Calculate Sharpe ratio (simplified)
        if len(equity) > 1:
            returns = [(equity[i] - equity[i-1]) / equity[i-1] for i in range(1, len(equity))]
            avg_return = sum(returns) / len(returns)
            std_return = np.std(returns) if len(returns) > 1 else 1
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_profit': net_profit,
            'net_profit_percentage': net_profit_percentage,
            'max_drawdown': max_drawdown,
            'max_drawdown_percentage': max_drawdown_percentage,
            'sharpe_ratio': sharpe_ratio,
            'average_win': average_win,
            'average_loss': average_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss
        }
    
    def generate_report(self, output_format: str = 'text') -> Union[str, io.BytesIO]:
        """
        Generate a backtest report
        
        Args:
            output_format (str): Output format ('text', 'html', 'image')
            
        Returns:
            Union[str, io.BytesIO]: Report in the specified format
        """
        if not self.results or not self.results.get('success', False):
            return "No backtest results available"
        
        # Extract results
        symbol = self.results['symbol']
        timeframe = self.results['timeframe']
        period = self.results['period']
        strategy = self.results['strategy']
        trades = self.results['trades']
        equity = self.results['equity']
        metrics = self.results['metrics']
        initial_capital = self.results['initial_capital']
        
        if output_format == 'text':
            # Generate text report
            report = [
                f"Backtest Report: {symbol} ({timeframe}, {period})",
                f"Strategy: {strategy}",
                f"Initial Capital: ${self.results['initial_capital']:,.2f}",
                f"Risk Per Trade: {self.results['risk_per_trade']}%",
                "",
                "Performance Metrics:",
                f"Total Trades: {metrics['total_trades']}",
                f"Win Rate: {metrics['win_rate']:.2%}",
                f"Profit Factor: {metrics['profit_factor']:.2f}",
                f"Net Profit: ${metrics['net_profit']:,.2f} ({metrics['net_profit_percentage']:.2f}%)",
                f"Max Drawdown: ${metrics['max_drawdown']:,.2f} ({metrics['max_drawdown_percentage']:.2f}%)",
                f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}",
                f"Average Win: ${metrics['average_win']:,.2f}",
                f"Average Loss: ${metrics['average_loss']:,.2f}",
                f"Largest Win: ${metrics['largest_win']:,.2f}",
                f"Largest Loss: ${metrics['largest_loss']:,.2f}",
                "",
                "Trade Summary:"
            ]
            
            # Add trade details
            for i, trade in enumerate(trades, 1):
                status = trade['status']
                pnl = trade.get('profit_loss', 0)
                pnl_str = f"${pnl:,.2f}" if pnl is not None else "N/A"
                
                trade_line = (
                    f"Trade {i}: {trade['type']} {trade['symbol']} @ {trade['entry']} "
                    f"(SL: {trade['stop_loss']}, TP: {trade['take_profit']}) "
                    f"- {status} - P/L: {pnl_str}"
                )
                report.append(trade_line)
            
            return "\n".join(report)
            
        elif output_format == 'html':
            # Generate HTML report (simplified)
            html = [
                "<html>",
                "<head>",
                "<style>",
                "body { font-family: Arial, sans-serif; margin: 20px; }",
                "h1, h2 { color: #333; }",
                "table { border-collapse: collapse; width: 100%; }",
                "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
                "th { background-color: #f2f2f2; }",
                "tr:nth-child(even) { background-color: #f9f9f9; }",
                ".positive { color: green; }",
                ".negative { color: red; }",
                "</style>",
                "</head>",
                "<body>",
                f"<h1>Backtest Report: {symbol} ({timeframe}, {period})</h1>",
                f"<p><strong>Strategy:</strong> {strategy}</p>",
                f"<p><strong>Initial Capital:</strong> ${self.results['initial_capital']:,.2f}</p>",
                f"<p><strong>Risk Per Trade:</strong> {self.results['risk_per_trade']}%</p>",
                "<h2>Performance Metrics</h2>",
                "<table>",
                "<tr><th>Metric</th><th>Value</th></tr>"
            ]
            
            # Add metrics to table
            for key, value in metrics.items():
                formatted_key = key.replace('_', ' ').title()
                
                if 'percentage' in key or key == 'win_rate':
                    formatted_value = f"{value:.2%}"
                elif 'profit' in key or 'loss' in key or 'drawdown' in key:
                    formatted_value = f"${value:,.2f}"
                else:
                    formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                
                html.append(f"<tr><td>{formatted_key}</td><td>{formatted_value}</td></tr>")
            
            html.append("</table>")
            
            # Add trade table
            html.extend([
                "<h2>Trade Summary</h2>",
                "<table>",
                "<tr><th>#</th><th>Type</th><th>Entry</th><th>Stop Loss</th><th>Take Profit</th><th>Status</th><th>P/L</th></tr>"
            ])
            
            for i, trade in enumerate(trades, 1):
                status = trade['status']
                pnl = trade.get('profit_loss', 0)
                pnl_class = "positive" if pnl and pnl > 0 else "negative"
                pnl_str = f"${pnl:,.2f}" if pnl is not None else "N/A"
                
                html.append(
                    f"<tr>"
                    f"<td>{i}</td>"
                    f"<td>{trade['type']}</td>"
                    f"<td>{trade['entry']:.5f}</td>"
                    f"<td>{trade['stop_loss']:.5f}</td>"
                    f"<td>{trade['take_profit']:.5f}</td>"
                    f"<td>{status}</td>"
                    f"<td class='{pnl_class}'>{pnl_str}</td>"
                    f"</tr>"
                )
            
            html.extend([
                "</table>",
                "</body>",
                "</html>"
            ])
            
            return "\n".join(html)
            
        elif output_format == 'image':
            # Generate image report with matplotlib
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [2, 1]})
            
            # Plot equity curve
            ax1.plot(range(len(equity)), equity, label='Equity Curve')
            ax1.set_title(f'Backtest Results: {symbol} ({timeframe}, {period})')
            ax1.set_ylabel('Equity ($)')
            ax1.grid(True)
            ax1.legend()
            
            # Add trade markers
            for trade in trades:
                if trade['status'] == 'CLOSED' and 'exit_date' in trade:
                    # Find index of entry and exit
                    try:
                        entry_idx = list(self.results['df'].index).index(trade['entry_date'])
                        exit_idx = list(self.results['df'].index).index(trade['exit_date'])
                        
                        # Plot entry and exit points
                        if trade['type'] == 'BUY':
                            ax1.plot(entry_idx, equity[entry_idx], '^', color='green', markersize=8)
                            if trade['profit_loss'] > 0:
                                ax1.plot(exit_idx, equity[exit_idx], 'o', color='green', markersize=8)
                            else:
                                ax1.plot(exit_idx, equity[exit_idx], 'o', color='red', markersize=8)
                        else:  # SELL
                            ax1.plot(entry_idx, equity[entry_idx], 'v', color='red', markersize=8)
                            if trade['profit_loss'] > 0:
                                ax1.plot(exit_idx, equity[exit_idx], 'o', color='green', markersize=8)
                            else:
                                ax1.plot(exit_idx, equity[exit_idx], 'o', color='red', markersize=8)
                    except (ValueError, KeyError):
                        # Skip if we can't find the index
                        pass
            
            # Plot drawdown
            max_equity = initial_capital
            drawdown = []
            
            for eq in equity:
                if eq > max_equity:
                    max_equity = eq
                drawdown.append((max_equity - eq) / max_equity * 100)
            
            ax2.fill_between(range(len(drawdown)), 0, drawdown, color='red', alpha=0.3)
            ax2.set_title('Drawdown (%)')
            ax2.set_xlabel('Trade Number')
            ax2.set_ylabel('Drawdown (%)')
            ax2.grid(True)
            
            # Add metrics as text
            metrics_text = (
                f"Total Trades: {metrics['total_trades']}\n"
                f"Win Rate: {metrics['win_rate']:.2%}\n"
                f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                f"Net Profit: ${metrics['net_profit']:,.2f} ({metrics['net_profit_percentage']:.2f}%)\n"
                f"Max Drawdown: {metrics['max_drawdown_percentage']:.2f}%\n"
                f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}"
            )
            
            # Add text box with metrics
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.05, 0.95, metrics_text, transform=ax1.transAxes, fontsize=10,
                    verticalalignment='top', bbox=props)
            
            plt.tight_layout()
            
            # Save figure to BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)
            
            return buf
        
        else:
            return "Unsupported output format"    
    async def generate_chart(self, with_analysis: bool = True) -> io.BytesIO:
        """
        Generate a chart of the backtest results
        
        Args:
            with_analysis (bool): Whether to include analysis markers
            
        Returns:
            io.BytesIO: Chart image
        """
        if not self.results or not self.results.get('success', False):
            # Return a simple error chart
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No backtest results available", 
                   horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)
            return buf
        
        # Get the data
        symbol = self.results['symbol']
        timeframe = self.results['timeframe']
        trades = self.results['trades']
        
        # We need the original dataframe for plotting
        if 'df' not in self.results:
            logger.warning("Original dataframe not available for chart generation")
            return self.generate_report(output_format='image')
        
        df = self.results['df']
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot OHLC data
        visualization.plot_ohlc(df, ax)
        
        # Add trade markers if analysis is enabled
        if with_analysis:
            for trade in trades:
                if 'entry_date' in trade:
                    try:
                        # Find the candle at entry date
                        entry_candle = df.loc[trade['entry_date']]
                        
                        # Plot entry marker
                        if trade['type'] == 'BUY':
                            ax.plot(trade['entry_date'], entry_candle['low'] * 0.999, '^', 
                                   color='green', markersize=10, label='Buy Entry')
                        else:  # SELL
                            ax.plot(trade['entry_date'], entry_candle['high'] * 1.001, 'v', 
                                   color='red', markersize=10, label='Sell Entry')
                        
                        # Plot stop loss and take profit levels
                        ax.axhline(y=trade['stop_loss'], color='red', linestyle='--', alpha=0.5)
                        ax.axhline(y=trade['take_profit'], color='green', linestyle='--', alpha=0.5)
                        
                        # If trade is closed, plot exit marker
                        if trade['status'] == 'CLOSED' and 'exit_date' in trade:
                            exit_candle = df.loc[trade['exit_date']]
                            ax.plot(trade['exit_date'], trade['exit_price'], 'o', 
                                   color='blue', markersize=10, label='Exit')
                    except (KeyError, ValueError):
                        # Skip if we can't find the candle
                        pass
        
        # Set title and labels
        ax.set_title(f"{symbol} ({timeframe}) Backtest Results")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        
        # Format x-axis dates
        fig.autofmt_xdate()
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Remove duplicate labels
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper left')
        
        # Save to BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
    async def run_multi_timeframe_backtest(self, symbol: str, timeframes: List[str], period: str = '1y',
                                         market_type: str = 'forex', initial_capital: float = 10000.0,
                                         risk_per_trade: float = 1.0) -> Dict:
        """
        Run a backtest using multi-timeframe analysis
        
        Args:
            symbol (str): Trading symbol
            timeframes (list): List of timeframes to analyze
            period (str): Time period ('1m', '3m', '6m', '1y', '2y', '5y')
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            initial_capital (float): Initial capital
            risk_per_trade (float): Risk percentage per trade
            
        Returns:
            dict: Backtest results
        """
        try:
            # Load historical data for each timeframe
            dfs = {}
            for timeframe in timeframes:
                df = await self.load_data(symbol, timeframe, period, market_type)
                if df is not None and not df.empty:
                    dfs[timeframe] = df
            
            if not dfs:
                return {
                    'success': False,
                    'message': f"Failed to load data for {symbol} (any timeframe)"
                }
            
            # Initialize combined strategy
            combined_strategy = CombinedStrategy()
            
            # Initialize backtest variables
            equity = [initial_capital]
            trades = []
            current_position = None
            capital = initial_capital
            
            # Use the lowest timeframe for trade execution
            execution_tf = min(timeframes, key=lambda tf: self._timeframe_to_minutes(tf))
            execution_df = dfs[execution_tf]
            
            # Ensure DataFrame has datetime index
            if not isinstance(execution_df.index, pd.DatetimeIndex):
                logger.warning("DataFrame index is not DatetimeIndex, attempting to convert")
                try:
                    if 'datetime' in execution_df.columns:
                        execution_df = execution_df.set_index('datetime')
                    else:
                        execution_df = execution_df.set_index(pd.DatetimeIndex(execution_df.index))
                except Exception as e:
                    logger.error(f"Failed to convert index to DatetimeIndex: {e}")
                    return {
                        'success': False,
                        'message': f"Failed to process data for {symbol}"
                    }
            
            # Ensure column names are lowercase
            execution_df.columns = [col.lower() for col in execution_df.columns]
            
            # Minimum required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in execution_df.columns for col in required_cols):
                logger.error(f"DataFrame missing required columns. Available: {execution_df.columns.tolist()}")
                return {
                    'success': False,
                    'message': f"Missing required columns for {symbol}"
                }
            
            # Iterate through each candle (starting from enough history for indicators)
            start_idx = 200  # Allow enough data for indicators
            
            for i in range(start_idx, len(execution_df)):
                # Get current date and price
                current_date = execution_df.index[i]
                current_price = execution_df.iloc[i]['close']
                
                # Update equity
                if current_position:
                    # Calculate current value of position
                    if current_position['type'] == 'BUY':
                        position_value = current_position['size'] * current_price
                    else:  # SELL
                        position_value = current_position['size'] * (2 * current_position['entry'] - current_price)
                    
                    # Update equity with position value
                    equity.append(capital + position_value - current_position['value'])
                else:
                    equity.append(capital)
                
                # Check for exit conditions if in a position
                if current_position:
                    # For long positions
                    if current_position['type'] == 'BUY':
                        # Check if take profit hit
                        if execution_df.iloc[i]['high'] >= current_position['take_profit']:
                            # Calculate profit
                            profit = current_position['size'] * (current_position['take_profit'] - current_position['entry'])
                            capital += profit
                            
                            # Record trade
                            trades.append({
                                'entry_date': current_position['date'],
                                'exit_date': current_date,
                                'type': current_position['type'],
                                'entry': current_position['entry'],
                                'exit': current_position['take_profit'],
                                'size': current_position['size'],
                                'profit': profit,
                                'profit_pct': (profit / current_position['value']) * 100,
                                'exit_reason': 'take_profit'
                            })
                            
                            # Reset position
                            current_position = None
                            continue
                        
                        # Check if stop loss hit
                        if execution_df.iloc[i]['low'] <= current_position['stop_loss']:
                            # Calculate loss
                            loss = current_position['size'] * (current_position['stop_loss'] - current_position['entry'])
                            capital += loss
                            
                            # Record trade
                            trades.append({
                                'entry_date': current_position['date'],
                                'exit_date': current_date,
                                'type': current_position['type'],
                                'entry': current_position['entry'],
                                'exit': current_position['stop_loss'],
                                'size': current_position['size'],
                                'profit': loss,
                                'profit_pct': (loss / current_position['value']) * 100,
                                'exit_reason': 'stop_loss'
                            })
                            
                            # Reset position
                            current_position = None
                            continue
                    
                    # For short positions
                    else:  # SELL
                        # Check if take profit hit
                        if execution_df.iloc[i]['low'] <= current_position['take_profit']:
                            # Calculate profit
                            profit = current_position['size'] * (current_position['entry'] - current_position['take_profit'])
                            capital += profit
                            
                            # Record trade
                            trades.append({
                                'entry_date': current_position['date'],
                                'exit_date': current_date,
                                'type': current_position['type'],
                                'entry': current_position['entry'],
                                'exit': current_position['take_profit'],
                                'size': current_position['size'],
                                'profit': profit,
                                'profit_pct': (profit / current_position['value']) * 100,
                                'exit_reason': 'take_profit'
                            })
                            
                            # Reset position
                            current_position = None
                            continue
                        
                        # Check if stop loss hit
                        if execution_df.iloc[i]['high'] >= current_position['stop_loss']:
                            # Calculate loss
                            loss = current_position['size'] * (current_position['entry'] - current_position['stop_loss'])
                            capital += loss
                            
                            # Record trade
                            trades.append({
                                'entry_date': current_position['date'],
                                'exit_date': current_date,
                                'type': current_position['type'],
                                'entry': current_position['entry'],
                                'exit': current_position['stop_loss'],
                                'size': current_position['size'],
                                'profit': loss,
                                'profit_pct': (loss / current_position['value']) * 100,
                                'exit_reason': 'stop_loss'
                            })
                            
                            # Reset position
                            current_position = None
                            continue
                
                # Only look for new trades if not in a position
                if not current_position:
                    # Prepare multi-timeframe data up to current candle
                    current_dfs = {}
                    for tf, df in dfs.items():
                        # Filter data up to current date
                        current_dfs[tf] = df[df.index <= current_date].copy()
                    
                    # Perform multi-timeframe analysis
                    mtf_analysis = combined_strategy.get_multi_timeframe_analysis(current_dfs, symbol, market_type)
                    
                    # Get LTF entries that align with HTF POIs
                    ltf_entries = mtf_analysis.get('ltf_entries', [])
                    
                    # Filter for high-quality setups (RR >= 3)
                    quality_setups = [setup for setup in ltf_entries if setup.get('risk_reward', 0) >= 3]
                    
                    if quality_setups:
                        # Take the highest RR setup
                        setup = max(quality_setups, key=lambda x: x.get('risk_reward', 0))
                        
                        # Calculate position size based on risk
                        risk_amount = capital * (risk_per_trade / 100)
                        
                        if setup['direction'] == 'BUY':
                            # Calculate risk per unit
                            risk_per_unit = setup['entry'] - setup['stop_loss']
                            
                            if risk_per_unit > 0:
                                # Calculate position size
                                position_size = risk_amount / risk_per_unit
                                position_value = position_size * setup['entry']
                                
                                # Enter long position
                                current_position = {
                                    'date': current_date,
                                    'type': 'BUY',
                                    'entry': setup['entry'],
                                    'stop_loss': setup['stop_loss'],
                                    'take_profit': setup['take_profit'],
                                    'size': position_size,
                                    'value': position_value,
                                    'risk': risk_amount
                                }
                        
                        elif setup['direction'] == 'SELL':
                            # Calculate risk per unit
                            risk_per_unit = setup['stop_loss'] - setup['entry']
                            
                            if risk_per_unit > 0:
                                # Calculate position size
                                position_size = risk_amount / risk_per_unit
                                position_value = position_size * setup['entry']
                                
                                # Enter short position
                                current_position = {
                                    'date': current_date,
                                    'type': 'SELL',
                                    'entry': setup['entry'],
                                    'stop_loss': setup['stop_loss'],
                                    'take_profit': setup['take_profit'],
                                    'size': position_size,
                                    'value': position_value,
                                    'risk': risk_amount
                                }
            
            # Close any open position at the end of the backtest
            if current_position:
                final_price = execution_df.iloc[-1]['close']
                
                if current_position['type'] == 'BUY':
                    profit = current_position['size'] * (final_price - current_position['entry'])
                else:  # SELL
                    profit = current_position['size'] * (current_position['entry'] - final_price)
                
                capital += profit
                
                # Record trade
                trades.append({
                    'entry_date': current_position['date'],
                    'exit_date': execution_df.index[-1],
                    'type': current_position['type'],
                    'entry': current_position['entry'],
                    'exit': final_price,
                    'size': current_position['size'],
                    'profit': profit,
                    'profit_pct': (profit / current_position['value']) * 100,
                    'exit_reason': 'end_of_test'
                })
                
                # Update final equity
                equity[-1] = capital
            
            # Calculate performance metrics
            win_trades = [t for t in trades if t['profit'] > 0]
            loss_trades = [t for t in trades if t['profit'] <= 0]
            
            win_rate = len(win_trades) / len(trades) if trades else 0
            avg_win = sum(t['profit'] for t in win_trades) / len(win_trades) if win_trades else 0
            avg_loss = sum(t['profit'] for t in loss_trades) / len(loss_trades) if loss_trades else 0
            profit_factor = abs(sum(t['profit'] for t in win_trades) / sum(t['profit'] for t in loss_trades)) if loss_trades and sum(t['profit'] for t in loss_trades) != 0 else float('inf')
            
            # Calculate average RR
            avg_rr = 0
            if trades:
                rr_values = []
                for trade in trades:
                    if trade['type'] == 'BUY':
                        risk = trade['entry'] - trade['stop_loss'] if 'stop_loss' in trade else 0
                        reward = trade['exit'] - trade['entry']
                    else:  # SELL
                        risk = trade['stop_loss'] - trade['entry'] if 'stop_loss' in trade else 0
                        reward = trade['entry'] - trade['exit']
                    
                    if risk > 0:
                        rr_values.append(abs(reward / risk))
                
                avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0
            
            # Compile results
            results = {
                'success': True,
                'symbol': symbol,
                'timeframes': timeframes,
                'period': period,
                'market_type': market_type,
                'initial_capital': initial_capital,
                'final_capital': equity[-1],
                'profit': equity[-1] - initial_capital,
                'profit_pct': ((equity[-1] / initial_capital) - 1) * 100,
                'trades': trades,
                'equity': equity,
                'trade_count': len(trades),
                'win_count': len(win_trades),
                'loss_count': len(loss_trades),
                'win_rate': win_rate * 100,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'avg_rr': avg_rr,
                'execution_timeframe': execution_tf,
                'df': execution_df  # Include the execution dataframe for charting
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error in multi-timeframe backtest: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f"Error running backtest: {str(e)}"
            }
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe string to minutes
        
        Args:
            timeframe (str): Timeframe string (e.g., '1m', '1h', '1d')
            
        Returns:
            int: Minutes
        """
        if not timeframe:
            return 0
        
        # Extract number and unit
        import re
        match = re.match(r'(\d+)([mhdw])', timeframe.lower())
        if not match:
            return 0
        
        number, unit = match.groups()
        number = int(number)
        
        # Convert to minutes
        if unit == 'm':
            return number
        elif unit == 'h':
            return number * 60
        elif unit == 'd':
            return number * 60 * 24
        elif unit == 'w':
            return number * 60 * 24 * 7
        else:
            return 0
