# Exportação CSV/Excel
import pandas as pd
import io
import logging
from typing import List, Optional
from datetime import date
from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.allocation import Allocation
from app.models.client import Client
from app.models.asset import Asset
from app.core.config import settings

logger = logging.getLogger(__name__)

async def export_allocations_to_excel(
    db: AsyncSession,
    client_ids: Optional[List[int]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> StreamingResponse:
    """
    Export client allocations to an Excel file.
    """
    try:
        query = select(Allocation).options(
            selectinload(Allocation.client),
            selectinload(Allocation.asset)
        )
        
        conditions = []
        if client_ids:
            conditions.append(Allocation.client_id.in_(client_ids))
        if start_date:
            conditions.append(Allocation.purchase_date >= start_date)
        if end_date:
            conditions.append(Allocation.purchase_date <= end_date)
            
        if conditions:
            query = query.where(and_(*conditions))
            
        result = await db.execute(query)
        allocations = result.scalars().all()
        
        if not allocations:
            raise ValueError("No allocations found for the given criteria.")
            
        data = []
        for alloc in allocations:
            data.append({
                "Client Name": alloc.client.name if alloc.client else "N/A",
                "Asset Ticker": alloc.asset.ticker if alloc.asset else "N/A",
                "Asset Name": alloc.asset.name if alloc.asset else "N/A",
                "Quantity": float(alloc.quantity),
                "Purchase Price": float(alloc.purchase_price),
                "Purchase Date": alloc.purchase_date,
                "Total Invested": float(alloc.total_invested),
                "Current Price": float(alloc.asset.current_price) if alloc.asset and alloc.asset.current_price else None,
                "Current Value": float(alloc.current_value),
                "Daily Change (%)": float(alloc.asset.daily_change_percent) if alloc.asset and alloc.asset.daily_change_percent else None,
                "Gain/Loss (%)": float(alloc.gain_loss_percent),
                "Status": "Active" if alloc.is_active else "Closed"
            })
            
        df = pd.DataFrame(data)
        
        # Use a BytesIO buffer to store the Excel file in memory
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Allocations')
        writer.close()
        output.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="investment_report.xlsx"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()), 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Error during export: {e}")
        raise