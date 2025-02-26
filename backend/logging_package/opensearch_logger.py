import logging
from opensearchpy import OpenSearch
from datetime import datetime
import os

from settings import settings

class OpenSearchHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.client = OpenSearch(
            hosts=[{
                'host': settings.OPENSEARCH_HOST,
                'port': settings.OPENSEARCH_PORT
            }],
            http_auth=(
                settings.OPENSEARCH_USER,
                settings.OPENSEARCH_PASSWORD
            ),
            use_ssl=False,
            verify_certs=False,
            timeout=30  # Add timeout
        )
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        try:
            if not self.client.indices.exists(index=settings.OPENSEARCH_INDEX):
                self.client.indices.create(
                    index=settings.OPENSEARCH_INDEX,
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "index.refresh_interval": "30s"
                        },
                        # Keep existing mappings...
                    }
                )
        except Exception as e:
            print(f"OpenSearch index creation failed: {str(e)}")
