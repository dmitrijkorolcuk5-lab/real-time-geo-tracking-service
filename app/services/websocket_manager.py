import asyncio
import contextlib
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True, eq=False)
class ManagedSession:
    websocket: WebSocket
    user_id: str
    update_queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    alert_queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    sender_task: asyncio.Task | None = None
    closed: bool = False


class WebsocketManager:
    def __init__(self, update_queue_size: int = 512, alert_queue_size: int = 512) -> None:
        self.update_queue_size = update_queue_size
        self.alert_queue_size = alert_queue_size
        self._sessions: dict[str, set[ManagedSession]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, user_id: str) -> ManagedSession:
        await websocket.accept()
        session = ManagedSession(
            websocket=websocket,
            user_id=user_id,
            update_queue=asyncio.Queue(maxsize=self.update_queue_size),
            alert_queue=asyncio.Queue(maxsize=self.alert_queue_size),
        )
        session.sender_task = asyncio.create_task(self._session_sender(session))
        async with self._lock:
            self._sessions[user_id].add(session)
        logger.info("websocket connected user_id=%s active_sessions=%s", user_id, self.active_session_count(user_id))
        return session

    async def disconnect(self, session: ManagedSession) -> None:
        if session.closed:
            return
        session.closed = True
        if session.sender_task is not None:
            session.sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await session.sender_task
        async with self._lock:
            sessions = self._sessions.get(session.user_id)
            if sessions is not None:
                sessions.discard(session)
                if not sessions:
                    self._sessions.pop(session.user_id, None)
        with contextlib.suppress(Exception):
            await session.websocket.close()
        logger.info("websocket disconnected user_id=%s active_sessions=%s", session.user_id, self.active_session_count(session.user_id))

    async def broadcast_location(self, user_id: str, payload: dict) -> None:
        await self._broadcast(user_id, payload, alert=False)

    async def broadcast_alert(self, user_id: str, payload: dict) -> None:
        await self._broadcast(user_id, payload, alert=True)

    async def _broadcast(self, user_id: str, payload: dict, *, alert: bool) -> None:
        async with self._lock:
            sessions = list(self._sessions.get(user_id, set()))
        for session in sessions:
            queue = session.alert_queue if alert else session.update_queue
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    if alert:
                        logger.warning("dropped websocket alert due to full queue user_id=%s", user_id)
                    else:
                        logger.warning("dropped stale websocket location update user_id=%s", user_id)

    async def _session_sender(self, session: ManagedSession) -> None:
        try:
            while not session.closed:
                while True:
                    try:
                        payload = session.alert_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    await session.websocket.send_json(jsonable_encoder(payload))
                try:
                    payload = await asyncio.wait_for(session.update_queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                await session.websocket.send_json(jsonable_encoder(payload))
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass
        except Exception:
            logger.exception("websocket sender failed for user_id=%s", session.user_id)
        finally:
            session.closed = True

    def active_session_count(self, user_id: str) -> int:
        return len(self._sessions.get(user_id, set()))
