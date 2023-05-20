
from json import dumps, loads
from fastapi import WebSocket


from .sql_app import crud
from .sql_app.database import SessionLocal
from .auth_bearer import JWTBearer
from .auth_handler import decodeJWT
from .consts import WebSocketMessage
from .model import UserSchema


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    def __get_user_from_token__(self, token: str) -> UserSchema | None:
        decoded = decodeJWT(token)
        if decoded is None or JWTBearer().verify_jwt(token) is False:
            return None
        db = SessionLocal()
        user = crud.get_user_by_email(db, decoded["email"])
        if user is None:
            return None
        db.close()
        return user

    async def connect(self, websocket: WebSocket, token: str):
        user = self.__get_user_from_token__(token)
        if user is None:
            await websocket.close()
            return
        if self.active_connections.get(user.username) is None:
            self.active_connections[user.username] = []
        self.active_connections[user.username].append(websocket)
        await websocket.accept()

    def disconnect(self, websocket: WebSocket, token: str):
        user = self.__get_user_from_token__(token)
        if user is None or self.active_connections.get(user.username) is None:
            return
        self.active_connections[user.username].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, token: str):
        user = self.__get_user_from_token__(token)
        for username in self.active_connections:
            if user is not None and username == user.username:
                for connection in self.active_connections[username]:
                    await connection.send_text(message)
            else:
                for connection in self.active_connections[username]:
                    await connection.send_text(dumps({
                        "type": loads(message)["type"],
                        "data": None
                    }))


manager = ConnectionManager()


async def broadcast(message: WebSocketMessage, token: str):
    await manager.broadcast(dumps(message.__dict__), token)
