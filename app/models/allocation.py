from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from app.core.database import Base

class Allocation(Base):
    """
    Allocation model - alocações dos clientes em ativos
    Representa a posição de um cliente em um ativo específico
    """
    __tablename__ = "allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    
    # Position Info
    quantity = Column(Numeric(15, 4), nullable=False)  # Quantidade de ações/cotas
    purchase_price = Column(Numeric(12, 4), nullable=False)  # Preço de compra
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    
    # Optional fields for fractional purchases
    total_invested = Column(Numeric(15, 2), nullable=False)  # quantity * purchase_price
    fees = Column(Numeric(10, 2), default=0.00, nullable=False)  # Taxas de corretagem
    
    # Position Status
    is_active = Column(Boolean, default=True, nullable=False)
    position_type = Column(String(20), default="long", nullable=False)  # long, short
    
    # Exit Info (for closed positions)
    exit_price = Column(Numeric(12, 4), nullable=True)
    exit_date = Column(DateTime(timezone=True), nullable=True)
    exit_fees = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Performance Tracking
    last_price_check = Column(DateTime(timezone=True), nullable=True)
    unrealized_gain_loss = Column(Numeric(15, 2), nullable=True)
    unrealized_gain_loss_percent = Column(Numeric(8, 4), nullable=True)
    realized_gain_loss = Column(Numeric(15, 2), nullable=True)  # For closed positions
    
    # Metadata
    notes = Column(String(500), nullable=True)
    order_id = Column(String(100), nullable=True)  # External order reference
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="allocations")
    asset = relationship("Asset", back_populates="allocations")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_allocation_client_active', 'client_id', 'is_active'),
        Index('idx_allocation_asset_active', 'asset_id', 'is_active'),
        Index('idx_allocation_purchase_date', 'purchase_date'),
        Index('idx_allocation_client_asset', 'client_id', 'asset_id'),
    )
    
    def __repr__(self):
        return f"<Allocation(id={self.id}, client_id={self.client_id}, asset_id={self.asset_id}, quantity={self.quantity})>"
    
    @property
    def current_value(self) -> Decimal:
        """Calculate current market value of the position"""
        if self.asset and self.asset.current_price:
            return Decimal(str(self.quantity)) * Decimal(str(self.asset.current_price))
        return Decimal('0')
    
    @property
    def total_cost(self) -> Decimal:
        """Total cost including fees"""
        return Decimal(str(self.total_invested)) + Decimal(str(self.fees))
    
    @property
    def gain_loss_amount(self) -> Decimal:
        """Current gain/loss in absolute value"""
        return self.current_value - self.total_cost
    
    @property
    def gain_loss_percent(self) -> Decimal:
        """Current gain/loss in percentage"""
        if self.total_cost > 0:
            return (self.gain_loss_amount / self.total_cost) * 100
        return Decimal('0')
    
    @property
    def days_held(self) -> int:
        """Number of days position has been held"""
        from datetime import datetime
        if self.is_active:
            return (datetime.now(self.purchase_date.tzinfo) - self.purchase_date).days
        elif self.exit_date:
            return (self.exit_date - self.purchase_date).days
        return 0
    
    def update_performance(self, current_price: Decimal) -> None:
        """Update unrealized gain/loss based on current price"""
        current_value = Decimal(str(self.quantity)) * current_price
        self.unrealized_gain_loss = current_value - self.total_cost
        
        if self.total_cost > 0:
            self.unrealized_gain_loss_percent = (self.unrealized_gain_loss / self.total_cost) * 100
        
        self.last_price_check = func.now()
    
    def close_position(self, exit_price: Decimal, exit_date: DateTime = None, exit_fees: Decimal = None) -> None:
        """Close the position and calculate realized gains/losses"""
        self.is_active = False
        self.exit_price = exit_price
        self.exit_date = exit_date or func.now()
        self.exit_fees = exit_fees or Decimal('0')
        
        # Calculate realized gain/loss
        exit_value = Decimal(str(self.quantity)) * exit_price
        total_costs = self.total_cost + self.exit_fees
        self.realized_gain_loss = exit_value - total_costs
        
        # Clear unrealized values
        self.unrealized_gain_loss = None
        self.unrealized_gain_loss_percent = None