from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.schemas.client import Client
from app.schemas.asset import Asset

class PositionType(str, Enum):
    LONG = "long"
    SHORT = "short"

class AllocationStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    PARTIAL = "partial"

# Base Allocation Schemas
class AllocationBase(BaseModel):
    """Base allocation schema"""
    client_id: int = Field(..., gt=0, description="Client ID")
    asset_id: int = Field(..., gt=0, description="Asset ID")
    quantity: Decimal = Field(..., gt=0, description="Quantity of shares/units")
    purchase_price: Decimal = Field(..., gt=0, description="Purchase price per unit")
    purchase_date: datetime = Field(..., description="Purchase date")
    fees: Decimal = Field(Decimal('0'), ge=0, description="Transaction fees")
    position_type: PositionType = PositionType.LONG
    notes: Optional[str] = Field(None, max_length=500)
    order_id: Optional[str] = Field(None, max_length=100)
    
    @validator('total_invested', always=True)
    def calculate_total_invested(cls, v, values):
        """Calculate total invested amount"""
        quantity = values.get('quantity', Decimal('0'))
        price = values.get('purchase_price', Decimal('0'))
        return quantity * price

class AllocationCreate(AllocationBase):
    """Schema for allocation creation"""
    pass

class AllocationUpdate(BaseModel):
    """Schema for allocation updates"""
    quantity: Optional[Decimal] = Field(None, gt=0)
    fees: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=500)
    order_id: Optional[str] = Field(None, max_length=100)

class AllocationClose(BaseModel):
    """Schema for closing allocation"""
    exit_price: Decimal = Field(..., gt=0, description="Exit price per unit")
    exit_date: Optional[datetime] = None
    exit_fees: Decimal = Field(Decimal('0'), ge=0, description="Exit transaction fees")
    notes: Optional[str] = Field(None, max_length=500)

# Full Allocation Schema
class Allocation(AllocationBase):
    """Full allocation schema"""
    id: int
    total_invested: Decimal
    is_active: bool
    
    # Exit information
    exit_price: Optional[Decimal] = None
    exit_date: Optional[datetime] = None
    exit_fees: Decimal = Decimal('0')
    
    # Performance tracking
    last_price_check: Optional[datetime] = None
    unrealized_gain_loss: Optional[Decimal] = None
    unrealized_gain_loss_percent: Optional[Decimal] = None
    realized_gain_loss: Optional[Decimal] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    client: Optional[Client] = None
    asset: Optional[Asset] = None
    
    class Config:
        from_attributes = True

class AllocationWithPerformance(Allocation):
    """Allocation with calculated performance metrics"""
    current_price: Optional[Decimal] = None
    current_value: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    gain_loss_amount: Decimal = Decimal('0')
    gain_loss_percent: Decimal = Decimal('0')
    days_held: int = 0
    annualized_return: Optional[Decimal] = None
    
    # Asset performance
    asset_daily_change: Optional[Decimal] = None
    asset_daily_change_percent: Optional[Decimal] = None

# Portfolio Schemas
class PortfolioSummary(BaseModel):
    """Portfolio summary for a client"""
    client_id: int
    total_invested: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    total_gain_loss: Decimal = Decimal('0')
    total_gain_loss_percent: Decimal = Decimal('0')
    active_positions: int = 0
    closed_positions: int = 0
    last_updated: Optional[datetime] = None

class PortfolioPosition(BaseModel):
    """Individual position in portfolio"""
    allocation: AllocationWithPerformance
    weight_percent: Decimal = Decimal('0')  # Position weight in portfolio
    sector_allocation: Optional[str] = None
    risk_contribution: Optional[Decimal] = None

class Portfolio(BaseModel):
    """Complete portfolio view"""
    client: Client
    summary: PortfolioSummary
    positions: List[PortfolioPosition]
    asset_allocation: dict[str, Decimal]  # By asset type
    sector_allocation: dict[str, Decimal]  # By sector
    currency_allocation: dict[str, Decimal]  # By currency
    
class AssetAllocationSummary(BaseModel):
    """Asset allocation breakdown"""
    asset_type: str
    total_value: Decimal
    percentage: Decimal
    positions_count: int
    avg_gain_loss_percent: Decimal

class SectorAllocationSummary(BaseModel):
    """Sector allocation breakdown"""
    sector: str
    total_value: Decimal
    percentage: Decimal
    positions_count: int
    avg_gain_loss_percent: Decimal

# Performance Schemas
class PerformanceMetricBase(BaseModel):
    """Base performance metric schema"""
    client_id: int
    period_type: str = Field(..., regex="^(daily|weekly|monthly|yearly)$")
    period_date: datetime
    
    total_invested: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    total_gain_loss: Decimal = Decimal('0')
    total_gain_loss_percent: Decimal = Decimal('0')
    
    # Risk metrics
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    
    # Allocation percentages
    equity_percentage: Optional[Decimal] = None
    fixed_income_percentage: Optional[Decimal] = None
    alternatives_percentage: Optional[Decimal] = None
    cash_percentage: Optional[Decimal] = None
    
    # Activity
    total_trades: int = 0
    active_positions: int = 0

class PerformanceMetric(PerformanceMetricBase):
    """Full performance metric schema"""
    id: int
    calculation_date: datetime
    is_estimated: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PerformanceHistory(BaseModel):
    """Performance history over time"""
    client_id: int
    client_name: str
    period_type: str
    data_points: List[PerformanceMetric]
    start_date: datetime
    end_date: datetime
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Decimal

# Lists and Pagination
class AllocationList(BaseModel):
    """Paginated allocation list"""
    items: List[AllocationWithPerformance]
    total: int
    page: int
    size: int
    pages: int

class AllocationFilter(BaseModel):
    """Allocation filtering options"""
    client_id: Optional[int] = None
    asset_id: Optional[int] = None
    is_active: Optional[bool] = None
    position_type: Optional[PositionType] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    min_gain_loss_percent: Optional[Decimal] = None
    max_gain_loss_percent: Optional[Decimal] = None
    purchase_date_from: Optional[datetime] = None
    purchase_date_to: Optional[datetime] = None

class AllocationSearch(BaseModel):
    """Allocation search parameters"""
    query: Optional[str] = Field(None, min_length=1, description="Search in client name, asset ticker")
    filters: Optional[AllocationFilter] = None
    sort_by: Optional[str] = Field("purchase_date", description="Sort field")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$")

# Bulk Operations
class BulkAllocationUpdate(BaseModel):
    """Bulk allocation update"""
    allocation_ids: List[int] = Field(..., min_items=1)
    updates: AllocationUpdate

class BulkAllocationClose(BaseModel):
    """Bulk allocation close"""
    allocation_ids: List[int] = Field(..., min_items=1)
    close_data: AllocationClose

# Statistics and Analytics
class AllocationStats(BaseModel):
    """Allocation statistics"""
    total_allocations: int
    active_allocations: int
    closed_allocations: int
    total_invested: Decimal
    current_value: Decimal
    total_gain_loss: Decimal
    avg_gain_loss_percent: Decimal
    best_performer: Optional[AllocationWithPerformance]
    worst_performer: Optional[AllocationWithPerformance]
    by_asset_type: dict[str, dict]
    by_sector: dict[str, dict]

class TopPerformers(BaseModel):
    """Top performing allocations"""
    best_performers: List[AllocationWithPerformance]
    worst_performers: List[AllocationWithPerformance]
    most_traded: List[dict]  # Asset with allocation count
    largest_positions: List[AllocationWithPerformance]