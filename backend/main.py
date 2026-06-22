import os
import sqlite3
import time
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import docker
import psutil
from typing import Optional

app = FastAPI(title="PulseBoard Backend API", version="3.0.0")

# CORS — restrict to known local origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:4321",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:4321",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub token — read from environment, never stored in the database
GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")

# API Key — if set, all non-public endpoints require X-API-Key header
# Leave empty to disable auth in local dev mode
API_KEY: str = os.environ.get("PULSEBOARD_API_KEY", "")

def check_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Validate X-API-Key header. Skips when PULSEBOARD_API_KEY is empty (dev mode)."""
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Set X-API-Key header.")

# SQLite — path from env var, falls back to backend/settings.db
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "settings.db"))

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # github_token is intentionally NOT stored — use GITHUB_TOKEN env var
    defaults = [
        ("github_repo", ""),
        ("refresh_interval", "5"),
        ("backend_url", "http://localhost:8000"),
        ("docker_host", ""),
    ]
    for key, value in defaults:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

init_db()

class SettingsModel(BaseModel):
    github_repo: str
    refresh_interval: str
    backend_url: str
    docker_host: str = ""

# Public endpoints — no auth required
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "3.0.0"}

@app.get("/")
def root():
    return {"message": "PulseBoard Backend API v3.0.0", "docs": "/docs", "health": "/health"}

# Settings
@app.get("/api/settings", dependencies=[Depends(check_api_key)])
def get_settings():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM settings")
        rows = cursor.fetchall()
        conn.close()
        return {row["key"]: row["value"] for row in rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings", dependencies=[Depends(check_api_key)])
def save_settings(settings: SettingsModel):
    try:
        interval = int(settings.refresh_interval)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="refresh_interval must be a number")
    interval = max(1, min(60, interval))
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('github_repo', ?)", (settings.github_repo,))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('refresh_interval', ?)", (str(interval),))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('backend_url', ?)", (settings.backend_url,))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('docker_host', ?)", (settings.docker_host,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# System metrics
@app.get("/api/system-metrics", dependencies=[Depends(check_api_key)])
def get_system_metrics():
    """Real host metrics via psutil."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_ghz = round(cpu_freq.current / 1000, 2) if cpu_freq else None
        vm = psutil.virtual_memory()
        du = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        process_count = len(psutil.pids())
        uptime_secs = int(time.time() - psutil.boot_time())
        uptime_str = f"{uptime_secs // 3600}h {(uptime_secs % 3600) // 60}m"
        return {
            "cpu": round(cpu_percent, 1),
            "memory": round(vm.percent, 1),
            "disk": round(du.percent, 1),
            "cpuText": f"{cpu_count} Cores" + (f" @ {cpu_freq_ghz} GHz" if cpu_freq_ghz else ""),
            "memText": f"{round(vm.used/(1024**3),1)}GB / {round(vm.total/(1024**3),1)}GB",
            "memAvailable": f"{round(vm.available/(1024**3),1)}GB free",
            "diskText": f"{round(du.used/(1024**3),1)}GB / {round(du.total/(1024**3),1)}GB",
            "diskFree": f"{round(du.free/(1024**3),1)}GB free",
            "netSentMB": round(net.bytes_sent / (1024**2), 1),
            "netRecvMB": round(net.bytes_recv / (1024**2), 1),
            "processCount": process_count,
            "uptime": uptime_str,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to read system metrics", "reason": str(e)})

# Docker helpers
def _get_docker_client():
    """Return a Docker client from settings, or raise HTTP 503."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key='docker_host'")
        row = cursor.fetchone()
        conn.close()
        docker_host = row[0] if row else ""
        client = (
            docker.DockerClient(base_url=docker_host.strip())
            if docker_host and docker_host.strip() and docker_host.strip().lower() != "local"
            else docker.from_env()
        )
        client.ping()
        return client
    except Exception as e:
        raise HTTPException(status_code=503, detail={
            "error": "Docker daemon unreachable",
            "reason": str(e),
            "fix": "Mount the Docker socket: '-v /var/run/docker.sock:/var/run/docker.sock:ro' or configure a remote Docker Host URL in Settings."
        })

# Containers
@app.get("/api/containers", dependencies=[Depends(check_api_key)])
def list_containers():
    """List all Docker containers visible via the mounted socket."""
    client = _get_docker_client()
    result = []
    for c in client.containers.list(all=True):
        state_obj = c.attrs.get("State", {})
        ports = c.attrs.get("NetworkSettings", {}).get("Ports", {})
        port_list = [
            f"{hb['HostPort']}→{cp}"
            for cp, hbs in ports.items() if hbs
            for hb in hbs
        ]
        cpu_pct = mem_pct = mem_usage_mb = None
        if c.status == "running":
            try:
                stats = c.stats(stream=False)
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                sys_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
                num_cpus = stats["cpu_stats"].get("online_cpus") or len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
                if sys_delta > 0 and cpu_delta > 0:
                    cpu_pct = round((cpu_delta / sys_delta) * num_cpus * 100, 1)
                mem_usage = stats["memory_stats"].get("usage", 0)
                mem_limit = stats["memory_stats"].get("limit", 1)
                mem_usage_mb = round(mem_usage / (1024**2), 1)
                mem_pct = round((mem_usage / mem_limit) * 100, 1)
            except Exception:
                pass
        result.append({
            "id": c.short_id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.id[:19],
            "state": c.status,
            "status": state_obj.get("Status", "unknown"),
            "uptime": "Running" if c.status == "running" else state_obj.get("FinishedAt", "N/A"),
            "ports": port_list,
            "cpuPct": cpu_pct,
            "memPct": mem_pct,
            "memMB": mem_usage_mb,
        })
    return {"containers": result, "live": True, "count": len(result)}

@app.post("/api/containers/{container_name}/start", dependencies=[Depends(check_api_key)])
def start_container(container_name: str):
    client = _get_docker_client()
    try:
        client.containers.get(container_name).start()
        return {"status": "started", "container": container_name}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/containers/{container_name}/stop", dependencies=[Depends(check_api_key)])
def stop_container(container_name: str):
    client = _get_docker_client()
    try:
        client.containers.get(container_name).stop(timeout=10)
        return {"status": "stopped", "container": container_name}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/containers/{container_name}/restart", dependencies=[Depends(check_api_key)])
def restart_container(container_name: str):
    client = _get_docker_client()
    try:
        client.containers.get(container_name).restart(timeout=10)
        return {"status": "restarted", "container": container_name}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/containers/{container_name}/logs", dependencies=[Depends(check_api_key)])
def get_container_logs(container_name: str, tail: int = 100):
    """Fetch the last N lines of container logs."""
    client = _get_docker_client()
    try:
        c = client.containers.get(container_name)
        raw_logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        lines = [l for l in raw_logs.splitlines() if l.strip()]
        return {"container": container_name, "lines": lines, "tail": tail}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Images
@app.get("/api/images", dependencies=[Depends(check_api_key)])
def list_images():
    """List all local Docker images with size, tags and creation date."""
    client = _get_docker_client()
    result = [
        {
            "id": img.short_id.replace("sha256:", ""),
            "tags": img.tags or ["<none>:<none>"],
            "sizeMB": round(img.attrs.get("Size", 0) / (1024**2), 1),
            "created": img.attrs.get("Created", "")[:10],
        }
        for img in client.images.list(all=False)
    ]
    result.sort(key=lambda x: (x["tags"][0] == "<none>:<none>", -x["sizeMB"]))
    return {"images": result, "count": len(result)}

@app.delete("/api/images/{image_id}", dependencies=[Depends(check_api_key)])
def remove_image(image_id: str, force: bool = False):
    """Remove a Docker image by short ID or tag."""
    client = _get_docker_client()
    try:
        client.images.remove(image_id, force=force)
        return {"status": "removed", "image": image_id}
    except docker.errors.ImageNotFound:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found")
    except docker.errors.APIError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PullImageModel(BaseModel):
    repository: str

@app.post("/api/images/pull", dependencies=[Depends(check_api_key)])
def pull_image(body: PullImageModel):
    """Pull a Docker image from a registry."""
    client = _get_docker_client()
    try:
        parts = body.repository.rsplit(":", 1)
        img = client.images.pull(parts[0], tag=parts[1] if len(parts) == 2 else "latest")
        return {"status": "pulled", "id": img.short_id, "tags": img.tags}
    except docker.errors.APIError as e:
        raise HTTPException(status_code=400, detail=str(e.explanation or str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/images/prune", dependencies=[Depends(check_api_key)])
def prune_images():
    """Remove all dangling (untagged) images and return space reclaimed."""
    client = _get_docker_client()
    try:
        result = client.images.prune()
        space_mb = round(result.get("SpaceReclaimed", 0) / (1024**2), 1)
        deleted = [d.get("Deleted") or d.get("Untagged") for d in (result.get("ImagesDeleted") or [])]
        return {"status": "pruned", "spaceReclaimedMB": space_mb, "deleted": [d for d in deleted if d]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/prune", dependencies=[Depends(check_api_key)])
def prune_system():
    """Prune all unused Docker resources and return space reclaimed."""
    client = _get_docker_client()
    try:
        c_res = client.containers.prune()
        i_res = client.images.prune()
        v_res = client.volumes.prune()
        n_res = client.networks.prune()
        space_bytes = i_res.get("SpaceReclaimed", 0) + v_res.get("SpaceReclaimed", 0)
        return {
            "status": "success",
            "reclaimedMB": round(space_bytes / (1024**2), 1),
            "containers": len(c_res.get("ContainersDeleted") or []),
            "images": len(i_res.get("ImagesDeleted") or []),
            "volumes": len(v_res.get("VolumesDeleted") or []),
            "networks": len(n_res.get("NetworksDeleted") or []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Failed to prune system", "reason": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
