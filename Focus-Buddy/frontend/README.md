# Focus Buddy Frontend

This folder contains two static frontend pages. They do not require npm, Vite, React, or a build step.

## Files

| File | Purpose |
| --- | --- |
| `family.html` | Family dashboard: live monitor, alert list, elder profile, medication settings, and alarm settings. |
| `elderly.html` | Elder view: large temperature/humidity display, reminders, browser voice output, and AI chat. |

## Backend Requirement

Before opening the pages, start the Python backend:

```powershell
cd C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy
python api_server.py
```

The backend runs at:

```text
http://localhost:8000
```

Both HTML pages already use this address:

```js
const API = 'http://localhost:8000';
```

## How To Open

Double-click:

```text
family.html
elderly.html
```

Or open them from PowerShell:

```powershell
Start-Process "C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy\frontend\family.html"
Start-Process "C:\Users\ROG-PC\Desktop\ENT\Focus-Buddy\frontend\elderly.html"
```

## API Used By The Frontend

| Endpoint | Method | Used for |
| --- | --- | --- |
| `/api/status` | GET | Live temperature, humidity, backend status, and AI alert message. |
| `/api/logs?n=20` | GET | Recent environment logs and alerts. |
| `/api/settings` | GET | Load elder profile, medications, and alarms. |
| `/api/settings` | POST | Save elder profile, medications, and alarms. |
| `/api/chat` | POST | Elder-side AI chat. |

## Voice Output

The elder page uses the browser's built-in Web Speech API:

```js
window.speechSynthesis.speak(...)
```

This means voice output happens in the browser, not inside the Python backend.

## Notes For Frontend Developers

- Do not connect directly to M5Stack from the browser.
- Do not copy or run any separate `api.py` from old zip exports.
- The official local backend is `Focus-Buddy/api_server.py`.
- The frontend should treat `/api/status` and `/api/logs` as the source of truth.
- API keys stay in the local `.env` file and must never appear in frontend code.
