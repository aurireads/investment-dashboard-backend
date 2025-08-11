from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class InvestmentExperience(str, Enum):
    NONE = "none"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"

# Advisor Schemas
class AdvisorBase(BaseModel):
    """Base advisor schema"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=50)
    commission_rate: Decimal = Field(Decimal('0.02'), ge=0, le=1, description="Commission rate (0-1)")
    is_active: bool = True

class AdvisorCreate(AdvisorBase):
    """Schema for advisor creation"""
    hire_date: Optional[datetime] = None

class AdvisorUpdate(BaseModel):
    """Schema for advisor updates"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=50)
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None

class Advisor(AdvisorBase):
    """Full advisor schema"""
    id: int
    hire_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AdvisorWithStats(Advisor):
    """Advisor with performance statistics"""
    total_clients: int = 0
    active_clients: int = 0
    total_aum: Decimal = Decimal('0')  # Assets Under Management
    monthly_commission: Decimal = Decimal('0')
    ytd_commission: Decimal = Decimal('0')

# Client Schemas
class ClientBase(BaseModel):
    """Base client schema"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    
    # Address
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: str = Field("Brasil", max_length=100)
    
    # Investment Profile
    risk_profile: Optional[RiskProfile] = None
    investment_experience: Optional[InvestmentExperience] = None
    monthly_income: Optional[Decimal] = Field(None, ge=0)
    net_worth: Optional[Decimal] = Field(None, ge=0)
    
    # Account info
    is_active: bool = True
    account_opened_date: Optional[datetime] = None
    kyc_status: KYCStatus = KYCStatus.PENDING
    advisor_id: Optional[int] = None
    
    @validator('cpf_cnpj')
    def validate_cpf_cnpj(cls, v):
        """Basic CPF/CNPJ validation"""
        if v:
            # Remove non-digits
            clean = ''.join(filter(str.isdigit, v))
            if len(clean) not in [11, 14]:
                raise ValueError('CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos')
        return v

class ClientCreate(ClientBase):
    """Schema for client creation"""
    pass

class ClientUpdate(BaseModel):
    """Schema for client updates"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    risk_profile: Optional[RiskProfile] = None
    investment_experience: Optional[InvestmentExperience] = None
    monthly_income: Optional[Decimal] = Field(None, ge=0)
    net_worth: Optional[Decimal] = Field(None, ge=0)
    
    is_active: Optional[bool] = None
    kyc_status: Optional[KYCStatus] = None
    advisor_id: Optional[int] = None

class Client(ClientBase):
    """Full client schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    advisor: Optional[Advisor] = None
    
    class Config:
        from_attributes = True

class ClientWithPortfolio(Client):
    """Client with portfolio summary"""
    total_invested: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    total_gain_loss: Decimal = Decimal('0')
    total_gain_loss_percent: Decimal = Decimal('0')
    active_positions: int = 0
    portfolio_risk_score: Optional[float] = None
    last_activity_date: Optional[datetime] = None

# List and Pagination Schemas
class ClientList(BaseModel):
    """Paginated client list"""
    items: List[Client]
    total: int
    page: int
    size: int
    pages: int

class ClientListWithPortfolio(BaseModel):
    """Paginated client list with portfolio data"""
    items: List[ClientWithPortfolio]
    total: int
    page: int
    size: int
    pages: int

class AdvisorList(BaseModel):
    """Paginated advisor list"""
    items: List[Advisor]
    total: int
    page: int
    size: int
    pages: int

# Search and Filter Schemas
class ClientFilter(BaseModel):
    """Client filtering options"""
    is_active: Optional[bool] = None
    kyc_status: Optional[KYCStatus] = None
    risk_profile: Optional[RiskProfile] = None
    advisor_id: Optional[int] = None
    min_net_worth: Optional[Decimal] = None
    max_net_worth: Optional[Decimal] = None
    city: Optional[str] = None
    state: Optional[str] = None

class ClientSearch(BaseModel):
    """Client search parameters"""
    query: Optional[str] = Field(None, min_length=2, description="Search in name, email, CPF/CNPJ")
    filters: Optional[ClientFilter] = None
    sort_by: Optional[str] = Field("name", description="Sort field")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$")

# Statistics Schemas
class ClientStats(BaseModel):
    """Client statistics"""
    total_clients: int
    active_clients: int
    inactive_clients: int
    pending_kyc: int
    approved_kyc: int
    by_risk_profile: dict[str, int]
    by_advisor: dict[str, int]
    new_clients_this_month: int
    total_aum: Decimal  # Assets Under Management

class AdvisorStats(BaseModel):
    """Advisor performance statistics"""
    total_advisors: int
    active_advisors: int
    top_performers: List[AdvisorWithStats]
    avg_clients_per_advisor: float
    total_commissions_ytd: Decimal