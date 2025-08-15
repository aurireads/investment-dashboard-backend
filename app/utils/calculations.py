# Utilitários de cálculo
from typing import List, Dict
from decimal import Decimal
import logging
from datetime import date, datetime
from collections import defaultdict
from app.models.allocation import Allocation
from app.models.daily_return import DailyReturn

logger = logging.getLogger(__name__)

def calculate_irr(cash_flows: List[float]) -> float:
    """
    Calculate the Internal Rate of Return (IRR) of a series of cash flows.
    This is a placeholder and would require a proper library like numpy-financial.
    """
    try:
        # A proper implementation would use numpy.irr
        # For now, we return 0
        return 0.0
    except Exception as e:
        logger.error(f"Error calculating IRR: {e}")
        return 0.0

def calculate_twr(daily_returns: Dict[date, float]) -> float:
    """
    Calculate Time-Weighted Return (TWR) from a dictionary of daily returns.
    """
    if not daily_returns:
        return 0.0
    
    returns_product = 1.0
    for day in sorted(daily_returns.keys()):
        returns_product *= (1 + daily_returns[day])
        
    twr = (returns_product - 1)
    return twr

def calculate_daily_returns(
    allocations: List[Allocation], 
    price_history: List[DailyReturn], 
    start_date: date, 
    end_date: date
) -> (Dict[date, float], Decimal, Decimal):
    """
    Calculate daily returns for a portfolio based on allocations and price history.
    """
    # Group price history by asset
    asset_prices = defaultdict(dict)
    for price in price_history:
        asset_prices[price.asset_id][price.date] = price.close_price
    
    # Get a list of all dates in the period
    all_dates = sorted(list(set(p.date for p in price_history)))
    
    daily_returns = {}
    portfolio_value = {}
    start_value = Decimal('0')
    
    # Calculate portfolio value for each day
    for day in all_dates:
        day_value = Decimal('0')
        for alloc in allocations:
            price = asset_prices.get(alloc.asset_id, {}).get(day)
            if price:
                day_value += alloc.quantity * price
        
        if day_value > 0:
            portfolio_value[day] = day_value
            
    # Calculate daily returns
    sorted_days = sorted(portfolio_value.keys())
    for i in range(1, len(sorted_days)):
        today = sorted_days[i]
        yesterday = sorted_days[i-1]
        
        if portfolio_value[yesterday] > 0:
            daily_returns[today] = float((portfolio_value[today] - portfolio_value[yesterday]) / portfolio_value[yesterday])
            
    start_value = portfolio_value.get(sorted_days[0], Decimal('0')) if sorted_days else Decimal('0')
    end_value = portfolio_value.get(sorted_days[-1], Decimal('0')) if sorted_days else Decimal('0')
    
    return daily_returns, start_value, end_value

def calculate_returns_from_history(history: List[DailyReturn], current_price: Decimal = None) -> Dict[str, Decimal]:
    """
    Calculate various returns (weekly, monthly, yearly) from price history.
    """
    if not history:
        return {}
        
    latest_price = current_price or history[-1].close_price
    
    # Get prices from specific points in time
    one_week_ago_price = None
    one_month_ago_price = None
    one_year_ago_price = None
    
    for dr in reversed(history):
        days_ago = (date.today() - dr.date).days
        if not one_week_ago_price and days_ago >= 7:
            one_week_ago_price = dr.close_price
        if not one_month_ago_price and days_ago >= 30:
            one_month_ago_price = dr.close_price
        if not one_year_ago_price and days_ago >= 365:
            one_year_ago_price = dr.close_price
    
    results = {}
    if one_week_ago_price and one_week_ago_price > 0:
        results["weekly_change_percent"] = (latest_price - one_week_ago_price) / one_week_ago_price * 100
    if one_month_ago_price and one_month_ago_price > 0:
        results["monthly_change_percent"] = (latest_price - one_month_ago_price) / one_month_ago_price * 100
    if one_year_ago_price and one_year_ago_price > 0:
        results["yearly_change_percent"] = (latest_price - one_year_ago_price) / one_year_ago_price * 100
        
    return results