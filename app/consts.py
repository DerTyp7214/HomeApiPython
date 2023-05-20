from dataclasses import dataclass
from json import dumps, loads
from typing import Optional
from pydantic import BaseModel
from os import path, environ
from dotenv import load_dotenv

DOTENV_FILE = path.join(path.dirname(__file__), "..", ".env")

load_dotenv(DOTENV_FILE)

config = environ.get

port = int(config("port", "8000"))

version = str(config("version", "1.0.0"))

JWT_SECRET = str(config("secret"))
JWT_ALGORITHM = str(config("algorithm"))

SQLALCHEMY_DATABASE_URL = str(
    config("DATABASE_URL", "sqlite:///./home_api.db"))


class BaseClass(BaseModel):
    def to_dict(self, recursive: bool = True) -> dict:
        keys_to_remove = []
        if recursive:
            for key in self.__dict__:
                if isinstance(self.__dict__[key], BaseClass):
                    self.__dict__[key] = self.__dict__[key].to_dict(recursive)
                elif isinstance(self.__dict__[key], list):
                    for i in range(len(self.__dict__[key])):
                        if isinstance(self.__dict__[key][i], BaseClass):
                            self.__dict__[key][i] = self.__dict__[
                                key][i].to_dict(recursive)
                elif self.__dict__[key] is None:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.__dict__[key]

        return self.__dict__

    def to_json(self) -> str:
        return dumps(self.__dict__)

    def load_from_dict(self, __dict__: dict):
        self.__dict__.update(__dict__)

    @classmethod
    def from_dict(cls, __dict__: dict):
        return cls(**__dict__)

    @classmethod
    def from_json(cls, json: str):
        cls.from_dict(loads(json))


class HueConfig(BaseClass):
    id: str
    ip: str
    user: str

    class Config:
        orm_mode = True


class WledItem(BaseClass):
    ip: str
    name: str

    class Config:
        orm_mode = True


class WledConfig(BaseClass):
    ips: Optional[list[WledItem]]


# @brief A class representing a light.
#
# @on Whether the light is on or off.
# @brightness The brightness of the light.
# @color A list of tuples containing the color of the light.
# value ranges:
#   red: 0-255
#   green: 0-255
#   blue: 0-255
class LightState(BaseClass):
    on: Optional[bool]
    brightness: Optional[float]
    color: Optional[list[tuple[int, int, int]]]


class WledNl(BaseClass):
    on: bool
    dur: int
    fade: bool
    tbri: int


class WledUdpn(BaseClass):
    send: bool
    recv: bool


class WledSeg(BaseClass):
    start: int
    stop: int
    len: int
    col: list[tuple[int, int, int]]
    fx: int
    sx: int
    ix: int
    pal: int
    sel: bool
    rev: bool
    cln: int


class WledState(BaseClass):
    on: Optional[bool]
    bri: Optional[float]
    transition: Optional[int]
    ps: Optional[int]
    pl: Optional[int]
    nl: Optional[WledNl]
    udpn: Optional[WledUdpn]
    seg: Optional[list[WledSeg]]


class WledLeds(BaseClass):
    count: int
    rgbw: bool
    pin: list[int]
    pwr: int
    maxpwr: int
    maxseg: int


class WledInfo(BaseClass):
    ver: str
    vid: str
    leds: WledLeds
    name: str
    udpport: int
    live: bool
    fxcount: int
    palcount: int
    arch: str
    core: str
    freeheap: int
    uptime: int
    opt: int
    brand: str
    product: str
    btype: str
    mac: str


class Wled(BaseClass):
    state: WledState
    info: WledInfo
    effects: list[str]
    palettes: list[str]


class HueLightState(BaseClass):
    on: Optional[bool]
    bri: Optional[float]
    hue: Optional[float]
    sat: Optional[float]


class HueLightStateResponse(BaseClass):
    on: bool
    bri: int
    hue: int
    sat: int
    effect: str
    xy: list[float]
    ct: int
    alert: str
    colormode: str
    reachable: bool


class HuePlugStateResponse(BaseClass):
    on: bool


class HueLightSwUpdateResponse(BaseClass):
    state: str
    lastinstall: str


class HueLightCapabilitiesResponse(BaseClass):
    certified: bool
    control: dict
    streaming: dict


class HueLightConfigResponse(BaseClass):
    archetype: str
    function: str
    direction: str
    startup: dict


class HueLightResponse(BaseClass):
    state: HueLightStateResponse
    swupdate: HueLightSwUpdateResponse
    type: str
    name: str
    modelid: str
    manufacturername: str
    productname: str
    capabilities: HueLightCapabilitiesResponse
    config: HueLightConfigResponse
    uniqueid: str
    swversion: str
    swconfigid: str
    productid: Optional[str]


class HuePlugResponse(BaseClass):
    state: HuePlugStateResponse
    swupdate: HueLightSwUpdateResponse
    type: str
    name: str
    modelid: str
    manufacturername: str
    productname: str
    capabilities: HueLightCapabilitiesResponse
    config: HueLightConfigResponse
    uniqueid: str
    swversion: str
    swconfigid: str
    productid: Optional[str]


class PlugState(LightState):
    on: bool


class HuePlugState(HueLightState):
    on: bool


class Light(BaseClass):
    id: str
    name: str
    on: bool
    brightness: float
    color: list[tuple[int, int, int]]
    reachable: bool
    type: str
    model: str
    manufacturer: str
    uniqueid: str
    swversion: str
    productid: Optional[str]


class Plug(BaseClass):
    id: str
    name: str
    on: bool
    reachable: bool
    type: str
    model: str
    manufacturer: str
    uniqueid: str
    swversion: str
    productid: Optional[str]


class WebSocketMessage(BaseClass):
    type: str
    data: dict


@dataclass
class ErrorResponse():
    error: str


origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:433",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:5173",
]
