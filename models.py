import peewee
from datetime import datetime

db = peewee.SqliteDatabase('database.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = peewee.IntegerField(null=False)
    power_level = peewee.IntegerField(null=False, default=1)


class Action(BaseModel):
    chat_id = peewee.IntegerField(null=False)
    message_thread_id = peewee.IntegerField(null=True)
    regular_expression = peewee.CharField(null=False)
    def_name = peewee.CharField(null=False)
    text = peewee.CharField(null=False)
    time_out_value = peewee.IntegerField(null=True, default=0)


class TMessage(BaseModel):
    chat_id = peewee.IntegerField(null=False)
    message_thread_id = peewee.IntegerField(null=True)
    message_author = peewee.ForeignKeyField(User, related_name='message_author')
    message_id = peewee.IntegerField(null=False)
    action = peewee.ForeignKeyField(Action, null=True)


class DeleteList(BaseModel):
    t_message = peewee.ForeignKeyField(TMessage, related_name='t_message')
    time_delete = peewee.DateTimeField(null=True)


Action.create_table()
User.create_table()
TMessage.create_table()
DeleteList.create_table()