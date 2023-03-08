import datetime
import peewee
import telebot
import json
import threading
import logging
import sys
from src import keyboards
from src.database import models

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


@bot.message_handler(chat_types=['private'], func=lambda msg: models.User.get_or_create(telegram_id=msg.from_user.id)[0].power_level > 0)  # do not forget change to >1
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
        title=message.chat.title,
        type=message.chat.type
    )[0]

    message_thread: models.MessageThread = models.MessageThread.get_or_create(
        group=group,
        thread_id=message.message_thread_id
    )[0]


@bot.callback_query_handler(func=lambda call: call.data.startswith('group_'))
def on_group_select_click(call: telebot.types.CallbackQuery) -> None:
    group: models.Group = models.Group.get(
        models.Group.chat_id == call.data.replace('group_list_for_', '')
    )

    bot.edit_message_text(
        message_id=call.message.id,
        chat_id=call.message.chat.id,
        text='Menupoint select',
        reply_markup=keyboards.group_settings_generate(group)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('exists_rules_for_'))
def on_exists_rules_click(call: telebot.types.CallbackQuery) -> None:
    group: models.Group = models.Group.get(
        models.Group.chat_id == call.data.replace('exists_rules_for_', '')
    )

    pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('new_rule_for_'))
def on_create_rule_click(call: telebot.types.CallbackQuery) -> None:
    group: models.Group = models.Group.get(
        models.Group.chat_id == call.data.replace('new_rule_for_', '')
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Thread select',
        reply_markup=keyboards.threads_list_generate(group)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_thread_'))
def on_thread_select(call: telebot.types.CallbackQuery):
    call.data = call.data.split('_')

    group: models.Group = models.Group.get(
        models.Group.chat_id == call.data[5]
    )

    thread: models.MessageThread = models.MessageThread.get(
        models.MessageThread.id == call.data[2]
    )


def start_poll():
    bot.infinity_polling()
    global stop
    stop = True
