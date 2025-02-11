import asyncio
import signal

from nats_consumer.nats_setup import create_ssl_context, connect_to_nats_server, setup_jetstream_stream
from nats_consumer.auth import authenticate_client
from nats_consumer.handlers import (
    handle_lpr_settings_request,
    handle_plates_data,
)
from nats_consumer.record_handling import handle_recording
from settings import settings


async def main():
    # Create an SSL context
    ssl_ctx = await create_ssl_context(
        settings.NATS_CA_PATH,
        settings.NATS_CERT_PATH,
        settings.NATS_KEY_PATH
    )

    # Connect to NATS
    nc = await connect_to_nats_server(ssl_ctx)

    # Define handlers for JetStream subscriptions
    async def on_plates_data(msg):
        try:
            await handle_plates_data(msg, nc)
        except Exception as e:
            print(f"Error handling plates_data: {e}")

    async def on_lpr_settings_request(msg):
        try:
            await handle_lpr_settings_request(msg, nc)
        except Exception as e:
            print(f"Error handling lpr_settings_request: {e}")

    # Event for stopping the main loop
    stop_event = asyncio.Event()

    # Enhanced shutdown function
    async def shutdown():
        print("Shutting down...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        # Cancel all tasks except the current one
        for task in tasks:
            task.cancel()

        # Wait for all tasks to finish and handle exceptions gracefully
        await asyncio.gather(*tasks, return_exceptions=True)

        try:
            if nc.is_connected:
                print("Draining NATS connection...")
                await asyncio.wait_for(nc.drain(), timeout=15)
        except asyncio.TimeoutError:
            print("NATS drain timeout.")
        except asyncio.CancelledError:
            print("NATS drain was interrupted.")
        except Exception as e:
            print(f"Error during NATS drain: {e}")
        finally:
            try:
                if nc.is_connected:
                    print("Explicitly closing NATS connection...")
                    await nc.close()
                    print("NATS connection closed.")
            except Exception as close_error:
                print(f"Error during NATS connection close: {close_error}")

        print("Shutdown complete.")

    # Attach signal handlers
    async def handle_signal(sig_name):
        print(f"Received signal {sig_name}, initiating shutdown...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(handle_signal(sig.name)))

    # Set up subscriptions
    try:
        await nc.subscribe("alpr.settings.request", cb=on_lpr_settings_request)
        print("Subscribed to 'alpr.settings.request'.")

        await nc.subscribe("authenticate", cb=authenticate_client)
        print("Subscribed to 'authenticate' subject.")

        await nc.subscribe("message.recording.*", cb=handle_recording)
        print("Subscribed to 'recording.*' subject pattern.")

        js = nc.jetstream()
        await setup_jetstream_stream(js)

        await js.subscribe(
            "messages.plates_data",
            # durable="plates_consumer",
            cb=on_plates_data,
        )
        print("Subscribed to 'messages.plates_data' with JetStream.")
    except Exception as e:
        print(f"Subscription setup failed: {e}")
        await shutdown()
        return

    # Wait for the stop event to be set
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        print("Main event loop canceled.")
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application stopped.")
