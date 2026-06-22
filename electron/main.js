/**
 * PulseBoard Desktop — Electron Main Process
 *
 * Launches the main window instantly and hosts the pre-built Astro frontend
 * statically on local port 8082, ensuring it loads even when the Docker backend is offline.
 */

const { app, BrowserWindow, Tray, Menu, nativeImage, shell, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const fs   = require('fs');
const { spawn } = require('child_process');

// ─── Constants & Paths ────────────────────────────────────────────────────────
const DASHBOARD_URL = 'http://127.0.0.1:8082';
const BACKEND_URL   = 'http://127.0.0.1:8000';

// In production, files are copied to 'frontend-dist' next to main.js. In dev, we read from '../frontend/dist'.
const STATIC_DIR = fs.existsSync(path.join(__dirname, 'frontend-dist'))
  ? path.join(__dirname, 'frontend-dist')
  : path.resolve(__dirname, '../frontend/dist');

let mainWindow = null;
let tray = null;
let staticServer = null;
let backendProcess = null;

// ─── Local HTTP Server ────────────────────────────────────────────────────────
function startStaticServer() {
  const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
  };

  staticServer = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    if (reqPath === '/') reqPath = '/index.html';

    const filePath = path.join(STATIC_DIR, decodeURIComponent(reqPath));
    const ext = path.extname(filePath).toLowerCase();
    const mime = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
      if (err) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404 Not Found');
      } else {
        res.writeHead(200, { 'Content-Type': mime });
        res.end(content);
      }
    });
  });

  staticServer.listen(8082, '127.0.0.1', () => {
    console.log(`[PulseBoard] Local frontend server running on http://127.0.0.1:8082`);
  });
}

// ─── Main Window ──────────────────────────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 860,
    minWidth: 640,
    minHeight: 480,
    frame: false,            // borderless for a native-app feel
    titleBarStyle: 'hidden',
    backgroundColor: '#070708',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: true,
  });

  mainWindow.loadURL(DASHBOARD_URL);

  // Listen for window state changes and notify renderer
  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window-state-changed', { isMaximized: true });
  });
  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window-state-changed', { isMaximized: false });
  });

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// ─── System Tray ─────────────────────────────────────────────────────────────
function createTray() {
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip('PulseBoard — DevOps Control Center');

  const menu = Menu.buildFromTemplate([
    { label: 'Open Dashboard', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    { label: 'Reload', click: () => mainWindow?.webContents.reload() },
    { type: 'separator' },
    {
      label: 'Open in Browser',
      click: () => shell.openExternal(DASHBOARD_URL)
    },
    { label: 'API Docs (Swagger)', click: () => shell.openExternal(`${BACKEND_URL}/docs`) },
    { type: 'separator' },
    { label: 'Quit PulseBoard', role: 'quit' }
  ]);
  tray.setContextMenu(menu);
  tray.on('double-click', () => { mainWindow?.show(); mainWindow?.focus(); });
}

// ─── Python Path Resolver ─────────────────────────────────────────────────────
function getPythonExecutable() {
  const isWin = process.platform === 'win32';
  if (!isWin) return 'python3';

  // Common Windows Python installation paths to bypass Microsoft Store execution shims
  const paths = [
    'C:\\Python314\\python.exe',
    'C:\\Python313\\python.exe',
    'C:\\Python312\\python.exe',
    'C:\\Python311\\python.exe',
    path.join(process.env.USERPROFILE || '', 'AppData\\Local\\Programs\\Python\\Python314\\python.exe'),
    path.join(process.env.USERPROFILE || '', 'AppData\\Local\\Programs\\Python\\Python313\\python.exe'),
    path.join(process.env.USERPROFILE || '', 'AppData\\Local\\Programs\\Python\\Python312\\python.exe'),
    path.join(process.env.USERPROFILE || '', 'AppData\\Local\\Programs\\Python\\Python311\\python.exe'),
  ];

  for (const p of paths) {
    if (fs.existsSync(p)) {
      console.log(`[PulseBoard] Resolved Python executable to: ${p}`);
      return p;
    }
  }

  // Fallback to path resolution
  return 'python';
}

// ─── Backend Spawning (Plug-and-Play) ─────────────────────────────────────────
function startBackend() {
  const devBackendPath = path.resolve(__dirname, '../backend/main.py');
  const isDev = fs.existsSync(devBackendPath);

  if (isDev) {
    const pythonExe = getPythonExecutable();

    // ─── Ensure dependencies are installed ──────────────────────────────────
    try {
      const { execSync } = require('child_process');
      console.log('[PulseBoard] Checking Python dependencies...');
      // Timeout: 10s — prevents hanging if Python shim is slow
      execSync(`"${pythonExe}" -c "import fastapi, uvicorn, docker, psutil, requests"`, { stdio: 'ignore', timeout: 10000 });
      console.log('[PulseBoard] Python dependencies are satisfied.');
    } catch (e) {
      console.log('[PulseBoard] Missing Python dependencies. Installing via pip...');
      try {
        const { execSync } = require('child_process');
        const reqPath = path.resolve(__dirname, '../backend/requirements.txt');
        // Timeout: 120s — pip install can be slow on first run
        execSync(`"${pythonExe}" -m pip install -r "${reqPath}" --user`, { stdio: 'ignore', timeout: 120000 });
        console.log('[PulseBoard] Python dependencies installed successfully.');
      } catch (err) {
        console.error('[PulseBoard] Auto-installation of Python dependencies failed:', err.message);
      }
    }

    console.log(`[PulseBoard] Spawning backend child process: ${pythonExe} ${devBackendPath}`);
    backendProcess = spawn(pythonExe, [devBackendPath], {
      cwd: path.resolve(__dirname, '../backend'),
      stdio: 'inherit'
    });

    backendProcess.on('error', (err) => {
      console.error('[PulseBoard] Failed to start backend child process:', err);
    });

    backendProcess.on('exit', (code, signal) => {
      console.log(`[PulseBoard] Backend process exited with code ${code} (signal: ${signal})`);
    });
  } else {
    // Package production support (e.g. if bundled via electron-builder ExtraResources)
    const prodBackendPath = path.join(process.resourcesPath, 'backend-dist', 'main.exe');
    if (fs.existsSync(prodBackendPath)) {
      console.log(`[PulseBoard] Spawning production backend: ${prodBackendPath}`);
      backendProcess = spawn(prodBackendPath, [], {
        cwd: path.dirname(prodBackendPath),
        stdio: 'inherit'
      });
    } else {
      console.log(`[PulseBoard] Local Python backend not found at ${devBackendPath}. Assuming backend runs externally.`);
    }
  }
}

// ─── App lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startBackend();
  startStaticServer();
  createMainWindow();
  createTray();
});

app.on('will-quit', () => {
  if (backendProcess) {
    console.log('[PulseBoard] Killing backend child process...');
    backendProcess.kill('SIGTERM');
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
});

// ─── IPC Window Controls ──────────────────────────────────────────────────────
ipcMain.on('win-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('win-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('win-close', () => {
  if (mainWindow) mainWindow.close();
});
