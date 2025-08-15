# Integração Yahoo Finance

import yfinance as yf
from yfinance.shared import TickerError
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import backoff

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use backoff to handle rate limiting
@backoff.on_exception(
    backoff.expo,
    (yf.exceptions.YFInternalError, yf.exceptions.YFQueryError),
    max_tries=settings.YAHOO_FINANCE_MAX_RETRIES,
    factor=settings.YAHOO_FINANCE_BACKOFF_FACTOR
)
@lru_cache(maxsize=128)
def get_asset_info_and_price_sync(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch asset info and current price synchronously from Yahoo Finance.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        if not info:
            logger.warning(f"No info found for ticker {ticker}")
            return None
        
        data = {
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market": info.get("exchange") or "UNKNOWN",
            "currency": info.get("currency") or "USD",
            "asset_type": info.get("quoteType", "STOCK").lower(),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "current_price": info.get("regularMarketPrice"),
            "previous_close": info.get("regularMarketPreviousClose"),
            "daily_change": info.get("regularMarketChange"),
            "daily_change_percent": info.get("regularMarketChangePercent"),
            "volume": info.get("regularMarketVolume"),
            "website": info.get("website"),
            "logo_url": info.get("logo_url"),
            "last_price_update": datetime.now(),
            "price_update_source": "yahoo_finance"
        }
        
        return data
        
    except TickerError as e:
        logger.error(f"TickerError for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

@backoff.on_exception(
    backoff.expo,
    (yf.exceptions.YFInternalError, yf.exceptions.YFQueryError),
    max_tries=settings.YAHOO_FINANCE_MAX_RETRIES,
    factor=settings.YAHOO_FINANCE_BACKOFF_FACTOR
)
def get_price_history_sync(
    ticker: str, 
    period: str = "1y", 
    interval: str = "1d"
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch price history synchronously from Yahoo Finance.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        history_df = ticker_obj.history(period=period, interval=interval)
        
        if history_df.empty:
            return None
            
        history_df.index = history_df.index.tz_convert(None) # Remove timezone for database compatibility
        history_df = history_df.reset_index().rename(columns={'index': 'date'})
        history_df = history_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].rename(columns={
            'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        })
        
        return history_df.to_dict('records')
        
    except TickerError as e:
        logger.error(f"TickerError fetching history for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching price history for {ticker}: {e}")
        return None

def get_current_price_sync(ticker: str) -> Optional[Decimal]:
    """
    Fetch only the current price for a ticker.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        price = ticker_obj.info.get("regularMarketPrice")
        if price is not None:
            return Decimal(str(price))
        return None
    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {e}")
        return None