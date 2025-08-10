# api.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import os

app = FastAPI()
clients: List[WebSocket] = []

# Load API key from environment variable (set in Render dashboard)
API_KEY = os.getenv("API_KEY", "changeme")  # "changeme" only as a fallback for local testing

class Signal(BaseModel):
    action: str  # e.g., "open" or "close"
    symbol: str
    type: str = None  # long/short
    entry_price: float = None
    sl: float = None
    tp: float = None
    ticket: int = None
    reason: str = None

def check_api_key(key: str):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API key")

@app.post("/send_signal")
async def send_signal(request: Request, signal: Signal):
    # Check API key in header
    api_key = request.headers.get("x-api-key")
    check_api_key(api_key)

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
    # Check API key in query params for WS (since headers are trickier here)
    api_key = websocket.query_params.get("api_key")
    if api_key != API_KEY:
        await websocket.close(code=1008)  # Policy Violation
        return

    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
