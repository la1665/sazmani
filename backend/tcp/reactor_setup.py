# import sys
# import asyncio
# from twisted.internet import asyncioreactor

# if "twisted.internet.reactor" in sys.modules:
#     del sys.modules["twisted.internet.reactor"]
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# try:
#     asyncioreactor.install(asyncio.get_event_loop())
#     print("[INFO] Twisted reactor installed successfully.")
# except RuntimeError:
#     print("[WARN] Reactor already installed.")
