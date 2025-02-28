import uuid
from redis import asyncio as aioredis
import json
import time
import asyncio

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from settings import settings
import logging

logger = logging.getLogger(__name__)

class HeartbeatManager:
    def __init__(self, emit_to_requested_sids, disconnect_timeout=60):
        # Initialize Redis client and other variables
        self.redis = aioredis.from_url(settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True)
        self.disconnect_timeout = disconnect_timeout  # 5 minutes
        self.client_key_pattern = "heartbeat:*"  # Redis key pattern for heartbeats
        self.emit_to_requested_sids = emit_to_requested_sids


    async def handle_heartbeat(self, message):
        """
        Handles heartbeat messages by updating the client's heartbeat timestamp in Redis.
        """
        lpr_id = message.get("lpr_id")

        # Store the current time as the heartbeat timestamp in Redis with an expiration time
        await self.redis.setex(f"heartbeat:{lpr_id}", 4*self.disconnect_timeout, time.time())
        print(f"Heartbeat updated for client {lpr_id}")

    async def check_disconnected_clients(self):
        """
        Periodically checks Redis for any clients whose heartbeat has expired.
        """
        current_time = time.time()

        # Get all client ids (keys starting with 'heartbeat:')
        client_ids = await self.redis.keys(self.client_key_pattern)

        for client_key in client_ids:
            lpr_id = client_key.split(":")[1]  # Extract lpr_id from the key
            last_heartbeat = await self.redis.get(client_key)

            if last_heartbeat:
                last_heartbeat_time = float(last_heartbeat)
                if current_time - last_heartbeat_time > 20:
                    print(f"Client {lpr_id} is disconnected")

                    # Construct the heartbeat message
                    heartbeat_message = {
                        "messageId": str(uuid.uuid4()),  # Unique message ID
                        "messageType": "heartbeat",  # Message type
                        "lpr_id": lpr_id,  # License plate reader ID
                        "messageBody": {
                            "info": "off"
                        }
                    }

                    # Emit the message using emit_to_requested_sids
                    await self.emit_to_requested_sids(
                        event_name="heartbeat",  # Event name
                        data=json.dumps(heartbeat_message).encode(),  # Data
                        camera_id=None  # Optionally pass camera_id if required
                    )

                    await self.redis.delete(client_key)  # Optionally, remove the client from Redis
                else:
                    await self.redis.setex(f"heartbeat:{lpr_id}", 4 * self.disconnect_timeout, time.time())
