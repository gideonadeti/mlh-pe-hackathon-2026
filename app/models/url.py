from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    TextField,
)

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, field=User.id, backref="urls", on_delete="CASCADE")
    short_code = CharField(unique=True, max_length=32, index=True)
    original_url = TextField()
    title = CharField(max_length=512)
    is_active = BooleanField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        table_name = "urls"
