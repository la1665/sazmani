from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.security.utils import get_authorization_scheme_param

from database.engine import get_db
from auth.authorization import get_current_user
from logging_package.user_logging import get_user_from_token
import logging
import time
import uuid
import json

logger = logging.getLogger("api_logs")

class CentralizedLoggingMiddleware(BaseHTTPMiddleware):
    SENSITIVE_KEYS = {"password", "api_key", "token"}
    SLOW_REQUEST_THRESHOLD = 2.0  # Threshold for slow requests in seconds
    MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB

    def __init__(self, app, api_prefix: str = "/v1/"):
        super().__init__(app)
        self.api_prefix = api_prefix

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(self.api_prefix):
            # Generate a correlation ID for the request
            correlation_id = str(uuid.uuid4())
            request.state.correlation_id = correlation_id

            start_time = time.time()
            user_info = "Anonymous"
            action = self.infer_action(request)

            # Extract user information from the token, if available
            auth_header = request.headers.get("Authorization")
            if auth_header:
                scheme, token = get_authorization_scheme_param(auth_header)
                if scheme.lower() == "bearer" and token:
                    db_generator = get_db()
                    try:
                        db_session = await db_generator.__anext__()
                        user = await get_user_from_token(token, db_session)
                        # user = await get_current_user(token=token)
                        if user:
                            user_info = f"User {user.username} (ID: {user.id})"
                    except Exception as e:
                        logger.error(f"[{correlation_id}] Error retrieving user: {e}", exc_info=True)

            # Log the incoming request
            await self.log_request(request, user_info, action, correlation_id)

            try:
                response = await call_next(request)
                response_status = response.status_code
            except Exception as e:
                response_status = 500
                logger.error(f"[{correlation_id}] Unhandled exception: {e}", exc_info=True)
                raise

            # Log the response details
            duration = time.time() - start_time
            self.log_response(request, response, user_info, action, correlation_id, duration, response_status)

            return response
        else:
            return await call_next(request)

    @staticmethod
    def infer_action(request: Request) -> str:
        """Determine the action type based on the HTTP method and URL path."""
        if "/login" in request.url.path and request.method == "POST":
            return "Login"
        if "/change-password" in request.url.path and request.method == "PUT":
            return "Change Password"
        if request.method == "POST":
            return f"Creating resource at {request.url.path}"
        elif request.method == "PUT":
            return f"Updating resource at {request.url.path}"
        elif request.method == "DELETE":
            return f"Deleting resource at {request.url.path}"
        elif request.method == "GET":
            return f"Fetching resource from {request.url.path}"
        return "Unknown action"

    async def log_request(self, request: Request, user_info: str, action: str, correlation_id: str):
        """Log details of the incoming request, masking sensitive data."""
        client_details = self.get_client_details(request)
        query_params = dict(request.query_params)
        try:
            body = await self.get_request_body(request)
            masked_body = self.mask_sensitive_data(body)
            request_size = len(json.dumps(masked_body).encode("utf-8"))
            logger.info(
                f"[{correlation_id}] {user_info} is performing action: {action} "
                f"with query params: {query_params}, payload: {masked_body}, size: {request_size} bytes {client_details}"
            )
            if request_size > self.MAX_PAYLOAD_SIZE:
                logger.warning(f"[{correlation_id}] Large request payload: {request_size} bytes")
        except Exception:
            logger.warning(f"[{correlation_id}] Failed to parse request payload {client_details}")

    def log_response(self, request: Request, response, user_info: str, action: str, correlation_id: str, duration: float, response_status: int):
        """Log details of the response."""
        client_details = f"from IP {request.client.host}"
        response_size = len(response.body) if hasattr(response, "body") else 0
        logger.info(
            f"[{correlation_id}] {user_info} completed action: {action} "
            f"Response: status={response_status}, size: {response_size} bytes, duration={duration:.2f}s {client_details}"
        )
        if response_size > self.MAX_PAYLOAD_SIZE:
            logger.warning(f"[{correlation_id}] Large response payload: {response_size} bytes")
        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(f"[{correlation_id}] Slow request: {duration:.2f}s for {action}")

    @staticmethod
    def get_client_details(request: Request) -> str:
        """Retrieve client User-Agent and IP address."""
        user_agent = request.headers.get("User-Agent", "Unknown User-Agent")
        client_ip = request.client.host
        return f"(User-Agent: {user_agent}, IP: {client_ip})"

    @staticmethod
    async def get_request_body(request: Request) -> dict:
        """Retrieve and cache the request body as a dictionary."""
        if not hasattr(request.state, "cached_body"):
            request.state.cached_body = await request.body()
        try:
            return json.loads(request.state.cached_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def mask_sensitive_data(self, data: dict) -> dict:
        """Recursively mask sensitive fields in the data."""
        if isinstance(data, dict):
            return {
                key: self.mask_sensitive_data(value) if key not in self.SENSITIVE_KEYS else "****"
                for key, value in data.items()
            }
        if isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        return data
