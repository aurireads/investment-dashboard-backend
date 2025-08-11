from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class AssetType(str, Enum):
    STOCK = "stock"
    BOND = "bond"
    FUND = "fund"
    ETF = "etf"
    REIT = "reit"
    CRYPTO = "crypto"
    OPTION = "option"
    FUTURE = "future"

class Market(str, Enum):
    BOVESPA = "BOVESPA"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    CRYPTO = "CRYPTO"
    COMMODITIES = "COMMODITIES"

class Currency(str, Enum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"
    BTC = "BTC"

class DataQuality(str, Enum):
    GOOD = "good"
    ESTIMATED = "estimated"
    POOR = "poor"
    STALE = "stale"

# Asset Schemas
class AssetBase(BaseModel):
    """Base asset schema"""
    ticker: str = Field(..., min_length=1, max_length=20, description="Asset ticker symbol")
    name: str = Field(..., min_length=1, max_length=255, description="Asset name")
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market: Market
    currency: Currency = Currency.BRL
    asset_type: AssetType
    
    # Optional metadata
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    
    # Trading info
    is_tradeable: bool = True
    is_active: bool = True
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format"""
        return v.upper().strip()

class AssetCreate(AssetBase):
    """Schema for asset creation"""
    pass

class AssetUpdate(BaseModel):
    """Schema for asset updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    is_tradeable: Optional[bool] = None
    is_active: Optional[bool] = None

class AssetPriceUpdate(BaseModel):
    """Schema for updating asset prices"""
    current_price: Decimal = Field(..., gt=0, description="Current asset price")
    previous_close: Optional[Decimal] = Field(None, gt=0, description="Previous close price")
    volume: Optional[int] = Field(None, ge=0, description="Trading volume")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Market capitalization")

class Asset(AssetBase):
    """Full asset schema"""
    id: int
    
    # Financial data
    market_cap: Optional[Decimal] = None
    shares_outstanding: Optional[Decimal] = None
    
    # Current price info
    current_price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    daily_change: Optional[Decimal] = None
    daily_change_percent: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    
    # Update info
    last_price_update: Optional[datetime] = None
    price_update_source: str = "yahoo_finance"
    delisted_date: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AssetWithPerformance(Asset):
    """Asset with performance metrics"""
    weekly_change: Optional[Decimal] = None
    monthly_change: Optional[Decimal] = None
    yearly_change: Optional[Decimal] = None
    volatility_30d: Optional[Decimal] = None
    avg_volume_30d: Optional[Decimal] = None
    market_status: str = "closed"  # open, closed, pre_market, after_hours

# Daily Return Schemas
class DailyReturnBase(BaseModel):
    """Base daily return schema"""
    date: datetime
    open_price: Optional[Decimal] = Field(None, gt=0)
    high_price: Optional[Decimal] = Field(None, gt=0)
    low_price: Optional[Decimal] = Field(None, gt=0)
    close_price: Decimal = Field(..., gt=0)
    adjusted_close: Optional[Decimal] = Field(None, gt=0)
    volume: Optional[int] = Field(None, ge=0)
    source: str = "yahoo_finance"
    data_quality: DataQuality = DataQuality.GOOD

class DailyReturnCreate(DailyReturnBase):
    """Schema for creating daily returns"""
    asset_id: int

class DailyReturn(DailyReturnBase):
    """Full daily return schema"""
    id: int
    asset_id: int
    daily_return: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Price History Schemas
class PriceHistoryRequest(BaseModel):
    """Request schema for price history"""
    ticker: str = Field(..., description="Asset ticker")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = Field("1y", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")
    interval: Optional[str] = Field("1d", regex="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$")

class PricePoint(BaseModel):
    """Single price point"""
    timestamp: datetime
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[int] = None
    returns: Optional[Decimal] = None

class PriceHistory(BaseModel):
    """Price history response"""
    ticker: str
    asset_name: str
    currency: str
    data_points: List[PricePoint]
    start_date: datetime
    end_date: datetime
    total_points: int

# Asset Lists and Search
class AssetList(BaseModel):
    """Paginated asset list"""
    items: List[Asset]
    total: int
    page: int
    size: int
    pages: int

class AssetFilter(BaseModel):
    """Asset filtering options"""
    asset_type: Optional[AssetType] = None
    market: Optional[Market] = None
    currency: Optional[Currency] = None
    sector: Optional[str] = None
    is_active: Optional[bool] = None
    is_tradeable: Optional[bool] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_market_cap: Optional[Decimal] = None
    max_market_cap: Optional[Decimal] = None

class AssetSearch(BaseModel):
    """Asset search parameters"""
    query: Optional[str] = Field(None, min_length=1, description="Search in ticker, name")
    filters: Optional[AssetFilter] = None
    sort_by: Optional[str] = Field("ticker", description="Sort field")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$")

# Market Data Schemas
class MarketSummary(BaseModel):
    """Market summary for dashboard"""
    total_assets: int
    active_assets: int
    last_update: Optional[datetime]
    top_gainers: List[Asset]
    top_losers: List[Asset]
    most_traded: List[Asset]

class SectorPerformance(BaseModel):
    """Sector performance summary"""
    sector: str
    total_assets: int
    avg_change_percent: Decimal
    total_market_cap: Optional[Decimal]
    top_performer: Optional[Asset]

class MarketStatus(BaseModel):
    """Current market status"""
    market: Market
    is_open: bool
    next_open: Optional[datetime]
    next_close: Optional[datetime]
    timezone: str
    trading_session: str  # pre_market, regular, after_hours, closed

# Yahoo Finance Integration Schemas
class YahooFinanceAsset(BaseModel):
    """Asset data from Yahoo Finance"""
    symbol: str
    shortName: Optional[str] = None
    longName: Optional[str] = None
    currency: Optional[str] = None
    market: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[int] = None
    regularMarketPrice: Optional[float] = None
    regularMarketPreviousClose: Optional[float] = None
    regularMarketVolume: Optional[int] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

class BulkPriceUpdate(BaseModel):
    """Bulk price update schema"""
    updates: List[dict] = Field(..., description="List of ticker:price mappings")
    source: str = Field("yahoo_finance", description="Data source")
    timestamp: datetime = Field(default_factory=datetime.now)

# Statistics
class AssetStats(BaseModel):
    """Asset statistics"""
    total_assets: int
    by_type: dict[str, int]
    by_market: dict[str, int]
    by_currency: dict[str, int]
    active_assets: int
    with_current_prices: int
    last_updated: Optional[datetime]
    avg_daily_volume: Optional[Decimal]
    total_market_cap: Optional[Decimal]