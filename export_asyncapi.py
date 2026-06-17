import json
from pydantic import TypeAdapter
from app.schemas.websocket import WsClientMessage, WsServerMessage

def generate_asyncapi_spec():
    # 1. Generate JSON Schemas for both wrappers using Pydantic
    client_adapter = TypeAdapter(WsClientMessage)
    client_adapter.rebuild()
    server_adapter = TypeAdapter(WsServerMessage)
    server_adapter.rebuild()
    
    # We set ref_template to target AsyncAPI components
    client_schema = client_adapter.json_schema(ref_template="#/components/schemas/{model}")
    server_schema = server_adapter.json_schema(ref_template="#/components/schemas/{model}")
    
    # 2. Extract nested Pydantic schemas ($defs) to bundle under Components
    components = {}
    if "$defs" in client_schema:
        components.update(client_schema.pop("$defs"))
    if "$defs" in server_schema:
        components.update(server_schema.pop("$defs"))
        
    # Also add the top-level wrappers themselves to components
    components["WsClientMessage"] = client_schema
    components["WsServerMessage"] = server_schema

    # 3. Assemble the AsyncAPI 3.1.0 Spec
    asyncapi_spec = {
        "asyncapi": "3.1.0",
        "info": {
            "title": "Chat Application WebSocket API",
            "version": "1.0.0",
            "description": "Real-time communication events for Chat App",
        },
        "channels": {
            "wsChannel": {
                "address": "/ws",
                "description": "Main WebSocket server gateway",
                "messages": {
                    "WsClientMessage": {
                        "$ref": "#/components/messages/WsClientMessage"
                    },
                    "WsServerMessage": {
                        "$ref": "#/components/messages/WsServerMessage"
                    }
                }
            }
        },
        "operations": {
            "sendClientMessage": {
                "action": "receive",
                "channel": {
                    "$ref": "#/channels/wsChannel"
                },
                "summary": "Send messages from Client to Server",
                "messages": [
                    {
                        "$ref": "#/channels/wsChannel/messages/WsClientMessage"
                    }
                ]
            },
            "receiveServerMessage": {
                "action": "send",
                "channel": {
                    "$ref": "#/channels/wsChannel"
                },
                "summary": "Listen to messages from Server to Client",
                "messages": [
                    {
                        "$ref": "#/channels/wsChannel/messages/WsServerMessage"
                    }
                ]
            }
        },
        "components": {
            "schemas": components,
            "messages": {
                "WsClientMessage": {
                    "payload": {
                        "$ref": "#/components/schemas/WsClientMessage"
                    }
                },
                "WsServerMessage": {
                    "payload": {
                        "$ref": "#/components/schemas/WsServerMessage"
                    }
                }
            }
        }
    }
    
    # Save the output
    output_path = "asyncapi.json"
    with open(output_path, "w") as f:
        json.dump(asyncapi_spec, f, indent=2)
        
    print(f"Generated {output_path} successfully!")

if __name__ == "__main__":
    generate_asyncapi_spec()
