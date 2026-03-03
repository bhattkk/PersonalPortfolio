"""
App-level logging: one log file per service (name + timestamp) under a root logs folder,
with configurable retention (keep N most recent files per service).
Redis and postgres are excluded (no file logging for them).
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def _get_log_dir() -> Path:
    """Log directory from env (app-level); default 'logs' relative to cwd."""
    raw = os.environ.get("LOGS_DIR", "logs")
    p = Path(raw)
    if not p.is_absolute():
        p = Path.cwd().joinpath(p)
    return p


def _get_retention_count() -> int:
    """Max number of log files to keep per service (app-level config)."""
    try:
        return max(1, int(os.environ.get("LOG_RETENTION_COUNT", "5")))
    except ValueError:
        return 5


def _prune_old_logs(log_dir: Path, service_name: str, retention: int) -> None:
    """Keep only the newest `retention` log files for this service; delete the rest."""
    pattern = f"{service_name}_*.log"
    files = sorted(log_dir.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[retention:]:
        try:
            f.unlink()
        except OSError:
            pass


def setup_logging(service_name: str) -> logging.Logger:
    """
    Configure logging for a service: one file per run (service_name_YYYY-MM-DD_HH-MM-SS.log)
    in the app logs directory. Prunes older files so only LOG_RETENTION_COUNT are kept.

    Use for: telegram, kite-portfolio, kite-market-data, stocks-refdata.
    Do not use for: redis, postgres.
    """
    log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    retention = _get_retention_count()

    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"{service_name}_{timestamp}.log"

    print(f"Logging to {log_file}")

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    has_stream = any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    if not has_stream:
        stream = logging.StreamHandler()
        stream.setLevel(logging.INFO)
        stream.setFormatter(logging.Formatter(fmt))
        root.addHandler(stream)

    # Ensure third-party libs (httpx, telegram, etc.) also write to the log file.
    # They may use loggers with propagate=False or attach only StreamHandlers.
    for logger_name in ("httpx", "httpcore", "telegram", "telegram.ext"):
        lib_logger = logging.getLogger(logger_name)
        lib_logger.setLevel(logging.DEBUG)
        if not any(h is file_handler for h in lib_logger.handlers):
            lib_logger.addHandler(file_handler)
        lib_logger.propagate = True

    _prune_old_logs(log_dir, service_name, retention)
    return logging.getLogger(service_name)
