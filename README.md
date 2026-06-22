<div align="center">

# 🖥️ PulseBoard

**Self-hosted DevOps Control Center**

[![License: MIT](https://img.shields.io/badge/License-MIT-00d4ff?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Astro](https://img.shields.io/badge/Astro-6+-ff5d01?style=flat-square&logo=astro)](https://astro.build)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker)](https://docker.com)

Real-time system metrics · Docker management · GitHub activity — in one beautiful dashboard.

</div>

---

## ✨ Features

- 📊 **System Metrics** — Live CPU, RAM, Disk & Network with sparkline charts
- 🐳 **Docker Management** — Start, stop, restart containers, view live logs
- 🖼️ **Image Manager** — Pull, remove, and prune Docker images
- 📡 **GitHub Activity** — Commits, PRs, issues & releases across multiple repos
- 🔔 **Alert Thresholds** — Browser notifications when metrics exceed custom limits
- 🌗 **Dark / Light Theme** — Smooth toggle with persistence
- 🖥️ **Desktop App** — Native Electron wrapper (Windows, macOS, Linux)
- 🐋 **Docker Compose** — One-command web deployment

---

## 🚀 Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/PulseBoard.git
cd PulseBoard
cp .env.example .env        # add your GITHUB_TOKEN
docker compose up -d
# Open http://localhost:8080
```

**Requirements:** Docker Desktop 24+

### Option 2 — Desktop App (Electron)

```bash
git clone https://github.com/YOUR_USERNAME/PulseBoard.git
cd PulseBoard
npm install --legacy-peer-deps
pip install -r backend/requirements.txt
cd frontend && npm run build && cd ..
cd electron && npm start
```

**Requirements:** Node.js 20+, Python 3.11+, npm 9+

### Option 3 — Development Mode

```bash
# Terminal 1 — Backend
cd backend && pip install -r requirements.txt && python main.py
# API at http://localhost:8000  |  Docs at http://localhost:8000/docs

# Terminal 2 — Frontend
cd frontend && npm install && npm run dev
# Dashboard at http://localhost:4321
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | PAT with `public_repo` (read-only) scope | No — but recommended |
| `PULSEBOARD_API_KEY` | API auth key (leave empty for local dev) | No |
| `DB_PATH` | SQLite path inside container | No |

Additional settings are available in the **Setup Config** tab of the dashboard (backend URL, Docker host, repos to monitor, alert thresholds).

---

## 🏗️ Architecture

```
PulseBoard/
├── backend/          # FastAPI + psutil + docker-py
├── frontend/         # Astro static → Nginx (Docker) or Electron
├── electron/         # Desktop wrapper + auto-spawns backend
├── .github/workflows/release.yml  # Auto-builds installers on git tag
└── docker-compose.yml
```

---

## 📦 Building Releases

Push a version tag to trigger automatic cross-platform builds:

```bash
git tag v3.0.0 && git push origin v3.0.0
```

GitHub Actions produces `.exe` (Windows), `.dmg` (macOS), `.AppImage`/`.deb` (Linux).

---

## 🔒 Security

- Backend port bound to `127.0.0.1` (localhost only)
- GitHub token stored in `localStorage` only — never sent to backend
- CORS restricted to localhost origins
- Docker socket mounted read-only (`:ro`)
- API key auth available via `PULSEBOARD_API_KEY` env var

---

## 📡 API

Swagger UI available at `http://localhost:8000/docs`.

Key endpoints: `/health` · `/api/system-metrics` · `/api/containers` · `/api/images` · `/api/settings`

---

## 📄 License

MIT
