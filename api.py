# api.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()
clients: List[WebSocket] = []

class Signal(BaseModel):
    action: str  # e.g., "open" or "close"
    symbol: str
    type: str = None  # long/short
    entry_price: float = None
    sl: float = None
    tp: float = None
    ticket: int = None
    reason: str = None

@app.post("/send_signal")
async def send_signal(signal: Signal):
    data = signal.dict()
    disconnected_clients = []
    for client in clients:
        try:
            await client.send_json(data)
        except:
            disconnected_clients.append(client)
    for dc in disconnected_clients:
        clients.remove(dc)
    return JSONResponse({"status": "Signal sent", "clients": len(clients)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
