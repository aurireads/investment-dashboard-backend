# Endpoints de ativos
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, asc, desc, func
from typing import Optional, List
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from app.api.deps import (
    get_db, get_current_active_user, get_user_with_write_access,
    get_pagination_params, PaginationParams, PaginatedResponse
)
from app.models.user import User
from app.models.asset import Asset
from app.models.daily_return import DailyReturn
from app.schemas.asset import (
    Asset as AssetSchema, AssetCreate, AssetUpdate, AssetWithPerformance,
    AssetList, AssetStats, MarketSummary
)
from app.services.yahoo_finance import get_asset_info_and_price_sync, get_price_history_sync
from app.utils.calculations import calculate_returns_from_history

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=AssetList)
async def get_assets(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = Query(None, min_length=1, description="Search by ticker or name"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    sort_by: str = Query("ticker", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List assets with pagination, search, and filters.
    """
    try:
        query = select(Asset).where(Asset.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Asset.ticker.ilike(search_term),
                    Asset.name.ilike(search_term)
                )
            )
        
        # Apply sorting
        if hasattr(Asset, sort_by):
            order_column = getattr(Asset, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        result = await db.execute(query)
        assets = result.scalars().all()
        
        return AssetList(
            items=[AssetSchema.from_orm(asset) for asset in assets],
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=(total + pagination.size - 1) // pagination.size
        )
        
    except Exception as e:
        logger.error(f"Error getting assets: {e}")
        raise HTTPException(status_code=500, detail="Error fetching assets")


@router.post("/", response_model=AssetSchema)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Create a new asset. Fetches and populates price data from Yahoo Finance.
    """
    try:
        # Check for existing ticker
        existing_asset = await db.execute(
            select(Asset).where(Asset.ticker == asset_data.ticker)
        )
        if existing_asset.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Asset with this ticker already exists"
            )
        
        # Fetch initial data from Yahoo Finance
        yf_data = get_asset_info_and_price_sync(asset_data.ticker)
        if not yf_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find data for ticker {asset_data.ticker}"
            )
        
        # Create asset instance
        asset_dict = asset_data.dict()
        asset_dict.update(yf_data)
        asset = Asset(**asset_dict)
        db.add(asset)
        
        # Fetch and store initial price history
        history_data = get_price_history_sync(asset_data.ticker, period="1y", interval="1d")
        if history_data:
            daily_returns = [
                DailyReturn(
                    asset_id=asset.id,
                    date=row['date'].date(),
                    close_price=Decimal(row['close']),
                    open_price=Decimal(row['open']),
                    high_price=Decimal(row['high']),
                    low_price=Decimal(row['low']),
                    volume=row['volume']
                ) for row in history_data
            ]
            db.add_all(daily_returns)
        
        await db.commit()
        await db.refresh(asset)
        
        logger.info(f"Asset created: {asset.ticker} by user {current_user.id}")
        
        return AssetSchema.from_orm(asset)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        raise HTTPException(status_code=500, detail="Error creating asset")

@router.get("/{asset_id}", response_model=AssetWithPerformance)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get asset details with performance metrics.
    """
    try:
        asset = await db.get(Asset, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        
        # Calculate performance metrics (e.g., weekly, monthly change)
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        one_week_ago = now - timedelta(weeks=1)
        one_month_ago = now - timedelta(days=30)
        one_year_ago = now - timedelta(days=365)
        
        # This is a simplified approach. A real system would use a pre-calculated table or more complex logic.
        daily_returns_query = select(DailyReturn).where(
            and_(
                DailyReturn.asset_id == asset_id,
                DailyReturn.date >= one_year_ago.date()
            )
        ).order_by(asc(DailyReturn.date))
        
        daily_returns_result = await db.execute(daily_returns_query)
        history = daily_returns_result.scalars().all()
        
        returns_dict = calculate_returns_from_history(history, asset.current_price)
        
        asset_with_performance = AssetWithPerformance.from_orm(asset)
        asset_with_performance.weekly_change = returns_dict.get("weekly_change_percent")
        asset_with_performance.monthly_change = returns_dict.get("monthly_change_percent")
        asset_with_performance.yearly_change = returns_dict.get("yearly_change_percent")
        # Add other metrics like volatility here
        
        return asset_with_performance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching asset")