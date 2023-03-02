import re
from telebot.types import Message
from telebot import TeleBot
import models

class RegexpParser:
    message: Message = None
    bot: TeleBot = None

    def __init__(self, active_message: Message, bot: TeleBot):
        self.message = active_message
        self.bot = bot

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
        models.Action.create(
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id,
            regular_expression=exs[0],
            text=exs[2].split("'")[1],
            def_name='answer_delete_after',
            time_out_value=int(exs[2].split(',')[-1].replace(' ', ''))
        ).save()

    def register_answer_question_yes_no(self, exs: re.Match) -> None:
        models.Action.create(
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id,
            regular_expression=exs[0],
            text=exs[2].split("'")[1],
            def_name='answer_question_yes_no',
            time_out_value=int(exs[2].split(',')[-1].replace(' ', ''))
        ).save()

    def answer(self, action: models.Action) -> str:
        return action.text

    def answer_delete_after(self, action: models.Action) -> str | None:
        t_message = self.create_bot_message(action)

        models.WaitAnswer.create(
            t_message=t_message,
            user=models.User.get(models.User.telegram_id == self.message.from_user.id),
        ).save()

        return None

    def answer_question_yes_no(self, action: models.Action) -> str | None:
        t_message = self.create_bot_message(action)

        models.WaitAnswer.create(
            t_message=t_message,
            user=models.User.get(models.User.telegram_id == self.message.from_user.id),
            yes_or_no=True
        ).save()

        return None

    def create_bot_message(self, action: models.Action) -> models.TMessage:
        new_message = self.bot.send_message(
            text=action.text,
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id
        )

        t_message = models.TMessage.create(
            chat_id=new_message.chat.id,
            message_thread_id=new_message.message_thread_id,
            message_author=models.User.get(models.User.telegram_id == self.bot.get_me().id),
            message_id=new_message.message_id
        )

        t_message.save()

        return t_message
