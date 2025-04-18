"""
Technical analysis module
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Class for technical analysis of price data"""
    
    def __init__(self):
        """Initialize the technical analyzer"""
        pass
    
    def analyze_chart(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Analyze chart for technical patterns"""
        logger.info(f"Starting technical analysis for {symbol} with {len(df)} candles")
        
        # Log data range
        if not df.empty:
            logger.info(f"Data range: {df.index[0]} to {df.index[-1]}")
        
        # Check for patterns with detailed logging
        patterns = []
        self._check_candlestick_patterns(df, patterns)
        logger.info(f"Found {len(patterns)} candlestick patterns")
        
        """
        Perform technical analysis on a chart
        
        Args:
            df (pandas.DataFrame): OHLCV data
            symbol (str): Trading symbol
            
        Returns:
            dict: Analysis results
        """
        try:
            if df.empty:
                return {
                    'symbol': symbol,
                    'error': 'Empty dataframe provided',
                    'signals': []
                }
            
            # Ensure column names are lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Calculate indicators
            indicators = self.calculate_indicators(df)
            
            # Generate signals
            signals = self.generate_signals(df, indicators)
            
            # Determine overall bias
            bias = self.determine_bias(df, indicators, signals)
            
            # Identify key levels
            key_levels = self.identify_key_levels(df)
            
            # Identify chart patterns
            patterns = self.identify_patterns(df)
            
            # Calculate volatility metrics
            volatility = self.calculate_volatility(df)
            
            # Determine trend strength
            trend_strength = self.calculate_trend_strength(df, indicators)
            
            # Compile analysis results
            analysis = {
                'symbol': symbol,
                'datetime': df.index[-1] if not df.empty else None,
                'current_price': df.iloc[-1]['close'] if not df.empty else None,
                'indicators': indicators,
                'signals': signals,
                'bias': bias,
                'key_levels': key_levels,
                'patterns': patterns,
                'volatility': volatility,
                'trend_strength': trend_strength
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing chart: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'signals': []
            }
    
    def _check_candlestick_patterns(self, df, patterns):
        """Check for various candlestick patterns"""
        # This method should call the individual pattern checks
        self._check_doji(df, patterns)
        self._check_engulfing(df, patterns)
        self._check_hammer_shooting_star(df, patterns)
        self._check_morning_evening_star(df, patterns)
        self._check_three_candles(df, patterns)


    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators
        
        Args:
            df (pandas.DataFrame): OHLCV data
            
        Returns:
            dict: Calculated indicators
        """
        indicators = {}
        
        # Moving Averages
        indicators['sma20'] = self._calculate_sma(df, 20)
        indicators['sma50'] = self._calculate_sma(df, 50)
        indicators['sma200'] = self._calculate_sma(df, 200)
        indicators['ema20'] = self._calculate_ema(df, 20)
        indicators['ema50'] = self._calculate_ema(df, 50)
        indicators['ema200'] = self._calculate_ema(df, 200)
        
        # Bollinger Bands (20, 2)
        bb = self._calculate_bollinger_bands(df, 20, 2)
        indicators['bb_upper'] = bb['upper']
        indicators['bb_middle'] = bb['middle']
        indicators['bb_lower'] = bb['lower']
        indicators['bb_width'] = bb['width']
        
        # RSI (14)
        indicators['rsi'] = self._calculate_rsi(df, 14)
        
        # MACD (12, 26, 9)
        macd = self._calculate_macd(df, 12, 26, 9)
        indicators['macd'] = macd['macd']
        indicators['macd_signal'] = macd['signal']
        indicators['macd_histogram'] = macd['histogram']
        
        # Stochastic Oscillator (14, 3, 3)
        stoch = self._calculate_stochastic(df, 14, 3, 3)
        indicators['stoch_k'] = stoch['k']
        indicators['stoch_d'] = stoch['d']
        
        # Average True Range (14)
        indicators['atr'] = self._calculate_atr(df, 14)
        
        # Ichimoku Cloud
        ichimoku = self._calculate_ichimoku(df)
        indicators.update(ichimoku)
        
        # ADX (14)
        adx = self._calculate_adx(df, 14)
        indicators['adx'] = adx['adx']
        indicators['di_plus'] = adx['di_plus']
        indicators['di_minus'] = adx['di_minus']
        
        # Volume indicators
        indicators['volume_sma20'] = self._calculate_sma(df, 20, 'volume')
        indicators['volume_ratio'] = df['volume'] / indicators['volume_sma20']
        
        # On-Balance Volume (OBV)
        indicators['obv'] = self._calculate_obv(df)
        
        return indicators
    
    def _calculate_sma(self, df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Simple Moving Average"""
        return df[column].rolling(window=period).mean()
    
    def _calculate_ema(self, df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df[column].ewm(span=period, adjust=False).mean()
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = self._calculate_sma(df, period)
        std = df['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = (upper - lower) / middle
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'width': width
        }

    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # For periods after the initial period
        for i in range(period, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + loss.iloc[i]) / period
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    
    def _calculate_macd(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD"""
        fast_ema = self._calculate_ema(df, fast_period)
        slow_ema = self._calculate_ema(df, slow_period)
        macd = fast_ema - slow_ema
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
    
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, k_smooth: int = 3, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        k = 100 * ((df['close'] - low_min) / (high_max - low_min))
        k = k.rolling(window=k_smooth).mean()
        d = k.rolling(window=d_period).mean()
        
        return {
            'k': k,
            'd': d
        }
    
    def _calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        # Fill NaN values with the first valid value
        atr = atr.bfill()
        return atr


    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate Ichimoku Cloud"""
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        period9_high = df['high'].rolling(window=9).max()
        period9_low = df['low'].rolling(window=9).min()
        tenkan_sen = (period9_high + period9_low) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        period26_high = df['high'].rolling(window=26).max()
        period26_low = df['low'].rolling(window=26).min()
        kijun_sen = (period26_high + period26_low) / 2
        
        # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
        period52_high = df['high'].rolling(window=52).max()
        period52_low = df['low'].rolling(window=52).min()
        senkou_span_b = ((period52_high + period52_low) / 2).shift(26)
        
        # Chikou Span (Lagging Span): Close price shifted back 26 periods
        chikou_span = df['close'].shift(-26)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index"""
        # True Range
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Plus Directional Movement (+DM)
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff().mul(-1)
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        
        # Minus Directional Movement (-DM)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # Smoothed +DM, -DM, and TR
        smoothed_plus_dm = plus_dm.rolling(window=period).sum()
        smoothed_minus_dm = minus_dm.rolling(window=period).sum()
        smoothed_tr = true_range.rolling(window=period).sum()
        
        # Directional Indicators
        di_plus = 100 * (smoothed_plus_dm / smoothed_tr)
        di_minus = 100 * (smoothed_minus_dm / smoothed_tr)
        
        # Directional Index
        dx = 100 * ((di_plus - di_minus).abs() / (di_plus + di_minus))
        
        # Average Directional Index
        adx = dx.rolling(window=period).mean()
        
        return {
            'adx': adx,
            'di_plus': di_plus,
            'di_minus': di_minus
        }
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume"""
        obv = pd.Series(index=df.index, dtype='float64')
        obv.iloc[0] = 0
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def generate_signals(self, df: pd.DataFrame, indicators: Dict) -> List[Dict]:
        """
        Generate trading signals based on technical indicators
        
        Args:
            df (pandas.DataFrame): OHLCV data
            indicators (dict): Calculated indicators
            
        Returns:
            list: Trading signals
        """
        signals = []
        
        # Get the latest values
        latest_close = df['close'].iloc[-1]
        
        # Moving Average Crossovers
        if indicators['sma20'].iloc[-2] < indicators['sma50'].iloc[-2] and indicators['sma20'].iloc[-1] > indicators['sma50'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'MA Crossover',
                'description': 'SMA20 crossed above SMA50',
                'strength': 70
            })
        
        if indicators['sma20'].iloc[-2] > indicators['sma50'].iloc[-2] and indicators['sma20'].iloc[-1] < indicators['sma50'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'MA Crossover',
                'description': 'SMA20 crossed below SMA50',
                'strength': 70
            })
        
        # RSI Signals
        latest_rsi = indicators['rsi'].iloc[-1]
        if latest_rsi < 30:
            signals.append({
                'type': 'bullish',
                'indicator': 'RSI',
                'description': f'RSI oversold at {latest_rsi:.2f}',
                'strength': 60 + (30 - latest_rsi)  # Stronger signal the more oversold
            })
        
        if latest_rsi > 70:
            signals.append({
                'type': 'bearish',
                'indicator': 'RSI',
                'description': f'RSI overbought at {latest_rsi:.2f}',
                'strength': 60 + (latest_rsi - 70)  # Stronger signal the more overbought
            })
        
        # MACD Signals
        if indicators['macd_histogram'].iloc[-2] < 0 and indicators['macd_histogram'].iloc[-1] > 0:
            signals.append({
                'type': 'bullish',
                'indicator': 'MACD',
                'description': 'MACD histogram turned positive',
                'strength': 65
            })
        
        if indicators['macd_histogram'].iloc[-2] > 0 and indicators['macd_histogram'].iloc[-1] < 0:
            signals.append({
                'type': 'bearish',
                'indicator': 'MACD',
                'description': 'MACD histogram turned negative',
                'strength': 65
            })
        
        # Bollinger Band Signals
        if df['close'].iloc[-1] < indicators['bb_lower'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'Bollinger Bands',
                'description': 'Price below lower Bollinger Band',
                'strength': 60
            })
        
        if df['close'].iloc[-1] > indicators['bb_upper'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'Bollinger Bands',
                'description': 'Price above upper Bollinger Band',
                'strength': 60
            })
        
        # Stochastic Signals
        if indicators['stoch_k'].iloc[-2] < 20 and indicators['stoch_k'].iloc[-1] > 20 and indicators['stoch_k'].iloc[-1] > indicators['stoch_d'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'Stochastic',
                'description': 'Stochastic K crossed above D from oversold',
                'strength': 70
            })
        
        if indicators['stoch_k'].iloc[-2] > 80 and indicators['stoch_k'].iloc[-1] < 80 and indicators['stoch_k'].iloc[-1] < indicators['stoch_d'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'Stochastic',
                'description': 'Stochastic K crossed below D from overbought',
                'strength': 70
            })
        
        # ADX Trend Strength
        latest_adx = indicators['adx'].iloc[-1]
        if latest_adx > 25:
            # Strong trend
            if indicators['di_plus'].iloc[-1] > indicators['di_minus'].iloc[-1]:
                signals.append({
                    'type': 'bullish',
                    'indicator': 'ADX',
                    'description': f'Strong uptrend (ADX: {latest_adx:.2f})',
                    'strength': 50 + min(latest_adx / 2, 30)  # Max 80
                })
            else:
                signals.append({
                    'type': 'bearish',
                    'indicator': 'ADX',
                    'description': f'Strong downtrend (ADX: {latest_adx:.2f})',
                    'strength': 50 + min(latest_adx / 2, 30)  # Max 80
                })
        
        # Ichimoku Cloud Signals
        if df['close'].iloc[-1] > indicators['senkou_span_a'].iloc[-1] and df['close'].iloc[-1] > indicators['senkou_span_b'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'Ichimoku',
                'description': 'Price above the cloud',
                'strength': 65
            })
        
        if df['close'].iloc[-1] < indicators['senkou_span_a'].iloc[-1] and df['close'].iloc[-1] < indicators['senkou_span_b'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'Ichimoku',
                'description': 'Price below the cloud',
                'strength': 65
            })
        
        if indicators['tenkan_sen'].iloc[-2] < indicators['kijun_sen'].iloc[-2] and indicators['tenkan_sen'].iloc[-1] > indicators['kijun_sen'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'Ichimoku',
                'description': 'Tenkan-sen crossed above Kijun-sen',
                'strength': 70
            })
        
        if indicators['tenkan_sen'].iloc[-2] > indicators['kijun_sen'].iloc[-2] and indicators['tenkan_sen'].iloc[-1] < indicators['kijun_sen'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'Ichimoku',
                'description': 'Tenkan-sen crossed below Kijun-sen',
                'strength': 70
            })
        
        # Volume-based signals
        if indicators['volume_ratio'].iloc[-1] > 2.0 and df['close'].iloc[-1] > df['open'].iloc[-1]:
            signals.append({
                'type': 'bullish',
                'indicator': 'Volume',
                'description': 'High volume bullish candle',
                'strength': 60 + min(indicators['volume_ratio'].iloc[-1] * 5, 20)  # Max 80
            })
        
        if indicators['volume_ratio'].iloc[-1] > 2.0 and df['close'].iloc[-1] < df['open'].iloc[-1]:
            signals.append({
                'type': 'bearish',
                'indicator': 'Volume',
                'description': 'High volume bearish candle',
                'strength': 60 + min(indicators['volume_ratio'].iloc[-1] * 5, 20)  # Max 80
            })
        
        # OBV Divergence
        if len(df) >= 10:
            price_change = df['close'].iloc[-1] - df['close'].iloc[-10]
            obv_change = indicators['obv'].iloc[-1] - indicators['obv'].iloc[-10]
            
            if price_change < 0 and obv_change > 0:
                signals.append({
                    'type': 'bullish',
                    'indicator': 'OBV',
                    'description': 'Bullish OBV divergence',
                    'strength': 75
                })
            
            if price_change > 0 and obv_change < 0:
                signals.append({
                    'type': 'bearish',
                    'indicator': 'OBV',
                    'description': 'Bearish OBV divergence',
                    'strength': 75
                })
        
        # Sort signals by strength (descending)
        signals.sort(key=lambda x: x['strength'], reverse=True)
        
        return signals
    
    def determine_bias(self, df: pd.DataFrame, indicators: Dict, signals: List[Dict]) -> Dict:
        """
        Determine overall market bias
        
        Args:
            df (pandas.DataFrame): OHLCV data
            indicators (dict): Calculated indicators
            signals (list): Generated signals
            
        Returns:
            dict: Market bias details including direction, strength and confidence
        """
        # Count bullish and bearish signals
        bullish_count = sum(1 for signal in signals if signal['type'] == 'bullish')
        bearish_count = sum(1 for signal in signals if signal['type'] == 'bearish')
        
        # Calculate weighted signal strength
        bullish_strength = sum(signal['strength'] for signal in signals if signal['type'] == 'bullish')
        bearish_strength = sum(signal['strength'] for signal in signals if signal['type'] == 'bearish')
        
        # Check trend based on moving averages
        ma_trend = 'neutral'
        if indicators['sma20'].iloc[-1] > indicators['sma50'].iloc[-1] > indicators['sma200'].iloc[-1]:
            ma_trend = 'bullish'
        elif indicators['sma20'].iloc[-1] < indicators['sma50'].iloc[-1] < indicators['sma200'].iloc[-1]:
            ma_trend = 'bearish'
        
        # Check price position relative to key MAs
        price_above_ma20 = df['close'].iloc[-1] > indicators['sma20'].iloc[-1]
        price_above_ma50 = df['close'].iloc[-1] > indicators['sma50'].iloc[-1]
        price_above_ma200 = df['close'].iloc[-1] > indicators['sma200'].iloc[-1]
        
        # Calculate overall strength (0-100)
        total_strength = bullish_strength + bearish_strength
        strength = 0
        
        # Determine bias and calculate strength
        if (bullish_strength > bearish_strength * 1.5 or 
            (ma_trend == 'bullish' and price_above_ma20 and price_above_ma50) or
            (bullish_count > bearish_count * 2)):
            bias = 'bullish'
            strength = min(100, int((bullish_strength / (total_strength or 1)) * 100))
        elif (bearish_strength > bullish_strength * 1.5 or 
              (ma_trend == 'bearish' and not price_above_ma20 and not price_above_ma50) or
              (bearish_count > bullish_count * 2)):
            bias = 'bearish'
            strength = min(100, int((bearish_strength / (total_strength or 1)) * 100))
        else:
            bias = 'neutral'
            strength = 50
        
        # Calculate confidence score (0-100)
        confidence = 0
        
        # MA alignment contribution (max 30)
        if ma_trend == bias:
            confidence += 30
        
        # Signal count contribution (max 30)
        signal_ratio = max(bullish_count, bearish_count) / (bullish_count + bearish_count) if (bullish_count + bearish_count) > 0 else 0
        confidence += int(signal_ratio * 30)
        
        # Price position contribution (max 40)
        ma_alignment = sum([price_above_ma20, price_above_ma50, price_above_ma200])
        if bias == 'bullish':
            confidence += int((ma_alignment / 3) * 40)
        elif bias == 'bearish':
            confidence += int(((3 - ma_alignment) / 3) * 40)
        else:
            confidence += 20
            
        return {
            'direction': bias,  # 'bullish', 'bearish', or 'neutral'
            'strength': strength,
            'confidence': confidence
        }

    def identify_key_levels(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify key support and resistance levels
        
        Args:
            df (pandas.DataFrame): OHLCV data
            
        Returns:
            list: Key price levels
        """
        key_levels = []
        
        # Use recent swing highs and lows
        window = 5  # Window size for swing point detection
        
        # Find swing highs
        for i in range(window, len(df) - window):
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                key_levels.append({
                    'type': 'resistance',
                    'price': df['high'].iloc[i],
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'strength': self._calculate_level_strength(df, df['high'].iloc[i], 'resistance')
                })
        
        # Find swing lows
        for i in range(window, len(df) - window):
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                key_levels.append({
                    'type': 'support',
                    'price': df['low'].iloc[i],
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'strength': self._calculate_level_strength(df, df['low'].iloc[i], 'support')
                })
        
        # Add round numbers as psychological levels
        current_price = df['close'].iloc[-1]
        
        # Determine the appropriate scale for round numbers
        if current_price < 1:
            round_numbers = [0.1, 0.25, 0.5, 0.75]
        elif current_price < 10:
            round_numbers = [1, 2.5, 5, 7.5]
        elif current_price < 100:
            round_numbers = [10, 25, 50, 75]
        elif current_price < 1000:
            round_numbers = [100, 250, 500, 750]
        else:
            round_numbers = [1000, 2500, 5000, 7500]
        
        # Add nearby round numbers
        for base in round_numbers:
            level = round(current_price / base) * base
            if abs(level - current_price) / current_price < 0.05:  # Within 5% of current price
                key_levels.append({
                    'type': 'psychological',
                    'price': level,
                    'date': None,
                    'strength': 50  # Medium strength for psychological levels
                })
        
        # Sort by price
        key_levels.sort(key=lambda x: x['price'])
        
        # Merge nearby levels (within 0.2% of each other)
        merged_levels = []
        i = 0
        while i < len(key_levels):
            current_level = key_levels[i]
            j = i + 1
            while j < len(key_levels) and abs(key_levels[j]['price'] - current_level['price']) / current_level['price'] < 0.002:
                # Merge levels by taking the stronger one
                if key_levels[j]['strength'] > current_level['strength']:
                    current_level = key_levels[j]
                j += 1
            
            merged_levels.append(current_level)
            i = j
        
        return merged_levels
    
    def _calculate_level_strength(self, df: pd.DataFrame, price: float, level_type: str) -> int:
        """
        Calculate the strength of a support/resistance level
        
        Args:
            df (pandas.DataFrame): OHLCV data
            price (float): Level price
            level_type (str): 'support' or 'resistance'
            
        Returns:
            int: Strength score (0-100)
        """
        # Count how many times price has respected this level
        touches = 0
        strong_touches = 0
        
        # Define price range for level (0.1% of price)
        price_range = price * 0.001
        
        for i in range(len(df)):
            if level_type == 'support':
                # Price came within range of level and bounced up
                if abs(df['low'].iloc[i] - price) <= price_range and df['close'].iloc[i] > df['open'].iloc[i]:
                    touches += 1
                    # Strong bounce (closed significantly higher)
                    if (df['close'].iloc[i] - df['low'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) > 0.7:
                        strong_touches += 1
            else:  # resistance
                # Price came within range of level and bounced down
                if abs(df['high'].iloc[i] - price) <= price_range and df['close'].iloc[i] < df['open'].iloc[i]:
                    touches += 1
                    # Strong bounce (closed significantly lower)
                    if (df['high'].iloc[i] - df['close'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) > 0.7:
                        strong_touches += 1
        
        # Calculate strength based on touches and strong touches
        strength = min(100, touches * 10 + strong_touches * 15)
        
        return strength
    
    def identify_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify chart patterns
        
        Args:
            df (pandas.DataFrame): OHLCV data
            
        Returns:
            list: Identified patterns
        """
        patterns = []
        
        # Need at least 20 candles for pattern recognition
        if len(df) < 20:
            return patterns
        
        # Check for doji
        self._check_doji(df, patterns)
        
        # Check for engulfing patterns
        self._check_engulfing(df, patterns)
        
        # Check for hammer and shooting star
        self._check_hammer_shooting_star(df, patterns)
        
        # Check for morning and evening star
        self._check_morning_evening_star(df, patterns)
        
        # Check for three white soldiers and three black crows
        self._check_three_candles(df, patterns)
        
        # Check for double top/bottom
        self._check_double_patterns(df, patterns)
        
        # Check for head and shoulders
        self._check_head_and_shoulders(df, patterns)
        
        # Sort patterns by recency (most recent first)
        patterns.sort(key=lambda x: x['index'], reverse=True)
        
        return patterns
    
    def _check_doji(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for doji candlestick patterns"""
        # Look at the last 10 candles
        for i in range(max(0, len(df) - 10), len(df)):
            body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
            total_range = df['high'].iloc[i] - df['low'].iloc[i]
            
            # Doji has very small body compared to total range
            if total_range > 0 and body_size / total_range < 0.1:
                patterns.append({
                    'type': 'doji',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'neutral'
                })
    
    def _check_engulfing(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for bullish and bearish engulfing patterns"""
        # Look at the last 10 candles
        for i in range(max(1, len(df) - 10), len(df)):
            prev_body_size = abs(df['close'].iloc[i-1] - df['open'].iloc[i-1])
            curr_body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
            
            # Bullish engulfing
            if (df['close'].iloc[i] > df['open'].iloc[i] and  # Current candle is bullish
                df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Previous candle is bearish
                df['close'].iloc[i] > df['open'].iloc[i-1] and  # Current close > previous open
                df['open'].iloc[i] < df['close'].iloc[i-1] and  # Current open < previous close
                curr_body_size > prev_body_size):  # Current body larger than previous
                
                patterns.append({
                    'type': 'bullish_engulfing',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bullish'
                })
            
            # Bearish engulfing
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # Current candle is bearish
                df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Previous candle is bullish
                df['close'].iloc[i] < df['open'].iloc[i-1] and  # Current close < previous open
                df['open'].iloc[i] > df['close'].iloc[i-1] and  # Current open > previous close
                curr_body_size > prev_body_size):  # Current body larger than previous
                
                patterns.append({
                    'type': 'bearish_engulfing',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bearish'
                })
    
    def _check_hammer_shooting_star(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for hammer and shooting star patterns"""
        # Look at the last 10 candles
        for i in range(max(0, len(df) - 10), len(df)):
            body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
            total_range = df['high'].iloc[i] - df['low'].iloc[i]
            
            if total_range == 0:
                continue
            
            body_percent = body_size / total_range
            
            # Hammer: small body at the top, long lower shadow
            if body_percent < 0.3:
                upper_shadow = df['high'].iloc[i] - max(df['open'].iloc[i], df['close'].iloc[i])
                lower_shadow = min(df['open'].iloc[i], df['close'].iloc[i]) - df['low'].iloc[i]
                
                if lower_shadow > 2 * body_size and upper_shadow < 0.1 * total_range:
                    patterns.append({
                        'type': 'hammer',
                        'index': i,
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                        'price': df['close'].iloc[i],
                        'significance': 'bullish'
                    })
                
                # Shooting star: small body at the bottom, long upper shadow
                if upper_shadow > 2 * body_size and lower_shadow < 0.1 * total_range:
                    patterns.append({
                        'type': 'shooting_star',
                        'index': i,
                        'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                        'price': df['close'].iloc[i],
                        'significance': 'bearish'
                    })
    
    def _check_morning_evening_star(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for morning star and evening star patterns"""
        # Need at least 3 candles
        if len(df) < 3:
            return
        
        # Look at the last 10 candles
        for i in range(max(2, len(df) - 10), len(df)):
            # Morning star
            if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and  # First candle is bearish
                abs(df['close'].iloc[i-1] - df['open'].iloc[i-1]) < abs(df['close'].iloc[i-2] - df['open'].iloc[i-2]) * 0.3 and  # Second candle has small body
                df['close'].iloc[i] > df['open'].iloc[i] and  # Third candle is bullish
                df['close'].iloc[i] > (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Third candle closes above midpoint of first
                
                patterns.append({
                    'type': 'morning_star',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bullish'
                })
            
            # Evening star
            if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and  # First candle is bullish
                abs(df['close'].iloc[i-1] - df['open'].iloc[i-1]) < abs(df['close'].iloc[i-2] - df['open'].iloc[i-2]) * 0.3 and  # Second candle has small body
                df['close'].iloc[i] < df['open'].iloc[i] and  # Third candle is bearish
                df['close'].iloc[i] < (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Third candle closes below midpoint of first
                
                patterns.append({
                    'type': 'evening_star',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bearish'
                })
    
    def _check_three_candles(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for three white soldiers and three black crows patterns"""
        # Need at least 3 candles
        if len(df) < 3:
            return
        
        # Look at the last 10 candles
        for i in range(max(2, len(df) - 10), len(df)):
            # Three white soldiers
            if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and  # First candle is bullish
                df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Second candle is bullish
                df['close'].iloc[i] > df['open'].iloc[i] and  # Third candle is bullish
                df['close'].iloc[i-1] > df['close'].iloc[i-2] and  # Each close is higher than the previous
                df['close'].iloc[i] > df['close'].iloc[i-1] and
                df['open'].iloc[i-1] > df['open'].iloc[i-2] and  # Each open is higher than the previous
                df['open'].iloc[i] > df['open'].iloc[i-1]):
                
                patterns.append({
                    'type': 'three_white_soldiers',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bullish'
                })
            
            # Three black crows
            if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and  # First candle is bearish
                df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Second candle is bearish
                df['close'].iloc[i] < df['open'].iloc[i] and  # Third candle is bearish
                df['close'].iloc[i-1] < df['close'].iloc[i-2] and  # Each close is lower than the previous
                df['close'].iloc[i] < df['close'].iloc[i-1] and
                df['open'].iloc[i-1] < df['open'].iloc[i-2] and  # Each open is lower than the previous
                df['open'].iloc[i] < df['open'].iloc[i-1]):
                
                patterns.append({
                    'type': 'three_black_crows',
                    'index': i,
                    'date': df.index[i] if hasattr(df.index, '__getitem__') else None,
                    'price': df['close'].iloc[i],
                    'significance': 'bearish'
                })
    
    def _check_double_patterns(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for double top and double bottom patterns"""
        # Need at least 20 candles for these patterns
        if len(df) < 20:
            return
        
        # Find swing highs and lows
        window = 5
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            # Swing high
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                swing_highs.append((i, df['high'].iloc[i]))
            
            # Swing low
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                swing_lows.append((i, df['low'].iloc[i]))
        
        # Check for double top
        if len(swing_highs) >= 2:
            for i in range(len(swing_highs) - 1):
                for j in range(i + 1, len(swing_highs)):
                    idx1, price1 = swing_highs[i]
                    idx2, price2 = swing_highs[j]
                    
                    # Check if prices are within 1% of each other
                    if abs(price1 - price2) / price1 < 0.01 and idx2 - idx1 >= 5:
                        # Check if there's a significant drop between the two tops
                        min_between = min(df['low'].iloc[idx1:idx2+1])
                        if (price1 - min_between) / price1 > 0.03:  # At least 3% drop
                            patterns.append({
                                'type': 'double_top',
                                'index': idx2,
                                'date': df.index[idx2] if hasattr(df.index, '__getitem__') else None,
                                'price': price2,
                                'significance': 'bearish'
                            })
        
        # Check for double bottom
        if len(swing_lows) >= 2:
            for i in range(len(swing_lows) - 1):
                for j in range(i + 1, len(swing_lows)):
                    idx1, price1 = swing_lows[i]
                    idx2, price2 = swing_lows[j]
                    
                    # Check if prices are within 1% of each other
                    if abs(price1 - price2) / price1 < 0.01 and idx2 - idx1 >= 5:
                        # Check if there's a significant rise between the two bottoms
                        max_between = max(df['high'].iloc[idx1:idx2+1])
                        if (max_between - price1) / price1 > 0.03:  # At least 3% rise
                            patterns.append({
                                'type': 'double_bottom',
                                'index': idx2,
                                'date': df.index[idx2] if hasattr(df.index, '__getitem__') else None,
                                'price': price2,
                                'significance': 'bullish'
                            })
    
    def _check_head_and_shoulders(self, df: pd.DataFrame, patterns: List[Dict]) -> None:
        """Check for head and shoulders and inverse head and shoulders patterns"""
        # Need at least 30 candles for these patterns
        if len(df) < 30:
            return
        
        # Find swing highs and lows
        window = 5
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            # Swing high
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                swing_highs.append((i, df['high'].iloc[i]))
            
            # Swing low
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                swing_lows.append((i, df['low'].iloc[i]))
        
        # Check for head and shoulders
        if len(swing_highs) >= 3:
            for i in range(len(swing_highs) - 2):
                # Get three consecutive swing highs
                idx1, price1 = swing_highs[i]      # Left shoulder
                idx2, price2 = swing_highs[i + 1]  # Head
                idx3, price3 = swing_highs[i + 2]  # Right shoulder
                
                # Check pattern criteria
                if (price2 > price1 and price2 > price3 and  # Head is higher than shoulders
                    abs(price1 - price3) / price1 < 0.05 and  # Shoulders at similar levels
                    idx2 - idx1 >= 3 and idx3 - idx2 >= 3):  # Adequate spacing
                    
                    # Find neckline (connecting the lows between shoulders and head)
                    lows_between = [df['low'].iloc[j] for j in range(idx1, idx3 + 1)]
                    neckline = min(lows_between)
                    
                    patterns.append({
                        'type': 'head_and_shoulders',
                        'index': idx3,
                        'date': df.index[idx3] if hasattr(df.index, '__getitem__') else None,
                        'price': price3,
                        'neckline': neckline,
                        'significance': 'bearish'
                    })
        
        # Check for inverse head and shoulders
        if len(swing_lows) >= 3:
            for i in range(len(swing_lows) - 2):
                # Get three consecutive swing lows
                idx1, price1 = swing_lows[i]      # Left shoulder
                idx2, price2 = swing_lows[i + 1]  # Head
                idx3, price3 = swing_lows[i + 2]  # Right shoulder
                
                # Check pattern criteria
                if (price2 < price1 and price2 < price3 and  # Head is lower than shoulders
                    abs(price1 - price3) / price1 < 0.05 and  # Shoulders at similar levels
                    idx2 - idx1 >= 3 and idx3 - idx2 >= 3):  # Adequate spacing
                    
                    # Find neckline (connecting the highs between shoulders and head)
                    highs_between = [df['high'].iloc[j] for j in range(idx1, idx3 + 1)]
                    neckline = max(highs_between)
                    
                    patterns.append({
                        'type': 'inverse_head_and_shoulders',
                        'index': idx3,
                        'date': df.index[idx3] if hasattr(df.index, '__getitem__') else None,
                        'price': price3,
                        'neckline': neckline,
                        'significance': 'bullish'
                    })
    
    def calculate_volatility(self, df: pd.DataFrame) -> Dict:
        """
        Calculate volatility metrics
        
        Args:
            df (pandas.DataFrame): OHLCV data
            
        Returns:
            dict: Volatility metrics
        """
        volatility = {}
        
        # Calculate Average True Range (ATR)
        atr = self._calculate_atr(df, 14)
        volatility['atr'] = atr.iloc[-1] if not atr.empty else None
        
        # Calculate ATR as percentage of price
        if not atr.empty and df['close'].iloc[-1] > 0:
            volatility['atr_percent'] = (atr.iloc[-1] / df['close'].iloc[-1]) * 100
        else:
            volatility['atr_percent'] = None
        
        # Calculate historical volatility (standard deviation of returns)
        if len(df) > 20:
            returns = df['close'].pct_change().dropna()
            volatility['daily_volatility'] = returns.std() * 100  # As percentage
            volatility['annualized_volatility'] = returns.std() * np.sqrt(252) * 100  # Annualized, as percentage
        else:
            volatility['daily_volatility'] = None
            volatility['annualized_volatility'] = None
        
        # Calculate Bollinger Band width
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            bb_width = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            volatility['bollinger_width'] = bb_width.iloc[-1] if not bb_width.empty else None
        else:
            bb = self._calculate_bollinger_bands(df)
            volatility['bollinger_width'] = (bb['upper'].iloc[-1] - bb['lower'].iloc[-1]) / bb['middle'].iloc[-1] if not bb['upper'].empty else None
        
        # Volatility trend (increasing or decreasing)
        if len(df) > 20 and not atr.empty:
            atr_5_periods_ago = atr.iloc[-6] if len(atr) > 5 else atr.iloc[0]
            volatility['trend'] = 'increasing' if atr.iloc[-1] > atr_5_periods_ago else 'decreasing'
        else:
            volatility['trend'] = 'unknown'
        
        return volatility
    
    def calculate_trend_strength(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """
        Calculate trend strength metrics
        
        Args:
            df (pandas.DataFrame): OHLCV data
            indicators (dict): Technical indicators
            
        Returns:
            dict: Trend strength metrics
        """
        trend = {}
        
        # ADX (Average Directional Index) - measures trend strength
        if 'adx' in indicators:
            adx_value = indicators['adx'].iloc[-1]
            trend['adx'] = adx_value
            
            # Interpret ADX
            if adx_value < 20:
                trend['strength'] = 'weak'
            elif adx_value < 40:
                trend['strength'] = 'moderate'
            elif adx_value < 60:
                trend['strength'] = 'strong'
            else:
                trend['strength'] = 'very strong'
        else:
            adx = self._calculate_adx(df)
            trend['adx'] = adx['adx'].iloc[-1] if not adx['adx'].empty else None
            
            # Interpret ADX
            if trend['adx'] is not None:
                if trend['adx'] < 20:
                    trend['strength'] = 'weak'
                elif trend['adx'] < 40:
                    trend['strength'] = 'moderate'
                elif trend['adx'] < 60:
                    trend['strength'] = 'strong'
                else:
                    trend['strength'] = 'very strong'
            else:
                trend['strength'] = 'unknown'
        
        # Determine trend direction
        if 'di_plus' in indicators and 'di_minus' in indicators:
            di_plus = indicators['di_plus'].iloc[-1]
            di_minus = indicators['di_minus'].iloc[-1]
            
            if di_plus > di_minus:
                trend['direction'] = 'bullish'
            else:
                trend['direction'] = 'bearish'
        else:
            # Use moving averages to determine direction
            if 'sma20' in indicators and 'sma50' in indicators:
                if indicators['sma20'].iloc[-1] > indicators['sma50'].iloc[-1]:
                    trend['direction'] = 'bullish'
                else:
                    trend['direction'] = 'bearish'
            else:
                trend['direction'] = 'unknown'
        
        # Check if price is above/below key moving averages
        if 'sma20' in indicators and 'sma50' in indicators and 'sma200' in indicators:
            current_price = df['close'].iloc[-1]
            
            trend['above_sma20'] = current_price > indicators['sma20'].iloc[-1]
            trend['above_sma50'] = current_price > indicators['sma50'].iloc[-1]
            trend['above_sma200'] = current_price > indicators['sma200'].iloc[-1]
            
            # Golden cross / death cross
            trend['golden_cross'] = indicators['sma50'].iloc[-1] > indicators['sma200'].iloc[-1] and indicators['sma50'].iloc[-2] <= indicators['sma200'].iloc[-2]
            trend['death_cross'] = indicators['sma50'].iloc[-1] < indicators['sma200'].iloc[-1] and indicators['sma50'].iloc[-2] >= indicators['sma200'].iloc[-2]
        
        # Calculate linear regression slope
        if len(df) > 20:
            # Use last 20 periods for slope calculation
            x = np.arange(20)
            y = df['close'].iloc[-20:].values
            
            if len(y) == 20:  # Ensure we have enough data
                slope, _, _, _, _ = np.polyfit(x, y, 1, full=True)
                trend['slope'] = slope[0]
                
                # Normalize slope as percentage of price
                trend['slope_percent'] = (slope[0] * 20) / y[0] * 100 if y[0] > 0 else 0
            else:
                trend['slope'] = None
                trend['slope_percent'] = None
        else:
            trend['slope'] = None
            trend['slope_percent'] = None
        
        return trend
    
    def find_trade_setups(self, df: pd.DataFrame, min_rr: float = 2.0) -> List[Dict]:
        """
        Find potential trade setups based on technical analysis
        
        Args:
            df (pandas.DataFrame): OHLCV data
            min_rr (float): Minimum risk-reward ratio
            
        Returns:
            list: Trade setups
        """
        trade_setups = []
        
        # Calculate indicators
        indicators = self.calculate_indicators(df)
        
        # Generate signals
        signals = self.generate_signals(df, indicators)
        
        # Determine bias
        bias = self.determine_bias(df, indicators, signals)
        
        # Identify key levels
        key_levels = self.identify_key_levels(df)
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        # Find bullish setups
        if bias in ['bullish', 'neutral']:
            bullish_signals = [s for s in signals if s['type'] == 'bullish' and s['strength'] > 60]
            
            if bullish_signals:
                # Find nearest support level for stop loss
                supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
                nearest_support = min(supports, key=lambda x: current_price - x['price']) if supports else None
                
                # Find nearest resistance level for take profit
                resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
                nearest_resistance = min(resistances, key=lambda x: x['price'] - current_price) if resistances else None
                
                if nearest_support and nearest_resistance:
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = nearest_support['price'] * 0.99  # Just below support
                    take_profit = nearest_resistance['price']
                    
                    # Calculate risk-reward ratio
                    risk = entry - stop_loss
                    reward = take_profit - entry
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with sufficient RR
                    if risk_reward >= min_rr:
                        # Combine signal descriptions
                        signal_desc = "; ".join([s['description'] for s in bullish_signals[:3]])
                        
                        trade_setups.append({
                            'direction': 'BUY',
                            'entry': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': max(s['strength'] for s in bullish_signals),
                            'reason': f"Bullish signals: {signal_desc}. Support at {nearest_support['price']:.5f}, resistance at {nearest_resistance['price']:.5f}"
                        })
        
        # Find bearish setups
        if bias in ['bearish', 'neutral']:
            bearish_signals = [s for s in signals if s['type'] == 'bearish' and s['strength'] > 60]
            
            if bearish_signals:
                # Find nearest resistance level for stop loss
                resistances = [level for level in key_levels if level['type'] == 'resistance' and level['price'] > current_price]
                nearest_resistance = min(resistances, key=lambda x: x['price'] - current_price) if resistances else None
                
                # Find nearest support level for take profit
                supports = [level for level in key_levels if level['type'] == 'support' and level['price'] < current_price]
                nearest_support = min(supports, key=lambda x: current_price - x['price']) if supports else None
                
                if nearest_support and nearest_resistance:
                    # Calculate entry, stop loss, and take profit
                    entry = current_price
                    stop_loss = nearest_resistance['price'] * 1.01  # Just above resistance
                    take_profit = nearest_support['price']
                    
                    # Calculate risk-reward ratio
                    risk = stop_loss - entry
                    reward = entry - take_profit
                    risk_reward = reward / risk if risk > 0 else 0
                    
                    # Only include setups with sufficient RR
                    if risk_reward >= min_rr:
                        # Combine signal descriptions
                        signal_desc = "; ".join([s['description'] for s in bearish_signals[:3]])
                        
                        trade_setups.append({
                            'direction': 'SELL',
                            'entry': entry,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'risk_reward': risk_reward,
                            'strength': max(s['strength'] for s in bearish_signals),
                            'reason': f"Bearish signals: {signal_desc}. Resistance at {nearest_resistance['price']:.5f}, support at {nearest_support['price']:.5f}"
                        })
        
        # If no key levels found, use ATR for stop loss and take profit
        if not trade_setups and signals:
            atr = indicators.get('atr', self._calculate_atr(df, 14).iloc[-1])
            
            if atr is not None:
                # For bullish signals
                bullish_signals = [s for s in signals if s['type'] == 'bullish' and s['strength'] > 60]
                if bullish_signals and bias in ['bullish', 'neutral']:
                    entry = current_price
                    stop_loss = entry - (2 * atr)  # 2 ATR below entry
                    take_profit = entry + (min_rr * 2 * atr)  # min_rr times the risk
                    
                    risk_reward = min_rr  # By definition
                    
                    signal_desc = "; ".join([s['description'] for s in bullish_signals[:3]])
                    
                    trade_setups.append({
                        'direction': 'BUY',
                        'entry': entry,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': max(s['strength'] for s in bullish_signals),
                        'reason': f"Bullish signals: {signal_desc}. Using ATR for stop loss and take profit."
                    })
                
                # For bearish signals
                bearish_signals = [s for s in signals if s['type'] == 'bearish' and s['strength'] > 60]
                if bearish_signals and bias in ['bearish', 'neutral']:
                    entry = current_price
                    stop_loss = entry + (2 * atr)  # 2 ATR above entry
                    take_profit = entry - (min_rr * 2 * atr)  # min_rr times the risk
                    
                    risk_reward = min_rr  # By definition
                    
                    signal_desc = "; ".join([s['description'] for s in bearish_signals[:3]])
                    
                    trade_setups.append({
                        'direction': 'SELL',
                        'entry': entry,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'risk_reward': risk_reward,
                        'strength': max(s['strength'] for s in bearish_signals),
                        'reason': f"Bearish signals: {signal_desc}. Using ATR for stop loss and take profit."
                    })
        
        # Sort trade setups by strength and risk-reward ratio
        trade_setups.sort(key=lambda x: (x['strength'], x['risk_reward']), reverse=True)
        
        return trade_setups
    
# Add to both technical.py and smc.py
    def calculate_optimal_position_size(self, account_size: float, risk_percentage: float, 
                                    entry_price: float, stop_loss: float) -> Dict:
        """
        Calculate optimal position size based on account risk parameters
        
        Args:
            account_size (float): Account size in base currency
            risk_percentage (float): Risk percentage per trade (e.g., 1.0 for 1%)
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            
        Returns:
            dict: Position sizing information
        """
        try:
            # Calculate risk amount in account currency
            risk_amount = account_size * (risk_percentage / 100)
            
            # Calculate pip/point risk
            if entry_price > stop_loss:  # Long position
                pip_risk = entry_price - stop_loss
            else:  # Short position
                pip_risk = stop_loss - entry_price
            
            # Calculate position size
            position_size = risk_amount / pip_risk if pip_risk > 0 else 0
            
            # Calculate risk-reward (default to 0 since we don't have take_profit)
            risk_reward = 0
            
            return {
                'position_size': position_size,
                'risk_amount': risk_amount,
                'pip_risk': pip_risk,
                'risk_percentage': risk_percentage,
                'risk_reward': risk_reward  # Add this field
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'position_size': 0,
                'risk_amount': 0,
                'pip_risk': 0,
                'risk_percentage': risk_percentage,
                'risk_reward': 0  # Add this field
            }


    def multi_timeframe_analysis(self, dfs: Dict[str, pd.DataFrame], symbol: str) -> Dict:
        """
        Perform multi-timeframe analysis
        
        Args:
            dfs (dict): Dictionary of dataframes for different timeframes
            symbol (str): Trading symbol
            
        Returns:
            dict: Multi-timeframe analysis results
        """
        mtf_analysis = {
            'symbol': symbol,
            'timeframes': {},
            'overall_bias': 'neutral',
            'confluence_signals': [],
            'trade_setups': []
        }
        
        # Analyze each timeframe
        for timeframe, df in dfs.items():
            analysis = self.analyze_chart(df, symbol)
            mtf_analysis['timeframes'][timeframe] = analysis
        
        # Determine overall bias (weighted by timeframe)
        timeframe_weights = {
            '1m': 0.05,
            '5m': 0.1,
            '15m': 0.15,
            '1h': 0.2,
            '4h': 0.25,
            '1d': 0.25
        }
        
        bullish_weight = 0
        bearish_weight = 0
        total_weight = 0
        
        for timeframe, analysis in mtf_analysis['timeframes'].items():
            weight = timeframe_weights.get(timeframe, 0.1)
            total_weight += weight
            
            if analysis['bias'] == 'bullish':
                bullish_weight += weight
            elif analysis['bias'] == 'bearish':
                bearish_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            bullish_weight /= total_weight
            bearish_weight /= total_weight
        
        # Determine overall bias
        if bullish_weight > 0.6:
            mtf_analysis['overall_bias'] = 'strongly bullish'
        elif bullish_weight > 0.4:
            mtf_analysis['overall_bias'] = 'bullish'
        elif bearish_weight > 0.6:
            mtf_analysis['overall_bias'] = 'strongly bearish'
        elif bearish_weight > 0.4:
            mtf_analysis['overall_bias'] = 'bearish'
        else:
            mtf_analysis['overall_bias'] = 'neutral'
        
        # Find confluence signals across timeframes
        signal_counts = {}
        
        for timeframe, analysis in mtf_analysis['timeframes'].items():
            for signal in analysis['signals']:
                key = f"{signal['type']}_{signal['indicator']}"
                if key not in signal_counts:
                    signal_counts[key] = {
                        'type': signal['type'],
                        'indicator': signal['indicator'],
                        'description': signal['description'],
                        'timeframes': [],
                        'strength': 0
                    }
                
                signal_counts[key]['timeframes'].append(timeframe)
                signal_counts[key]['strength'] += signal['strength'] * timeframe_weights.get(timeframe, 0.1)
        
        # Filter for signals with multiple timeframe confluence
        for key, signal in signal_counts.items():
            if len(signal['timeframes']) >= 2:  # Signal appears in at least 2 timeframes
                mtf_analysis['confluence_signals'].append({
                    'type': signal['type'],
                    'indicator': signal['indicator'],
                    'description': signal['description'],
                    'timeframes': signal['timeframes'],
                    'strength': signal['strength']
                })
        
        # Sort confluence signals by strength
        mtf_analysis['confluence_signals'].sort(key=lambda x: x['strength'], reverse=True)
        
        # Get trade setups from the primary timeframe (if specified)
        primary_timeframe = '1h'  # Default to 1h
        if primary_timeframe in mtf_analysis['timeframes']:
            mtf_analysis['trade_setups'] = mtf_analysis['timeframes'][primary_timeframe].get('trade_setups', [])
        
        return mtf_analysis

