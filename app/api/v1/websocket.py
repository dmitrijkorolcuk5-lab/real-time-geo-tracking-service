from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, user_id: str | None = Query(default=None)) -> None:
    resolved_user_id = user_id or websocket.headers.get("x-user-id")
    if not resolved_user_id:
        await websocket.close(code=1008)
        return
    manager = websocket.app.state.websocket_manager
    session = await manager.connect(websocket, user_id=resolved_user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(session)

