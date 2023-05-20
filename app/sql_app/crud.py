from typing import Optional, Sequence
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from ..auth_handler import hash_password
from ..model import UserSchema

from . import models


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.scalars(select(models.User).where(
        models.User.id == user_id)).one_or_none()


def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.scalars(select(models.User).where(
        models.User.username == username)).one_or_none()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.scalars(select(models.User).where(
        models.User.email == email)).one_or_none()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> Sequence[models.User]:
    return db.scalars(select(models.User).offset(skip).limit(limit)).all()


def create_user(db: Session, user: UserSchema) -> models.User | None:
    db.execute(insert(models.User), [
        {
            "username": user.username,
            "email": user.email,
            "hashed_password": hash_password(user.password),
            "settings": models.UserSettings(
                hue_index=0,
            ) if user.settings is None else models.UserSettings(**{
                "hue_index": user.settings.hue_index,
                "hue_bridges": [models.HueBridge(**{
                    "id": bridge.id,
                    "ip": bridge.ip,
                    "user": bridge.user,
                }) for bridge in user.settings.hue_bridges],
                "wled_ips": [models.WledItem(**{
                    "ip": wled.ip,
                    "name": wled.name,
                }) for wled in user.settings.wled_ips],
            }),
        }
    ])
    db.commit()
    return get_user_by_email(db, user.email)


def delete_user_by_email(db: Session, email: str) -> bool:
    user = db.scalars(select(models.User).where(
        models.User.email == email)).one_or_none()
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True


def update_user_by_email(db: Session, email: str, new_user: UserSchema) -> UserSchema | None:
    db_user = db.scalars(select(models.User).where(
        models.User.email == email)).one_or_none()
    if db_user is None:
        return None
    for key, value in new_user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return UserSchema(**db_user.__dict__)


def get_user_settings_by_email(db: Session, email: str) -> models.UserSettings | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    if user.settings is None:
        user.settings = models.UserSettings(hue_index=0)
        db.commit()
        db.refresh(user)
    return user.settings if user is not None else None


def add_hue_bridge(db: Session, email: str, host: Optional[str] = None, user: Optional[str] = None) -> models.HueBridge | None:
    user_settings = get_user_settings_by_email(db, email)
    if user_settings is None:
        return None

    user_settings.hue_index += 1
    bridge = models.HueBridge(
        id=str(user_settings.hue_index),
        ip="",
        user="",
    )
    if host is not None:
        bridge.ip = host
    if user is not None:
        bridge.user = user

    user_settings.hue_bridges.append(bridge)
    db.commit()
    db.refresh(bridge)
    return bridge


def get_hue_bridge_by_id(db: Session, email: str, bridge_id: str) -> models.HueBridge | None:
    user_settings = get_user_settings_by_email(db, email)
    if user_settings is None:
        return None

    return next((bridge for bridge in user_settings.hue_bridges if bridge.id == bridge_id), None)


def update_hue_bridge(db: Session, bridge_db_id: int, ip: Optional[str] = None, user: Optional[str] = None) -> models.HueBridge | None:
    bridge = db.scalars(select(models.HueBridge).where(
        models.HueBridge._id == bridge_db_id)).one_or_none()
    if bridge is None:
        return None
    if ip is not None:
        setattr(bridge, "ip", ip)
    if user is not None:
        setattr(bridge, "user", user)
    db.commit()
    db.refresh(bridge)
    return bridge


def delete_hue_bridge(db: Session, bridge_db_id: int) -> bool:
    bridge = db.scalars(select(models.HueBridge).where(
        models.HueBridge._id == bridge_db_id)).one_or_none()
    if bridge is None:
        return False
    db.delete(bridge)
    db.commit()
    return True


def delete_hue_bridge_by_id(db: Session, email: str, bridge_id: str) -> bool:
    bridge = get_hue_bridge_by_id(db, email, bridge_id)
    if bridge is None:
        return False
    db.delete(bridge)
    db.commit()
    return True


def get_wled(db: Session, email: str, ip: str) -> models.WledItem | None:
    user_settings = get_user_settings_by_email(db, email)
    if user_settings is None:
        return None

    return next((wled for wled in user_settings.wled_ips if wled.ip == ip), None)


def add_wled(db: Session, email: str, ip: str, name: Optional[str] = None) -> models.WledItem | None:
    user_settings = get_user_settings_by_email(db, email)
    if user_settings is None:
        return None

    wled = models.WledItem()
    wled.ip = ip
    if name is not None:
        wled.name = name

    user_settings.wled_ips.append(wled)
    db.commit()
    db.refresh(user_settings)
    return wled


def update_wled(db: Session, email: str, ip: str, name: Optional[str] = None) -> models.WledItem | None:
    wled = get_wled(db, email, ip)
    if wled is None:
        return None
    if name is not None:
        setattr(wled, "name", name)
    db.commit()
    db.refresh(wled)
    return wled


def delete_wled(db: Session, email: str, ip: str) -> bool:
    wled = get_wled(db, email, ip)
    if wled is None:
        return False
    db.delete(wled)
    db.commit()
    return True
