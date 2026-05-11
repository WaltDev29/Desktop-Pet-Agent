import asyncio
import uuid
import logging
from collections import defaultdict
from fastapi import WebSocket
from sqlalchemy import select, update, insert
from app.db.database import AsyncSessionLocal
from app.db.models import Message, MessageLog

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # user_id -> role ("agent" | "app") -> client_id -> WebSocket
        self.active_connections: dict[str, dict[str, dict[str, WebSocket]]] = defaultdict(lambda: {"agent": {}, "app": {}})
        self.token_buffers: dict[str, str] = defaultdict(str)
        self.flush_task = None
        self.running = False

    async def connect(self, websocket: WebSocket, user_id: str, role: str, client_id: str):
        await websocket.accept()
        self.active_connections[user_id][role][client_id] = websocket
        logger.info(f"Client connected: user_id={user_id}, role={role}, client_id={client_id}")

    def disconnect(self, user_id: str, role: str, client_id: str):
        if client_id in self.active_connections[user_id][role]:
            del self.active_connections[user_id][role][client_id]
            logger.info(f"Client disconnected: user_id={user_id}, role={role}, client_id={client_id}")

    async def send_to_role(self, user_id: str, role: str, message: dict):
        # Forward message to all clients of a specific role for a given user
        clients = self.active_connections[user_id][role]
        for client_id, ws in list(clients.items()):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(user_id, role, client_id)
                
    async def buffer_token(self, message_id: str, chunk: str):
        self.token_buffers[message_id] += chunk

    async def flush_tokens_to_db(self):
        if not self.token_buffers:
            return
            
        buffers_to_flush = self.token_buffers.copy()
        self.token_buffers.clear()
        
        async with AsyncSessionLocal() as db:
            try:
                for message_id, chunk in buffers_to_flush.items():
                    # Update message content in DB
                    stmt = select(Message).where(Message.message_id == uuid.UUID(message_id))
                    result = await db.execute(stmt)
                    msg = result.scalar_one_or_none()
                    if msg:
                        msg.content += chunk
                        msg.status = "streaming"
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to flush tokens: {e}")
                # Requeue failed buffers
                for message_id, chunk in buffers_to_flush.items():
                    self.token_buffers[message_id] = chunk + self.token_buffers.get(message_id, "")

    async def _flush_loop(self):
        while self.running:
            await asyncio.sleep(2)  # Flush every 2 seconds
            await self.flush_tokens_to_db()

    def start_flush_worker(self):
        self.running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Token flush worker started.")

    async def stop_flush_worker(self):
        self.running = False
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self.flush_tokens_to_db()
        logger.info("Token flush worker stopped.")

manager = ConnectionManager()

def start_flush_worker():
    manager.start_flush_worker()

async def stop_flush_worker():
    await manager.stop_flush_worker()
