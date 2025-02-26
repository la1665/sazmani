import logging
from logging_package.opensearch_logger import OpenSearchHandler
from settings import settings

def logging_main():
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create OpenSearch handler
    opensearch_handler = OpenSearchHandler()
    opensearch_handler.setFormatter(formatter)
    opensearch_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(opensearch_handler)

    # Configure specific loggers
    api_logger = logging.getLogger("api_logs")
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(opensearch_handler)

    # Add file handler if in development
    if settings.ENV == "development":
        file_handler = logging.FileHandler(f"{settings.LOG_DIR}/app.log")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        api_logger.addHandler(file_handler)
