# Endpoints de clientes
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional, List
from decimal import Decimal
import logging

from app.api.deps import (
    get_db, get_current_active_user, get_user_with_write_access,
    PaginatedResponse, get_pagination_params, PaginationParams
)
from app.models.user import User
from app.models.client import Client, Advisor
from app.models.allocation import Allocation
from app.models.asset import Asset
from app.schemas.client import (
    Client as ClientSchema, ClientCreate, ClientUpdate, ClientWithPortfolio,
    ClientList, ClientFilter, ClientSearch, ClientStats,
    Advisor as AdvisorSchema, AdvisorCreate, AdvisorUpdate, AdvisorWithStats,
    RiskProfile, KYCStatus
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Client endpoints
@router.get("/", response_model=ClientList)
async def get_clients(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = Query(None, min_length=2, description="Buscar por nome, email ou CPF/CNPJ"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    kyc_status: Optional[KYCStatus] = Query(None, description="Filtrar por status KYC"),
    risk_profile: Optional[RiskProfile] = Query(None, description="Filtrar por perfil de risco"),
    advisor_id: Optional[int] = Query(None, description="Filtrar por assessor"),
    sort_by: str = Query("name", description="Campo de ordenação"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Ordem"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Listar clientes com paginação, busca e filtros
    """
    try:
        # Base query
        query = select(Client).options(selectinload(Client.advisor))
        
        # Aplicar filtros
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Client.name.ilike(search_term),
                    Client.email.ilike(search_term),
                    Client.cpf_cnpj.ilike(search_term)
                )
            )
        
        if is_active is not None:
            conditions.append(Client.is_active == is_active)
        
        if kyc_status:
            conditions.append(Client.kyc_status == kyc_status)
        
        if risk_profile:
            conditions.append(Client.risk_profile == risk_profile)
        
        if advisor_id:
            conditions.append(Client.advisor_id == advisor_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Aplicar ordenação
        if hasattr(Client, sort_by):
            order_column = getattr(Client, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute query
        result = await db.execute(query)
        clients = result.scalars().all()
        
        # Convert to schema
        client_schemas = [ClientSchema.from_orm(client) for client in clients]
        
        return ClientList(
            items=client_schemas,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=(total + pagination.size - 1) // pagination.size
        )
        
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        raise HTTPException(status_code=500, detail="Error fetching clients")

@router.post("/", response_model=ClientSchema)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Criar novo cliente (apenas admin)
    """
    try:
        # Verificar se email já existe
        existing_email = await db.execute(
            select(Client).where(Client.email == client_data.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verificar CPF/CNPJ se fornecido
        if client_data.cpf_cnpj:
            existing_cpf = await db.execute(
                select(Client).where(Client.cpf_cnpj == client_data.cpf_cnpj)
            )
            if existing_cpf.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPF/CNPJ already registered"
                )
        
        # Verificar se advisor existe
        if client_data.advisor_id:
            advisor = await db.execute(
                select(Advisor).where(Advisor.id == client_data.advisor_id)
            )
            if not advisor.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Advisor not found"
                )
        
        # Criar cliente
        client = Client(**client_data.dict())
        db.add(client)
        await db.commit()
        await db.refresh(client)
        
        # Carregar relacionamentos
        await db.execute(
            select(Client)
            .options(selectinload(Client.advisor))
            .where(Client.id == client.id)
        )
        
        logger.info(f"Client created: {client.id} by user {current_user.id}")
        
        return ClientSchema.from_orm(client)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail="Error creating client")

@router.get("/{client_id}", response_model=ClientSchema)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obter cliente por ID
    """
    try:
        query = select(Client).options(selectinload(Client.advisor)).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        return ClientSchema.from_orm(client)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client")

@router.put("/{client_id}", response_model=ClientSchema)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Atualizar cliente (apenas admin)
    """
    try:
        # Buscar cliente
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Verificar email duplicado
        if client_data.email and client_data.email != client.email:
            existing_email = await db.execute(
                select(Client).where(
                    and_(Client.email == client_data.email, Client.id != client_id)
                )
            )
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Verificar CPF/CNPJ duplicado
        if client_data.cpf_cnpj and client_data.cpf_cnpj != client.cpf_cnpj:
            existing_cpf = await db.execute(
                select(Client).where(
                    and_(Client.cpf_cnpj == client_data.cpf_cnpj, Client.id != client_id)
                )
            )
            if existing_cpf.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPF/CNPJ already registered"
                )
        
        # Verificar advisor
        if client_data.advisor_id:
            advisor = await db.execute(
                select(Advisor).where(Advisor.id == client_data.advisor_id)
            )
            if not advisor.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Advisor not found"
                )
        
        # Atualizar campos
        for field, value in client_data.dict(exclude_unset=True).items():
            setattr(client, field, value)
        
        await db.commit()
        await db.refresh(client)
        
        logger.info(f"Client updated: {client_id} by user {current_user.id}")
        
        return ClientSchema.from_orm(client)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating client")

@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Deletar cliente (apenas admin) - soft delete
    """
    try:
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Verificar se tem posições ativas
        active_allocations = await db.execute(
            select(func.count(Allocation.id)).where(
                and_(Allocation.client_id == client_id, Allocation.is_active == True)
            )
        )
        
        if active_allocations.scalar() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete client with active positions"
            )
        
        # Soft delete
        client.is_active = False
        await db.commit()
        
        logger.info(f"Client deleted: {client_id} by user {current_user.id}")
        
        return {"message": "Client deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting client")

@router.get("/{client_id}/portfolio", response_model=ClientWithPortfolio)
async def get_client_portfolio(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obter portfólio completo do cliente
    """
    try:
        # Buscar cliente
        client_query = select(Client).options(selectinload(Client.advisor)).where(Client.id == client_id)
        client_result = await db.execute(client_query)
        client = client_result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Calcular métricas do portfólio
        portfolio_query = select(
            func.coalesce(func.sum(Allocation.total_invested), 0).label('total_invested'),
            func.coalesce(func.sum(
                Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
            ), 0).label('current_value'),
            func.count(Allocation.id).label('active_positions')
        ).select_from(
            Allocation.join(Asset)
        ).where(
            and_(Allocation.client_id == client_id, Allocation.is_active == True)
        )
        
        portfolio_result = await db.execute(portfolio_query)
        portfolio_data = portfolio_result.fetchone()
        
        total_invested = portfolio_data.total_invested or Decimal('0')
        current_value = portfolio_data.current_value or Decimal('0')
        total_gain_loss = current_value - total_invested
        total_gain_loss_percent = (
            (total_gain_loss / total_invested * 100) if total_invested > 0 else Decimal('0')
        )
        
        # Última atividade
        last_activity_query = select(func.max(Allocation.purchase_date)).where(
            Allocation.client_id == client_id
        )
        last_activity_result = await db.execute(last_activity_query)
        last_activity_date = last_activity_result.scalar()
        
        # Converter para schema
        client_schema = ClientWithPortfolio.from_orm(client)
        client_schema.total_invested = total_invested
        client_schema.current_value = current_value
        client_schema.total_gain_loss = total_gain_loss
        client_schema.total_gain_loss_percent = total_gain_loss_percent
        client_schema.active_positions = portfolio_data.active_positions or 0
        client_schema.last_activity_date = last_activity_date
        
        return client_schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client portfolio {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client portfolio")

@router.get("/stats/overview", response_model=ClientStats)
async def get_client_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Estatísticas gerais dos clientes
    """
    try:
        # Total de clientes
        total_query = select(func.count(Client.id))
        total_result = await db.execute(total_query)
        total_clients = total_result.scalar() or 0
        
        # Clientes ativos
        active_query = select(func.count(Client.id)).where(Client.is_active == True)
        active_result = await db.execute(active_query)
        active_clients = active_result.scalar() or 0
        
        # Por status KYC
        kyc_pending_query = select(func.count(Client.id)).where(Client.kyc_status == "pending")
        kyc_pending_result = await db.execute(kyc_pending_query)
        pending_kyc = kyc_pending_result.scalar() or 0
        
        kyc_approved_query = select(func.count(Client.id)).where(Client.kyc_status == "approved")
        kyc_approved_result = await db.execute(kyc_approved_query)
        approved_kyc = kyc_approved_result.scalar() or 0
        
        # Por perfil de risco
        risk_profile_query = select(
            Client.risk_profile,
            func.count(Client.id)
        ).where(
            Client.risk_profile.isnot(None)
        ).group_by(Client.risk_profile)
        
        risk_profile_result = await db.execute(risk_profile_query)
        by_risk_profile = {row[0]: row[1] for row in risk_profile_result.fetchall()}
        
        # Por assessor
        advisor_query = select(
            Advisor.name,
            func.count(Client.id)
        ).select_from(
            Client.join(Advisor, Client.advisor_id == Advisor.id, isouter=True)
        ).group_by(Advisor.name)
        
        advisor_result = await db.execute(advisor_query)
        by_advisor = {row[0] or "Sem assessor": row[1] for row in advisor_result.fetchall()}
        
        # Novos clientes este mês
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_clients_query = select(func.count(Client.id)).where(
            Client.created_at >= month_start
        )
        new_clients_result = await db.execute(new_clients_query)
        new_clients_this_month = new_clients_result.scalar() or 0
        
        # Total AuM
        aum_query = select(
            func.coalesce(func.sum(
                Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
            ), 0)
        ).select_from(
            Allocation.join(Asset)
        ).where(
            Allocation.is_active == True
        )
        aum_result = await db.execute(aum_query)
        total_aum = aum_result.scalar() or Decimal('0')
        
        return ClientStats(
            total_clients=total_clients,
            active_clients=active_clients,
            inactive_clients=total_clients - active_clients,
            pending_kyc=pending_kyc,
            approved_kyc=approved_kyc,
            by_risk_profile=by_risk_profile,
            by_advisor=by_advisor,
            new_clients_this_month=new_clients_this_month,
            total_aum=total_aum
        )
        
    except Exception as e:
        logger.error(f"Error getting client stats: {e}")
        raise HTTPException(status_code=500, detail="Error fetching client statistics")

# Advisor endpoints
@router.get("/advisors/", response_model=List[AdvisorSchema])
async def get_advisors(
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Listar assessores
    """
    try:
        query = select(Advisor)
        
        if is_active is not None:
            query = query.where(Advisor.is_active == is_active)
        
        query = query.order_by(Advisor.name)
        
        result = await db.execute(query)
        advisors = result.scalars().all()
        
        return [AdvisorSchema.from_orm(advisor) for advisor in advisors]
        
    except Exception as e:
        logger.error(f"Error getting advisors: {e}")
        raise HTTPException(status_code=500, detail="Error fetching advisors")

@router.post("/advisors/", response_model=AdvisorSchema)
async def create_advisor(
    advisor_data: AdvisorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Criar novo assessor (apenas admin)
    """
    try:
        # Verificar email único
        existing_email = await db.execute(
            select(Advisor).where(Advisor.email == advisor_data.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verificar número de registro único
        if advisor_data.registration_number:
            existing_reg = await db.execute(
                select(Advisor).where(Advisor.registration_number == advisor_data.registration_number)
            )
            if existing_reg.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration number already exists"
                )
        
        advisor = Advisor(**advisor_data.dict())
        db.add(advisor)
        await db.commit()
        await db.refresh(advisor)
        
        logger.info(f"Advisor created: {advisor.id} by user {current_user.id}")
        
        return AdvisorSchema.from_orm(advisor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating advisor: {e}")
        raise HTTPException(status_code=500, detail="Error creating advisor")

@router.get("/advisors/{advisor_id}", response_model=AdvisorWithStats)
async def get_advisor_with_stats(
    advisor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obter assessor com estatísticas
    """
    try:
        # Buscar assessor
        advisor_query = select(Advisor).where(Advisor.id == advisor_id)
        advisor_result = await db.execute(advisor_query)
        advisor = advisor_result.scalar_one_or_none()
        
        if not advisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Advisor not found"
            )
        
        # Estatísticas do assessor
        stats_query = select(
            func.count(Client.id).label('total_clients'),
            func.count(func.nullif(Client.is_active, False)).label('active_clients'),
            func.coalesce(func.sum(
                Allocation.quantity * func.coalesce(Asset.current_price, Allocation.purchase_price)
            ), 0).label('total_aum')
        ).select_from(
            Client
            .join(Allocation, Client.id == Allocation.client_id, isouter=True)
            .join(Asset, Allocation.asset_id == Asset.id, isouter=True)
        ).where(
            and_(
                Client.advisor_id == advisor_id,
                or_(Allocation.is_active == True, Allocation.id.is_(None))
            )
        )
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.fetchone()
        
        # Comissões
        from datetime import datetime
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year_start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_commission_query = select(
            func.coalesce(func.sum(Commission.commission_amount), 0)
        ).where(
            and_(
                Commission.advisor_id == advisor_id,
                Commission.period_start >= current_month_start
            )
        )
        monthly_commission_result = await db.execute(monthly_commission_query)
        monthly_commission = monthly_commission_result.scalar() or Decimal('0')
        
        ytd_commission_query = select(
            func.coalesce(func.sum(Commission.commission_amount), 0)
        ).where(
            and_(
                Commission.advisor_id == advisor_id,
                Commission.period_start >= year_start
            )
        )
        ytd_commission_result = await db.execute(ytd_commission_query)
        ytd_commission = ytd_commission_result.scalar() or Decimal('0')
        
        # Converter para schema com stats
        advisor_schema = AdvisorWithStats.from_orm(advisor)
        advisor_schema.total_clients = stats.total_clients or 0
        advisor_schema.active_clients = stats.active_clients or 0
        advisor_schema.total_aum = stats.total_aum or Decimal('0')
        advisor_schema.monthly_commission = monthly_commission
        advisor_schema.ytd_commission = ytd_commission
        
        return advisor_schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting advisor stats {advisor_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching advisor statistics")

@router.put("/advisors/{advisor_id}", response_model=AdvisorSchema)
async def update_advisor(
    advisor_id: int,
    advisor_data: AdvisorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_user_with_write_access)
):
    """
    Atualizar assessor (apenas admin)
    """
    try:
        advisor_query = select(Advisor).where(Advisor.id == advisor_id)
        advisor_result = await db.execute(advisor_query)
        advisor = advisor_result.scalar_one_or_none()
        
        if not advisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Advisor not found"
            )
        
        # Verificar email único
        if advisor_data.email and advisor_data.email != advisor.email:
            existing_email = await db.execute(
                select(Advisor).where(
                    and_(Advisor.email == advisor_data.email, Advisor.id != advisor_id)
                )
            )
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Verificar número de registro único
        if advisor_data.registration_number and advisor_data.registration_number != advisor.registration_number:
            existing_reg = await db.execute(
                select(Advisor).where(
                    and_(
                        Advisor.registration_number == advisor_data.registration_number,
                        Advisor.id != advisor_id
                    )
                )
            )
            if existing_reg.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration number already exists"
                )
        
        # Atualizar campos
        for field, value in advisor_data.dict(exclude_unset=True).items():
            setattr(advisor, field, value)
        
        await db.commit()
        await db.refresh(advisor)
        
        logger.info(f"Advisor updated: {advisor_id} by user {current_user.id}")
        
        return AdvisorSchema.from_orm(advisor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating advisor {advisor_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating advisor")