from typing import Any, Optional
from fastapi.responses import JSONResponse

def success_response(data: Any = None, message: str = "Success", status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status": status_code,
            "message": message,
            "data": data
        }
    )

def error_response(message: str, code: str, details: Any = None, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status": status_code,
            "message": message,
            "error": {
                "code": code,
                "details": details
            }
        }
    )
