# Import models so Peewee registers them and FKs resolve.
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

__all__ = ["Event", "Url", "User"]
