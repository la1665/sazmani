# nats_setup.py

import ssl
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig, StorageType, RetentionPolicy, DiscardPolicy
from nats.aio.errors import ErrNoServers

from settings import settings



async def create_ssl_context(
    ca_path: str,
    cert_path: str,
    key_path: str) -> ssl.SSLContext:
    """
    Create and return an SSL context for secure NATS connections.
    """
    ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ssl_ctx.load_verify_locations(ca_path)
    ssl_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    return ssl_ctx


async def connect_to_nats_server(ssl_ctx: ssl.SSLContext) -> NATS:
    """
    Connect to NATS with provided SSL context and credentials, then return the client instance.
    """
    nc = NATS()
    try:
        await nc.connect(
            servers=[settings.NAT_SERVER],
            user=settings.NATS_USER,
            password=settings.NATS_PASS,
            tls=ssl_ctx,
            tls_hostname=settings.TLS_HOSTNAME,
            max_reconnect_attempts=-1,
            reconnect_time_wait=10,
            disconnected_cb=disconnected_cb,
            reconnected_cb=reconnected_cb,
            error_cb=error_cb,
            closed_cb=closed_cb
        )
        print("[INFO] Connected to NATS server.")
        return nc
    except ErrNoServers as e:
        print(f"[ERROR] Failed to connect to NATS server: {e}")
        return None

async def disconnected_cb():
    print("Disconnected from NATS server.")

async def reconnected_cb():
    print(f"Reconnected to NATS server.")

async def error_cb(e):
    print(f"NATS error: {e}")

async def closed_cb():
    print("Connection to NATS server closed.")

async def setup_jetstream_stream(js) -> None:
    """
    Create (or check) a JetStream stream for plates_data, if not already existing.
    """
    try:
        await js.stream_info("PLATES_STREAM")
        print("Stream 'PLATES_STREAM' already exists.")
    except Exception:
        # Stream does not exist; create it
        try:
            stream_config = StreamConfig(
                name="PLATES_STREAM",
                subjects=["messages.plates_data"],
                storage=StorageType.FILE,
                retention=RetentionPolicy.LIMITS,
                max_msgs=1_000_000,
                max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                discard=DiscardPolicy.OLD,
                num_replicas=1
            )
            await js.add_stream(stream_config)
        except Exception as e:
           print(f"Failed to create stream: {e}")
