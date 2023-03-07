import re
from telebot.types import Message
from telebot import TeleBot
from database import models
import keyboards
import datetime


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
            regular_expression=str(exs[0])[1:-1],
            text=exs[2].split("'")[1],
            def_name='answer'
        ).save()

    def register_answer_delete_after(self, exs: re.Match) -> None:
        models.Action.create(
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id,
            regular_expression=str(exs[0])[1: -1],
            text=exs[2].split("'")[1],
            def_name='answer_delete_after',
            time_out_value=int(exs[2].split(',')[-1].replace(' ', ''))
        ).save()

    def register_answer_question_yes_no(self, exs: re.Match) -> None:
        models.Action.create(
            chat_id=self.message.chat.id,
            message_thread_id=self.message.message_thread_id,
            regular_expression=str(exs[0])[1 : -1],
            text=exs[2].split("'")[1],
            def_name='answer_question_yes_no',
            time_out_value=int(exs[2].split(',')[-1].replace(' ', ''))
        ).save()

    def answer(self, action: models.Action) -> str:
        return action.text

    def answer_delete_after(self, action: models.Action, markup=None) -> str | None:
        new_message = self.bot.reply_to(
            message=self.message,
            text=action.text,
            reply_markup=markup
        )

        t_message = self.t_message_create(self.message, action)
        bot_t_message = self.t_message_create(new_message, action)
        correct_time_delete = datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)

        models.DeleteList.create(
            t_message=bot_t_message,
            time_delete=correct_time_delete
        ).save()

        models.DeleteList.create(
            t_message=t_message,
            time_delete=correct_time_delete
        ).save()

        return None

    def answer_question_yes_no(self, action: models.Action) -> str | None:
        self.answer_delete_after(action, keyboards.yes_no_markup)

        return None

    def t_message_create(self, message: Message, action: models.Action) -> models.TMessage:
        t_message = models.TMessage.create(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            message_author=models.User.get(models.User.telegram_id == self.bot.get_me().id),
            message_id=message.message_id,
            action=action
        )

        t_message.save()

        return t_message
