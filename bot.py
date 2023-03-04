import datetime
import peewee
import telebot
import json
import regexpparser
import threading
import models

bot = telebot.TeleBot(json.load(open('config.json', encoding='utf-8'))['token'])
bot_instance = models.User.get_or_create(telegram_id=bot.get_me().id, power_level=2)
stop = False


def message_cleaner():
    global stop
    while True:
        if stop: return
        for msg in models.DeleteList.select():
            if datetime.datetime.now() > msg.time_delete:
                try:
                    bot.delete_message(chat_id=msg.t_message.chat_id,
                                       message_id=msg.t_message.message_id)

                    print(f'{msg.t_message.message_id} was deleted at {datetime.datetime.now().time()}')

                    msg.t_message.delete_instance()

                except peewee.DoesNotExist:
                    print('TMessage не существует, пропуск')

                msg.delete_instance()


cleaner = threading.Thread(target=message_cleaner)
cleaner.start()


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message) -> None:
    time: datetime = datetime.datetime.now().time()
    print(f'{message.from_user.username} : {message.text} : {time}')

    user_instance = models.User.get_or_create(telegram_id=message.from_user.id)

    if message.text.startswith('regex'):
        regexpparser.RegexpParser(message, bot).parse_regex()
        return

    answer: str = regexpparser.RegexpParser(message, bot).parse_message()

    if not answer:
        return

    bot.reply_to(message, answer)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call: telebot.types.CallbackQuery):
    time: datetime = datetime.datetime.now().time()
    print(f'{call.from_user.username} : {call.data} : {time}')

    message = call.message.reply_to_message

    if message:
        if call.from_user.id != message.from_user.id:
            return
    else:
        return

    bot_t_message: models.TMessage = models.TMessage.get(
        models.TMessage.chat_id == call.message.chat.id,
        models.TMessage.message_thread_id == call.message.message_thread_id,
        models.TMessage.message_id == call.message.message_id
    )

    t_message: models.TMessage = models.TMessage.get(
        models.TMessage.chat_id == message.chat.id,
        models.TMessage.message_thread_id == message.message_thread_id,
        models.TMessage.message_id == message.message_id
    )

    if call.data == 'markup_yes':
        models.DeleteList.get(models.DeleteList.t_message == t_message).delete_instance()

        x: models.DeleteList = models.DeleteList.get(models.DeleteList.t_message == bot_t_message)
        x.time_delete = datetime.datetime.now()
        x.save()

    else:
        x: models.DeleteList = models.DeleteList.get(models.DeleteList.t_message == t_message)
        x.time_delete = datetime.datetime.now()
        x.save()

        y: models.DeleteList = models.DeleteList.get(models.DeleteList.t_message == bot_t_message)
        y.time_delete = datetime.datetime.now()
        y.save()


def start_poll():
    bot.infinity_polling()
    global stop

    stop = True
