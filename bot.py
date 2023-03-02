import datetime
import telebot
import json
import regexpparser
import threading
import models
import time

bot = telebot.TeleBot(json.load(open('config.json', encoding='utf-8'))['token'])
bot_instance = models.User.get_or_create(telegram_id=bot.get_me().id, power_level=2)


def message_cleaner():
    while True:
        for msg in models.DeleteList.select():
            if datetime.datetime.now() > msg.time_delete:
                bot.delete_message(chat_id=msg.t_message.chat_id,
                                   message_id=msg.t_message.message_id)

                msg.t_message.delete_instance()
                msg.delete_instance()


threading.Thread(target=message_cleaner).start()


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message) -> None:

    print(f'{message.from_user} : {message.text}')

    user_instance = models.User.get_or_create(telegram_id=message.from_user.id)
    waited: models.WaitAnswer = models.WaitAnswer.get_or_none(user=user_instance[0])

    if message.text.startswith('regex'):
        regexpparser.RegexpParser(message, bot).parse_regex()
        return

    if waited:
        action: models.Action = models.Action.get(
            models.Action.chat_id == message.chat.id,
            models.Action.message_thread_id == message.message_thread_id,
            )

        models.DeleteList.create(
            t_message=waited.t_message,
            time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
        ).save()

        if waited.yes_or_no:
            return

        else:
            models.DeleteList.create(
                t_message=waited.bot_t_message,
                time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
            ).save()

        waited.delete_instance()

    answer: str = regexpparser.RegexpParser(message, bot).parse_message()

    if not answer:
        return

    bot.reply_to(message, answer)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    user_instance = models.User.get_or_create(telegram_id=call.from_user.id)
    waited: models.WaitAnswer = models.WaitAnswer.get_or_none(user=user_instance[0])
    action: models.Action = models.Action.get(
        models.Action.chat_id == call.message.chat.id,
        models.Action.message_thread_id == call.message.message_thread_id,
    )

    if not waited: return

    models.DeleteList.create(
        t_message=waited.t_message,
        time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
    ).save()

    if call.data == 'markup_no':
        models.DeleteList.create(
            t_message=waited.bot_t_message,
            time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
        ).save()

        waited.delete_instance()