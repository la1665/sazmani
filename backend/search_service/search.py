from meilisearch import Client
from meilisearch.errors import MeilisearchError
from meilisearch.index import Index
from pydantic import BaseModel
from typing import Type, Generic, TypeVar, Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from redis_cache import redis_cache
from settings import settings


T = TypeVar('T', bound=BaseModel)

class BaseSearchService(Generic[T]):
    def __init__(
        self,
        index_name: str,
        schema_model: Type[T],
        searchable_attributes: List[str],
        filterable_attributes: List[str] = [],
        sortable_attributes: List[str] = [],
        ranking_rules: List[str] = None
    ):
        self.client = Client(
            settings.MEILI_URL,
            settings.MEILI_MASTER_KEY
        )
        self.index_name = index_name
        self.schema_model = schema_model
        self.searchable_attributes = searchable_attributes
        self.filterable_attributes = filterable_attributes
        self.sortable_attributes = sortable_attributes
        self.ranking_rules = ranking_rules or [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ]

    async def _get_index(self) -> Index:
        return self.client.index(self.index_name)

    async def sync_document(self, document: T) -> None:
        try:
            index = await self._get_index()
            # # Convert to JSON-serializable dict
            # doc_data = document.dict()
            # # Handle enums explicitly
            # for field, value in doc_data.items():
            #     if isinstance(value, Enum):
            #         doc_data[field] = value.value
            #     elif isinstance(value, datetime):
            #         doc_data[field] = value.isoformat()  # Convert datetime to ISO format

            # Use jsonable_encoder to convert nested relationships into JSON-serializable format
            doc_data = jsonable_encoder(document)

            index.add_documents([doc_data], primary_key='id')
            await redis_cache.invalidate_model(self.index_name)

        except MeilisearchError as e:
            print(f"Meilisearch sync error for {self.index_name}: {e}")

    async def delete_document(self, doc_id: int) -> None:
        try:
            index = await self._get_index()
            index.delete_document(doc_id)
            await redis_cache.invalidate_model(self.index_name)
        except MeilisearchError as e:
            print(f"Meilisearch delete error for {self.index_name}: {e}")

    async def search(
        self,
        query: str,
        filters: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        highlight: bool = True
    ) -> Dict[str, Any]:
        try:
            if filters and ":" in filters:
                filters = filters.replace(":", "=")

            cache_key = await redis_cache.generate_key(
                self.index_name,
                query,
                filters,
                limit,
                offset
            )

            # Try cache first
            if cached := await redis_cache.get(cache_key):
                return cached

            index = await self._get_index()
            params = {
                "limit": limit,
                "offset": offset,
                "attributesToSearchOn": self.searchable_attributes,
                "filter": filters,
                "attributesToHighlight": ["*"] if highlight else []
            }
            result = index.search(query, params)
            result_data = {
                "items": [jsonable_encoder(self.schema_model(**hit)) for hit in result["hits"]],
                "total": result["estimatedTotalHits"],
                "query": result["query"]
            }
            await redis_cache.set(cache_key, result_data)
            return result_data

        except MeilisearchError as e:
            print(f"Meilisearch search error for {self.index_name}: {e}")
            return {"items": [], "total": 0, "query": query}

    async def initialize_index(self) -> None:
        try:
            if not self.client.get_index(self.index_name):
                self.client.create_index(self.index_name, {'primaryKey': 'id'})

            index = await self._get_index()
            index.update_settings({
                "searchableAttributes": self.searchable_attributes,
                "filterableAttributes": self.filterable_attributes,  # camelCase
                "sortableAttributes": self.sortable_attributes,      # camelCase
                "rankingRules": self.ranking_rules
            })
        except MeilisearchError as e:
            print(f"Meilisearch initialization error for {self.index_name}: {e}")
