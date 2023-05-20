from typing import Optional
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import db
from pydantic import BaseModel
import requests
import colorsys
from sqlalchemy.orm import Session


from ..model import UserSchema
from ..auth_handler import decodeJWT
from ..auth_bearer import JWTBearer
from ..consts import ErrorResponse, HueLightResponse, HueLightState, HuePlugResponse, HuePlugState, Light, LightState, Plug, WebSocketMessage
from ..websocket import broadcast
from ..sql_app import crud

router = APIRouter(
    tags=["hue"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(JWTBearer())]
)


def user_by_token(db: Session, token: str) -> Optional[UserSchema]:
    email = (decodeJWT(token) or {}).get("email")
    return crud.get_user_by_email(db, email) if email else None


class LightHandler:
    token: str
    db: Session

    def __init__(self, token: str, db: Session):
        self.token = token
        self.db = db

    def __hsb_to_hsv__(self, hue: float, saturation: float, brightness: float) -> tuple[float, float, float]:
        return (hue/65535*360, saturation/255*100, brightness/255*100)

    def __hsv_to_rgb__(self, hue: float, saturation: float, brightness: float) -> tuple[int, int, int]:
        return tuple(round(i * 255) for i in colorsys.hsv_to_rgb(hue / 360, saturation / 100, brightness / 100))

    def __rgb_to_hsv__(self, red: int, green: int, blue: int) -> tuple[float, float, float]:
        hsv = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        return (hsv[0] * 360, hsv[1] * 100, hsv[2] * 100)

    def __hsv_to_hsb__(self, hue: float, saturation: float, brightness: float) -> tuple[float, float, float]:
        return (hue/360*65535, saturation/100*255, brightness/100*255)

    def __mapLight__(self, bridge_id: str, light, id: int) -> Light | None:
        if "colormode" not in light["state"]:
            return None

        hsv = self.__hsb_to_hsv__(
            light["state"]["hue"],
            light["state"]["sat"],
            light["state"]["bri"]
        )
        rgb = self.__hsv_to_rgb__(hsv[0], hsv[1], hsv[2])

        light = {
            "id": f"hue-{bridge_id}-{id}",
            "name": light["name"],
            "on": light["state"]["on"],
            "brightness": float(light["state"]["bri"]) / 255,
            "color": [rgb],
            "reachable": light["state"]["reachable"],
            "type": light["type"],
            "model": light["modelid"],
            "manufacturer": light["manufacturername"],
            "uniqueid": light["uniqueid"],
            "swversion": light["swversion"],
            "productid": light["productid"]
        }

        return Light.from_dict(light)

    def __mapPlug__(self, bridge_id: str, plug, id: int) -> Plug | None:
        if plug["config"]["archetype"] != "plug":
            return None

        new_plug = {
            "id": f"hue-{bridge_id}-{id}",
            "name": plug["name"],
            "on": plug["state"]["on"],
            "reachable": plug["state"]["reachable"],
            "type": plug["type"],
            "model": plug["modelid"],
            "manufacturer": plug["manufacturername"],
            "uniqueid": plug["uniqueid"],
            "swversion": plug["swversion"],
            "productid": plug["productid"]
        }

        return Plug.from_dict(new_plug)

    def __user_by_token__(self):
        return user_by_token(self.db, self.token)

    def __config_by_token__(self):
        user = user_by_token(self.db, self.token)
        return user.settings if user else None

    def getLightsBride(self, bride_id: str):
        user = self.__user_by_token__()
        bridge = crud.get_hue_bridge_by_id(
            self.db, user.email, bride_id) if user else None
        if bridge is None:
            return None
        lights = requests.get(
            f"http://{bridge.ip}/api/{bridge.user}/lights")
        return lights.json()

    def __getLights__(self):
        config = self.__config_by_token__()
        if config is None:
            return {}
        bridges = config.hue_bridges
        lights = {}
        for bridge in bridges:
            lights_bridge = self.getLightsBride(bridge.id)
            if lights_bridge is not None:
                lights.update(lights_bridge)
        return lights

    def getLights(self):
        config = self.__config_by_token__()
        if config is None:
            return []
        bridges = config.hue_bridges
        normalizedLights = []
        for bridge in bridges:
            lights = self.getLightsBride(bridge.id)
            if lights is not None:
                for light in lights:
                    normalized = self.__mapLight__(
                        bridge.id, lights[light], light)
                    if normalized is not None:
                        normalizedLights.append(normalized)
        return normalizedLights

    def __getLight__(self, bridge_id: str, id: int):
        db_user = self.__user_by_token__()
        if db_user is None:
            return None
        bridge = crud.get_hue_bridge_by_id(self.db, db_user.email, bridge_id)
        if bridge is None or bridge.ip == "" or bridge.user == "":
            return None
        light = requests.get(
            f"http://{bridge.ip}/api/{bridge.user}/lights/{id}")
        return light.json()

    def getLight(self, bridge_id: str, id: int):
        config = self.__config_by_token__()
        if config is None:
            return None
        light = self.__getLight__(bridge_id, id)
        normalizedLight = self.__mapLight__(bridge_id, light, id)
        return normalizedLight

    def getPlugsBride(self, bridge_id: str):
        lights = self.getLightsBride(bridge_id)
        plugs = {}
        if lights is not None:
            for light in lights:
                if lights[light].get("config", {}).get("archetype") == "plug":
                    plugs[light] = lights[light]
        return plugs

    def __getPlugs__(self):
        lights = self.__getLights__()
        plugs = {}
        for light in lights:
            if lights[light].get("config", {}).get("archetype") == "plug":
                plugs[light] = lights[light]
        return plugs

    def getPlugs(self):
        config = self.__config_by_token__()
        if config is None:
            return []
        bridges = config.hue_bridges
        normalizedPlugs = []
        for bridge in bridges:
            plugs = self.getPlugsBride(bridge.id)
            for plug in plugs:
                normalized = self.__mapPlug__(bridge.id, plugs[plug], plug)
                if normalized is not None:
                    normalizedPlugs.append(normalized)
        return normalizedPlugs

    def __getPlug__(self, bridge_id: str, id: int):
        plug = self.__getLight__(bridge_id, id)
        if plug is None or plug["config"]["archetype"] != "plug":
            return None
        return plug

    def getPlug(self, bridge_id: str, id: int):
        plug = self.__getPlug__(bridge_id, id)
        if plug is None:
            return None
        return self.__mapPlug__(bridge_id, plug, id)

    def __setLightState__(self, bridge_id: str, id: int, state: HueLightState):
        user = self.__user_by_token__()
        if user is None:
            return None
        bridge = crud.get_hue_bridge_by_id(self.db, user.email, bridge_id)
        if bridge is None:
            return None

        return requests.put(
            f"http://{bridge.ip}/api/{bridge.user}/lights/{id}/state", json=state.to_dict())

    def setLightState(self, bridge_id: str, id: int, state: LightState):
        new_state = HueLightState.from_dict({})

        if state.brightness is not None:
            new_state.bri = round(state.brightness / 100 * 255)

        if state.color is not None and len(state.color) > 0:
            hsv = self.__rgb_to_hsv__(
                state.color[0][0],
                state.color[0][1],
                state.color[0][2]
            )
            hsb = self.__hsv_to_hsb__(hsv[0], hsv[1], hsv[2])
            new_state.hue = round(hsb[0])
            new_state.sat = round(hsb[1])

        if state.on is not None:
            new_state.on = state.on

        return self.__setLightState__(bridge_id, id, new_state)


class NewBridge(BaseModel):
    id: str


class HueBody(BaseModel):
    host: Optional[str]
    user: Optional[str]


@router.put("/config/add", responses={200: {"model": NewBridge}, 400: {"model": str}, 401: {"model": ErrorResponse}})
def set_config(new_config: HueBody, token: str = Depends(JWTBearer())):
    user = user_by_token(db.session, token)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})

    bridge = crud.add_hue_bridge(
        db.session, user.email, host=new_config.host, user=new_config.user)

    if bridge is not None:
        return JSONResponse(status_code=200, content={"id": bridge.id})

    return Response(status_code=400, content="Bridge already added")


class UserResponse(BaseModel):
    username: str


@router.get("/init/{bridge_id}", responses={200: {"model": UserResponse}, 400: {"model": str}, 401: {"model": ErrorResponse}})
def hue_init(bridge_id: str, token: str = Depends(JWTBearer())):
    user = user_by_token(db.session, token)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    bridge = crud.get_hue_bridge_by_id(db.session, user.email, bridge_id)
    if bridge is None or bridge.ip == "":
        return Response(status_code=400, content="No host set")

    userRequest = requests.post(
        f"http://{bridge.ip}/api", json={"devicetype": "my_hue_app#home api"})

    json = userRequest.json()[0]
    error = json.get("error")

    if error is not None and error.get("type") == 101:
        return Response(status_code=400, content="Link button not pressed")

    user = userRequest.json()[0].get("success").get("username")

    crud.update_hue_bridge(db.session, bridge._id, user=user)

    return JSONResponse(status_code=200, content={"username": user})


@router.delete("/config/{bridge_id}", responses={200: {"model": str}, 401: {"model": ErrorResponse}})
def delete_config(bridge_id: str, token: str = Depends(JWTBearer())):
    user = user_by_token(db.session, token)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid token"})
    if crud.delete_hue_bridge_by_id(db.session, user.email, bridge_id):
        return Response(status_code=200)
    return Response(status_code=400)


@router.get("/lights", response_model=dict[str, HueLightResponse])
def get_lights(token: str = Depends(JWTBearer())):
    return JSONResponse(status_code=200, content=LightHandler(token, db.session).__getLights__())


@router.get("/lights/{bridge_id}", response_model=dict[str, HueLightResponse])
def get_lights_bridge(bridge_id: str, token: str = Depends(JWTBearer())):
    return JSONResponse(status_code=200, content=LightHandler(token, db.session).getLightsBride(bridge_id))


@router.get("/lights/{bridge_id}/{id}", response_model=HueLightResponse)
def get_light(bridge_id: str, id: int, token: str = Depends(JWTBearer())):
    return JSONResponse(status_code=200, content=LightHandler(token, db.session).__getLight__(bridge_id, id))


@router.put("/lights/{bridge_id}/{id}/state", response_model=dict)
async def set_light_state(bridge_id: str, id: int, state: HueLightState, token: str = Depends(JWTBearer())):
    light_handler = LightHandler(token, db.session)
    response = light_handler.__setLightState__(bridge_id, id, state)

    try:
        light = light_handler.__getLight__(bridge_id, id)
        if light is not None:
            await broadcast(WebSocketMessage(
                type="light",
                data=light,
            ), token)
    except:
        pass

    if response is None:
        return Response(status_code=400, content="No host or user set")

    if response.status_code == 200:
        return Response(status_code=200)

    return Response(status_code=400, content=response.json())


@router.get("/plugs", response_model=dict[str, HuePlugResponse])
def get_plugs(token: str = Depends(JWTBearer())):
    return JSONResponse(status_code=200, content=LightHandler(token, db.session).__getPlugs__())


@router.get("/plugs/{bridge_id}", response_model=dict[str, HuePlugResponse])
def get_plugs_bridge(bridge_id: str, token: str = Depends(JWTBearer())):
    return JSONResponse(status_code=200, content=LightHandler(token, db.session).getPlugsBride(bridge_id))


@router.get("/plugs/{bridge_id}/{id}", response_model=HuePlugResponse)
def get_plug(bridge_id: str, id: int, token: str = Depends(JWTBearer())):
    plug = LightHandler(token, db.session).__getPlug__(bridge_id, id)
    if plug is None:
        return Response(status_code=404, content="Plug not found")

    return JSONResponse(status_code=200, content=plug.to_dict())


@router.put("/plugs/{bridge_id}/{id}/state", response_model=dict)
async def set_plug_state(bridge_id: str, id: int, state: HuePlugState, token: str = Depends(JWTBearer())):
    light_handler = LightHandler(token, db.session)
    response = light_handler.__setLightState__(bridge_id, id, state)

    try:
        plug = light_handler.__getPlug__(bridge_id, id)
        if plug is not None:
            await broadcast(WebSocketMessage(
                type="plug",
                data=plug,
            ), token)
    except:
        pass

    if response is None:
        return Response(status_code=400, content="No host or user set")

    if response.status_code == 200:
        return Response(status_code=200)

    return Response(status_code=400, content=response.json())
