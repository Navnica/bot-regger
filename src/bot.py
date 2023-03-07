import datetime
import peewee
import telebot
import json
import threading
import logging
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


@bot.message_handler(chat_types=['private', function])


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message) -> None:
    logging.info(f'{message.from_user.username} : {message.text}')




def start_poll():
    bot.infinity_polling()
    global stop
    stop = True
