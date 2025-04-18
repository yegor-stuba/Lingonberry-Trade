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
import pytz

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

def is_night_time(timezone='Europe/London'):
    """
    Check if it's night time in the specified timezone
    
    Args:
        timezone (str): Timezone to check
        
    Returns:
        bool: True if it's night time (7 PM - 7 AM), False otherwise
    """
    try:
        # Get current time in the specified timezone
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        
        # Check if it's night time (7 PM - 7 AM)
        return current_time.hour >= 19 or current_time.hour < 7
    except Exception as e:
        logger.error(f"Error determining time of day: {e}")
        # Default to day time if there's an error
        return False

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
    import io
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    
    try:
        # Ensure DataFrame has the right format for mplfinance
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            logger.error("DataFrame missing required OHLC columns")
            return None
        
        # Make sure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'datetime' in df.columns:
                df.set_index('datetime', inplace=True)
            else:
                logger.error("DataFrame needs a datetime index or column")
                return None
        
        # Handle NaN values
        df = df.dropna()
        
        # Ensure we have data
        if len(df) == 0:
            logger.error("DataFrame is empty after dropping NaN values")
            return None
        
        # Determine if it's night time for theme selection
        use_dark_theme = is_night_time()
        
        # Prepare plot style based on time of day
        if use_dark_theme:
            # Dark theme (night)
            mc = mpf.make_marketcolors(
                up='#00e676', down='#ff5252',
                wick={'up': '#00e676', 'down': '#ff5252'},
                edge={'up': '#00e676', 'down': '#ff5252'},
                volume={'up': '#00e676', 'down': '#ff5252'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='#212121',
                figcolor='#212121',
                edgecolor='#424242',
                gridcolor='#424242',
                rc={'font.size': 10, 'text.color': '#e0e0e0', 'axes.labelcolor': '#e0e0e0',
                    'axes.edgecolor': '#424242', 'xtick.color': '#e0e0e0', 'ytick.color': '#e0e0e0'}
            )
        else:
            # Light theme (day)
            mc = mpf.make_marketcolors(
                up='#26a69a', down='#ef5350',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                edge={'up': '#26a69a', 'down': '#ef5350'},
                volume={'up': '#26a69a', 'down': '#ef5350'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='white',
                figcolor='white',
                edgecolor='black',
                gridcolor='#e0e0e0',
                rc={'font.size': 10}
            )
        
        # Create the plot
        title = f'{symbol} - {timeframe} Chart'
        if timestamp:
            title += f' (Analysis: {timestamp})'
        
        # Save to bytes buffer
        buf = io.BytesIO()
        
        # Plot without volume for cleaner look
        mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            volume=False,
            figsize=(12, 8),
            addplot=[],
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error creating price chart: {e}", exc_info=True)
        plt.close('all')  # Close any open figures
        return None

def create_trade_chart(df, trade_data, timestamp=None):
    """
    Create a chart with trade entry, stop loss, and take profit levels
    
    Args:
        df (pandas.DataFrame): OHLCV data
        trade_data (dict): Trade data including entry, stop loss, take profit
        timestamp (str, optional): Timestamp for the chart
        
    Returns:
        io.BytesIO: Buffer containing the chart image
    """
    import io
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    from datetime import datetime
    
    # Create a buffer for the image
    buf = io.BytesIO()
    
    try:
        # Check if we have data
        if df is None or df.empty:
            return None
            
        # Get the last 50 candles or all if less
        num_candles = min(50, len(df))
        df_plot = df.tail(num_candles).copy()
        
        # Extract trade data
        symbol = trade_data.get('symbol', 'Unknown')
        direction = trade_data.get('direction', 'Unknown')
        entry_price = trade_data.get('entry_price', 0)
        stop_loss = trade_data.get('stop_loss', 0)
        take_profit = trade_data.get('take_profit', 0)
        risk_reward = trade_data.get('risk_reward', 0)
        
        # Determine if it's night time for theme selection
        use_dark_theme = is_night_time()
        
        # Set up custom style based on time of day
        if use_dark_theme:
            # Dark theme (night)
            mc = mpf.make_marketcolors(
                up='#00e676', down='#ff5252',
                wick={'up': '#00e676', 'down': '#ff5252'},
                edge={'up': '#00e676', 'down': '#ff5252'},
                volume={'up': '#00e676', 'down': '#ff5252'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='#212121',
                figcolor='#212121',
                edgecolor='#424242',
                gridcolor='#424242',
                rc={'font.size': 10, 'text.color': '#e0e0e0', 'axes.labelcolor': '#e0e0e0',
                    'axes.edgecolor': '#424242', 'xtick.color': '#e0e0e0', 'ytick.color': '#e0e0e0'}
            )
            
            # Colors for annotations
            entry_color = '#2196f3'
            sl_color = '#ff5252'
            tp_color = '#00e676'
            text_color = '#e0e0e0'
            box_color = '#424242'
        else:
            # Light theme (day)
            mc = mpf.make_marketcolors(
                up='#26a69a', down='#ef5350',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                edge={'up': '#26a69a', 'down': '#ef5350'},
                volume={'up': '#26a69a', 'down': '#ef5350'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='white',
                figcolor='white',
                edgecolor='black',
                gridcolor='#e0e0e0',
                rc={'font.size': 10}
            )
            
            # Colors for annotations
            entry_color = 'blue'
            sl_color = 'red'
            tp_color = 'green'
            text_color = 'black'
            box_color = 'white'
        
        # Create horizontal lines for entry, SL, TP
        hlines = {
            'hlines': [entry_price, stop_loss, take_profit],
            'colors': [entry_color, sl_color, tp_color],
            'linewidths': [1.5, 1.5, 1.5],
            'linestyle': '-'
        }
        
        # Add timestamp if provided, otherwise use current time
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = f"{symbol} - {direction} Setup ({timestamp})"
        
        # Plot the chart without volume for cleaner look
        fig, axes = mpf.plot(
            df_plot,
            type='candle',
            style=s,
            title=title,
            hlines=hlines,
            volume=False,
            figsize=(12, 8),
            returnfig=True
        )
        
        # Add annotations for entry, SL, TP, and R/R
        ax = axes[0]
        
        # Format prices based on symbol type
        if 'JPY' in symbol:
            price_format = "{:.3f}"
        elif 'XAU' in symbol:
            price_format = "{:.2f}"
        else:
            price_format = "{:.5f}"
        
        # Add text annotations with better formatting and more spacing
        ax.text(0.02, 0.98, f"Entry: {price_format.format(entry_price)}", 
                transform=ax.transAxes, color=entry_color, fontsize=10, 
                verticalalignment='top', bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=entry_color, boxstyle='round,pad=0.5'))
        
        ax.text(0.02, 0.91, f"Stop Loss: {price_format.format(stop_loss)}", 
                transform=ax.transAxes, color=sl_color, fontsize=10, 
                verticalalignment='top', bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=sl_color, boxstyle='round,pad=0.5'))
        
        ax.text(0.02, 0.84, f"Take Profit: {price_format.format(take_profit)}", 
                transform=ax.transAxes, color=tp_color, fontsize=10, 
                verticalalignment='top', bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=tp_color, boxstyle='round,pad=0.5'))
        
        ax.text(0.02, 0.77, f"Risk/Reward: {risk_reward:.2f}", 
                transform=ax.transAxes, color=text_color, fontsize=10, 
                verticalalignment='top', bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=text_color, boxstyle='round,pad=0.5'))
        
        # Add direction arrow
        arrow_y = entry_price
        arrow_x = df_plot.index[-10]  # Position the arrow near the end
        
        if direction == 'BUY':
            arrow_start_y = arrow_y - (df_plot['high'].max() - df_plot['low'].min()) * 0.05
            arrow_end_y = arrow_y + (df_plot['high'].max() - df_plot['low'].min()) * 0.05
            ax.annotate('BUY', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_start_y),
                        arrowprops=dict(facecolor=tp_color, shrink=0.05, width=2, headwidth=8),
                        ha='center', va='bottom', fontsize=12, color=tp_color,
                        bbox=dict(boxstyle='round,pad=0.5', fc=box_color, alpha=0.8))
        else:  # SELL
            arrow_start_y = arrow_y + (df_plot['high'].max() - df_plot['low'].min()) * 0.05
            arrow_end_y = arrow_y - (df_plot['high'].max() - df_plot['low'].min()) * 0.05
            ax.annotate('SELL', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_start_y),
                        arrowprops=dict(facecolor=sl_color, shrink=0.05, width=2, headwidth=8),
                        ha='center', va='top', fontsize=12, color=sl_color,
                        bbox=dict(boxstyle='round,pad=0.5', fc=box_color, alpha=0.8))
        
        # Save to buffer
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        # Reset buffer position
        buf.seek(0)
        
        return buf
        
    except Exception as e:
        logger.error(f"Error creating trade chart: {e}", exc_info=True)
        plt.close('all')  # Close any open figures
        return None

def create_analysis_chart(df, analysis_data, timestamp=None):
    """
    Create a chart with technical analysis indicators and annotations
    
    Args:
        df (pandas.DataFrame): OHLCV data
        analysis_data (dict): Analysis data including key levels, patterns, etc.
        timestamp (str, optional): Timestamp for the chart
        
    Returns:
        io.BytesIO: Buffer containing the chart image
    """
    import io
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    from datetime import datetime
    
    # Create a buffer for the image
    buf = io.BytesIO()
    
    try:
        # Check if we have data
        if df is None or df.empty:
            return None
            
        # Get the last 100 candles or all if less
        num_candles = min(100, len(df))
        df_plot = df.tail(num_candles).copy()
        
        # Extract analysis data
        symbol = analysis_data.get('symbol', 'Unknown')
        bias = analysis_data.get('bias', 'neutral')
        key_levels = analysis_data.get('key_levels', [])
        patterns = analysis_data.get('patterns', [])
        
        # Determine if it's night time for theme selection
        use_dark_theme = is_night_time()
        
        # Set up custom style based on time of day
        if use_dark_theme:
            # Dark theme (night)
            mc = mpf.make_marketcolors(
                up='#00e676', down='#ff5252',
                wick={'up': '#00e676', 'down': '#ff5252'},
                edge={'up': '#00e676', 'down': '#ff5252'},
                volume={'up': '#00e676', 'down': '#ff5252'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='#212121',
                figcolor='#212121',
                edgecolor='#424242',
                gridcolor='#424242',
                rc={'font.size': 10, 'text.color': '#e0e0e0', 'axes.labelcolor': '#e0e0e0',
                    'axes.edgecolor': '#424242', 'xtick.color': '#e0e0e0', 'ytick.color': '#e0e0e0'}
            )
            
            # Colors for annotations
            support_color = '#00e676'
            resistance_color = '#ff5252'
            text_color = '#e0e0e0'
            box_color = '#424242'
        else:
            # Light theme (day)
            mc = mpf.make_marketcolors(
                up='#26a69a', down='#ef5350',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                edge={'up': '#26a69a', 'down': '#ef5350'},
                volume={'up': '#26a69a', 'down': '#ef5350'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True,
                facecolor='white',
                figcolor='white',
                edgecolor='black',
                gridcolor='#e0e0e0',
                rc={'font.size': 10}
            )
            
            # Colors for annotations
            support_color = 'green'
            resistance_color = 'red'
            text_color = 'black'
            box_color = 'white'
        
        # Create horizontal lines for key levels
        hlines = []
        hcolors = []
        
        for level in key_levels:
            level_price = level.get('price', 0)
            level_type = level.get('type', '')
            
            if level_price > 0:
                hlines.append(level_price)
                if level_type.lower() == 'support':
                    hcolors.append(support_color)
                elif level_type.lower() == 'resistance':
                    hcolors.append(resistance_color)
                else:
                    hcolors.append('gray')
        
        hlines_dict = {
            'hlines': hlines,
            'colors': hcolors,
            'linewidths': [1.5] * len(hlines),
            'linestyle': '--'
        }
        
        # Add timestamp if provided, otherwise use current time
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create title with bias
        bias_emoji = "🔴" if bias == "bearish" else "🟢" if bias == "bullish" else "⚪"
        title = f"{symbol} Analysis {bias_emoji} ({timestamp})"
        
        # Create additional plots for indicators if provided
        apds = []
        
        # Add moving averages if available
        if 'indicators' in analysis_data:
            indicators = analysis_data['indicators']
            
            # Add EMA 20
            if 'ema20' in indicators:
                ema20 = indicators['ema20']
                apds.append(mpf.make_addplot(ema20, color='#f48fb1', width=1))
            
            # Add EMA 50
            if 'ema50' in indicators:
                ema50 = indicators['ema50']
                apds.append(mpf.make_addplot(ema50, color='#90caf9', width=1))
            
            # Add EMA 200
            if 'ema200' in indicators:
                ema200 = indicators['ema200']
                apds.append(mpf.make_addplot(ema200, color='#ffcc80', width=1.5))
        
        # Plot the chart without volume for cleaner look
        fig, axes = mpf.plot(
            df_plot,
            type='candle',
            style=s,
            title=title,
            hlines=hlines_dict if hlines else None,
            volume=False,
            figsize=(12, 8),
            addplot=apds,
            returnfig=True
        )
        
        # Add annotations for key levels
        ax = axes[0]
        
        # Format prices based on symbol type
        if 'JPY' in symbol:
            price_format = "{:.3f}"
        elif 'XAU' in symbol:
            price_format = "{:.2f}"
        else:
            price_format = "{:.5f}"
        
        # Add text annotations for key levels
        y_positions = {}  # Track y-positions to avoid overlap
        
        for i, level in enumerate(key_levels):
            level_price = level.get('price', 0)
            level_type = level.get('type', '')
            level_strength = level.get('strength', 0)
            
            if level_price > 0:
                # Determine color based on level type
                color = support_color if level_type.lower() == 'support' else resistance_color
                
                # Find a position for the text that doesn't overlap
                y_pos = 0.98 - (i * 0.07)
                while y_pos in y_positions and y_pos > 0.1:
                    y_pos -= 0.07
                
                y_positions[y_pos] = True
                
                # Add the annotation
                ax.text(0.02, y_pos, 
                        f"{level_type.capitalize()}: {price_format.format(level_price)} (Strength: {level_strength})", 
                        transform=ax.transAxes, color=color, fontsize=9, 
                        verticalalignment='top', bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=color, boxstyle='round,pad=0.5'))
        
        # Add bias annotation
        bias_color = support_color if bias == "bullish" else resistance_color if bias == "bearish" else "gray"
        ax.text(0.98, 0.98, f"Bias: {bias.capitalize()}", 
                transform=ax.transAxes, color=bias_color, fontsize=10, 
                horizontalalignment='right', verticalalignment='top', 
                bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=bias_color, boxstyle='round,pad=0.5'))
        
        # Add pattern annotations if available
        if patterns:
            for i, pattern in enumerate(patterns[:3]):  # Show up to 3 patterns
                pattern_name = pattern.get('name', '')
                pattern_type = pattern.get('type', '')
                
                color = support_color if pattern_type.lower() == 'bullish' else resistance_color if pattern_type.lower() == 'bearish' else "gray"
                
                ax.text(0.98, 0.91 - (i * 0.07), f"Pattern: {pattern_name}", 
                        transform=ax.transAxes, color=color, fontsize=9, 
                        horizontalalignment='right', verticalalignment='top', 
                        bbox=dict(facecolor=box_color, alpha=0.8, edgecolor=color, boxstyle='round,pad=0.5'))
        
        # Save to buffer
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        # Reset buffer position
        buf.seek(0)
        
        return buf
        
    except Exception as e:
        logger.error(f"Error creating analysis chart: {e}", exc_info=True)
        plt.close('all')  # Close any open figures
        return None

def save_chart_to_file(chart_buffer, filename):
    """
    Save chart buffer to a file
    
    Args:
        chart_buffer (io.BytesIO): Chart buffer
        filename (str): Output filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if chart_buffer is None:
            logger.error("Cannot save chart: buffer is None")
            return False
            
        # Make sure the buffer is at the beginning
        chart_buffer.seek(0)
        
        # Save to file
        with open(filename, 'wb') as f:
            f.write(chart_buffer.getvalue())
            
        logger.info(f"Chart saved to {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving chart to file: {e}")
        return False

def format_price_for_symbol(price, symbol):
    """
    Format price with appropriate decimal places based on symbol
    
    Args:
        price (float): Price to format
        symbol (str): Trading symbol
        
    Returns:
        str: Formatted price
    """
    if 'JPY' in symbol:
        return f"{price:.3f}"
    elif 'XAU' in symbol:
        return f"{price:.2f}"
    elif any(crypto in symbol for crypto in ['BTC', 'ETH']):
        if price > 1000:
            return f"{price:.2f}"
        else:
            return f"{price:.5f}"
    else:
        return f"{price:.5f}"

