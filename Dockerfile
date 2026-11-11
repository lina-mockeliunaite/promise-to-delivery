# Public demo image (10 Nov). Build: the frontend, then the API that serves it. No API key goes in the image or the config:
# public mode never calls the model. Set DEALSHAPE_PUBLIC_DEMO=1 and DEALSHAPE_ALLOWED_HOSTS where it runs (render.yaml does).

FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=web /app/frontend/dist frontend/dist
RUN useradd --create-home app && mkdir -p workspace && chown -R app:app /app
USER app

# The disk is wiped on every restart, so the ledger is built at startup from the saved v2 output (no model call, no key).
# One worker, explicitly: the reset lock and the hourly reset job live inside the process, so a second worker would
# have its own lock and its own job and could reset the shared ledger under the first.
CMD ["sh", "-c", "python reset_demo.py && exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
