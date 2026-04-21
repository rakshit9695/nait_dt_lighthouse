"""Live WebSocket endpoint (spec §3.2)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.solver.simulator import SIMULATOR

router = APIRouter()


@router.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    await ws.accept()
    SIMULATOR.ensure_live_state()
    try:
        last_idx = -1
        while True:
            if SIMULATOR.live_buffer:
                frame = SIMULATOR.live_buffer[-1]
                idx = id(frame)
                if idx != last_idx:
                    await ws.send_json(frame.model_dump(mode="json"))
                    last_idx = idx
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
