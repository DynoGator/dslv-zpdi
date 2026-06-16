# dslv-zpdi Web Server & Frontend Integration

## Termux Network Interface Constraints

Android/Termux imposes restrictions on `uv_interface_addresses` (Node.js Error 13) which can cause the Vite dev server or the Python FastAPI server to crash if they attempt to bind to `0.0.0.0` or perform dynamic network interface resolution.

### Critical Configuration

The Node/Vite web server (`TheForge_PWA`) and the Python FastAPI backend **must** be strictly configured to bind to `127.0.0.1`.

#### 1. FastAPI Backend (`zpdi_web_server.py`)
Ensure `ZPDI_WEB_HOST` is set to `127.0.0.1` (default).
```bash
# .env
ZPDI_WEB_HOST=127.0.0.1
```

#### 2. Vite Frontend (`TheForge_PWA`)
When running the Vite development server, always force the host to `127.0.0.1`:
```bash
npm run dev -- --host 127.0.0.1
```
Or in `vite.config.ts`:
```typescript
export default defineConfig({
  server: {
    host: '127.0.0.1',
  },
})
```

### Architecture Overview

- **`zpdi_mobile_node.py`**: The metrology daemon. It writes the latest sensor state to `./data/zpdi_cache.db` (SQLite WAL).
- **`zpdi_web_server.py`**: The FastAPI backend. It reads from the SQLite cache to provide:
  - `GET /health`: Daemon status.
  - `GET /latest`: Latest sensor sample.
  - `WS /ws/live`: Real-time sensor stream gateway for the frontend.

This decoupled architecture allows the web server to poll live data without being blocked by the global HDF5 lock used for archival storage.
