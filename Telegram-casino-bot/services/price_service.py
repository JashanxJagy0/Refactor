"""
Cryptocurrency price fetching and caching service
"""
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict
from config import MEXC_API_KEY, MEXC_API_SECRET

# Price cache (in-memory, consider Redis for production)
_price_cache: Dict[str, float] = {}
_price_cache_timestamp: Dict[str, float] = {}
PRICE_CACHE_TTL = 60  # seconds


async def get_crypto_price_usd(symbol: str) -> float:
    """
    Get cryptocurrency price in USD
    Uses CoinGecko API with caching
    """
    # Check cache first
    now = datetime.now().timestamp()
    if symbol in _price_cache and symbol in _price_cache_timestamp:
        if now - _price_cache_timestamp[symbol] < PRICE_CACHE_TTL:
            return _price_cache[symbol]
    
    # Fetch fresh price from CoinGecko
    try:
        coin_ids = {
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'TRX': 'tron',
            'SOL': 'solana',
            'TON': 'the-open-network',
            'USDT': 'tether',
            'USDC': 'usd-coin'
        }
        
        coin_id = coin_ids.get(symbol)
        if not coin_id:
            return 1.0  # Default for unknown tokens
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd",
                timeout=5.0
            )
            data = response.json()
            price = data.get(coin_id, {}).get('usd', 1.0)
            
            # Cache the price
            _price_cache[symbol] = price
            _price_cache_timestamp[symbol] = now
            
            return price
    except Exception as e:
        logging.error(f"Error fetching price for {symbol}: {e}")
        # Fallback to approximate prices if API fails
        fallback_prices = {
            'ETH': 3000.0,
            'BNB': 400.0,
            'TRX': 0.15,
            'SOL': 100.0,
            'TON': 5.0,
            'USDT': 1.0,
            'USDC': 1.0
        }
        return fallback_prices.get(symbol, 1.0)


async def get_mexc_ticker(pair: str) -> Optional[Dict]:
    """
    Get 24hr ticker data from MEXC exchange
    
    Args:
        pair: Trading pair (e.g., "BTCUSDT")
        
    Returns:
        Dict with price, volume, and 24hr stats
    """
    url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={pair}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            return {
                'symbol': data['symbol'],
                'last_price': float(data['lastPrice']),
                'price_change_percent': float(data['priceChangePercent']),
                'high_price': float(data['highPrice']),
                'low_price': float(data['lowPrice']),
                'volume': float(data['volume']),
            }
    except httpx.HTTPStatusError as e:
        logging.error(f"MEXC API Error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error fetching MEXC ticker for {pair}: {e}")
        return None


def format_price_message(ticker_data: Dict) -> str:
    """
    Format ticker data into a readable message
    
    Args:
        ticker_data: Dict from get_mexc_ticker()
        
    Returns:
        Formatted HTML string
    """
    symbol = ticker_data['symbol'].replace("USDT", "")
    price = ticker_data['last_price']
    change_percent = ticker_data['price_change_percent'] * 100
    high_price = ticker_data['high_price']
    low_price = ticker_data['low_price']
    volume = ticker_data['volume']
    
    direction_emoji = "🔼" if change_percent >= 0 else "🔽"
    
    return (
        f"📈 <b>{ticker_data['symbol']}</b> Price: <code>${price:,.8f}</code>\n\n"
        f"{direction_emoji} <b>24h Change:</b> {change_percent:+.2f}%\n"
        f"⬆️ <b>24h High:</b> ${high_price:,.8f}\n"
        f"⬇️ <b>24h Low:</b> ${low_price:,.8f}\n"
        f"📊 <b>24h Volume:</b> {volume:,.2f} {symbol}"
    )
