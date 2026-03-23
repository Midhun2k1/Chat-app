from fastapi import FastAPI
from app.api import auth_routes, user_routes, chat_routes, chat_ws
from app.db.database import engine
from app.db import models


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(chat_routes.router)
app.include_router(chat_ws.router)

@app.get("/")
def root():
    return {"message": "Chat app is running 🚀"}