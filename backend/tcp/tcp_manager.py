import threading
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from twisted.internet import reactor
from twisted.internet.error import ReactorNotRunning

from models.lpr import DBLpr
from shared_resources import connections


async def add_connection(session: AsyncSession, lpr_id: int|None):
    """
    Add a new connection for the LPR.
    """
    from tcp.tcp_client import ReconnectingTCPClientFactory
    # global connections
    if lpr_id:
        lpr_query = await session.execute(select(DBLpr).where(DBLpr.id == lpr_id))
        db_lpr = lpr_query.unique().scalar_one_or_none()
        if db_lpr and db_lpr.is_active:
            if lpr_id in connections:
                print(f"[INFO] Connection for LPR ID {lpr_id} already exists")
                return

            factory = ReconnectingTCPClientFactory(db_lpr.id,  db_lpr.ip, db_lpr.port, db_lpr.auth_token)
            reactor.callFromThread(factory._attempt_reconnect)
            connections[db_lpr.id] = factory
            print(f"[INFO] Added connection for LPR ID {db_lpr.id}")
        else:
            print("No lpr object found")
    print(f"all connections: {connections}")



async def update_connection(session: AsyncSession, lpr_id: int):
    """
    Update an existing connection with new settings.
    """
    from tcp.tcp_client import ReconnectingTCPClientFactory
    global connections
    lpr_query = await session.execute(select(DBLpr).where(DBLpr.id == lpr_id))
    db_lpr = lpr_query.unique().scalar_one_or_none()
    if db_lpr and db_lpr.is_active:
        if db_lpr.id in connections:
            await remove_connection(db_lpr.id)  # Remove the old connection

        if db_lpr.id not in connections:
            factory = ReconnectingTCPClientFactory(db_lpr.id,  db_lpr.ip, db_lpr.port, db_lpr.auth_token)
            reactor.callFromThread(factory._attempt_reconnect)
            connections[db_lpr.id] = factory
            print(f"[INFO] Added connection for LPR ID {db_lpr.id}")

        print(f"[INFO] Updated connection for LPR ID {db_lpr.id}")
    else:
        print("No lpr object found")

async def remove_connection(lpr_id: int):
    """
    Remove an existing connection.
    """
    global connections
    if lpr_id in connections:
        factory = connections.pop(lpr_id)
        print(f"[DEBUG] Active reactor: {reactor}")
        print(f"[DEBUG] Reactor is running in thread: {threading.current_thread().name}")

        # Stop reconnection attempts
        reactor.callFromThread(factory.stopTrying)
        # Terminate the active connection (if any)
        if factory.active_protocol and factory.active_protocol.transport:
            print(f"[DEBUG] Terminating connection for lpr ID {lpr_id}")
            reactor.callFromThread(factory.active_protocol.transport.abortConnection)
            print(f"[DEBUG] Connection state after loseConnection: {factory.active_protocol.transport.connected}")
            factory.active_protocol = None
        print(f"[INFO] Removed connection for LPR ID {lpr_id}")
        print(f"all connections: {connections}")
    else:
        return f"No connection found for LPR ID {lpr_id}"


async def shutdown_all_connections():
    """
    Shutdown all active connections.
    """
    try:
        for lpr_id in list(connections.keys()):
            await remove_connection(lpr_id)
        reactor.stop()
        print("[INFO] All connections stopped.")
    except ReactorNotRunning:
        print("[INFO] Reactor is already stopped.")
