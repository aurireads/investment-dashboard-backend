from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Advisor(Base):
    """
    Advisor model - baseado no dashboard que mostra assessores
    """
    __tablename__ = "advisors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    registration_number = Column(String(50), unique=True, nullable=True)  # Registro CVM
    commission_rate = Column(Numeric(5, 4), default=0.0200, nullable=False)  # 2% default
    is_active = Column(Boolean, default=True, nullable=False)
    hire_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    clients = relationship("Client", back_populates="advisor")
    
    def __repr__(self):
        return f"<Advisor(id={self.id}, name='{self.name}')>"

class Client(Base):
    """
    Client model - clientes do escritório de investimentos
    """
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    cpf_cnpj = Column(String(20), unique=True, nullable=True, index=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), default="Brasil", nullable=False)
    
    # Investment Profile
    risk_profile = Column(String(50), nullable=True)  # conservative, moderate, aggressive
    investment_experience = Column(String(50), nullable=True)
    monthly_income = Column(Numeric(15, 2), nullable=True)
    net_worth = Column(Numeric(15, 2), nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    account_opened_date = Column(DateTime(timezone=True), nullable=True)
    kyc_status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    
    # Advisor relationship
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    advisor = relationship("Advisor", back_populates="clients")
    allocations = relationship("Allocation", back_populates="client", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', email='{self.email}')>"
    
    @property
    def total_invested(self):
        """Calculate total amount invested by this client"""
        return sum(allocation.quantity * allocation.purchase_price for allocation in self.allocations)
    
    @property
    def active_allocations_count(self):
        """Count of active allocations"""
        return len([a for a in self.allocations if a.is_active])