import datetime
import peewee
import telebot
import json
import threading
import logging
from src import keyboards
from src.database import models
import sys


logging.basicConfig(
    level=logging.INFO,
    format="(%(asctime)s) [%(levelname)s] %(message)s",
    datefmt="%d:%m:%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)

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
                    print('TMessage does not exist, a pass')

                msg.delete_instance()


cleaner = threading.Thread(target=message_cleaner)
cleaner.start()


@bot.message_handler(chat_types=['private'], func=lambda msg: models.User.get_or_create(telegram_id=msg.from_user.id)[0].power_level > 0) # do not forget change to >1
def on_admin_message(message: telebot.types.Message) -> None:
    logging.info(f'{message.from_user.username} : {message.text}')

    user: models.User = models.User.get(telegram_id=message.from_user.id)

    new_message = bot.send_message(
        chat_id=message.chat.id,
        text='Выберите пункт меню',
        reply_markup=keyboards.group_list_generate()
    )


@bot.message_handler(chat_types=['group', 'supergroup'])
def get_text_messages(message: telebot.types.Message) -> None:
    logging.info(f'{message.from_user.username} : {message.text}')

    group: models.Group = models.Group.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('group_'))
def on_group_select(call: telebot.types.CallbackQuery):
    group: models.Group = models.Group.get(models.Group.chat_id == call.data[6:])


def start_poll():
    bot.infinity_polling()
    global stop
    stop = True
