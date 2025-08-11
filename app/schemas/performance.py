from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class PeriodType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class MetricType(str, Enum):
    RETURN = "return"
    VOLATILITY = "volatility"
    SHARPE = "sharpe_ratio"
    DRAWDOWN = "max_drawdown"
    ALPHA = "alpha"
    BETA = "beta"

# Commission Schemas (baseado na tela de comissões do dashboard)
class CommissionType(str, Enum):
    MANAGEMENT = "management"
    PERFORMANCE = "performance"
    TRANSACTION = "transaction"
    ADVISORY = "advisory"

class CommissionStatus(str, Enum):
    CALCULATED = "calculated"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"

class CommissionBase(BaseModel):
    """Base commission schema"""
    advisor_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    allocation_id: Optional[int] = None
    commission_type: CommissionType
    period_start: date
    period_end: date
    gross_revenue: Decimal = Field(..., ge=0, description="Receita bruta")
    commission_rate: Decimal = Field(..., ge=0, le=1, description="Taxa de comissão")
    tax_rate: Decimal = Field(Decimal('0'), ge=0, le=1, description="Taxa de imposto")

class CommissionCreate(CommissionBase):
    """Schema for commission creation"""
    pass

class CommissionUpdate(BaseModel):
    """Schema for commission updates"""
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    status: Optional[CommissionStatus] = None
    payment_date: Optional[date] = None

class Commission(CommissionBase):
    """Full commission schema"""
    id: int
    commission_amount: Decimal
    net_commission: Decimal
    tax_amount: Decimal
    status: CommissionStatus
    payment_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    advisor_name: Optional[str] = None
    client_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# Performance Calculation Schemas
class ReturnCalculation(BaseModel):
    """Return calculation for a specific period"""
    start_date: date
    end_date: date
    start_value: Decimal
    end_value: Decimal
    cash_flows: List[Decimal] = []  # Aportes/resgates
    time_weighted_return: Decimal
    money_weighted_return: Decimal
    simple_return: Decimal

class RiskMetrics(BaseModel):
    """Risk metrics calculation"""
    period_start: date
    period_end: date
    volatility: Decimal  # Volatilidade anualizada
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Decimal
    var_95: Optional[Decimal] = None  # Value at Risk 95%
    cvar_95: Optional[Decimal] = None  # Conditional VaR 95%
    beta: Optional[Decimal] = None  # Beta vs benchmark
    alpha: Optional[Decimal] = None  # Alpha vs benchmark

class PerformanceSnapshot(BaseModel):
    """Performance snapshot for dashboard"""
    client_id: int
    client_name: str
    snapshot_date: datetime
    
    # Portfolio values
    total_invested: Decimal
    current_value: Decimal
    available_cash: Decimal = Decimal('0')
    
    # Returns
    total_return: Decimal
    total_return_percent: Decimal
    ytd_return: Decimal
    ytd_return_percent: Decimal
    mtd_return: Decimal
    mtd_return_percent: Decimal
    
    # Risk metrics
    risk_metrics: Optional[RiskMetrics] = None
    
    # Asset allocation
    equity_allocation: Decimal = Decimal('0')
    fixed_income_allocation: Decimal = Decimal('0')
    alternative_allocation: Decimal = Decimal('0')
    cash_allocation: Decimal = Decimal('0')

# Dashboard Schemas (baseado nas imagens)
class DashboardMetrics(BaseModel):
    """Métricas principais do dashboard"""
    # Net New Money metrics
    nnm_current_week: Decimal  # R$ 157M essa semana
    nnm_current_week_change: Decimal  # 17.5%
    nnm_semester: Decimal  # R$ 78M semestral
    nnm_semester_change: Decimal  # 17.5%
    nnm_monthly: Decimal  # R$ 12.7M mensal
    nnm_monthly_change: Decimal  # 9.3%
    
    # AuC (Assets under Custody)
    auc_total: Decimal  # R$ 1.4B
    auc_start_period: Decimal  # R$ 1.155B início período
    auc_end_period: Decimal  # R$ 1.400B fim período
    auc_variation: Decimal  # 36.8%
    
    # Receitas
    total_revenue_january: Decimal  # R$ 7.160.000
    total_revenue_change: Decimal  # 37.8%
    total_advisors: int  # 30 assessores
    
    # Comissões
    gross_commission_week: Decimal  # R$ 1.8M essa semana
    gross_commission_change: Decimal  # 17.5%
    net_commission_month: Decimal  # R$ 1.7M mês passado
    net_commission_change: Decimal  # 17.5%
    total_commission: Decimal  # R$ 980K total
    total_commission_change: Decimal  # 9.3%

class TopAdvisorMetric(BaseModel):
    """Métrica de top assessor"""
    advisor_id: int
    advisor_name: str
    revenue: Decimal  # Receita gerada
    revenue_percentage: Decimal  # Percentual do total
    net_new_money: Decimal  # Captação líquida
    clients_count: int
    change_percent: Decimal  # Variação percentual

class MonthlyPerformance(BaseModel):
    """Performance mensal para gráficos"""
    month: str  # Jan, Fev, Mar...
    nnm_value: Decimal  # Net New Money
    revenue_value: Decimal
    commission_value: Decimal
    auc_value: Decimal

class AdvisorCommissionDetail(BaseModel):
    """Detalhe de comissão por assessor"""
    advisor_id: int
    advisor_name: str
    net_commission: Decimal
    gross_commission: Decimal
    commission_percentage: Decimal
    month_over_month_change: Decimal
    status: str  # "Cumprida" ou "Não atingiu"

# Net New Money Schemas
class NetNewMoneyData(BaseModel):
    """Dados de captação líquida"""
    period: date
    inflows: Decimal  # Aportes
    outflows: Decimal  # Resgates
    net_flow: Decimal  # Líquido
    cumulative_net: Decimal  # Acumulado
    period_type: PeriodType

class NetNewMoneyHistory(BaseModel):
    """Histórico de captação líquida"""
    client_id: Optional[int] = None
    advisor_id: Optional[int] = None
    start_date: date
    end_date: date
    data_points: List[NetNewMoneyData]
    total_net_flow: Decimal
    avg_monthly_flow: Decimal

# Export Schemas
class PerformanceExportRequest(BaseModel):
    """Request para exportação de performance"""
    client_ids: Optional[List[int]] = None
    advisor_ids: Optional[List[int]] = None
    start_date: date
    end_date: date
    include_detailed_positions: bool = True
    include_risk_metrics: bool = True
    include_commissions: bool = False
    format: str = Field("excel", regex="^(excel|csv)$")

class ExportStatus(BaseModel):
    """Status da exportação"""
    export_id: str
    status: str  # pending, processing, completed, failed
    file_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None

# Real-time Performance Updates
class RealTimePrice(BaseModel):
    """Preço em tempo real para WebSocket"""
    ticker: str
    current_price: Decimal
    daily_change: Decimal
    daily_change_percent: Decimal
    volume: int
    timestamp: datetime
    market_status: str

class PortfolioUpdate(BaseModel):
    """Atualização de portfolio em tempo real"""
    client_id: int
    total_value: Decimal
    total_gain_loss: Decimal
    total_gain_loss_percent: Decimal
    positions_updated: List[dict]  # {allocation_id, new_value, gain_loss}
    timestamp: datetime

# Analytics Schemas
class PerformanceComparison(BaseModel):
    """Comparação de performance entre clientes/períodos"""
    baseline: PerformanceSnapshot
    comparison: PerformanceSnapshot
    relative_performance: Decimal
    outperformance_days: int
    correlation: Optional[Decimal] = None

class BenchmarkComparison(BaseModel):
    """Comparação com benchmark"""
    portfolio_return: Decimal
    benchmark_return: Decimal
    benchmark_name: str  # "IBOVESPA", "CDI", etc.
    outperformance: Decimal
    tracking_error: Decimal
    information_ratio: Optional[Decimal] = None

class PerformanceAttribution(BaseModel):
    """Atribuição de performance"""
    asset_selection: Decimal
    sector_allocation: Decimal
    timing_effect: Decimal
    interaction_effect: Decimal
    total_active_return: Decimal