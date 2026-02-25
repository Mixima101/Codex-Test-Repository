# Strategy Simulator Demo

A lightweight dashboard + simulation workflow that supports:

- Launching a simulation from a dashboard strategy via **Simulate**.
- Auto-filling simulation defaults:
  - Trade cost: **$1**
  - Starting amount: **$10,000**
  - End date: **today**
  - Start date: **2 years before today**
- Auto-running simulation when launched from dashboard.
- Adding a validated simulated strategy directly from the simulation page with **Add Strategy to Dashboard**.
- Preserving existing saved strategies in local storage.

## Run locally

```bash
python3 -m http.server 8000
```

Open <http://localhost:8000>.
