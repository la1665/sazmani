from fastapi import APIRouter
from typing import Optional

def include_router(
    app,
    router: APIRouter,
    prefix: str = "",
    tags: Optional[list[str]] = None,
    dependencies: Optional[list] = None,
):
    """
    Utility to include a router in the main app.

    Args:
        app: The FastAPI app instance.
        router: The APIRouter instance.
        prefix: The URL prefix for the router (optional).
        tags: Tags for the router (optional).
        dependencies: Global dependencies for the router (optional).
    """
    app.include_router(router, prefix=prefix, tags=tags or [], dependencies=dependencies or [])
