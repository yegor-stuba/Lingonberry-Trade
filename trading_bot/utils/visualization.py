"""
Chart generation for Telegram
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import io
import logging
import mplfinance as mpf
from datetime import datetime, timedelta

from trading_bot.config import settings

logger = logging.getLogger(__name__)

def normalize_dataframe(df):
    """
    Normalize DataFrame column names to ensure compatibility
    
    Args:
        df (pandas.DataFrame): Input DataFrame
        
    Returns:
        pandas.DataFrame: Normalized DataFrame
    """
    column_map = {
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
        'o': 'open',
        'h': 'high',
        'l': 'low',
        'c': 'close',
        'v': 'volume'
    }
    
    df_copy = df.copy()
    for old_col, new_col in column_map.items():
        if old_col in df_copy.columns and new_col not in df_copy.columns:
            df_copy[new_col] = df_copy[old_col]
    
    return df_copy

def create_price_chart(df, symbol, timeframe, indicators=None, timestamp=None):
    """
    Create a price chart with indicators
    
    Args:
        df (pandas.DataFrame): OHLCV data
        symbol (str): Trading symbol
        timeframe (str): Timeframe (e.g., '15m', '1h')
        indicators (dict, optional): Dictionary of indicators to add
        timestamp (str, optional): Timestamp of when the analysis was performed
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Ensure DataFrame has the right format for mplfinance
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            logger.error("DataFrame missing required OHLCV columns")
            return None
        
        # Make sure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            else:
                logger.error("DataFrame needs a datetime index or column")
                return None
        
        # Prepare plot style - Black and white theme
        mc = mpf.make_marketcolors(
            up='white', down='black',
            wick={'up': 'white', 'down': 'black'},
            volume={'up': 'white', 'down': 'black'},
            edge={'up': 'black', 'down': 'black'},
            ohlc='black'
        )
        
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            y_on_right=False,
            facecolor='white',
            figcolor='white',
            edgecolor='black',
            gridcolor='lightgray'
        )
        
        # Prepare additional plots for indicators
        apds = []
        
        if indicators:
            # Add moving averages
            if 'ma' in indicators:
                for period in indicators['ma']:
                    df[f'ma{period}'] = df['close'].rolling(window=period).mean()
                    apds.append(
                        mpf.make_addplot(df[f'ma{period}'], color='black', width=1, linestyle=f'-')
                    )
            
            # Add RSI
            if 'rsi' in indicators:
                period = indicators['rsi']
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=period).mean()
                avg_loss = loss.rolling(window=period).mean()
                rs = avg_gain / avg_loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
                # Create a separate subplot for RSI
                apds.append(
                    mpf.make_addplot(df['rsi'], panel=1, color='black', 
                                     secondary_y=False, ylabel='RSI')
                )
                
                # Add RSI overbought/oversold lines
                apds.append(
                    mpf.make_addplot([70] * len(df), panel=1, color='black', 
                                     linestyle='--', secondary_y=False)
                )
                apds.append(
                    mpf.make_addplot([30] * len(df), panel=1, color='black', 
                                     linestyle='--', secondary_y=False)
                )
        
        # Create the plot
        title = f'{symbol} - {timeframe} Chart'
        if timestamp:
            title += f' (Analysis: {timestamp})'
        
        # Save to bytes buffer
        buf = io.BytesIO()
        
        # Create the plot with volume and indicators
        mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            volume=True,
            addplot=apds if apds else None,
            panel_ratios=(4, 1) if 'rsi' in indicators else None,
            figratio=(12, 8),
            figscale=1.5,
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error creating price chart: {e}")
        return None

def create_trade_chart(df, trade_data, timestamp=None):
    """
    Create a chart with trade entry, stop loss, and take profit levels
    
    Args:
        df (pandas.DataFrame): OHLCV data
        trade_data (dict): Trade data including entry, stop loss, take profit
        timestamp (str, optional): Timestamp of when the trade was suggested
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Ensure DataFrame has the right format for mplfinance
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            logger.error("DataFrame missing required OHLCV columns")
            return None
        
        # Make sure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            else:
                logger.error("DataFrame needs a datetime index or column")
                return None
        
        # Extract trade details
        symbol = trade_data.get('symbol', 'Unknown')
        direction = trade_data.get('direction', 'BUY')
        entry_price = trade_data.get('entry_price', 0)
        stop_loss = trade_data.get('stop_loss', 0)
        take_profit = trade_data.get('take_profit', 0)
        
        # Prepare plot style - Black and white theme
        mc = mpf.make_marketcolors(
            up='white', down='black',
            wick={'up': 'white', 'down': 'black'},
            volume={'up': 'white', 'down': 'black'},
            edge={'up': 'black', 'down': 'black'},
            ohlc='black'
        )
        
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            y_on_right=False,
            facecolor='white',
            figcolor='white',
            edgecolor='black',
            gridcolor='lightgray'
        )
        
        # Create horizontal lines for entry, SL, TP
        entry_line = [entry_price] * len(df)
        sl_line = [stop_loss] * len(df)
        tp_line = [take_profit] * len(df)
        
        # Prepare additional plots
        apds = [
            mpf.make_addplot(entry_line, color='black', linestyle='--', width=1),
            mpf.make_addplot(sl_line, color='black', linestyle=':', width=1),
            mpf.make_addplot(tp_line, color='black', linestyle='-.', width=1)
        ]
        
        # Create the plot
        title = f'{symbol} - {direction} Trade'
        if timestamp:
            title += f' (Suggested: {timestamp})'
        
        # Save to bytes buffer
        buf = io.BytesIO()
        
        # Create the plot with volume and trade levels
        mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            volume=True,
            addplot=apds,
            figratio=(12, 8),
            figscale=1.5,
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error creating trade chart: {e}")
        return None

def create_smc_chart(df, smc_elements):
    """
    Create a chart with Smart Money Concepts elements
    
    Args:
        df (pandas.DataFrame): OHLCV data
        smc_elements (dict): Dictionary of SMC elements to add
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Ensure DataFrame has the right format for mplfinance
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            logger.error("DataFrame missing required OHLCV columns")
            return None
        
        # Make sure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            else:
                logger.error("DataFrame needs a datetime index or column")
                return None
        
        # Prepare plot style
        mc = mpf.make_marketcolors(
            up='green', down='red',
            wick={'up': 'green', 'down': 'red'},
            volume={'up': 'green', 'down': 'red'}
        )
        
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            y_on_right=False,
            facecolor='black',
            figcolor='black',
            edgecolor='white',
            gridcolor='gray'
        )
        
        # Prepare additional plots for SMC elements
        apds = []
        
        # Add order blocks
        if 'order_blocks' in smc_elements:
            for ob in smc_elements['order_blocks']:
                # Create rectangle for order block
                top = ob.get('top', 0)
                bottom = ob.get('bottom', 0)
                start_idx = df.index.get_loc(ob.get('datetime'))
                end_idx = min(start_idx + 5, len(df) - 1)  # Show order block for 5 candles
                
                # Create rectangle coordinates
                rect_x = [df.index[start_idx], df.index[end_idx]]
                rect_y_top = [top, top]
                rect_y_bottom = [bottom, bottom]
                
                # Plot rectangle
                color = 'green' if ob.get('type') == 'bullish' else 'red'
                alpha = min(0.3, ob.get('strength', 50) / 200)  # Adjust transparency based on strength
                
                apds.append(
                    mpf.make_addplot([top] * len(df), color=color, linestyle='-', width=1, alpha=alpha)
                )
                apds.append(
                    mpf.make_addplot([bottom] * len(df), color=color, linestyle='-', width=1, alpha=alpha)
                )
        
        # Add fair value gaps
        if 'fair_value_gaps' in smc_elements:
            for fvg in smc_elements['fair_value_gaps']:
                # Create rectangle patches for fair value gaps
                # This is a placeholder - actual implementation would depend on how you define FVGs
                pass
        
        # Add liquidity levels
        if 'liquidity_levels' in smc_elements:
            for level in smc_elements['liquidity_levels']:
                level_price = level['price']
                level_type = level['type']  # 'buy' or 'sell'
                
                # Create horizontal line for liquidity level
                level_line = [level_price] * len(df)
                color = 'green' if level_type == 'buy' else 'red'
                
                apds.append(
                    mpf.make_addplot(level_line, color=color, linestyle='-', width=2)
                )
        
        # Create the plot
        title = 'Smart Money Concepts Analysis'
        
        # Save to bytes buffer
        buf = io.BytesIO()
        
        # Create the plot with volume and SMC elements
        mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            volume=True,
            addplot=apds if apds else None,
            figratio=(12, 8),
            figscale=1.5,
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error creating SMC chart: {e}")
        return None

def create_multi_timeframe_chart(dataframes, symbol):
    """
    Create a multi-timeframe chart
    
    Args:
        dataframes (dict): Dictionary of DataFrames for different timeframes
        symbol (str): Trading symbol
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Create a figure with multiple subplots
        fig, axes = plt.subplots(len(dataframes), 1, figsize=(12, 4 * len(dataframes)), dpi=100)
        plt.style.use(settings.CHART_STYLE)
        
        # If only one timeframe, axes will not be an array
        if len(dataframes) == 1:
            axes = [axes]
        
        # Plot each timeframe
        for i, (timeframe, df) in enumerate(dataframes.items()):
            ax = axes[i]
            
            # Plot candlesticks
            width = 0.6
            width2 = width * 0.8
            
            up = df[df.close >= df.open]
            down = df[df.close < df.open]
            
            # Plot up candles
            ax.bar(up.index, up.close - up.open, width, bottom=up.open, color='green')
            ax.bar(up.index, up.high - up.close, width2, bottom=up.close, color='green')
            ax.bar(up.index, up.open - up.low, width2, bottom=up.low, color='green')
            
            # Plot down candles
            ax.bar(down.index, down.open - down.close, width, bottom=down.close, color='red')
            ax.bar(down.index, down.high - down.open, width2, bottom=down.open, color='red')
            ax.bar(down.index, down.close - down.low, width2, bottom=down.low, color='red')
            
            # Set title and labels
            ax.set_title(f'{symbol} - {timeframe}')
            ax.set_ylabel('Price')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Adjust layout
        plt.tight_layout()
        
        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        logger.error(f"Error creating multi-timeframe chart: {e}")
        return None

def create_analysis_chart(df, symbol, timeframe, analysis_result, timestamp=None):
    """
    Create a comprehensive analysis chart with both technical and SMC elements
    
    Args:
        df (pandas.DataFrame): OHLCV data
        symbol (str): Trading symbol
        timeframe (str): Timeframe
        analysis_result (dict): Combined analysis result
        timestamp (str, optional): Timestamp of analysis
        
    Returns:
        bytes: PNG image data
    """
    try:
        # Normalize DataFrame
        df = normalize_dataframe(df)
        
        # Ensure DataFrame has the right format for mplfinance
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            logger.error("DataFrame missing required OHLCV columns")
            return None
        
        # Make sure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            else:
                logger.error("DataFrame needs a datetime index or column")
                return None
        
        # Prepare plot style
        mc = mpf.make_marketcolors(
            up='green', down='red',
            wick={'up': 'green', 'down': 'red'},
            volume={'up': 'green', 'down': 'red'}
        )
        
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            y_on_right=False
        )
        
        # Prepare additional plots
        apds = []
        
        # Add technical indicators
        if 'technical' in analysis_result:
            tech = analysis_result['technical']
            # Add moving averages if available
            if 'indicators' in tech and 'ma' in tech['indicators']:
                for period, values in tech['indicators']['ma'].items():
                    if isinstance(values, list) and len(values) == len(df):
                        apds.append(
                            mpf.make_addplot(values, color='blue', width=1, linestyle=f'-')
                        )
        
        # Even if no trade setup, still show key levels and indicators
        if 'technical' in analysis_result:
            tech = analysis_result['technical']
            # Add key levels
            if 'key_levels' in tech:
                for level_type, levels in tech['key_levels'].items():
                    for level in levels:
                        color = 'blue' if level_type == 'support' else 'red'
                        apds.append(
                            mpf.make_addplot([level] * len(df), color=color, linestyle='--', width=1)
                        )
        
        # Add SMC elements
        if 'smc' in analysis_result:
            smc = analysis_result['smc']
            
            # Add market structure visualization
            if 'market_structure' in smc:
                structure = smc['market_structure']
                # Visualize trend, swing highs/lows, etc.
            
            # Add key levels
            if 'key_levels' in smc:
                for level in smc['key_levels']:
                    color = 'blue' if level['type'] == 'support' else 'red'
                    apds.append(
                        mpf.make_addplot([level['price']] * len(df), color=color, linestyle='--', width=1)
                    )
            
            # Add order blocks
            if 'order_blocks' in smc:
                for ob in smc['order_blocks']:
                    # Add visualization for order blocks
                    # (Implementation as suggested above)
                    pass
            
            # Add fair value gaps
            if 'fair_value_gaps' in smc:
                for fvg in smc['fair_value_gaps']:
                    # Add visualization for FVGs
                    pass
            
            # Add liquidity levels
            if 'liquidity_levels' in smc:
                for level in smc['liquidity_levels']:
                    level_price = level['price']
                    level_type = level['type']
                    
                    color = 'green' if level_type == 'low' else 'red'
                    apds.append(
                        mpf.make_addplot([level_price] * len(df), color=color, linestyle='--', width=1)
                    )
        
        # Add trade setup if available
        if 'trade_setup' in analysis_result:
            setup = analysis_result['trade_setup']
            entry = setup.get('entry', 0)
            sl = setup.get('stop_loss', 0)
            tp = setup.get('take_profit', 0)
            
            apds.append(mpf.make_addplot([entry] * len(df), color='black', linestyle='-', width=2))
            apds.append(mpf.make_addplot([sl] * len(df), color='red', linestyle='--', width=1))
            apds.append(mpf.make_addplot([tp] * len(df), color='green', linestyle='--', width=1))
        
        # Create the plot
        title = f'{symbol} - {timeframe} Analysis'
        if timestamp:
            title += f' (as of {timestamp})'
        
        # Save to bytes buffer
        buf = io.BytesIO()
        
        # Create the plot with volume and analysis elements
        mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            volume=True,
            addplot=apds if apds else None,
            figratio=(12, 8),
            figscale=1.5,
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error creating analysis chart: {e}")
        return None
