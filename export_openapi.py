import json
import subprocess
import os
from main import app
from export_ws_schema import export_ws_schema
# Import the new WebSocket schemas so they appear in the OpenAPI spec
from app.schemas.websocket import WsServerMessage, OnlineUsersPayload

def export_openapi():
    # Set server URL for production if needed, or leave default
    openapi_schema = app.openapi()

    # Import all payload models
    from app.schemas.websocket import (
        WsServerMessage,
        OnlineUsersPayload,
        AckSendMessagePayload,
        ReceiveMessagePayload,
        TypingBroadcastPayload,
        MessageStatusBroadcastPayload,
        PresenceBroadcastPayload,
        AckEditMessagePayload,
        ReceiveEditMessagePayload,
        AckDeleteMultipleMessagesPayload,
        ReceiveDeleteMultipleMessagesPayload,
        ErrorPayload,
    )

    # Ensure the new schemas are added to components
    components = openapi_schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    # Add schemas for each payload class
    schemas["WsServerMessage"] = WsServerMessage.model_json_schema()
    schemas["OnlineUsersPayload"] = OnlineUsersPayload.model_json_schema()
    schemas["AckSendMessagePayload"] = AckSendMessagePayload.model_json_schema()
    schemas["ReceiveMessagePayload"] = ReceiveMessagePayload.model_json_schema()
    schemas["TypingBroadcastPayload"] = TypingBroadcastPayload.model_json_schema()
    schemas["MessageStatusBroadcastPayload"] = MessageStatusBroadcastPayload.model_json_schema()
    schemas["PresenceBroadcastPayload"] = PresenceBroadcastPayload.model_json_schema()
    schemas["AckEditMessagePayload"] = AckEditMessagePayload.model_json_schema()
    schemas["ReceiveEditMessagePayload"] = ReceiveEditMessagePayload.model_json_schema()
    schemas["AckDeleteMultipleMessagesPayload"] = AckDeleteMultipleMessagesPayload.model_json_schema()
    schemas["ReceiveDeleteMultipleMessagesPayload"] = ReceiveDeleteMultipleMessagesPayload.model_json_schema()
    schemas["ErrorPayload"] = ErrorPayload.model_json_schema()


    # Save JSON
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("OpenAPI schema exported to openapi.json")

    # Skipping TypeScript generation to avoid schema resolution issues
    # print("Generating TypeScript types...")
    # try:
    #     result = subprocess.run(
    #         ["npx", "openapi-typescript", "openapi.json", "-o", "schema.ts"],
    #         check=True,
    #         shell=True,
    #         capture_output=True,
    #         text=True
    #     )
    #     print(result.stdout)
    #     print("TypeScript types generated in schema.ts")
    # except subprocess.CalledProcessError as e:
    #     print(f"Error generating TypeScript types: {e.stderr}")
    # except Exception as e:
    #     print(f"An unexpected error occurred: {e}")

    # Generate WebSocket types
    try:
        export_ws_schema()
    except Exception as e:
        print(f"Error generating WebSocket types: {e}")

if __name__ == "__main__":
    export_openapi()
 