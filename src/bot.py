import datetime
import peewee
import telebot
import json
import threading
import logging
import sys
from src import keyboards
from src.dbworker import DBWorker
from src.regexpparser import RegexpParser
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
# bot_instance = models.User.get_or_create(telegram_id=bot.get_me().id, power_level=2)
stop = False


def message_cleaner() -> None:
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

"""
    _____________________________________MESSAGE ZONE_____________________________________
"""


# при любом сообщении в группу
@bot.message_handler(chat_types=['group', 'supergroup'])
def on_group_message(message: telebot.types.Message):
    group = DBWorker.GroupManager.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title,
        group_type=message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=message.message_thread_id
    )


# при сообщении админа в личку
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.UserManager.user_is_admin(message.from_user.id),
    commands=['groups']
)
def on_private_admin_message(message: telebot.types.Message) -> None:
    bot.send_message(
        text='Выберите группу',
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        reply_markup=keyboards.get_group_list_markup()
    )


# при сообщении от пользователя, который должен ввести регулярное выражение
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexpWaitManager.user_in_wait_list(message.from_user.id),
)
def on_regex_input(message: telebot.types.Message) -> None:
    if not RegexpParser.regex_correct(message.text):
        bot.send_message(
            text='Заданное выражение неверно',
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            reply_markup=keyboards.back_to_menu_group_markup
        )

        return

    function_name: str = DBWorker.RegexpWaitManager.get_by_telegram_id(message.from_user.id).function_name



"""
    _____________________________________CALLBACK ZONE_____________________________________
"""


# при нажатии на "вернуться в меню групп"
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_group_menu')
def back_to_group_menu(call: telebot.types.CallbackQuery):
    if DBWorker.RegexpWaitManager.user_in_wait_list(call.from_user.id):
        DBWorker.RegexpWaitManager.delete_by_telegram_id(call.from_user.id)

    bot.edit_message_text(
        text='Выберите группу',
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=keyboards.get_group_list_markup()
    )


# при выборе группы
@bot.callback_query_handler(func=lambda call: call.data.startswith('group_select_'))
def on_select_group_pressed(call: telebot.types.CallbackQuery) -> None:
    group: int = int(call.data.split('_')[2])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text='Ввыберите топик',
        reply_markup=keyboards.get_threads_linked_group_by_group_id(group)
    )


# при выборе топика
@bot.callback_query_handler(func=lambda call: call.data.startswith('thread_select_'))
def on_select_group_pressed(call: telebot.types.CallbackQuery) -> None:
    thread: int = int(call.data.split('_')[2])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text='Выберите пункт меню',
        reply_markup=keyboards.get_thread_menu(thread)
    )


# при выборе пункта меню в треде
@bot.callback_query_handler(
    func=lambda call: call.data.startswith('thread_menu') or call.data.startswith('back_to_function_list_for_')
)
def on_menu_thread_pressed(call: telebot.types.CallbackQuery) -> None:
    thread_id: int = int(call.data.split('_')[-1])

    if 'all_rules' in call.data:
        pass

    elif 'new_rule' in call.data:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text='Выберите функцию для привязки',
            reply_markup=keyboards.get_function_list(thread_id)
        )

    elif 'clear_rules' in call.data:
        pass


# при выборе функции привязки
@bot.callback_query_handler(func=lambda call: call.data.startswith('answer'))
def on_function_select(call: telebot.types.CallbackQuery) -> None:
    call.data = call.data.split('_for_')

    thread_id: int = int(call.data[1])
    function_name: str = call.data[0]

    DBWorker.RegexpWaitManager.create_new(
        thread_id=thread_id,
        telegram_id=call.from_user.id,
        function_name=function_name
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text='Введите регулярное выражение',
        reply_markup=keyboards.back_to_menu_group_markup
    )


def start_poll() -> None:
    bot.infinity_polling()
    global stop
    stop = True
