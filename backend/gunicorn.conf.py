bind = "0.0.0.0:8000"
workers = 1  # Number of Gunicorn workers
worker_class = "uvicorn.workers.UvicornWorker"  # Use Uvicorn as worker class
worker_connections = 1000  # Maximum simultaneous clients

# Graceful timeout for workers
timeout = 30  # Workers timeout after 30 seconds of inactivity
graceful_timeout = 30  # Timeout for graceful shutdowns
keepalive = 2  # Number of seconds to wait for requests on a Keep-Alive connection


# Logging
accesslog = "-"  # Log access to stdout
errorlog = "-"  # Log errors to stdout
loglevel = "debug"  # Set log level to debug
