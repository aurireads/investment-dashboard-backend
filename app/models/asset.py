from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Asset(Base):
    """
    Asset model - ativos financeiros disponíveis
    Os dados vêm da Yahoo Finance API
    """
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)  # Ex: PETR4.SA, AAPL
    name = Column(String(255), nullable=False)  # Nome da empresa
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market = Column(String(50), nullable=False)  # BOVESPA, NYSE, NASDAQ
    currency = Column(String(10), default="BRL", nullable=False)
    asset_type = Column(String(50), nullable=False)  # stock, bond, fund, crypto
    
    # Financial Info
    market_cap = Column(Numeric(20, 2), nullable=True)
    shares_outstanding = Column(Numeric(15, 0), nullable=True)
    
    # Current Price Info (cached from Yahoo Finance)
    current_price = Column(Numeric(12, 4), nullable=True)
    previous_close = Column(Numeric(12, 4), nullable=True)
    daily_change = Column(Numeric(12, 4), nullable=True)
    daily_change_percent = Column(Numeric(8, 4), nullable=True)
    volume = Column(Numeric(15, 0), nullable=True)
    
    # Trading Info
    is_tradeable = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    delisted_date = Column(DateTime(timezone=True), nullable=True)
    
    # Price Update Info
    last_price_update = Column(DateTime(timezone=True), nullable=True)
    price_update_source = Column(String(50), default="yahoo_finance", nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    allocations = relationship("Allocation", back_populates="asset")
    daily_returns = relationship("DailyReturn", back_populates="asset", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_asset_ticker_active', 'ticker', 'is_active'),
        Index('idx_asset_market_type', 'market', 'asset_type'),
        Index('idx_asset_last_update', 'last_price_update'),
    )
    
    def __repr__(self):
        return f"<Asset(id={self.id}, ticker='{self.ticker}', name='{self.name}')>"
    
    @property
    def is_brazilian_asset(self) -> bool:
        """Check if asset is from Brazilian market"""
        return self.market == "BOVESPA" or self.ticker.endswith(".SA")
    
    @property
    def formatted_ticker(self) -> str:
        """Return ticker formatted for Yahoo Finance API"""
        if self.is_brazilian_asset and not self.ticker.endswith(".SA"):
            return f"{self.ticker}.SA"
        return self.ticker
    
    def is_price_stale(self, max_age_hours: int = 24) -> bool:
        """Check if price data is stale"""
        if not self.last_price_update:
            return True
        
        age = func.now() - self.last_price_update
        return age.total_seconds() > (max_age_hours * 3600)
    
    def update_price_info(
        self, 
        price: float, 
        previous_close: float, 
        volume: int = None
    ) -> None:
        """Update current price information"""
        self.current_price = price
        self.previous_close = previous_close
        
        if previous_close and previous_close > 0:
            self.daily_change = price - previous_close
            self.daily_change_percent = ((price - previous_close) / previous_close) * 100
        
        if volume:
            self.volume = volume
            
        self.last_price_update = func.now()