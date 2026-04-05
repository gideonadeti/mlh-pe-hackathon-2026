from peewee import CharField, DateTimeField, ForeignKeyField, IntegerField, TextField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    id = IntegerField(primary_key=True)
    url = ForeignKeyField(Url, field=Url.id, backref="events", on_delete="CASCADE")
    user = ForeignKeyField(User, field=User.id, backref="events", on_delete="CASCADE")
    event_type = CharField(max_length=64)
    timestamp = DateTimeField()
    details = TextField()

    class Meta:
        table_name = "events"
