from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api import auth_routes, user_routes, chat_routes, chat_ws
from app.db.database import engine, get_db
from app.db import models
from app.schemas.response import StandardResponse
from app.utils.response_utils import error_response, success_response


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        message=str(exc.detail),
        code="HTTP_ERROR",
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msgs = []
    for err in errors:
        reason = err.get("ctx", {}).get("reason")
        msg = reason if reason else err["msg"]
        error_msgs.append(msg)

    error_message = "; ".join(error_msgs) if error_msgs else "Validation error"

    return error_response(
        message=error_message,
        code="VALIDATION_ERROR",
        details=errors,
        status_code=422
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return error_response(
        message="An unexpected error occurred",
        code="INTERNAL_SERVER_ERROR",
        details=str(exc),
        status_code=500
    )

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(chat_routes.router)
app.include_router(chat_ws.router)

@app.get("/asyncapi.json")
def get_asyncapi():
    from pydantic import TypeAdapter
    from app.schemas.websocket import WsClientMessage, WsServerMessage
    
    client_adapter = TypeAdapter(WsClientMessage)
    server_adapter = TypeAdapter(WsServerMessage)
    
    client_schema = client_adapter.json_schema(ref_template="#/components/schemas/{model}")
    server_schema = server_adapter.json_schema(ref_template="#/components/schemas/{model}")
    
    components = {}
    if "$defs" in client_schema:
        components.update(client_schema.pop("$defs"))
    if "$defs" in server_schema:
        components.update(server_schema.pop("$defs"))
        
    components["WsClientMessage"] = client_schema
    components["WsServerMessage"] = server_schema

    return {
        "asyncapi": "2.6.0",
        "info": {
            "title": "Chat Application WebSocket API",
            "version": "1.0.0",
            "description": "Real-time communication events for Chat App",
        },
        "channels": {
            "/ws": {
                "description": "Main WebSocket server gateway",
                "publish": {
                    "summary": "Send messages from Client to Server",
                    "operationId": "sendClientMessage",
                    "message": {
                        "$ref": "#/components/schemas/WsClientMessage"
                    }
                },
                "subscribe": {
                    "summary": "Listen to messages from Server to Client",
                    "operationId": "receiveServerMessage",
                    "message": {
                        "$ref": "#/components/schemas/WsServerMessage"
                    }
                }
            }
        },
        "components": {
            "schemas": components
        }
    }

@app.get("/", response_model=StandardResponse[None])
def root():
    return success_response(message="Chat app is running 🚀")


@app.get("/health", response_model=StandardResponse[dict])
def health_check(db: Session = Depends(get_db)):
    try:
        # Perform a quick query to verify the database connection is OK
        db.execute(text("SELECT 1"))
        return success_response(
            data={
                "status": "healthy",
                "database": "connected"
            },
            message="Application and Database are healthy! 🚀"
        )
    except Exception as e:
        return error_response(
            message="Database connection failed",
            code="DATABASE_CONNECTION_ERROR",
            details=str(e),
            status_code=500
        )
