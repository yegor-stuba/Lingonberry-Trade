"""
Test the sentiment analyzer implementation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_bot.analysis.sentiment import SentimentAnalyzer

class TestSentimentAnalyzer(unittest.TestCase):
    """Test cases for the sentiment analyzer implementation"""
    
    def setUp(self):
        """Set up test data"""
        # Initialize analyzer
        self.analyzer = SentimentAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer)
    
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer._fetch_news')
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer._analyze_sentiment')
    async def test_get_sentiment(self, mock_analyze, mock_fetch):
        """Test get_sentiment method"""
        # Mock the news fetching
        mock_news = [
            {
                'title': 'EUR/USD rises on positive economic data',
                'summary': 'The EUR/USD pair rose after positive economic data from Europe.',
                'url': 'https://example.com/news1',
                'published_at': datetime.now().isoformat()
            },
            {
                'title': 'Analysts predict further gains for EUR/USD',
                'summary': 'Analysts are bullish on EUR/USD due to improving economic conditions.',
                'url': 'https://example.com/news2',
                'published_at': datetime.now().isoformat()
            }
        ]
        mock_fetch.return_value = mock_news
        
        # Mock the sentiment analysis
        mock_analyze.return_value = {
            'score': 0.75,
            'sentiment': 'bullish',
            'confidence': 0.8
        }
        
        # Call the method
        sentiment = await self.analyzer.get_sentiment('EURUSD', 'forex')
        
        # Check the result
        self.assertIsNotNone(sentiment)
        self.assertEqual(sentiment['symbol'], 'EURUSD')
        self.assertEqual(sentiment['sentiment'], 'bullish')
        self.assertEqual(sentiment['sentiment_score'], 0.75)
        self.assertEqual(sentiment['confidence'], 0.8)
        self.assertIn('news', sentiment)
        self.assertEqual(len(sentiment['news']), 2)
    
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer._fetch_social_media')
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer._analyze_sentiment')
    async def test_get_social_sentiment(self, mock_analyze, mock_fetch):
        """Test get_social_sentiment method"""
        # Mock the social media fetching
        mock_posts = [
            {
                'text': 'EUR/USD looking bullish today! #forex',
                'source': 'twitter',
                'timestamp': datetime.now().isoformat()
            },
            {
                'text': 'Going long on EUR/USD, technical setup looks great',
                'source': 'reddit',
                'timestamp': datetime.now().isoformat()
            }
        ]
        mock_fetch.return_value = mock_posts
        
        # Mock the sentiment analysis
        mock_analyze.return_value = {
            'score': 0.65,
            'sentiment': 'bullish',
            'confidence': 0.7
        }
        
        # Call the method
        sentiment = await self.analyzer.get_social_sentiment('EURUSD')
        
        # Check the result
        self.assertIsNotNone(sentiment)
        self.assertEqual(sentiment['symbol'], 'EURUSD')
        self.assertEqual(sentiment['sentiment'], 'bullish')
        self.assertEqual(sentiment['sentiment_score'], 0.65)
        self.assertEqual(sentiment['confidence'], 0.7)
        self.assertIn('posts', sentiment)
        self.assertEqual(len(sentiment['posts']), 2)
    
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer.get_sentiment')
    @patch('trading_bot.analysis.sentiment.SentimentAnalyzer.get_social_sentiment')
    async def test_get_combined_sentiment(self, mock_social, mock_news):
        """Test get_combined_sentiment method"""
        # Mock the news sentiment
        mock_news_sentiment = {
            'symbol': 'EURUSD',
            'sentiment': 'bullish',
            'sentiment_score': 0.75,
            'confidence': 0.8,
            'news': []
        }
        mock_news.return_value = mock_news_sentiment
        
        # Mock the social sentiment
        mock_social_sentiment = {
            'symbol': 'EURUSD',
            'sentiment': 'neutral',
            'sentiment_score': 0.5,
            'confidence': 0.6,
            'posts': []
        }
        mock_social.return_value = mock_social_sentiment
        
        # Call the method
        sentiment = await self.analyzer.get_combined_sentiment('EURUSD', 'forex')
        
        # Check the result
        self.assertIsNotNone(sentiment)
        self.assertEqual(sentiment['symbol'], 'EURUSD')
        self.assertIn('sentiment', sentiment)
        self.assertIn('sentiment_score', sentiment)
        self.assertIn('confidence', sentiment)
        self.assertIn('news_sentiment', sentiment)
        self.assertIn('social_sentiment', sentiment)
        
        # Combined sentiment should be weighted average
        expected_score = (0.75 * 0.8 + 0.5 * 0.6) / (0.8 + 0.6)
        self.assertAlmostEqual(sentiment['sentiment_score'], expected_score, places=4)
    
    def test_analyze_sentiment(self):
        """Test _analyze_sentiment method"""
        # Test with positive text
        positive_text = "The EUR/USD pair is showing strong bullish momentum with improving economic data."
        positive_result = self.analyzer._analyze_sentiment(positive_text)
        
        self.assertIsNotNone(positive_result)
        self.assertIn('score', positive_result)
        self.assertIn('sentiment', positive_result)
        self.assertIn('confidence', positive_result)
        self.assertGreater(positive_result['score'], 0.5)
        self.assertEqual(positive_result['sentiment'], 'bullish')
        
        # Test with negative text
        negative_text = "EUR/USD is facing significant downward pressure due to poor economic outlook."
        negative_result = self.analyzer._analyze_sentiment(negative_text)
        
        self.assertIsNotNone(negative_result)
        self.assertLess(negative_result['score'], 0.5)
        self.assertEqual(negative_result['sentiment'], 'bearish')
        
        # Test with neutral text
        neutral_text = "EUR/USD is trading within a range with no clear direction."
        neutral_result = self.analyzer._analyze_sentiment(neutral_text)
        
        self.assertIsNotNone(neutral_result)
        self.assertAlmostEqual(neutral_result['score'], 0.5, delta=0.2)
        self.assertEqual(neutral_result['sentiment'], 'neutral')
    
    def test_generate_synthetic_news(self):
        """Test _generate_synthetic_news method"""
        news = self.analyzer._generate_synthetic_news('EURUSD', 'forex')
        
        # Check the result
        self.assertIsNotNone(news)
        self.assertIsInstance(news, list)
        self.assertGreater(len(news), 0)
        
        # Check news item structure
        news_item = news[0]
        self.assertIn('title', news_item)
        self.assertIn('summary', news_item)
        self.assertIn('url', news_item)
        self.assertIn('published_at', news_item)
        
        # Check that the symbol is mentioned in the title or summary
        self.assertTrue('EURUSD' in news_item['title'] or 'EURUSD' in news_item['summary'] or 
                        'EUR/USD' in news_item['title'] or 'EUR/USD' in news_item['summary'])
    
    def test_generate_synthetic_social_posts(self):
        """Test _generate_synthetic_social_posts method"""
        posts = self.analyzer._generate_synthetic_social_posts('EURUSD')
        
        # Check the result
        self.assertIsNotNone(posts)
        self.assertIsInstance(posts, list)
        self.assertGreater(len(posts), 0)
        
        # Check post structure
        post = posts[0]
        self.assertIn('text', post)
        self.assertIn('source', post)
        self.assertIn('timestamp', post)
        
        # Check that the symbol is mentioned in the text
        self.assertTrue('EURUSD' in post['text'] or 'EUR/USD' in post['text'])
    
    def test_map_sentiment_score_to_label(self):
        """Test _map_sentiment_score_to_label method"""
        # Test bullish sentiment
        bullish = self.analyzer._map_sentiment_score_to_label(0.75)
        self.assertEqual(bullish, 'bullish')
        
        # Test bearish sentiment
        bearish = self.analyzer._map_sentiment_score_to_label(0.25)
        self.assertEqual(bearish, 'bearish')
        
        # Test neutral sentiment
        neutral = self.analyzer._map_sentiment_score_to_label(0.5)
        self.assertEqual(neutral, 'neutral')
    
    @patch('aiohttp.ClientSession.get')
    async def test_fetch_news_with_api(self, mock_get):
        """Test _fetch_news method with API"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'articles': [
                {
                    'title': 'EUR/USD rises on positive economic data',
                    'description': 'The EUR/USD pair rose after positive economic data from Europe.',
                    'url': 'https://example.com/news1',
                    'publishedAt': datetime.now().isoformat()
                },
                {
                    'title': 'Analysts predict further gains for EUR/USD',
                    'description': 'Analysts are bullish on EUR/USD due to improving economic conditions.',
                    'url': 'https://example.com/news2',
                    'publishedAt': datetime.now().isoformat()
                }
            ]
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Call the method
        news = await self.analyzer._fetch_news('EURUSD', 'forex')
        
        # Check the result
        self.assertIsNotNone(news)
        self.assertIsInstance(news, list)
        self.assertEqual(len(news), 2)
        
        # Check news item structure
        news_item = news[0]
        self.assertIn('title', news_item)
        self.assertIn('summary', news_item)
        self.assertIn('url', news_item)
        self.assertIn('published_at', news_item)
    
    @patch('aiohttp.ClientSession.get')
    async def test_fetch_news_api_error(self, mock_get):
        """Test _fetch_news method with API error"""
        # Mock the API response with an error
        mock_response = MagicMock()
        mock_response.status = 401
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Call the method
        news = await self.analyzer._fetch_news('EURUSD', 'forex')
        
        # Should fall back to synthetic news
        self.assertIsNotNone(news)
        self.assertIsInstance(news, list)
        self.assertGreater(len(news), 0)
    
    def test_calculate_sentiment_confidence(self):
        """Test _calculate_sentiment_confidence method"""
        # Test high confidence (score far from 0.5)
        high_confidence = self.analyzer._calculate_sentiment_confidence(0.9)
        self.assertGreater(high_confidence, 0.8)
        
        # Test low confidence (score close to 0.5)
        low_confidence = self.analyzer._calculate_sentiment_confidence(0.55)
        self.assertLess(low_confidence, 0.5)
        
        # Test symmetry (same confidence for equidistant scores)
        conf_high = self.analyzer._calculate_sentiment_confidence(0.8)
        conf_low = self.analyzer._calculate_sentiment_confidence(0.2)
        self.assertAlmostEqual(conf_high, conf_low, places=4)
    
    def test_get_market_keywords(self):
        """Test _get_market_keywords method"""
        # Test forex keywords
        forex_keywords = self.analyzer._get_market_keywords('forex')
        self.assertIsInstance(forex_keywords, list)
        self.assertIn('forex', forex_keywords)
        self.assertIn('currency', forex_keywords)
        
        # Test crypto keywords
        crypto_keywords = self.analyzer._get_market_keywords('crypto')
        self.assertIsInstance(crypto_keywords, list)
        self.assertIn('crypto', crypto_keywords)
        self.assertIn('bitcoin', crypto_keywords)
        
        # Test default keywords
        default_keywords = self.analyzer._get_market_keywords('unknown')
        self.assertIsInstance(default_keywords, list)
        self.assertGreater(len(default_keywords), 0)

if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSentimentAnalyzer)
    # Run the tests
    unittest.TextTestRunner(verbosity=2).run(suite)
