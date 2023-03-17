import datetime
from peewee import *

db = SqliteDatabase('src/database/database.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    telegram_id = IntegerField(null=False),
    username = CharField(null=True)
    power_level = IntegerField(null=False, default=1)


class Group(BaseModel):
    chat_id = IntegerField(null=False, unique=True)
    title = CharField(null=True)
    type = CharField(null=False)

    def get_linked_actions(self) -> list:
        return [action for action in Action.select().where(Action.chat_id == self)]


class MessageThread(BaseModel):
    group = ForeignKeyField(Group, related_name='group_thread')
    thread_id = IntegerField(null=True)
    is_log_chat = BooleanField(default=False)


class Action(BaseModel):
    name = CharField(null=True)
    thread = ForeignKeyField(MessageThread, related_name='action_thread', null=False)
    regular_expression = CharField(null=False)
    def_name = CharField(null=False)
    text = CharField(null=False)
    time_out_value = IntegerField(null=True, default=0)

    def set_text(self, text: str) -> None:
        self.text = text
        self.save()

    def set_delay(self, time_delay: int):
        self.time_out_value = time_delay
        self.save()

    def set_name(self, name: str):
        self.name = name
        self.save()


class DeleteList(BaseModel):
    thread = ForeignKeyField(MessageThread, related_name='delete_thread', null=False)
    message_id = IntegerField(null=False)
    time_delete = DateTimeField(null=True)

    def delete_now(self):
        self.time_delete = datetime.datetime.now()
        self.save()


class RegexWait(BaseModel):
    thread = ForeignKeyField(MessageThread, related_name='thread_regex', null=False)
    user = ForeignKeyField(User, related_name='user_regex', null=False)
    function_name = CharField(null=False)
    delay = IntegerField(null=True)
    stage = CharField(default='regex_wait')
    action = ForeignKeyField(Action, null=True, related_name='action_regex_wait')

    def set_stage(self, new_stage: str) -> None:
        self.stage = new_stage
        self.save()

    def set_action(self, new_action: Action) -> None:
        self.action = new_action
        self.save()


class ThreadHistory(BaseModel):
    thread = ForeignKeyField(MessageThread, related_name='thread_history')
    from_user = ForeignKeyField(User, related_name='user_history')
    message_id = IntegerField(null=False)
    message_datetime = DateTimeField(default=datetime.datetime.now())
    text = CharField(null=False)


Action.create_table()
Group.create_table()
User.create_table()
DeleteList.create_table()
MessageThread.create_table()
RegexWait.create_table()
