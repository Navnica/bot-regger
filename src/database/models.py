from peewee import *

db = SqliteDatabase('src/database/database.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = IntegerField(null=False)
    power_level = IntegerField(null=False, default=1)


class Group(BaseModel):
    chat_id = IntegerField(null=False)
    title = CharField(null=False)
    type = CharField(null=False)

    def get_linked_actions(self) -> list:
        return [action for action in Action.select().where(Action.chat_id == self)]


class MessageThread(BaseModel):
    group = ForeignKeyField(Group, related_name='group_thread')
    thread_id = IntegerField(null=True)


class Action(BaseModel):
    chat_id = ForeignKeyField(Group, related_name='group_action', null=False)
    message_thread_id = ForeignKeyField(MessageThread, null=False)
    regular_expression = CharField(null=False)
    def_name = CharField(null=False)
    text = CharField(null=False)
    time_out_value = IntegerField(null=True, default=0)


class TMessage(BaseModel):
    chat = ForeignKeyField(Group, related_name='group_t_message', null=False)
    message_thread_id = IntegerField(null=True)
    message_author = ForeignKeyField(User, related_name='message_author')
    message_id = IntegerField(null=False)
    action = ForeignKeyField(Action, null=True)


class DeleteList(BaseModel):
    t_message = ForeignKeyField(TMessage, related_name='t_message')
    time_delete = DateTimeField(null=True)


class RegexpWaitList(BaseModel):
    group = ForeignKeyField(Group, related_name='group_regex', null=False)
    thread = ForeignKeyField(MessageThread, related_name='thread_regex', null=False)
    t_message = ForeignKeyField(TMessage, related_name='t_message_regex', null=False)
    user = ForeignKeyField(User, related_name='user_regex', null=False)


Action.create_table()
Group.create_table()
User.create_table()
TMessage.create_table()
DeleteList.create_table()
MessageThread.create_table()
RegexpWaitList.create_table()
