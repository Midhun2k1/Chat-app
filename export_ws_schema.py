import json
import subprocess
import os
from fastapi import FastAPI
from typing import List, Union

from app.schemas.websocket import (
    WsClientMessage, 
    WsServerMessage,
    SendMessagePayload,
    TypingPayload,
    MessageStatusPayload,
    PresencePayload,
    EditMessagePayload,
    DeleteMessagePayload,
    AckSendMessagePayload,
    ReceiveMessagePayload,
    TypingBroadcastPayload,
    MessageStatusBroadcastPayload,
    PresenceBroadcastPayload,
    AckEditMessagePayload,
    ReceiveEditMessagePayload,
    AckDeleteMessagePayload,
    ReceiveDeleteMessagePayload,
    ErrorPayload
)

def export_ws_schema():
    app = FastAPI(title="WebSocket Schema")

    # We add dummy endpoints just to trigger the schema generation for these models
    @app.post("/client-message", response_model=WsClientMessage)
    async def client_msg(): pass

    @app.post("/server-message", response_model=WsServerMessage)
    async def server_msg(): pass

    # Also include the individual payloads for easier access in TS if needed
    @app.post("/payloads/send-message", response_model=SendMessagePayload)
    async def p1(): pass

    # ... and so on if we want all of them explicitly named ...
    # But WsClientMessage/WsServerMessage should pull them in anyway via Union

    openapi_schema = app.openapi()

    # Save temporary JSON
    temp_file = "ws_openapi.json"
    with open(temp_file, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print("Generating WebSocket TypeScript types...")
    try:
        result = subprocess.run(
            ["npx", "openapi-typescript", temp_file, "-o", "websocket_schema.ts"], 
            check=True, 
            shell=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("WebSocket TypeScript types generated in websocket_schema.ts")
    except subprocess.CalledProcessError as e:
        print(f"Error generating TypeScript types: {e.stderr}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    export_ws_schema()
 