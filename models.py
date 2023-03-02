import peewee
from datetime import datetime

db = peewee.SqliteDatabase('database.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = peewee.IntegerField(null=False)
    power_level = peewee.IntegerField(default=1)


class Action(BaseModel):
    chat_id = peewee.IntegerField(null=False)
    message_thread_id = peewee.IntegerField(null=False)
    regular_expression = peewee.CharField(null=False)
    def_name = peewee.CharField(null=False)
    text = peewee.CharField(null=False)
    time_out_value = peewee.IntegerField(null=True, default=0)


class TMessage(BaseModel):
    chat_id = peewee.IntegerField(null=False)
    message_thread_id = peewee.IntegerField(null=False)
    message_id = peewee.IntegerField(null=False)
    time_send = peewee.DateTimeField(null=False, default=datetime.now())


Action.create_table()
User.create_table()
TMessage.create_table()