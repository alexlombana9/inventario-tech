"""Configuracion de Gunicorn para produccion."""
import multiprocessing
import os

# Server
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "techstock"

# Preload app for faster worker startup
preload_app = True


def post_fork(server, worker):
    """Dispose SQLAlchemy engine after fork to avoid shared connections."""
    from database import engine
    engine.dispose()
