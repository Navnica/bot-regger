import re
from telebot.types import Message
import models


class RegexpParser:
    message: Message = None

    def __init__(self, active_message: Message):
        self.message = active_message

    def parse_message(self) -> str | None:
        for action in models.Action.select():
            if re.search(action.regular_expression, self.message.text) is not None\
                    and action.chat_id == self.message.chat.id \
                    and action.message_thread_id == self.message.message_thread_id:

                return RegexpParser.__dict__[action.def_name](self, action)

    def parse_regex(self) -> None:
        ex = '([(].+[)])[ ](.+)[(](.+)[)]'
        exs = re.search(ex, self.message.text).groups()

        if not exs:
            return

        RegexpParser.__dict__[f'register_{exs[1]}'](self, exs)

    def register_answer(self, exs: re.Match) -> None:
        models.Action.create(
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id,
            regular_expression=exs[0],
            text=exs[2].split("'")[1],
            def_name='answer'
        ).save()

    def register_answer_delete_after(self, exs: re.Match) -> None:
        pass

    def register_answer_question_yes_no(self, exs: re.Match) -> None:
        pass

    def answer(self, action: models.Action) -> str:
        return action.text
