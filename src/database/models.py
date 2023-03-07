from peewee import *

db = SqliteDatabase('database.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = IntegerField(null=False)
    power_level = IntegerField(null=False, default=1)


class Action(BaseModel):
    chat_id = IntegerField(null=False)
    message_thread_id = IntegerField(null=True)
    regular_expression = CharField(null=False)
    def_name = CharField(null=False)
    text = CharField(null=False)
    time_out_value = IntegerField(null=True, default=0)


class TMessage(BaseModel):
    chat_id = IntegerField(null=False)
    message_thread_id = IntegerField(null=True)
    message_author = ForeignKeyField(User, related_name='message_author')
    message_id = IntegerField(null=False)
    action = ForeignKeyField(Action, null=True)


class DeleteList(BaseModel):
    t_message = ForeignKeyField(TMessage, related_name='t_message')
    time_delete = DateTimeField(null=True)


Action.create_table()
User.create_table()
TMessage.create_table()
DeleteList.create_table()