import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import uvicorn

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
async def websocket_endpoint(websocket: WebSocket):
    slave_id = websocket.query_params.get("slave_id")
    api_key = websocket.query_params.get("api_key")

    # Slave_id will match the env var name (e.g., slave_1)
    if not slave_id or slave_id not in SLAVE_AUTH or SLAVE_AUTH[slave_id] != api_key:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    clients[slave_id] = websocket

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.pop(slave_id, None)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

