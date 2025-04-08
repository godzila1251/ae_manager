import os
import uuid
import shutil
import json
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS = []
CLIENTS = {}  # {client_id: {hostname, status, os}}
CONNECTED: Dict[str, WebSocket] = {}
PROJECTS_DIR = "projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

@app.get("/jobs")
def get_jobs():
    return JOBS

@app.get("/clients")
def get_clients():
    return CLIENTS

@app.post("/register")
def register_client(payload: dict):
    client_id = payload.get("client_id")
    if not client_id:
        return JSONResponse(status_code=400, content={"error": "Missing client_id"})

    hostname = payload.get("hostname", "unknown")
    os_type = payload.get("os", "unknown")

    CLIENTS[client_id] = {
        "hostname": hostname,
        "os": os_type,
        "status": "connected"
    }
    return {"status": "registered", "client_id": client_id}

@app.post("/jobs")
def create_job(
    project_file: UploadFile = File(...),
    jsx_file: UploadFile = File(...),
    output_path: str = Form(...),
    assigned_clients: str = Form("")
):
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(PROJECTS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    project_path = os.path.join(job_dir, project_file.filename)
    with open(project_path, "wb") as f:
        shutil.copyfileobj(project_file.file, f)

    jsx_path = os.path.join(job_dir, jsx_file.filename)
    with open(jsx_path, "wb") as f:
        shutil.copyfileobj(jsx_file.file, f)

    client_ids = assigned_clients.split(",") if assigned_clients else []

    job = {
        "id": job_id,
        "project": project_file.filename,
        "project_path": project_path,
        "jsx_path": jsx_path,
        "output_path": output_path,
        "status": "pending",
        "assigned_clients": client_ids,
        "progress": {cid: 0 for cid in client_ids}
    }
    JOBS.append(job)
    return {"job_id": job_id, "status": "created"}

@app.patch("/jobs/{job_id}/progress")
async def update_progress(job_id: str, request: Request):
    try:
        data = await request.json()
        client_id = data.get("client_id")
        percent = data.get("progress")
        for job in JOBS:
            if job["id"] == job_id:
                job["progress"][client_id] = percent
                return {"ok": True}
        return JSONResponse(status_code=404, content={"error": "job not found"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(ws: WebSocket, client_id: str):
    await ws.accept()
    CONNECTED[client_id] = ws
    if client_id in CLIENTS:
        CLIENTS[client_id]["status"] = "connected"
    else:
        # Lazy register fallback
        CLIENTS[client_id] = {
            "hostname": "unknown",
            "os": "unknown",
            "status": "connected"
        }

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        CONNECTED.pop(client_id, None)
        if client_id in CLIENTS:
            CLIENTS[client_id]["status"] = "disconnected"

@app.post("/start_job/{job_id}")
def start_job(job_id: str):
    for job in JOBS:
        if job["id"] == job_id:
            job["status"] = "running"
            for cid in job["assigned_clients"]:
                if cid in CONNECTED:
                    try:
                        data = json.dumps({"action": "start", "job_id": job_id})
                        import asyncio
                        asyncio.create_task(CONNECTED[cid].send_text(data))
                    except Exception:
                        pass
            return {"status": "started", "job_id": job_id}
    return JSONResponse(status_code=404, content={"error": "Job not found"})

@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    global JOBS
    JOBS = [job for job in JOBS if job["id"] != job_id]
    return {"status": "cancelled", "job_id": job_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
