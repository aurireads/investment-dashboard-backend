# WebSocket real-time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from typing import List
import logging

from app.core.security import verify_token
from app.schemas.user import TokenPayload

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, token: str):
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
            
        token_data = TokenPayload(**payload)
        client_id = f"user:{token_data.sub}"
        
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")

manager = ConnectionManager()
router = APIRouter()

@router.websocket("/ws/real-time-prices")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        # Authentication via token in query params
        await manager.connect(websocket, token)
        
        client_id = f"user:{verify_token(token).get('sub')}"
        
        while True:
            # We don't expect messages from the client in this case,
            # so we just wait for disconnection.
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except HTTPException as e:
        await websocket.close(code=status.HTTP_401_UNAUTHORIZED)
        logger.warning(f"WebSocket connection failed: {e.detail}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.HTTP_500_INTERNAL_SERVER_ERROR)