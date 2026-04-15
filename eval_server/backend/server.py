"""
Simple FastAPI server for the Checkpoint Viewer UI.

For development:
  1. Start this server: poetry run python eval_server/backend/server.py
  2. In another terminal: npm run dev
  3. Open http://localhost:3000

For production:
  1. Build the React app: npm run build
  2. Start this server: poetry run python eval_server/backend/server.py
  3. Open http://localhost:8765
"""
from pathlib import Path
from dotenv import load_dotenv

# Project root = wwai_agent_orchestration (where pyproject.toml lives)
# server.py is at eval_server/backend/server.py -> parents[2] = project root
_project_root = Path(__file__).resolve().parents[2]
_env_path = _project_root / ".env"
if load_dotenv(_env_path):
    print(f"Loaded .env from {_env_path}")
else:
    print(f"No .env found at {_env_path} (AWS/S3 may fail if credentials not in environment)")

import os
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from eval_server.backend.routers import get_all_routers
from eval_server.backend.data_providers.router import router as data_debug_router

app = FastAPI(title="LangGraph Checkpoint Viewer")

for r in get_all_routers():
    app.include_router(r)
app.include_router(data_debug_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the React app."""
        index_path = os.path.join(DIST_DIR, "index.html")
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
else:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Development mode - redirect to Vite dev server."""
        return HTMLResponse(content="""
            <html>
                <body style="background:#0d1117;color:#e6edf3;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
                    <div style="text-align:center;">
                        <h1>Checkpoint Viewer API</h1>
                        <p>React build not found. For development:</p>
                        <ol style="text-align:left;">
                            <li>Run <code>npm install</code> in this directory</li>
                            <li>Run <code>npm run dev</code> to start Vite dev server</li>
                            <li>Open <a href="http://localhost:3000" style="color:#58a6ff;">http://localhost:3000</a></li>
                        </ol>
                        <p>For production: run <code>npm run build</code> first.</p>
                    </div>
                </body>
            </html>
        """)


if __name__ == "__main__":
    print("Starting Checkpoint Viewer server at http://localhost:8765 (reload enabled)")
    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=True)
