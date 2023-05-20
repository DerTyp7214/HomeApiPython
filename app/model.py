from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from .consts import HueConfig, WledItem


class UserSettingsSchema(BaseModel):
    hue_index: int = Field(0)
    hue_bridges: list[HueConfig] = Field(...)
    wled_ips: list[WledItem] = Field(...)

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "hue_bridges": [
                    {
                        "id": "id",
                        "host": "host",
                        "user": "user"
                    }
                ],
                "wled_ips": [
                    {
                        "ip": "ip",
                        "name": "name"
                    }
                ]
            }
        }


class UserSchema(BaseModel):
    username: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    settings: UserSettingsSchema = UserSettingsSchema(
        hue_index=0, hue_bridges=[], wled_ips=[]
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "username": "Username",
                "email": "full-name@x.com",
                "password": "weakpassword",
                "settings": UserSettingsSchema.Config.schema_extra["example"]
            }
        }


class UserSignupSchema(BaseModel):
    username: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "username": "Username",
                "email": "full-name@x.com",
                "password": "weakpassword"
            }
        }


class UserLoginSchema(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "email": "full-name@x.com",
                "password": "weakpassword"
            }
        }
