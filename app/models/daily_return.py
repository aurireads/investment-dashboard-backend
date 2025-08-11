from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Numeric, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class DailyReturn(Base):
    """
    Daily Return model - armazena preços históricos diários dos ativos
    Alimentado pela tarefa Celery que consulta Yahoo Finance
    """
    __tablename__ = "daily_returns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    
    # Price Data
    date = Column(Date, nullable=False, index=True)  # Data do pregão
    open_price = Column(Numeric(12, 4), nullable=True)
    high_price = Column(Numeric(12, 4), nullable=True)
    low_price = Column(Numeric(12, 4), nullable=True)
    close_price = Column(Numeric(12, 4), nullable=False)  # Preço de fechamento
    adjusted_close = Column(Numeric(12, 4), nullable=True)  # Preço ajustado para splits/dividendos
    volume = Column(Numeric(15, 0), nullable=True)
    
    # Calculated Fields
    daily_return = Column(Numeric(10, 6), nullable=True)  # Retorno percentual diário
    price_change = Column(Numeric(12, 4), nullable=True)  # Variação absoluta
    
    # Data Source
    source = Column(String(50), default="yahoo_finance", nullable=False)
    data_quality = Column(String(20), default="good", nullable=False)  # good, estimated, poor
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    asset = relationship("Asset", back_populates="daily_returns")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('asset_id', 'date', name='uq_daily_return_asset_date'),
        Index('idx_daily_return_date_desc', 'date', 'asset_id'),
        Index('idx_daily_return_asset_date', 'asset_id', 'date'),
    )
    
    def __repr__(self):
        return f"<DailyReturn(asset_id={self.asset_id}, date={self.date}, close={self.close_price})>"
    
    @property
    def is_recent(self) -> bool:
        """Check if this is recent data (within last 7 days)"""
        from datetime import datetime, timedelta
        return self.date >= (datetime.now().date() - timedelta(days=7))
    
    def calculate_return(self, previous_close: Decimal) -> None:
        """Calculate daily return percentage"""
        if previous_close and previous_close > 0:
            self.daily_return = ((self.close_price - previous_close) / previous_close) * 100
            self.price_change = self.close_price - previous_close

class PerformanceMetric(Base):
    """
    Performance Metrics model - métricas calculadas para clients
    Usado para otimizar consultas do dashboard
    """
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Time Period
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    period_date = Column(Date, nullable=False, index=True)
    
    # Portfolio Metrics
    total_invested = Column(Numeric(15, 2), nullable=False)
    current_value = Column(Numeric(15, 2), nullable=False)
    total_gain_loss = Column(Numeric(15, 2), nullable=False)
    total_gain_loss_percent = Column(Numeric(8, 4), nullable=False)
    
    # Risk Metrics
    volatility = Column(Numeric(8, 4), nullable=True)  # Volatilidade anualizada
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    max_drawdown = Column(Numeric(8, 4), nullable=True)
    
    # Asset Allocation
    equity_percentage = Column(Numeric(5, 2), nullable=True)
    fixed_income_percentage = Column(Numeric(5, 2), nullable=True)
    alternatives_percentage = Column(Numeric(5, 2), nullable=True)
    cash_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Activity Metrics
    total_trades = Column(Integer, default=0, nullable=False)
    active_positions = Column(Integer, default=0, nullable=False)
    
    # Data Quality
    calculation_date = Column(DateTime(timezone=True), nullable=False)
    is_estimated = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    client = relationship("Client")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('client_id', 'period_type', 'period_date', name='uq_performance_client_period'),
        Index('idx_performance_period', 'period_type', 'period_date'),
        Index('idx_performance_client_period', 'client_id', 'period_type', 'period_date'),
    )
    
    def __repr__(self):
        return f"<PerformanceMetric(client_id={self.client_id}, period={self.period_type}, date={self.period_date})>"

class Commission(Base):
    """
    Commission model - comissões dos assessores
    Baseado na tela de comissões do dashboard
    """
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    allocation_id = Column(Integer, ForeignKey("allocations.id"), nullable=True)  # Opcional
    
    # Commission Details
    commission_type = Column(String(50), nullable=False)  # management, performance, transaction
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Amounts
    gross_revenue = Column(Numeric(15, 2), nullable=False)  # Receita bruta
    commission_rate = Column(Numeric(5, 4), nullable=False)  # Taxa de comissão
    commission_amount = Column(Numeric(15, 2), nullable=False)  # Valor da comissão
    net_commission = Column(Numeric(15, 2), nullable=False)  # Comissão líquida (após impostos)
    
    # Tax Info
    tax_rate = Column(Numeric(5, 4), default=0.0, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Status
    status = Column(String(20), default="calculated", nullable=False)  # calculated, paid, cancelled
    payment_date = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    advisor = relationship("Advisor")
    client = relationship("Client")
    allocation = relationship("Allocation")
    
    # Indexes
    __table_args__ = (
        Index('idx_commission_advisor_period', 'advisor_id', 'period_start', 'period_end'),
        Index('idx_commission_client_period', 'client_id', 'period_start', 'period_end'),
        Index('idx_commission_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Commission(id={self.id}, advisor_id={self.advisor_id}, amount={self.commission_amount})>"