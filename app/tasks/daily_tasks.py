# Tarefas diárias
import logging
from datetime import date, datetime, timedelta
from sqlalchemy import select, and_, desc, insert
from app.core.database import SessionLocal, get_sync_session
from app.models.asset import Asset
from app.models.daily_return import DailyReturn
from app.services.yahoo_finance import get_price_history_sync, get_current_price_sync
from app.tasks.celery_app import celery_app
from app.websockets.real_time import manager
from app.schemas.performance import RealTimePrice
from app.schemas.asset import AssetPriceUpdate
from app.services.cache import get_redis_client, set_cache
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task
def update_all_daily_prices():
    """
    Celery task to update daily closing prices for all active assets.
    """
    with SessionLocal() as db:
        logger.info("Starting daily price update task...")
        
        assets_to_update_query = select(Asset).where(Asset.is_active == True)
        assets_to_update = db.execute(assets_to_update_query).scalars().all()
        
        for asset in assets_to_update:
            try:
                # Fetch only the last day's data
                history = get_price_history_sync(asset.ticker, period="2d", interval="1d")
                
                if history and len(history) > 1:
                    latest_price = history[-1]
                    previous_price = history[-2]
                    
                    daily_return = DailyReturn(
                        asset_id=asset.id,
                        date=latest_price['date'].date(),
                        close_price=latest_price['close'],
                        open_price=latest_price['open'],
                        high_price=latest_price['high'],
                        low_price=latest_price['low'],
                        volume=latest_price['volume']
                    )
                    
                    # Calculate daily return based on previous close
                    if previous_price and previous_price.get('close'):
                        daily_return.calculate_return(previous_price['close'])
                    
                    # Insert or update
                    db.merge(daily_return)
                    
                    # Update asset's current price
                    asset.update_price_info(
                        price=latest_price['close'],
                        previous_close=previous_price['close'],
                        volume=latest_price['volume']
                    )
                    db.merge(asset)
                    
            except Exception as e:
                logger.error(f"Failed to update daily price for {asset.ticker}: {e}")
        
        db.commit()
        logger.info("Daily price update task finished.")

@celery_app.task
def update_all_realtime_prices():
    """
    Celery task to update current prices for all active assets.
    This will be triggered more frequently.
    """
    with SessionLocal() as db:
        logger.info("Starting real-time price update task...")
        
        assets_query = select(Asset).where(Asset.is_active == True)
        assets = db.execute(assets_query).scalars().all()
        
        for asset in assets:
            try:
                yf_data = get_current_price_sync(asset.ticker)
                
                if yf_data:
                    current_price = yf_data
                    
                    if current_price != asset.current_price:
                        # Update asset model and commit
                        asset.current_price = current_price
                        asset.last_price_update = datetime.now()
                        db.merge(asset)
                        db.commit()
                        
                        # Create a RealTimePrice object
                        real_time_data = RealTimePrice(
                            ticker=asset.ticker,
                            current_price=current_price,
                            daily_change=asset.daily_change,
                            daily_change_percent=asset.daily_change_percent,
                            volume=asset.volume,
                            timestamp=datetime.now(),
                            market_status="open" # Placeholder
                        )
                        
                        # Send to WebSocket clients
                        asyncio.run(manager.broadcast(real_time_data.json()))
                        
                        # Update cache
                        asyncio.run(set_cache(f"asset:price:{asset.ticker}", real_time_data.dict()))
                        
            except Exception as e:
                logger.error(f"Failed to update real-time price for {asset.ticker}: {e}")
                
        logger.info("Real-time price update task finished.")