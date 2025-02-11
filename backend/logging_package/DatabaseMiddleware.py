import logging


from starlette.middleware.base import BaseHTTPMiddleware
from database.engine import get_db
from fastapi import Depends
import logging
from starlette.requests import Request


logger = logging.getLogger("api_logs")


class DatabaseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Start the async generator to get the database session
        db_generator = get_db()
        try:
            # Retrieve the first value from the async generator
            db_session = await db_generator.__anext__()
            request.state.db = db_session  # Attach session to request.state
            logger.debug("Database session attached to request.state")
            response = await call_next(request)
        except StopAsyncIteration:
            logger.error("Failed to retrieve database session from get_db")
            raise RuntimeError("Could not retrieve database session")
        finally:
            # Properly close the generator (cleanup)
            #await db_generator.aclose()
            print()
        return response


