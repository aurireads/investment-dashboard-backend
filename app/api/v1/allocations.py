# Endpoints de alocações
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List
from decimal import Decimal
import logging
from datetime import datetime

from app.api.deps import (
    get_db, get_current_active_user, get_user_with_write_access,
    get_pagination_params, PaginationParams, PaginatedResponse
)
from app.models.user import User
from app.models.allocation import Allocation
from app.models.client import Client
from app.models.asset import Asset
from app.schemas.allocation import (
    Allocation as AllocationSchema, AllocationCreate, AllocationUpdate,
    AllocationClose, AllocationWithPerformance, AllocationList
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=AllocationList)
async def get_allocations(
    pagination: PaginationParams = Depends(get_pagination_params),
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: str = Query("purchase_date", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List allocations with pagination and filters.
    """
    try:
        query = select(Allocation).options(
            selectinload(Allocation.client),
            selectinload(Allocation.asset)
        )
        
        conditions = []
        if client_id is not None:
            conditions.append(Allocation.client_id == client_id)
        if is_active is not None:
            conditions.append(Allocation.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        if hasattr(Allocation, sort_by):
            order_column = getattr(Allocation, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        result = await db.execute(query)
        allocations = result.scalars().all()
        
        # Convert to schemas with performance data
        allocations_with_perf = []
        for alloc in allocations:
            alloc_perf = AllocationWithPerformance.from_orm(alloc)
            alloc_perf.current_value = alloc.current_value
            alloc_perf.total_cost = alloc.total_cost
            alloc_perf.gain_loss_amount = alloc.gain_loss_amount
            alloc_perf.gain_loss_percent = alloc.gain_loss_percent
            alloc_perf.days_held = alloc.days_held
            alloc_perf.asset_daily_change = alloc.asset.daily_change if alloc.asset else None
            alloc_perf.asset_daily_change_percent = alloc.asset.daily_change_percent if alloc.asset else None
            allocations_with_perf.append(alloc_perf)
        
        return AllocationList(
            items=allocations_with_perf,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=(total + pagination.size - 1) // pagination.size
        )
        
    except Exception as e:
        logger.error(f"Error getting allocations: {e}")
        raise HTTPException(status_code=500, detail="Error fetching allocations")

@router.post("/", response_model=AllocationSchema)
async def create_allocation(
    allocation_data: AllocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Create a new allocation for a client.
    """
    try:
        # Check if client and asset exist
        client = await db.get(Client, allocation_data.client_id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        
        asset = await db.get(Asset, allocation_data.asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
            
        total_invested = allocation_data.quantity * allocation_data.purchase_price
        
        new_allocation = Allocation(
            **allocation_data.dict(exclude_unset=True),
            total_invested=total_invested
        )
        
        db.add(new_allocation)
        await db.commit()
        await db.refresh(new_allocation)
        
        logger.info(f"Allocation created: {new_allocation.id} by user {current_user.id}")
        
        return AllocationSchema.from_orm(new_allocation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating allocation: {e}")
        raise HTTPException(status_code=500, detail="Error creating allocation")

@router.put("/{allocation_id}", response_model=AllocationSchema)
async def update_allocation(
    allocation_id: int,
    allocation_data: AllocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Update an existing allocation.
    """
    try:
        allocation = await db.get(Allocation, allocation_id)
        if not allocation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
        
        if not allocation.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a closed allocation")
        
        for field, value in allocation_data.dict(exclude_unset=True).items():
            setattr(allocation, field, value)
            
        if allocation_data.quantity or allocation.purchase_price:
            allocation.total_invested = allocation.quantity * allocation.purchase_price
        
        await db.commit()
        await db.refresh(allocation)
        
        logger.info(f"Allocation updated: {allocation_id} by user {current_user.id}")
        
        return AllocationSchema.from_orm(allocation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating allocation {allocation_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating allocation")

@router.post("/{allocation_id}/close", response_model=AllocationSchema)
async def close_allocation(
    allocation_id: int,
    close_data: AllocationClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Close an allocation and calculate realized gain/loss.
    """
    try:
        allocation = await db.get(Allocation, allocation_id)
        if not allocation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
            
        if not allocation.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation is already closed")
            
        allocation.close_position(
            exit_price=close_data.exit_price,
            exit_date=close_data.exit_date,
            exit_fees=close_data.exit_fees
        )
        
        await db.commit()
        await db.refresh(allocation)
        
        logger.info(f"Allocation closed: {allocation_id} by user {current_user.id}")
        
        return AllocationSchema.from_orm(allocation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing allocation {allocation_id}: {e}")
        raise HTTPException(status_code=500, detail="Error closing allocation")