from typing import List
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


class HueBridge(Base):
    __tablename__ = "huebridges"
    _id: Mapped[int] = mapped_column(primary_key=True, index=True)

    id: Mapped[str] = mapped_column(String, index=True)
    ip: Mapped[str] = mapped_column(String)
    user: Mapped[str] = mapped_column(String)

    user_settings_id: Mapped[int] = mapped_column(ForeignKey("usersettings.id"))

class WledItem(Base):
    __tablename__ = "wleditems"
    _id: Mapped[int] = mapped_column(primary_key=True, index=True)

    ip: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)

    user_settings_id: Mapped[int] = mapped_column(ForeignKey("usersettings.id"))

class UserSettings(Base):
    __tablename__ = "usersettings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    hue_index: Mapped[int] = mapped_column(Integer, default=0)
    hue_bridges: Mapped[List["HueBridge"]] = relationship("HueBridge")
    wled_ips: Mapped[List["WledItem"]] = relationship("WledItem")

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=False, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    settings: Mapped[UserSettings] = relationship("UserSettings", uselist=False)
