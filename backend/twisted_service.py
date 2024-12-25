import asyncio
import sys
from threading import Thread
from twisted.internet import asyncioreactor

# Ensure no pre-existing reactor is loaded
if "twisted.internet.reactor" in sys.modules:
    del sys.modules["twisted.internet.reactor"]

# Install the asyncio reactor for Twisted
try:
    asyncioreactor.install()
    print("[INFO] Twisted reactor installed successfully.")
except RuntimeError:
    print("[WARN] Reactor already installed.")

from twisted.internet import reactor
from twisted.internet.defer import ensureDeferred
from twisted.internet.error import ReactorNotRunning
from sqlalchemy.future import select

from database.engine import twisted_session
from models.lpr import DBLpr
from tcp.tcp_client import ReconnectingTCPClientFactory
from shared_resources import connections


async def fetch_and_connect_lprs():
    """Fetch LPRs from the database and connect them."""
    try:
        # Ensure we have an event loop
        loop = asyncio.get_running_loop()
        print(f"[INFO] Running on event loop: {loop}")

        # Fetch LPRs from the database
        async with twisted_session() as session:
            query = await session.execute(select(DBLpr).order_by(DBLpr.id))
            lprs = query.unique().scalars().all()

            if not lprs:
                print("[INFO] No LPR objects found, returning ...")
                return

            # Create connections for active LPRs
            for lpr in lprs:
                if lpr.is_active:
                    if lpr.id in connections:
                        print(f"[INFO] Connection for LPR ID {lpr.id} already exists")
                        continue

                    factory = ReconnectingTCPClientFactory(
                        lpr_id=lpr.id,
                        server_ip=lpr.ip,
                        port=lpr.port,
                        auth_token=lpr.auth_token
                    )
                    factory._attempt_reconnect()
                    connections[lpr.id] = factory
                    print(f"[INFO] Added connection for LPR ID {lpr.id}")
            print(f"[INFO] All connections: {connections.keys()}")
    except Exception as e:
        print(f"[ERROR] An error occurred while fetching and connecting LPRs: {e}")


def start_event_loop():
    """Start the asyncio event loop for Twisted."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(fetch_and_connect_lprs())
    print("[INFO] Starting asyncio event loop.")
    try:
        reactor.run(installSignalHandlers=False)
    except KeyboardInterrupt:
        print("[INFO] Reactor stopping due to KeyboardInterrupt.")
        try:
            reactor.stop()
        except ReactorNotRunning:
            pass
    finally:
        print("[INFO] Closing asyncio event loop.")
        loop.close()


if __name__ == "__main__":
    # Run the Twisted service with a dedicated event loop
    loop_thread = Thread(target=start_event_loop, daemon=True)
    loop_thread.start()

    # Keep the main thread alive while the loop runs
    try:
        loop_thread.join()
    except KeyboardInterrupt:
        print("[INFO] Shutting down the Twisted service.")
