# Endpoints do dashboard
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, extract
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging

from app.api.deps import get_db, get_current_active_user, PaginatedResponse
from app.models.user import User
from app.models.client import Client, Advisor
from app.models.asset import Asset
from app.models.allocation import Allocation
from app.models.daily_return import PerformanceMetric, Commission
from app.schemas.performance import (
    DashboardMetrics, TopAdvisorMetric, MonthlyPerformance,
    AdvisorCommissionDetail, NetNewMoneyData
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    period: Optional[str] = Query("current_month", description="Período: current_month, last_month, ytd"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Métricas principais do dashboard baseadas nas imagens
    """
    try:
        now = datetime.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Net New Money - Captação semanal atual
        week_start = now - timedelta(days=7)
        nnm_week_query = select(
            func.coalesce(func.sum(Allocation.total_invested), 0)
        ).where(
            Allocation.purchase_date >= week_start,
            Allocation.is_active == True
        )
        nnm_week_result = await db.execute(nnm_week_query)
        nnm_current_week = nnm_week_result.scalar() or Decimal('0')
        
        # NNM semestre 
        semester_start = now.replace(month=7 if now.month >= 7 else 1, day=1)
        nnm_semester_query = select(
            func.coalesce(func.sum(Allocation.total_invested), 0)
        ).where(
            Allocation.purchase_date >= semester_start,
            Allocation.is_active == True
        )
        nnm_semester_result = await db.execute(nnm_semester_query)
        nnm_semester = nnm_semester_result.scalar() or Decimal('0')
        
        # NNM mensal
        nnm_monthly_query = select(
            func.coalesce(func.sum(Allocation.total_invested), 0)
        ).where(
            Allocation.purchase_date >= current_month_start,
            Allocation.is_active == True
        )
        nnm_monthly_result = await db.execute(nnm_monthly_query)
        nnm_monthly = nnm_monthly_result.scalar() or Decimal('0')
        
        # AuC (Assets under Custody) - Total atual
        auc_query = select(
            func.coalesce(func.sum(
                Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
            ), 0)
        ).select_from(
            Allocation.join(Asset)
        ).where(
            Allocation.is_active == True
        )
        auc_result = await db.execute(auc_query)
        auc_total = auc_result.scalar() or Decimal('0')
        
        # AuC início do período
        auc_start_query = select(
            func.coalesce(func.sum(Allocation.total_invested), 0)
        ).where(
            Allocation.purchase_date < current_month_start,
            Allocation.is_active == True
        )
        auc_start_result = await db.execute(auc_start_query)
        auc_start_period = auc_start_result.scalar() or Decimal('0')
        
        # Receita total do mês atual (baseado em janeiro no dashboard)
        revenue_query = select(
            func.coalesce(func.sum(Commission.gross_revenue), 0)
        ).where(
            Commission.period_start >= current_month_start
        )
        revenue_result = await db.execute(revenue_query)
        total_revenue_january = revenue_result.scalar() or Decimal('0')
        
        # Total de assessores
        advisors_query = select(func.count(Advisor.id)).where(Advisor.is_active == True)
        advisors_result = await db.execute(advisors_query)
        total_advisors = advisors_result.scalar() or 0
        
        # Comissões da semana
        commission_week_query = select(
            func.coalesce(func.sum(Commission.commission_amount), 0)
        ).where(
            Commission.period_start >= week_start
        )
        commission_week_result = await db.execute(commission_week_query)
        gross_commission_week = commission_week_result.scalar() or Decimal('0')
        
        # Comissão líquida do mês passado
        commission_month_query = select(
            func.coalesce(func.sum(Commission.net_commission), 0)
        ).where(
            and_(
                Commission.period_start >= last_month_start,
                Commission.period_start < current_month_start
            )
        )
        commission_month_result = await db.execute(commission_month_query)
        net_commission_month = commission_month_result.scalar() or Decimal('0')
        
        # Comissão total atual
        commission_total_query = select(
            func.coalesce(func.sum(Commission.commission_amount), 0)
        ).where(
            Commission.period_start >= current_month_start
        )
        commission_total_result = await db.execute(commission_total_query)
        total_commission = commission_total_result.scalar() or Decimal('0')
        
        # Calcular variações percentuais (simuladas para demonstração)
        # Em um sistema real, essas seriam calculadas comparando com períodos anteriores
        
        return DashboardMetrics(
            nnm_current_week=nnm_current_week,
            nnm_current_week_change=Decimal('17.5'),  # Mock - seria calculado
            nnm_semester=nnm_semester,
            nnm_semester_change=Decimal('17.5'),
            nnm_monthly=nnm_monthly,
            nnm_monthly_change=Decimal('9.3'),
            
            auc_total=auc_total,
            auc_start_period=auc_start_period,
            auc_end_period=auc_total,
            auc_variation=Decimal('36.8') if auc_start_period > 0 else Decimal('0'),
            
            total_revenue_january=total_revenue_january,
            total_revenue_change=Decimal('37.8'),
            total_advisors=total_advisors,
            
            gross_commission_week=gross_commission_week,
            gross_commission_change=Decimal('17.5'),
            net_commission_month=net_commission_month,
            net_commission_change=Decimal('17.5'),
            total_commission=total_commission,
            total_commission_change=Decimal('9.3')
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching dashboard metrics")

@router.get("/top-advisors", response_model=List[TopAdvisorMetric])
async def get_top_advisors(
    limit: int = Query(5, ge=1, le=20, description="Número de top assessores"),
    period: str = Query("current_month", description="Período de análise"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Top assessores por receita/captação (baseado na imagem do dashboard)
    """
    try:
        now = datetime.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Query para top assessores por receita
        query = select(
            Advisor.id,
            Advisor.name,
            func.coalesce(func.sum(Commission.gross_revenue), 0).label('revenue'),
            func.count(Client.id).label('clients_count'),
            func.coalesce(func.sum(Allocation.total_invested), 0).label('net_new_money')
        ).select_from(
            Advisor
            .outerjoin(Commission, Commission.advisor_id == Advisor.id)
            .outerjoin(Client, Client.advisor_id == Advisor.id)
            .outerjoin(Allocation, Allocation.client_id == Client.id)
        ).where(
            Advisor.is_active == True
        ).group_by(
            Advisor.id, Advisor.name
        ).order_by(
            desc('revenue')
        ).limit(limit)
        
        result = await db.execute(query)
        top_advisors = result.fetchall()
        
        # Calcular total de receita para percentuais
        total_revenue_query = select(func.coalesce(func.sum(Commission.gross_revenue), 0))
        total_revenue_result = await db.execute(total_revenue_query)
        total_revenue = total_revenue_result.scalar() or Decimal('1')  # Evitar divisão por zero
        
        response = []
        for advisor in top_advisors:
            revenue_percentage = (advisor.revenue / total_revenue * 100) if total_revenue > 0 else Decimal('0')
            
            response.append(TopAdvisorMetric(
                advisor_id=advisor.id,
                advisor_name=advisor.name,
                revenue=advisor.revenue,
                revenue_percentage=revenue_percentage,
                net_new_money=advisor.net_new_money,
                clients_count=advisor.clients_count,
                change_percent=Decimal('15.5')  # Mock - seria calculado comparando períodos
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting top advisors: {e}")
        raise HTTPException(status_code=500, detail="Error fetching top advisors")

@router.get("/monthly-performance", response_model=List[MonthlyPerformance])
async def get_monthly_performance(
    year: int = Query(2024, description="Ano para análise"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Performance mensal para gráficos (baseado nos gráficos do dashboard)
    """
    try:
        months = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ]
        
        response = []
        
        for month_num in range(1, 13):
            month_start = datetime(year, month_num, 1)
            if month_num == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month_num + 1, 1)
            
            # NNM do mês
            nnm_query = select(
                func.coalesce(func.sum(Allocation.total_invested), 0)
            ).where(
                and_(
                    Allocation.purchase_date >= month_start,
                    Allocation.purchase_date < month_end,
                    Allocation.is_active == True
                )
            )
            nnm_result = await db.execute(nnm_query)
            nnm_value = nnm_result.scalar() or Decimal('0')
            
            # Receita do mês
            revenue_query = select(
                func.coalesce(func.sum(Commission.gross_revenue), 0)
            ).where(
                and_(
                    Commission.period_start >= month_start,
                    Commission.period_start < month_end
                )
            )
            revenue_result = await db.execute(revenue_query)
            revenue_value = revenue_result.scalar() or Decimal('0')
            
            # Comissão do mês
            commission_query = select(
                func.coalesce(func.sum(Commission.commission_amount), 0)
            ).where(
                and_(
                    Commission.period_start >= month_start,
                    Commission.period_start < month_end
                )
            )
            commission_result = await db.execute(commission_query)
            commission_value = commission_result.scalar() or Decimal('0')
            
            # AuC do final do mês
            auc_query = select(
                func.coalesce(func.sum(
                    Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
                ), 0)
            ).select_from(
                Allocation.join(Asset)
            ).where(
                and_(
                    Allocation.purchase_date <= month_end,
                    Allocation.is_active == True
                )
            )
            auc_result = await db.execute(auc_query)
            auc_value = auc_result.scalar() or Decimal('0')
            
            response.append(MonthlyPerformance(
                month=months[month_num - 1],
                nnm_value=nnm_value,
                revenue_value=revenue_value,
                commission_value=commission_value,
                auc_value=auc_value
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting monthly performance: {e}")
        raise HTTPException(status_code=500, detail="Error fetching monthly performance")

@router.get("/advisor-commissions", response_model=List[AdvisorCommissionDetail])
async def get_advisor_commissions(
    period: str = Query("current_month", description="Período de análise"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Detalhes de comissão por assessor (baseado na tela de comissões)
    """
    try:
        now = datetime.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Query principal
        query = select(
            Advisor.id,
            Advisor.name,
            func.coalesce(func.sum(Commission.commission_amount), 0).label('gross_commission'),
            func.coalesce(func.sum(Commission.net_commission), 0).label('net_commission'),
            func.avg(Commission.commission_rate * 100).label('avg_commission_rate')
        ).select_from(
            Advisor.join(Commission, Commission.advisor_id == Advisor.id)
        ).where(
            and_(
                Advisor.is_active == True,
                Commission.period_start >= current_month_start
            )
        ).group_by(
            Advisor.id, Advisor.name
        ).order_by(
            desc('net_commission')
        )
        
        result = await db.execute(query)
        advisor_commissions = result.fetchall()
        
        response = []
        for advisor in advisor_commissions:
            # Simular status baseado na performance
            status = "Cumprida" if advisor.net_commission > 1000 else "Não atingiu"
            
            response.append(AdvisorCommissionDetail(
                advisor_id=advisor.id,
                advisor_name=advisor.name,
                net_commission=advisor.net_commission,
                gross_commission=advisor.gross_commission,
                commission_percentage=advisor.avg_commission_rate or Decimal('2.0'),
                month_over_month_change=Decimal('10.5'),  # Mock - seria calculado
                status=status
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting advisor commissions: {e}")
        raise HTTPException(status_code=500, detail="Error fetching advisor commissions")

@router.get("/net-new-money", response_model=List[NetNewMoneyData])
async def get_net_new_money_history(
    start_date: Optional[date] = Query(None, description="Data inicial"),
    end_date: Optional[date] = Query(None, description="Data final"),
    period_type: str = Query("daily", description="Tipo: daily, weekly, monthly"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Histórico de Net New Money (captação líquida)
    """
    try:
        if not start_date:
            start_date = datetime.now().date() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now().date()
        
        # Agrupamento baseado no period_type
        if period_type == "monthly":
            date_trunc = func.date_trunc('month', Allocation.purchase_date)
        elif period_type == "weekly":
            date_trunc = func.date_trunc('week', Allocation.purchase_date)
        else:
            date_trunc = func.date_trunc('day', Allocation.purchase_date)
        
        # Query para aportes (novas alocações)
        inflows_query = select(
            date_trunc.label('period'),
            func.coalesce(func.sum(Allocation.total_invested), 0).label('inflows')
        ).where(
            and_(
                Allocation.purchase_date >= start_date,
                Allocation.purchase_date <= end_date,
                Allocation.is_active == True
            )
        ).group_by(
            date_trunc
        ).order_by(
            date_trunc
        )
        
        inflows_result = await db.execute(inflows_query)
        inflows_data = {row.period.date(): row.inflows for row in inflows_result.fetchall()}
        
        # Query para resgates (alocações fechadas)
        outflows_query = select(
            date_trunc.label('period'),
            func.coalesce(func.sum(
                Allocation.quantity * Allocation.exit_price
            ), 0).label('outflows')
        ).where(
            and_(
                Allocation.exit_date >= start_date,
                Allocation.exit_date <= end_date,
                Allocation.is_active == False,
                Allocation.exit_date.isnot(None)
            )
        ).group_by(
            date_trunc
        ).order_by(
            date_trunc
        )
        
        outflows_result = await db.execute(outflows_query)
        outflows_data = {row.period.date(): row.outflows for row in outflows_result.fetchall()}
        
        # Combinar dados
        all_dates = set(inflows_data.keys()) | set(outflows_data.keys())
        response = []
        cumulative_net = Decimal('0')
        
        for period_date in sorted(all_dates):
            inflows = inflows_data.get(period_date, Decimal('0'))
            outflows = outflows_data.get(period_date, Decimal('0'))
            net_flow = inflows - outflows
            cumulative_net += net_flow
            
            response.append(NetNewMoneyData(
                period=period_date,
                inflows=inflows,
                outflows=outflows,
                net_flow=net_flow,
                cumulative_net=cumulative_net,
                period_type=period_type
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting net new money history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching net new money data")

@router.get("/portfolio-summary")
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Resumo geral do portfólio para o dashboard
    """
    try:
        # Total de clientes ativos
        clients_query = select(func.count(Client.id)).where(Client.is_active == True)
        clients_result = await db.execute(clients_query)
        total_clients = clients_result.scalar() or 0
        
        # Total de ativos diferentes
        assets_query = select(func.count(func.distinct(Allocation.asset_id))).where(
            Allocation.is_active == True
        )
        assets_result = await db.execute(assets_query)
        total_assets = assets_result.scalar() or 0
        
        # Total de posições ativas
        positions_query = select(func.count(Allocation.id)).where(
            Allocation.is_active == True
        )
        positions_result = await db.execute(positions_query)
        total_positions = positions_result.scalar() or 0
        
        # Valor total sob custódia
        auc_query = select(
            func.coalesce(func.sum(
                Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
            ), 0)
        ).select_from(
            Allocation.join(Asset)
        ).where(
            Allocation.is_active == True
        )
        auc_result = await db.execute(auc_query)
        total_auc = auc_result.scalar() or Decimal('0')
        
        return {
            "total_clients": total_clients,
            "total_assets": total_assets,
            "total_positions": total_positions,
            "total_auc": total_auc,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail="Error fetching portfolio summary")