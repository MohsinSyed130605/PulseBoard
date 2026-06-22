const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  platform: process.platform,     // 'win32' | 'darwin' | 'linux'
  version:  process.versions.electron,
  minimize: () => ipcRenderer.send('win-minimize'),
  maximize: () => ipcRenderer.send('win-maximize'),
  close:    () => ipcRenderer.send('win-close'),
  onWindowStateChanged: (callback) => {
    ipcRenderer.on('window-state-changed', (event, state) => callback(state));
  }
});
