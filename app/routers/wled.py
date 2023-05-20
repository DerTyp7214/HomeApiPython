from typing import Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, Response
import requests
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import db
from sqlalchemy.orm import Session

from ..auth_handler import decodeJWT
from ..model import UserSchema
from ..sql_app import crud
from ..auth_bearer import JWTBearer
from ..consts import ErrorResponse, Light, LightState, Wled, WledItem, WledState

router = APIRouter(
    tags=["wled"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(JWTBearer())]
)


class WledReponseState(Wled):
    ip: str
    name: str


def user_by_token(db: Session, token: str) -> Optional[UserSchema]:
    email = (decodeJWT(token) or {}).get("email")
    return crud.get_user_by_email(db, email) if email else None


class LightHandler:
    token: str
    db: Session

    def __init__(self, token: str, db: Session):
        self.token = token
        self.db = db

    def __user_by_token__(self):
        return user_by_token(self.db, self.token)

    def __config_by_token__(self):
        user = user_by_token(self.db, self.token)
        return user.settings if user else None

    def __map_light__(self, light: WledReponseState) -> Light:
        colors = []
        if light.state is not None and light.state.seg is not None:
            for seg in light.state.seg:
                colors.append((seg.col[0], seg.col[1], seg.col[2]))

        return Light(
            id=light.ip,
            name=light.name,
            on=light.state.on is True,
            brightness=light.state.bri if light.state.bri is not None else 0,
            color=colors,
            reachable=True,
            type="Extended color light",
            model="LCT001",
            manufacturer="Philips",
            uniqueid=light.ip,
            swversion="1.0",
            productid=None
        )

    async def __allLights__(self) -> list[WledReponseState]:
        lights = []
        config = self.__config_by_token__()
        if config is None:
            return lights
        for light in config.wled_ips:
            lightResponse = self.__getLight__(light.ip)
            if lightResponse is not None:
                lights.append(lightResponse)

        return lights

    def __getLight__(self, ip: str) -> WledReponseState | None:
        user = self.__user_by_token__()
        if user is None:
            return None
        wled = crud.get_wled(self.db, user.email, ip)
        if wled is None:
            return None

        try:
            response = requests.get(f"http://{ip}/json")

            data: dict = response.json()
            data.update({
                "ip": ip,
                "name": wled.name,
            })
            return WledReponseState.from_dict(data)
        except:
            return None

    def __setLightState__(self, ip: str, state: WledState):
        return requests.post(f"http://{ip}/json/state", json=state.to_dict())

    async def getLights(self):
        lights = []
        for light in await self.__allLights__():
            lights.append(self.__map_light__(light))
        return lights

    def getLight(self, id: str):
        light = self.__getLight__(id)
        if light is None:
            return None
        return self.__map_light__(light)

    def setLightState(self, id: str, state: LightState):
        light = self.__getLight__(id)
        if light is None:
            return None
        new_state = {}
        if state.color is not None:
            new_state["seg"] = []
            for color in state.color:
                new_state["seg"].append({
                    "col": [color[0], color[1], color[2]]
                })
        if state.on is not None:
            new_state["on"] = state.on
        if state.brightness is not None:
            new_state["bri"] = state.brightness
        return self.__setLightState__(id, WledState.from_dict(new_state))


@router.put("/devices/add", responses={401: {"model": ErrorResponse}, 200: {"model": str}})
async def add_device(item: WledItem, token: str = Depends(JWTBearer())):
    user = user_by_token(db.session, token)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    crud.add_wled(db.session, user.email, ip=item.ip, name=item.name)
    return Response(status_code=200)


@router.delete("/devices/remove/{ip}", responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 200: {"model": str}})
async def remove_device(ip: str, token: str = Depends(JWTBearer())):
    user = user_by_token(db.session, token)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    if crud.delete_wled(db.session, user.email, unquote(ip)):
        return Response(status_code=200)
    return JSONResponse(status_code=404, content={"error": "Light not found"})


@router.get("/lights", response_model=list[WledReponseState])
async def lights(token: str = Depends(JWTBearer())):
    lights = await LightHandler(token, db.session).__allLights__()

    return JSONResponse(status_code=200, content=lights)


@router.get("/lights/{ip}", responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 200: {"model": WledReponseState}})
async def light(ip: str, token: str = Depends(JWTBearer())):
    light = LightHandler(token, db.session).__getLight__(ip)

    if light is None:
        return JSONResponse(status_code=404, content={"error": "Light not found"})
    return JSONResponse(status_code=200, content=light)


@router.put("/lights/{ip}/state", responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 200: {"model": WledReponseState}})
async def light_state(ip: str, state: WledState, token: str = Depends(JWTBearer())):
    light_handler = LightHandler(token, db.session)
    response = light_handler.__setLightState__(ip, state)

    light = light_handler.__getLight__(ip)

    if light is None:
        return JSONResponse(status_code=404, content={"error": "Light not found"})

    if response.status_code == 200:
        return JSONResponse(status_code=200, content=light)

    return response
