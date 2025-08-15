# Endpoints de performance

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List
from datetime import date
from decimal import Decimal
import logging

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.allocation import Allocation
from app.models.daily_return import DailyReturn
from app.schemas.performance import ReturnCalculation, NetNewMoneyHistory
from app.utils.calculations import calculate_twr, calculate_daily_returns, calculate_irr

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/clients/{client_id}/performance", response_model=ReturnCalculation)
async def get_client_performance(
    client_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculate and return the time-weighted return (TWR) for a client's portfolio.
    This is a simplified endpoint and would be more complex in a real-world scenario.
    """
    try:
        if not start_date:
            # Default to 1 year ago
            start_date = date.today().replace(year=date.today().year - 1)
        if not end_date:
            end_date = date.today()
            
        # Get all allocations for the client
        allocations_query = select(Allocation).where(
            and_(
                Allocation.client_id == client_id,
                Allocation.purchase_date.cast(date) <= end_date,
                (Allocation.exit_date.cast(date) >= start_date) | (Allocation.exit_date.is_(None))
            )
        )
        
        allocations_result = await db.execute(allocations_query)
        allocations = allocations_result.scalars().all()
        
        # Get price history for all assets in the portfolio
        asset_ids = [alloc.asset_id for alloc in allocations]
        
        prices_query = select(DailyReturn).where(
            and_(
                DailyReturn.asset_id.in_(asset_ids),
                DailyReturn.date >= start_date,
                DailyReturn.date <= end_date
            )
        ).order_by(DailyReturn.date)
        
        prices_result = await db.execute(prices_query)
        price_history = prices_result.scalars().all()
        
        # Perform TWR calculation
        returns, start_value, end_value = calculate_daily_returns(allocations, price_history, start_date, end_date)
        twr = calculate_twr(returns)
        
        return ReturnCalculation(
            start_date=start_date,
            end_date=end_date,
            start_value=start_value,
            end_value=end_value,
            cash_flows=[], # Not implemented in this example
            time_weighted_return=Decimal(twr),
            money_weighted_return=Decimal('0'), # IRR calculation not implemented for simplicity
            simple_return=(end_value - start_value) / start_value if start_value > 0 else Decimal('0')
        )
        
    except Exception as e:
        logger.error(f"Error calculating client performance: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client performance")

@router.get("/net-new-money/history", response_model=NetNewMoneyHistory)
async def get_net_new_money(
    client_id: Optional[int] = Query(None),
    advisor_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the net new money history (inflows - outflows) for a client or advisor.
    This is an expanded version of the dashboard endpoint.
    """
    try:
        # Implementation is in dashboard.py, but this is a separate endpoint for detail
        # For simplicity, we can reuse the logic from dashboard.py
        # You would query allocations to find inflows (new allocations) and outflows (closed ones)
        
        # This is a simplified placeholder
        return NetNewMoneyHistory(
            client_id=client_id,
            advisor_id=advisor_id,
            start_date=start_date or date.today(),
            end_date=end_date or date.today(),
            data_points=[],
            total_net_flow=Decimal('0'),
            avg_monthly_flow=Decimal('0')
        )
    
    except Exception as e:
        logger.error(f"Error fetching net new money history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching net new money history")