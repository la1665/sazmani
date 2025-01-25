# import asyncio
# import signal
# import sys

# from settings import settings
# from nats_consumer.nats_setup import create_ssl_context, connect_to_nats_server, setup_jetstream_stream
# from nats_consumer.auth import authenticate_client
# from nats_consumer.handlers import (
#     handle_lpr_settings_request,
#     handle_plates_data,
# )
# from nats_consumer.record_handling import handle_recording


# async def main():
#     # Create an SSL context
#     ssl_ctx = await create_ssl_context(
#         settings.NATS_CA_PATH,
#         settings.NATS_CERT_PATH,
#         settings.NATS_KEY_PATH
#     )

#     # Connect to NATS
#     nc = await connect_to_nats_server(ssl_ctx)

#     # Define handlers for JetStream subscriptions
#     async def on_plates_data(msg):
#         try:
#             await handle_plates_data(msg, nc)
#         except Exception as e:
#             print(f"Error handling plates_data: {e}")

#     async def on_lpr_settings_request(msg):
#         try:
#             await handle_lpr_settings_request(msg, nc)
#         except Exception as e:
#             print(f"Error handling lpr_settings_request: {e}")

#     # Set up subscriptions
#     try:
#         # Subscribe to LPR settings requests
#         await nc.subscribe("alpr.settings.request", cb=on_lpr_settings_request)
#         print("Subscribed to 'alpr.settings.request'.")

#         # Subscribe to authentication subject
#         await nc.subscribe("authenticate", cb=authenticate_client)
#         print("Subscribed to 'authenticate' subject.")

#         # Subscribe to messages for general handling
#         await nc.subscribe("message.recording.*", cb=handle_recording)
#         print("Subscribed to 'recording.*' subject pattern.")

#         # Access JetStream and ensure the stream is set up
#         js = nc.jetstream()
#         await setup_jetstream_stream(js)

#         # Subscribe to plates_data from JetStream
#         await js.subscribe(
#             "messages.plates_data",
#             durable="plates_consumer",
#             cb=on_plates_data,
#         )
#         print("Subscribed to 'messages.plates_data' with JetStream.")
#     except Exception as e:
#         print(f"Subscription setup failed: {e}")
#         await nc.drain()
#         return

#     # Keep the application running until terminated
#     stop_event = asyncio.Event()

#     async def shutdown():
#         print("Shutting down...")
#         stop_event.set()
#         await nc.drain()  # Gracefully close NATS connection

#     # Platform-specific signal handling
#     if sys.platform == "win32":
#         print("Windows detected: Using manual signal handling.")
#         loop = asyncio.get_running_loop()

#         def handle_signal():
#             loop.create_task(shutdown())

#         signal.signal(signal.SIGINT, lambda s, f: handle_signal())
#         signal.signal(signal.SIGTERM, lambda s, f: handle_signal())
#     else:
#         print("POSIX detected: Using asyncio signal handling.")
#         loop = asyncio.get_running_loop()
#         for sig in (signal.SIGINT, signal.SIGTERM):
#             loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

#     # Wait for stop_event to be set
#     await stop_event.wait()


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("Application stopped.")
