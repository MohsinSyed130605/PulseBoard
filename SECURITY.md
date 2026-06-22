# Security Policy

## Supported Versions

Only the latest release version receives security updates.

| Version | Supported |
| ------- | --------- |
| v3.x.x  | ✅ Yes     |
| < v3    | ❌ No      |

## Reporting a Vulnerability

If you discover a security vulnerability, please do not disclose it publicly. Report it directly to the project maintainers by opening a private draft security advisory on GitHub or sending an email to the repository owner.

## Security Controls in PulseBoard

1. **Localhost Binding:** By default, the FastAPI backend is configured to bind to `127.0.0.1` so it is not exposed to the public internet unless explicitly set to `0.0.0.0` or proxied.
2. **Docker Socket Read-Only:** When using Docker Compose, the Docker socket (`docker.sock`) is mounted as read-only (`:ro`) to prevent containers from modifying the host Docker daemon settings.
3. **CORS Policies:** CORS is restricted strictly to local dev and production ports (`localhost:8080`, `localhost:4321`, `localhost:3000`).
4. **Credential Security:** Sensitive tokens (e.g., your GitHub Personal Access Token) are saved and queried locally in `localStorage` in the browser. They are never sent to or stored in the database.
5. **Optional API Auth:** An API key can be enabled by setting the `PULSEBOARD_API_KEY` environment variable.
