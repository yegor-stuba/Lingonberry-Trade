"""
Sentiment analysis module for trading decisions
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
from trading_bot.config.credentials import FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY, NEWS_API_KEY

# Optional: If transformers is available, use it for more advanced sentiment analysis
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Class for analyzing market sentiment from news and social media"""
    
    def __init__(self, use_transformers=True):
        """Initialize the sentiment analyzer"""
        # Check if transformers is available
        try:
            from transformers import pipeline
            TRANSFORMERS_AVAILABLE = True
        except ImportError:
            TRANSFORMERS_AVAILABLE = False
            logger.warning("Transformers library not available. Using rule-based sentiment analysis only.")
        
        self.use_transformers = use_transformers and TRANSFORMERS_AVAILABLE
        self.sentiment_model = None
        
        if self.use_transformers:
            try:
                # Try to load a simpler, more commonly available model
                self.sentiment_model = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
                logger.info("Loaded distilbert sentiment model successfully")
            except Exception as e:
                logger.warning(f"Could not load primary sentiment model: {e}")
                try:
                    # Fallback to default model
                    self.sentiment_model = pipeline("sentiment-analysis")
                    logger.info("Loaded default sentiment model successfully")
                except Exception as e:
                    logger.error(f"Could not load any sentiment model: {e}")
                    self.sentiment_model = None

    async def analyze_news_sentiment(self, symbol: str, market_type: str = 'forex') -> Dict:
        """
        Analyze sentiment from financial news
        
        Args:
            symbol (str): Trading symbol
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            dict: Sentiment analysis results
        """
        try:
            # Get news articles
            news_articles = await self._fetch_news(symbol, market_type)
            
            if not news_articles:
                logger.warning(f"No news articles found for {symbol}, using neutral sentiment")
                return {
                    'symbol': symbol,
                    'sentiment_score': 0,
                    'sentiment': 'neutral',
                    'confidence': 0,
                    'news_count': 0,
                    'latest_news': [],
                    'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0}
                }
        
            # Analyze sentiment for each article
            sentiment_scores = []
            sentiment_labels = []
            
            for article in news_articles:
                title = article.get('title', '')
                summary = article.get('summary', '')
                
                # Combine title and summary for analysis
                text = f"{title}. {summary}"
                
                # Get sentiment score
                if self.use_transformers and self.sentiment_model:
                    # Use transformers for more accurate sentiment
                    result = self.sentiment_model(text)[0]
                    label = result['label'].lower()
                    score = result['score']
                    
                    # Convert label to numeric score (-1 to 1)
                    if label == 'positive':
                        numeric_score = score
                    elif label == 'negative':
                        numeric_score = -score
                    else:
                        numeric_score = 0
                else:
                    # Simple rule-based sentiment
                    numeric_score, label = self._simple_sentiment_analysis(text)
                    score = abs(numeric_score)
                
                sentiment_scores.append(numeric_score)
                sentiment_labels.append(label)
                
                # Add sentiment to article
                article['sentiment'] = label
                article['sentiment_score'] = numeric_score
            
            # Calculate overall sentiment
            if sentiment_scores:
                avg_score = sum(sentiment_scores) / len(sentiment_scores)
                
                # Count sentiment labels
                sentiment_counts = {
                    'positive': sentiment_labels.count('positive'),
                    'neutral': sentiment_labels.count('neutral'),
                    'negative': sentiment_labels.count('negative')
                }
                
                # Determine overall sentiment
                if avg_score > 0.2:
                    overall_sentiment = 'bullish'
                elif avg_score < -0.2:
                    overall_sentiment = 'bearish'
                else:
                    overall_sentiment = 'neutral'
                
                # Calculate confidence based on consistency of sentiment
                dominant_count = max(sentiment_counts.values())
                confidence = dominant_count / len(sentiment_scores) if sentiment_scores else 0
                
                return {
                    'symbol': symbol,
                    'sentiment_score': avg_score,
                    'sentiment': overall_sentiment,
                    'confidence': confidence,
                    'news_count': len(news_articles),
                    'latest_news': news_articles[:5],  # Return only the 5 most recent articles
                    'sentiment_breakdown': sentiment_counts
                }
            else:
                return {
                    'symbol': symbol,
                    'sentiment_score': 0,
                    'sentiment': 'neutral',
                    'confidence': 0,
                    'news_count': 0,
                    'latest_news': [],
                    'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0}
                }
                
        except Exception as e:
            logger.error(f"Error analyzing news sentiment: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'sentiment': 'neutral',
                'sentiment_score': 0
            }
    
    async def _fetch_news(self, symbol: str, market_type: str) -> List[Dict]:
        """Fetch news articles for a symbol"""
        try:
            # Prepare search terms based on market type and symbol
            search_query = f"{symbol} {market_type} trading"
            
            # Get current date and date 3 days ago
            today = datetime.now()
            three_days_ago = today - timedelta(days=3)
            
            # Format dates for API
            from_date = three_days_ago.strftime('%Y-%m-%d')
            to_date = today.strftime('%Y-%m-%d')
            
            # Check if API key is valid
            if not NEWS_API_KEY or NEWS_API_KEY == "45f69cc6c2a44605af277a157349eaad":
                logger.warning(f"Invalid News API key. Using synthetic news data for {symbol}")
                return self._generate_synthetic_news(symbol, market_type)
                
            # Use NewsAPI
            url = f"https://newsapi.org/v2/everything?q={search_query}&from={from_date}&to={to_date}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
                
            logger.info(f"Fetching news for {symbol} using URL: {url[:60]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get('articles', [])
                        
                        logger.info(f"Successfully fetched {len(articles)} news articles for {symbol}")
                        
                        # Process articles
                        processed_articles = []
                        for article in articles:
                            processed_articles.append({
                                'title': article.get('title', ''),
                                'summary': article.get('description', ''),
                                'url': article.get('url', ''),
                                'source': article.get('source', {}).get('name', ''),
                                'published_at': article.get('publishedAt', '')
                            })
                        
                        return processed_articles
                    else:
                        # Log specific error details
                        error_text = await response.text()
                        logger.warning(f"Failed to fetch news for {symbol}: {response.status} - {error_text[:100]}")
                        return self._generate_synthetic_news(symbol, market_type)
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return self._generate_synthetic_news(symbol, market_type)

    def _generate_synthetic_news(self, symbol: str, market_type: str) -> List[Dict]:
        """Generate synthetic news when API fails"""
        logger.info(f"Generating synthetic news for {symbol}")
        
        # Create a few generic news items
        current_time = datetime.now().isoformat()
        
        return [
            {
                'title': f"Market analysis for {symbol}",
                'summary': f"Recent market movements show {symbol} in consolidation phase.",
                'url': "",
                'source': "Synthetic Data",
                'published_at': current_time
            },
            {
                'title': f"Technical outlook for {symbol}",
                'summary': f"Technical indicators suggest {symbol} may be approaching key levels.",
                'url': "",
                'source': "Synthetic Data",
                'published_at': current_time
            }
        ]

    
    def _simple_sentiment_analysis(self, text: str) -> tuple[float, str]:
        """
        Simple rule-based sentiment analysis
        
        Args:
            text (str): Text to analyze
            
        Returns:
            tuple: (sentiment_score, sentiment_label)
        """
        # Lists of positive and negative words
        positive_words = [
            'bullish', 'rally', 'gain', 'rise', 'up', 'surge', 'soar', 'jump',
            'positive', 'strong', 'strength', 'growth', 'growing', 'improve',
            'improved', 'improving', 'outperform', 'beat', 'exceeded', 'exceed',
            'higher', 'record', 'support', 'buy', 'opportunity', 'optimistic',
            'confident', 'uptrend', 'upside', 'recovery', 'rebound'
        ]
        
        negative_words = [
            'bearish', 'fall', 'drop', 'decline', 'down', 'plunge', 'tumble',
            'negative', 'weak', 'weakness', 'contraction', 'contracting', 'worsen',
            'worsened', 'worsening', 'underperform', 'miss', 'missed', 'lower',
            'resistance', 'sell', 'risk', 'pessimistic', 'concerned', 'downtrend',
            'downside', 'recession', 'crash', 'correction', 'fear', 'worry'
        ]
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Count positive and negative words
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        # Calculate sentiment score (-1 to 1)
        total_count = positive_count + negative_count
        if total_count > 0:
            sentiment_score = (positive_count - negative_count) / total_count
        else:
            sentiment_score = 0
        
        # Determine sentiment label
        if sentiment_score > 0.2:
            sentiment_label = 'positive'
        elif sentiment_score < -0.2:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        return sentiment_score, sentiment_label    
    async def analyze_social_sentiment(self, symbol: str, market_type: str = 'forex') -> Dict:
        """
        Analyze sentiment from social media
        
        Args:
            symbol (str): Trading symbol
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            dict: Sentiment analysis results
        """
        try:
            # This would typically call a social media API or web scraper
            # For now, we'll return a placeholder result
            
            # In a real implementation, you would:
            # 1. Fetch tweets/posts about the symbol
            # 2. Analyze sentiment of each post
            # 3. Calculate overall sentiment
            
            # Placeholder result
            return {
                'symbol': symbol,
                'sentiment_score': 0.1,  # Range from -1 to 1
                'sentiment': 'neutral',
                'confidence': 0.6,
                'source': 'social_media',
                'post_count': 0,
                'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing social sentiment: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'sentiment': 'neutral',
                'sentiment_score': 0
            }
    
    async def get_combined_sentiment(self, symbol: str, market_type: str = 'forex') -> Dict:
        """
        Get combined sentiment from news and social media
        
        Args:
            symbol (str): Trading symbol
            market_type (str): Market type ('forex', 'crypto', 'indices', 'metals')
            
        Returns:
            dict: Combined sentiment analysis
        """
        try:
            # Get sentiment from different sources
            news_sentiment = await self.analyze_news_sentiment(symbol, market_type)
            social_sentiment = await self.analyze_social_sentiment(symbol, market_type)
            
            # Calculate weighted average of sentiment scores
            # News sentiment is given more weight (0.7) than social sentiment (0.3)
            combined_score = (
                news_sentiment.get('sentiment_score', 0) * 0.7 + 
                social_sentiment.get('sentiment_score', 0) * 0.3
            )
            
            # Determine overall sentiment
            if combined_score > 0.2:
                overall_sentiment = 'bullish'
            elif combined_score < -0.2:
                overall_sentiment = 'bearish'
            else:
                overall_sentiment = 'neutral'
            
            # Calculate confidence as weighted average of confidences
            combined_confidence = (
                news_sentiment.get('confidence', 0) * 0.7 + 
                social_sentiment.get('confidence', 0) * 0.3
            )
            
            return {
                'symbol': symbol,
                'sentiment_score': combined_score,
                'sentiment': overall_sentiment,
                'confidence': combined_confidence,
                'news_sentiment': news_sentiment,
                'social_sentiment': social_sentiment,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting combined sentiment: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'sentiment': 'neutral',
                'sentiment_score': 0
            }
    
    def get_sentiment_signals(self, sentiment_data: Dict) -> List[Dict]:
        """
        Generate trading signals based on sentiment analysis
        
        Args:
            sentiment_data (dict): Sentiment analysis data
            
        Returns:
            list: Sentiment-based trading signals
        """
        signals = []
        
        try:
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            sentiment = sentiment_data.get('sentiment', 'neutral')
            confidence = sentiment_data.get('confidence', 0)
            
            # Strong bullish sentiment
            if sentiment == 'bullish' and sentiment_score > 0.5 and confidence > 0.6:
                signals.append({
                    'type': 'bullish',
                    'source': 'sentiment',
                    'strength': min(100, int(sentiment_score * 100) + int(confidence * 20)),
                    'description': f"Strong bullish sentiment with {confidence:.2f} confidence"
                })
            
            # Moderate bullish sentiment
            elif sentiment == 'bullish' and sentiment_score > 0.2:
                signals.append({
                    'type': 'bullish',
                    'source': 'sentiment',
                    'strength': min(100, int(sentiment_score * 80) + int(confidence * 20)),
                    'description': f"Moderate bullish sentiment with {confidence:.2f} confidence"
                })
            
            # Strong bearish sentiment
            elif sentiment == 'bearish' and sentiment_score < -0.5 and confidence > 0.6:
                signals.append({
                    'type': 'bearish',
                    'source': 'sentiment',
                    'strength': min(100, int(abs(sentiment_score) * 100) + int(confidence * 20)),
                    'description': f"Strong bearish sentiment with {confidence:.2f} confidence"
                })
            
            # Moderate bearish sentiment
            elif sentiment == 'bearish' and sentiment_score < -0.2:
                signals.append({
                    'type': 'bearish',
                    'source': 'sentiment',
                    'strength': min(100, int(abs(sentiment_score) * 80) + int(confidence * 20)),
                    'description': f"Moderate bearish sentiment with {confidence:.2f} confidence"
                })
            
            # Check for sentiment shifts in news
            news_sentiment = sentiment_data.get('news_sentiment', {})
            if 'latest_news' in news_sentiment and news_sentiment['latest_news']:
                # Check if the most recent news has a different sentiment than the overall
                latest_news = news_sentiment['latest_news'][0]
                latest_sentiment = latest_news.get('sentiment', 'neutral')
                
                if latest_sentiment == 'positive' and sentiment != 'bullish':
                    signals.append({
                        'type': 'bullish',
                        'source': 'sentiment_shift',
                        'strength': 60,
                        'description': "Recent news shows positive shift in sentiment"
                    })
                elif latest_sentiment == 'negative' and sentiment != 'bearish':
                    signals.append({
                        'type': 'bearish',
                        'source': 'sentiment_shift',
                        'strength': 60,
                        'description': "Recent news shows negative shift in sentiment"
                    })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating sentiment signals: {e}")
            return []
    
    def find_trade_setups(self, sentiment_data: Dict, min_rr: float = 2.0) -> List[Dict]:
        """
        Find potential trade setups based on sentiment analysis
        
        Args:
            sentiment_data (dict): Sentiment analysis data
            min_rr (float): Minimum risk-reward ratio
            
        Returns:
            list: List of trade setups
        """
        trade_setups = []
        
        try:
            # Generate signals
            signals = self.get_sentiment_signals(sentiment_data)
            
            # We need price data to determine entry, stop loss, and take profit
            # Since sentiment analysis alone can't provide these, we'll return
            # a simplified trade setup that can be combined with technical/SMC analysis
            
            if signals:
                # Get the strongest signal
                strongest_signal = max(signals, key=lambda x: x['strength'])
                
                if strongest_signal['type'] == 'bullish' and strongest_signal['strength'] > 70:
                    trade_setups.append({
                        'direction': 'BUY',
                        'strength': strongest_signal['strength'],
                        'reason': strongest_signal['description'],
                        'sentiment_score': sentiment_data.get('sentiment_score', 0),
                        'confidence': sentiment_data.get('confidence', 0)
                    })
                elif strongest_signal['type'] == 'bearish' and strongest_signal['strength'] > 70:
                    trade_setups.append({
                        'direction': 'SELL',
                        'strength': strongest_signal['strength'],
                        'reason': strongest_signal['description'],
                        'sentiment_score': sentiment_data.get('sentiment_score', 0),
                        'confidence': sentiment_data.get('confidence', 0)
                    })
            
            return trade_setups
            
        except Exception as e:
            logger.error(f"Error finding sentiment-based trade setups: {e}")
            return []
