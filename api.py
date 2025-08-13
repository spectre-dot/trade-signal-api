import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
import asyncio

app = FastAPI()

# Store connected slaves
clients: Dict[str, WebSocket] = {}

# Master key
MASTER_KEY = os.getenv("master_key")

# Slave keys - dynamically read all env vars starting with "slave_"
SLAVE_AUTH = {k: v for k, v in os.environ.items() if k.startswith("slave_")}

class Signal(BaseModel):
    action: str
    symbol: str
    type: str = None
    entry_price: float = None
    sl: float = None
    tp: float = None
    ticket: int = None
    reason: str = None
    target_ids: List[str] = None

def check_master_key(key: str):
    if key != MASTER_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid master key")

@app.post("/send_signal")
async def send_signal(request: Request, signal: Signal):
    api_key = request.headers.get("x-api-key")
    check_master_key(api_key)

    data = signal.dict()
    target_ids = data.pop("target_ids", None)

    disconnected_clients = []
    for slave_id, client_ws in clients.items():
        if target_ids is None or slave_id in target_ids:
            try:
                await client_ws.send_json(data)
            except:
                disconnected_clients.append(slave_id)

    for dc in disconnected_clients:
        clients.pop(dc, None)

    return JSONResponse({"status": "Signal sent", "clients": len(clients)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, slave_id: str, api_key: str):
    if api_key != os.getenv(slave_id):
        await websocket.close()
        return

    await websocket.accept()
    clients[slave_id] = websocket
    print(f"[{slave_id}] ✅ Connected")

    try:
        while True:
            # Keep connection alive with periodic ping
            await websocket.send_text("ping")  # optional
            await asyncio.sleep(20)  # 20 sec keepalive
    except WebSocketDisconnect:
        print(f"[{slave_id}] ❌ Disconnected")
        clients.pop(slave_id, None)
    except Exception as e:
        print(f"[{slave_id}] ⚠️ Error: {e}")
        clients.pop(slave_id, None)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
