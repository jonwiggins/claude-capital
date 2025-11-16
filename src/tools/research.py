"""
Research tools for Claude Capital.

Integrates web search and news for market research.
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class ResearchTools:
    """Tools for conducting market research."""

    def __init__(self):
        """Initialize research tools."""
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')
        self.news_api_key = os.getenv('NEWS_API_KEY')

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search for trading research.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            Search results
        """
        if not self.tavily_api_key:
            return {
                "error": "TAVILY_API_KEY not set",
                "suggestion": "Add Tavily API key to .env for web search capabilities"
            }

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "query": query,
                    "results": data.get('results', []),
                    "answer": data.get('answer', '')
                }
            else:
                return {"error": f"Search failed: {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    def get_crypto_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get cryptocurrency news.

        Args:
            symbols: List of symbols to get news for
            limit: Number of articles

        Returns:
            News articles
        """
        # Simplified implementation - would integrate with crypto news APIs
        # like CryptoPanic, CoinGecko, or NewsAPI

        if not symbols:
            symbols = ['BTC', 'ETH']

        # Placeholder response
        return {
            "symbols": symbols,
            "articles": [],
            "note": "Integrate with CryptoPanic API or NewsAPI for real news"
        }

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Sentiment analysis
        """
        # Simple keyword-based sentiment (placeholder)
        # In production, use proper NLP library or API

        positive_keywords = ['bullish', 'gains', 'rally', 'surge', 'growth', 'positive']
        negative_keywords = ['bearish', 'crash', 'drop', 'decline', 'loss', 'negative']

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)

        total = positive_count + negative_count

        if total == 0:
            sentiment = "neutral"
            score = 0
        else:
            score = (positive_count - negative_count) / total
            if score > 0.3:
                sentiment = "positive"
            elif score < -0.3:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": score,
            "positive_signals": positive_count,
            "negative_signals": negative_count
        }

    def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Comprehensive research on a topic.

        Args:
            topic: Research topic

        Returns:
            Research findings
        """
        results = {}

        # Web search
        search_results = self.web_search(topic)
        results['web_search'] = search_results

        # If topic contains a crypto symbol, get news
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'BNB']
        mentioned_symbols = [s for s in crypto_symbols if s in topic.upper()]

        if mentioned_symbols:
            results['news'] = self.get_crypto_news(mentioned_symbols)

        # Analyze sentiment of search results
        if 'results' in search_results and search_results['results']:
            combined_text = " ".join([
                r.get('content', '') for r in search_results['results'][:3]
            ])
            results['sentiment'] = self.analyze_sentiment(combined_text)

        results['topic'] = topic
        results['timestamp'] = datetime.utcnow().isoformat()

        return results
