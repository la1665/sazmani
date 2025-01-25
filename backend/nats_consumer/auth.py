# auth.py

import json
import jwt
from nats.aio.msg import Msg


async def authenticate_client(msg: Msg) -> None:
    """
    Authenticate the client and assign a client ID.
    Expects a JSON payload with a 'token'.
    """
    try:
        # Parse token from msg
        token_json = json.loads(msg.data.decode())
        token = token_json.get("token")
        if not token:
            print.error("No token found in request data.")
            if msg.reply:
                await msg.respond(json.dumps({"status": "error", "message": "Missing token"}).encode())
            return

        print(f"Received token: {token}")
        #decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        #client_id = decoded_token.get("client_id")
        client_id = "1"

        if not client_id:
            raise ValueError("Invalid token: missing client_id")

        response_data = {"status": "success", "client_id": client_id}
        print(f"Sending authentication response: {response_data}")

        # Respond if reply subject exists
        if msg.reply:
            await msg.respond(json.dumps(response_data).encode())
        else:
            print("No reply subject available. Response not sent.")

    except jwt.ExpiredSignatureError:
        print("Token expired")
        if msg.reply:
            await msg.respond(json.dumps({"status": "error", "message": "Token expired"}).encode())
    except jwt.InvalidTokenError:
        print("Invalid token")
        if msg.reply:
            await msg.respond(json.dumps({"status": "error", "message": "Invalid token"}).encode())
    except Exception as e:
        print(f"Unexpected error during authentication: {e}")
        if msg.reply:
            await msg.respond(json.dumps({"status": "error", "message": str(e)}).encode())
