# Deploying the public demo on Render

A hosted, read-and-try copy of Dealshape for people you send a link to. It serves two deals (Noma Journeys and Alder Bank), takes only the bundled sample files, never calls the model, and has **no API key anywhere**. Do not add one.

## Before you start
- The repo is on GitHub (or GitLab) and contains `Dockerfile`, `render.yaml` and `.dockerignore`. Pushing is yours to do; the app does nothing with Git.
- A Render account (render.com). The free web service is enough.

## Steps in Render's dashboard
1. **New +** → **Blueprint**.
2. Connect your GitHub account if asked, then choose the repository.
3. Render reads `render.yaml` and shows one service, **dealshape-demo** (Docker, Free). Give the Blueprint a name if it asks.
4. It asks for **DEALSHAPE_ALLOWED_HOSTS**. Enter the service's host name: `dealshape-demo.onrender.com`. (If that name is already taken, Render adds a suffix to the URL; use the host you see on the service page, with no `https://`. You can change it later under **Environment**.)
5. Do **not** add `ANTHROPIC_API_KEY`. `DEALSHAPE_PUBLIC_DEMO` is already set to `1` by the Blueprint.
6. **Apply** (Deploy Blueprint). The first build takes a few minutes: it installs the frontend, builds it, installs Python packages, then starts.
7. When the service says **Live**, open its URL. You should see the thin "Public demo · fictional data · shared with other visitors…" banner above the landing page, and only Noma Journeys and Alder Bank in the deal list.
8. Check it: open a deal, **Add updated document** shows **Use a sample file**, choose one and **Add and check**. Then click **Reset demo** at the bottom of the deal list to put it back.

### If the page says "Invalid host header" (or the deploy never goes Live)
The host in `DEALSHAPE_ALLOWED_HOSTS` does not match the URL. Service → **Environment** → fix the value (comma-separated for more than one, e.g. a custom domain) → **Save**; Render redeploys. The health check (`/api/deals`) also needs the host to be right.

## What runs
The container runs `python reset_demo.py` to build the ledger from the saved v2 output (no model call, about a few seconds), then `uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1`.

### Why exactly one worker
The reset lock and the hourly reset job live inside the process. A second worker would have its own lock and its own job, so two resets could run at once, and the shared ledger could be swapped under a request that another worker was serving. `--workers 1` is set explicitly in the `Dockerfile` for that reason. Do not raise it, and do not scale the service to more than one instance.

## When the demo resets
- **Every hour**, while the service is running: the app restores the sample deals (the same reset as the **Reset demo** button), under the same lock. If a reset is already running, that tick is skipped and the next one tries again.
- **On every start.** The disk is wiped on each restart, so the ledger is rebuilt from scratch at startup. On Render's free plan the service **sleeps after about 15 minutes without a request** and starts again on the next visit (the first load then takes up to about a minute). So in practice the demo is back at its starting point after every sleep, and at least once an hour while it is busy.
- **Anyone can click Reset demo**, which resets it for every visitor. That is by design, and the banner says so.
- Backups: each reset keeps the previous ledger as `ledger.backup-<time>.sqlite`; in public mode only the newest 3 are kept. They are lost on restart with the rest of the disk.

## Visitors share one ledger
Everyone sees the same deals, names and notes. Notes are capped at 500 characters, and the name field says other visitors can see it. A visitor who completes a handover locks that deal for everyone until the next reset.

## Updating
Push to the branch Render watches; it rebuilds and restarts. The ledger is rebuilt on start.

## Running the image yourself
```
docker build -t dealshape-demo .
docker run --rm -p 8000:10000 -e PORT=10000 -e DEALSHAPE_PUBLIC_DEMO=1 -e DEALSHAPE_ALLOWED_HOSTS=localhost dealshape-demo
```
Then open http://localhost:8000. Without `DEALSHAPE_PUBLIC_DEMO=1` the same image runs in the ordinary local mode.
