# Contributing to PulseBoard

First off, thank you for considering contributing to PulseBoard! It's people like you who make self-hosted tools so great.

## How Can I Contribute?

### Reporting Bugs
* Ensure the bug was not already reported by searching on GitHub under Issues.
* If you find a new bug, open a new Issue, clearly describing the problem, steps to reproduce, and any logs/screenshots.

### Suggesting Enhancements
* Open a new Issue describing the feature you'd like to see, why it is useful, and how it should work.

### Pull Requests
1. Fork the repository and create your branch from `main`.
2. Install local development dependencies:
   * Backend: `cd backend && pip install -r requirements.txt`
   * Frontend: `cd frontend && npm install`
   * Electron: `cd electron && npm install`
3. Run the services locally to test your changes.
4. Ensure your code is clean and properly formatted.
5. Submit a Pull Request targeting the `main` branch.

## Development Setup

### Backend Dev
```bash
cd backend
python main.py
```
API runs on `http://localhost:8000`.

### Frontend Dev
```bash
cd frontend
npm run dev
```
Dashboard runs on `http://localhost:4321`.
