"""FastAPI web server for dslv-zpdi.

Provides a REST API and WebSocket gateway to access the latest sensor state
cached by the metrology node.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# Configuration from environment
SQLITE_PATH = Path(os.environ.get("ZPDI_SQLITE_PATH", "./data/zpdi_cache.db"))
WEB_HOST = os.environ.get("ZPDI_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("ZPDI_WEB_PORT", "8000"))

app = FastAPI(title="dslv-zpdi Web Server")

class HealthStatus(BaseModel):
    status: str
    last_sample_ts: int | None

def get_latest_from_cache() -> dict[str, Any] | None:
    """Read the latest state from the SQLite WAL cache."""
    if not SQLITE_PATH.exists():
        return None
    try:
        # Connect in read-only mode to avoid interfering with the writer
        conn = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)
        cursor = conn.execute("SELECT wall_ns, payload FROM latest_state WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[1])
    except Exception:
        pass
    return None

@app.get("/health", response_model=HealthStatus)
async def health():
    latest = get_latest_from_cache()
    return {
        "status": "online",
        "last_sample_ts": latest.get("timestamps", {}).get("wall_ns") if latest else None
    }

@app.get("/latest")
async def latest():
    latest_data = get_latest_from_cache()
    if not latest_data:
        return {"error": "No data available"}
    return latest_data

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        import asyncio
        last_sent_ts = 0
        while True:
            latest = get_latest_from_cache()
            if latest:
                current_ts = latest.get("timestamps", {}).get("wall_ns", 0)
                if current_ts > last_sent_ts:
                    await websocket.send_json(latest)
                    last_sent_ts = current_ts
            # Poll interval — in a production scenario, we might use
            # SQLite's update notifications or a shared event.
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
