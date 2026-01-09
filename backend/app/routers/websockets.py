"""WebSocket connections for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

router = APIRouter()

# Active WebSocket connections
class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Map of run_id -> set of websocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of user_id -> set of websocket connections for dashboard
        self.dashboard_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: int = None, user_id: int = None):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        if run_id:
            if run_id not in self.active_connections:
                self.active_connections[run_id] = set()
            self.active_connections[run_id].add(websocket)
        
        if user_id:
            if user_id not in self.dashboard_connections:
                self.dashboard_connections[user_id] = set()
            self.dashboard_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, run_id: int = None, user_id: int = None):
        """Remove WebSocket connection."""
        if run_id and run_id in self.active_connections:
            self.active_connections[run_id].discard(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        
        if user_id and user_id in self.dashboard_connections:
            self.dashboard_connections[user_id].discard(websocket)
            if not self.dashboard_connections[user_id]:
                del self.dashboard_connections[user_id]

    async def send_run_update(self, run_id: int, message: dict):
        """Broadcast run status update to all connected clients."""
        if run_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[run_id].discard(conn)

    async def send_dashboard_update(self, user_id: int, message: dict):
        """Broadcast dashboard update to user's connections."""
        if user_id in self.dashboard_connections:
            disconnected = set()
            for connection in self.dashboard_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.dashboard_connections[user_id].discard(conn)


manager = ConnectionManager()


@router.websocket("/ws/run/{run_id}")
async def websocket_run_status(websocket: WebSocket, run_id: int):
    """WebSocket endpoint for real-time run status updates.
    
    Clients connect to this endpoint to receive live updates
    about analysis run progress and results.
    """
    await manager.connect(websocket, run_id=run_id)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "pong", "run_id": run_id})
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id=run_id)


@router.websocket("/ws/dashboard/{user_id}")
async def websocket_dashboard(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time dashboard updates.
    
    Clients connect to this endpoint to receive live updates
    about new runs, status changes, and statistics.
    """
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)
