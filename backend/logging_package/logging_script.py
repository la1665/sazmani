import logging
import os
import asyncio
from dotenv import load_dotenv
import httpx
import logging.config

from settings import settings

def setup_logging():
    """Set up logging configuration dynamically based on environment variables."""
    # Read environment variables
    env = settings.ENV
    log_dir = settings.LOG_DIR
    log_backend = settings.LOG_BACKEND  # Options: file, elasticsearch, splunk, loki

    # Ensure the log directory exists for file logging
    if log_backend == "file":
        os.makedirs(log_dir, exist_ok=True)

    # Logging configuration
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"time": "%(asctime)s", "level": "%(levelname)s", '
                          '"name": "%(name)s", "message": "%(message)s"}',
            },
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            },
        },
        "filters": {
            "sensitive_data": {
                "()": SensitiveDataFilter,
            },
            "slow_operations": {
                "()": SlowOperationFilter,
                "threshold": 2.0,
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(log_dir, "application.log"),
                "formatter": "default",
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 10,
                "encoding": "utf-8",
                "level": "DEBUG",
                "filters": ["sensitive_data", "slow_operations"],
            },
            "elasticsearch": {
                "()": AsyncLoggingHandler,
                "backend": "elasticsearch",
                "hosts": settings.ELASTIC_HOSTS,
                "index": settings.ELASTIC_INDEX,
                "formatter": "json",
                "level": "INFO",
                "filters": ["sensitive_data", "slow_operations"],
            },
            "splunk": {
                "()": AsyncLoggingHandler,
                "backend": "splunk",
                "hosts": [os.getenv("SPLUNK_URL", "http://localhost:8088")],
                "auth_token": os.getenv("SPLUNK_TOKEN", ""),
                "formatter": "json",
                "level": "INFO",
                "filters": ["sensitive_data", "slow_operations"],
            },
            "loki": {
                "()": AsyncLoggingHandler,
                "backend": "loki",
                "hosts": [os.getenv("LOKI_URL", "http://localhost:3100")],
                "labels": '{job="application"}',
                "formatter": "json",
                "level": "INFO",
                "filters": ["sensitive_data", "slow_operations"],
            },
        },
        "loggers": {
            "": {  # This is the root logger
                "level": "DEBUG",  # Ensure it captures all levels
                "handlers": [log_backend],
                "propagate": True,  # Ensure log messages bubble up to the root logger
            },
            "uvicorn": {
                "level": "INFO",  # You might want to adjust this to DEBUG if needed
                "handlers": [log_backend],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": [log_backend],
                "propagate": False,
            },
            "api_logs": {  # This is the logger used in CentralizedLoggingMiddleware
                "level": "DEBUG",  # Ensure it captures all logs
                "handlers": [log_backend],
                "propagate": True,
            },
        },
    }
    print(f"LOG Backend is: <<<<< { log_backend } >>>>>>>>>>>>>>>")
    logging.config.dictConfig(LOGGING_CONFIG)


class AsyncLoggingHandler(logging.Handler):
    """Unified asynchronous logging handler for Elasticsearch, Loki, and Splunk."""

    def __init__(self, backend, hosts, index=None, auth=None, auth_token=None, labels=None):
        """
        :param backend: Logging backend ('elasticsearch', 'loki', 'splunk').
        :param hosts: List of host URLs (e.g., ['http://localhost:9200']).
        :param index: For Elasticsearch, the index name (e.g., 'application_logs').
        :param auth: (username, password) tuple for basic authentication.
        :param auth_token: Token for Splunk HEC.
        :param labels: For Loki, the label set (e.g., '{job="application"}').
        """
        super().__init__()
        self.backend = backend
        self.hosts = hosts
        self.index = index
        self.auth = auth
        self.auth_token = auth_token
        self.labels = labels
        self.client = httpx.AsyncClient()

    async def emit(self, record):
        """Dispatch logs to the appropriate backend."""
        log_entry = self.format(record)
        try:
            if self.backend == "elasticsearch":
                await self._send_to_elasticsearch(log_entry)
            elif self.backend == "loki":
                await self._send_to_loki(log_entry, record)
            elif self.backend == "splunk":
                await self._send_to_splunk(log_entry)
            else:
                print(f"Unsupported backend: {self.backend}")
        except Exception as e:
            print(f"Failed to send log to {self.backend}: {e}")

    async def _send_to_elasticsearch(self, log_entry):
        """Send logs to Elasticsearch."""
        if not self.index:
            raise ValueError("Elasticsearch requires an index name.")
        url = f"{self.hosts[0]}/{self.index}/_doc"
        payload = {"message": log_entry, "level": "INFO"}
        await self.client.post(url, json=payload, auth=self.auth)

    async def _send_to_loki(self, log_entry, record):
        """Send logs to Loki."""
        url = f"{self.hosts[0]}/loki/api/v1/push"
        payload = {
            "streams": [
                {
                    "labels": self.labels,
                    "entries": [{"ts": str(int(record.created * 1e9)), "line": log_entry}],
                }
            ]
        }
        await self.client.post(url, json=payload)

    async def _send_to_splunk(self, log_entry):
        """Send logs to Splunk."""
        if not self.auth_token:
            raise ValueError("Splunk requires an authentication token.")
        url = self.hosts[0]
        headers = {"Authorization": f"Splunk {self.auth_token}"}
        payload = {"event": log_entry}
        await self.client.post(url, json=payload, headers=headers)


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data like passwords and API keys."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = record.msg.replace("password", "****").replace("api_key", "****")
        return True


class SlowOperationFilter(logging.Filter):
    """Filter to log slow operations exceeding a threshold."""
    def __init__(self, threshold=2.0):
        super().__init__()
        self.threshold = threshold

    def filter(self, record):
        return hasattr(record, "duration") and record.duration > self.threshold


def logging_main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("This operation took 3 seconds", extra={"duration": 3})
    logger.warning("Sensitive data warning: api_key=12345")


# if __name__ == "__main__":
#     asyncio.run(main())
