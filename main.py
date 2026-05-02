from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api import auth_routes, user_routes, chat_routes, chat_ws
from app.db.database import engine
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

@app.get("/", response_model=StandardResponse[None])
def root():
    return success_response(message="Chat app is running 🚀")
