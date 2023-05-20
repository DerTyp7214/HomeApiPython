from dataclasses import dataclass
import json
import os
from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import DBSessionMiddleware, db
from starlette.routing import Router

from .sql_app import crud
from .auth_bearer import JWTBearer
from .model import UserLoginSchema, UserSchema

from .routers import main, hue, wled
from .consts import ErrorResponse, origins, version, SQLALCHEMY_DATABASE_URL
from .auth_handler import check_password, decodeJWT, signJWT
from .websocket import manager

app = FastAPI(
    title="Home API",
    description="API for controlling my home",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DBSessionMiddleware, db_url=SQLALCHEMY_DATABASE_URL)

app.include_router(main, prefix="/api")
app.include_router(hue, prefix="/api/hue")
app.include_router(wled, prefix="/api/wled")

dist = os.path.join(os.path.dirname(__file__), "dist")


def check_user(user: UserLoginSchema) -> bool:
    db_user = crud.get_user_by_email(db.session, user.email)
    if db_user is None:
        return False
    if check_password(user.password, db_user.hashed_password):
        return True
    return False


@dataclass
class AuthResponse():
    access_token: str
    token_type: str


@app.post("/api/auth/signup", responses={200: {"model": AuthResponse}, 409: {"model": ErrorResponse}})
def signup(user: UserSchema):
    if crud.get_user_by_email(db.session, user.email) is not None:
        return JSONResponse(status_code=409, content={"error": "Email already exists"})
    if crud.get_user_by_username(db.session, user.username) is not None:
        return JSONResponse(status_code=409, content={"error": "Username already exists"})
    crud.create_user(db.session, user)
    return signJWT(user.email)


@app.post("/api/auth/login", responses={200: {"model": AuthResponse}, 401: {"model": ErrorResponse}})
def login(user: UserLoginSchema):
    if check_user(user):
        return JSONResponse(status_code=200, content=signJWT(user.email))
    return JSONResponse(status_code=401, content={"error": "Invalid credentials"})


def getPackageJson():
    try:
        package_json = os.path.join(os.path.dirname(
            __file__), "..", "..", "package.json")
        with open(package_json, "r") as f:
            return json.load(f)
    except:
        return {"version": version}


@dataclass
class StatusResponse():
    status: str
    version: str


@app.get("/api/status", response_model=StatusResponse)
def get_status():
    return JSONResponse(status_code=200, content={"status": "OK", "version": getPackageJson()["version"]})


@app.get("/api/auth/refresh", response_model=AuthResponse)
def refresh(token: str = Depends(JWTBearer())):
    decoded = decodeJWT(token)
    if decoded is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    email = decoded["email"]
    if email is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    return signJWT(email)


@dataclass
class UserResponse():
    email: str


@app.get("/api/auth/me", responses={200: {"model": UserResponse}, 401: {"model": ErrorResponse}})
def me(token: str = Depends(JWTBearer())):
    decoded = decodeJWT(token)
    if decoded is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    email = decoded["email"]
    if email is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    return JSONResponse(status_code=200, content={"email": email})


if os.path.exists(dist):
    static_router = Router()
    static_router.mount(
        "/", StaticFiles(directory=dist, html=True), name="dist")
    app.mount("/static", static_router, name="static")

    @app.get("/")
    def root():
        return RedirectResponse(url="/static")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    if not JWTBearer().verify_jwt(token):
        await websocket.close()
        return
    await manager.connect(websocket, token)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, token)
