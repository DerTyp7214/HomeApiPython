from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import db
from sqlalchemy.orm import Session

from ..auth_bearer import JWTBearer
from ..consts import Light, LightState, Plug, PlugState, WebSocketMessage
from ..websocket import broadcast
from .hue import LightHandler as HueLightHandler
from .wled import LightHandler as WledLightHandler


router = APIRouter(
    tags=["main"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(JWTBearer())]
)


class LightHandler:
    token: str
    hue: HueLightHandler
    wled: WledLightHandler
    db: Session

    def __init__(self, token: str, db: Session):
        self.token = token
        self.db = db
        self.hue = HueLightHandler(token, db)
        self.wled = WledLightHandler(token, db)

    def allLights(self) -> list[Light]:
        return [*self.hue.getLights()]

    def allPlugs(self) -> list[Plug]:
        return [*self.hue.getPlugs()]

    def getLight(self, id: str):
        try:
            if id.startswith("hue-"):
                bridge_id, light_id = id.replace("hue-", "").split("-")
                return self.hue.getLight(bridge_id, int(light_id))
            return self.allLights()[int(id)]
        except ValueError:
            return None
        except IndexError:
            return None

    def getPlug(self, id: str):
        try:
            if id.startswith("hue-"):
                bridge_id, plug_id = id.replace("hue-", "").split("-")
                return self.hue.getPlug(bridge_id, int(plug_id))
            return self.allPlugs()[int(id)]
        except ValueError:
            return None
        except IndexError:
            return None

    def setLightState(self, id: str, state: LightState):
        try:
            if id.startswith("hue-"):
                bridge_id, light_id = id.replace("hue-", "").split("-")
                response = self.hue.setLightState(
                    bridge_id, int(light_id), state)
                if response is None:
                    return JSONResponse(status_code=404, content={"error": "Light not found"})
                return response
            return JSONResponse(status_code=404, content={"error": "Light not found"})
        except ValueError:
            return JSONResponse(status_code=404, content={"error": "Light not found"})

    def setPlugState(self, id: str, state: PlugState):
        try:
            if id.startswith("hue-"):
                bridge_id, plug_id = id.replace("hue-", "").split("-")
                response = self.hue.setLightState(
                    bridge_id, int(plug_id), state)
                if response is None:
                    return JSONResponse(status_code=404, content={"error": "Plug not found"})
                return response
            return JSONResponse(status_code=404, content={"error": "Plug not found"})
        except ValueError:
            return JSONResponse(status_code=404, content={"error": "Plug not found"})


@router.get("/lights", response_model=list[Light])
def get_lights(token: str = Depends(JWTBearer())):
    lights = []
    for light in LightHandler(token, db.session).allLights():
        lights.append(light.to_dict())

    return JSONResponse(status_code=200, content=lights)


@router.get("/lights/{id}", response_model=Light)
def get_light(id: str, token: str = Depends(JWTBearer())):
    light = LightHandler(token, db.session).getLight(id)

    if light is None:
        return JSONResponse(status_code=404, content={"error": "Light not found"})
    return JSONResponse(status_code=200, content=light.to_dict())


@router.put("/lights/{id}/state", response_model=dict)
async def set_light_state(id: str, state: LightState, token: str = Depends(JWTBearer())):
    light_handler = LightHandler(token, db.session)
    response = light_handler.setLightState(id, state)

    light = light_handler.getLight(id)

    if light is None:
        return JSONResponse(status_code=404, content={"error": "Light not found"})

    try:
        await broadcast(WebSocketMessage.from_dict({
            "type": "light",
            "data": light.__dict__,
        }), token)
    except:
        pass

    if response.status_code == 200:
        return JSONResponse(status_code=200, content=light.to_dict())

    return response


@router.get("/plugs", response_model=list[Plug])
def get_plugs(token: str = Depends(JWTBearer())):
    plugs = []
    for plug in LightHandler(token, db.session).allPlugs():
        plugs.append(plug.to_dict())

    return JSONResponse(status_code=200, content=plugs)


@router.get("/plugs/{id}", response_model=Plug)
def get_plug(id: str, token: str = Depends(JWTBearer())):
    plug = LightHandler(token, db.session).getPlug(id)

    if plug is None:
        return JSONResponse(status_code=404, content={"error": "Plug not found"})
    return JSONResponse(status_code=200, content=plug.to_dict())


@router.put("/plugs/{id}/state", response_model=dict)
async def set_plug_state(id: str, state: PlugState, token: str = Depends(JWTBearer())):
    light_handler = LightHandler(token, db.session)
    response = light_handler.setPlugState(id, state)

    plug = light_handler.getPlug(id)

    if plug is None:
        return JSONResponse(status_code=404, content={"error": "Plug not found"})

    try:
        await broadcast(WebSocketMessage(
            type="plug",
            data=plug.__dict__,
        ), token)
    except:
        pass

    if response.status_code == 200:
        return JSONResponse(status_code=200, content=plug.to_dict())

    return response
