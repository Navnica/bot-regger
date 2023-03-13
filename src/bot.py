import peewee
import telebot
import json
import threading
import logging
import sys
from src import keyboards
from src.dbworker import DBWorker
from src.regexpworker import RegexWorker
import datetime

logging.basicConfig(
    level=logging.INFO,
    format="(%(asctime)s) [%(levelname)s] %(message)s",
    datefmt="%d:%m:%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)

telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(json.load(open('config.json', encoding='utf-8'))['token'])
stop = False


def log(message: telebot.types.Message | telebot.types.CallbackQuery | str, log_level: int) -> None:
    for log_thread in DBWorker.MessageThreadManager.get_log_threads():
        match str(type(message)):
            case "<class 'str'>":
                bot.send_message(
                    chat_id=log_thread.group.chat_id,
                    message_thread_id=log_thread.thread_id,
                    text=message
                )

                logging.log(log_level, message)

            case "<class 'telebot.types.CallbackQuery'>":
                text = f'{message.from_user.username} pressed on {message.data} at {datetime.datetime.now()}'
                bot.send_message(
                    chat_id=log_thread.group.chat_id,
                    message_thread_id=log_thread.thread_id,
                    text=text
                )

                logging.log(log_level, text)

            case "<class 'telebot.types.Message'>":
                text = f'{message.from_user} send {message.text} to {message.chat.id}::{message.message_thread_id}'

                bot.forward_message(
                    chat_id=log_thread.group.chat_id,
                    message_thread_id=log_thread.thread_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )

                logging.log(log_level, text)


def message_cleaner() -> None:
    global stop
    while True:
        if stop: return
        for msg in DBWorker.DeleteListManager.get_all_delete_list():
            if datetime.datetime.now() > msg.time_delete:
                try:
                    bot.delete_message(chat_id=msg.thread.group.chat_id,
                                       message_id=msg.message_id)

                    log(f'Message {msg.message_id} for {msg.thread.group.title}::{msg.thread.thread_id} was deleted',
                        logging.INFO)

                except peewee.OperationalError:
                    log('Message ' + msg.message_id + 'does not exists. Skip', logging.WARNING)

                msg.delete_instance()


cleaner = threading.Thread(target=message_cleaner)
cleaner.start()

"""
    _____________________________________MESSAGE ZONE_____________________________________
"""

# при любом сообщении в группу
@bot.message_handler(chat_types=['group', 'supergroup'])
def on_group_message(message: telebot.types.Message):
    DBWorker.UserManager.user_is_admin(message.from_user.id)

    group = DBWorker.GroupManager.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title,
        group_type=message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=message.message_thread_id
    )

    action = RegexWorker.message_match(message_thread.id, message.text)

    if action:
        match action.def_name:
            case 'answer':
                bot.reply_to(message, action.text)

            case 'answer_delete_after' | 'answer_yes_no':
                new_message = bot.reply_to(
                    message=message,
                    text=action.text,
                    reply_markup=keyboards.yes_no_markup if action.def_name == 'answer_yes_no' else None
                )

                DBWorker.DeleteListManager.create_new(
                    thread_id=message_thread.id,
                    message_id=message.message_id,
                    time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
                )

                DBWorker.DeleteListManager.create_new(
                    thread_id=message_thread.id,
                    message_id=new_message.message_id,
                    time_delete=datetime.datetime.now() + datetime.timedelta(seconds=action.time_out_value)
                )


# для регистрации приватного чата в список
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.UserManager.user_is_admin(message.from_user.id),
    commands=['register']
)
def on_chat_register(message: telebot.types.Message):
    log(message, logging.INFO)
    group = DBWorker.GroupManager.get_or_create(
        chat_id=message.chat.id,
        title=str(message.from_user.id) if not message.from_user.username else message.from_user.username,
        group_type=message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=message.message_thread_id
    )

    bot.send_message(
        text='Чат был добавлен в список',
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
    )


# при сообщении админа в личку
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.UserManager.user_is_admin(message.from_user.id),
    commands=['groups']
)
def on_private_admin_message(message: telebot.types.Message) -> None:
    log(message, logging.INFO)
    bot.send_message(
        text='Выберите группу',
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        reply_markup=keyboards.get_group_list_markup()
    )


# при сообщении от пользователя, который должен ввести регулярное выражение
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'regex_wait'
)
def on_regex_stage_is_regex_wait(message: telebot.types.Message) -> None:
    log(message, logging.INFO)
    if not RegexWorker.regex_is_correct(message.text):
        bot.send_message(
            text='Заданное выражение неверно',
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            reply_markup=keyboards.back_to_menu_group_markup
        )

        return

    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(message.from_user.id)
    function_name: str = regex_wait.function_name
    regex_text: str = message.text
    answer_text: str = 'Введите текст ответа'

    new_action = DBWorker.ActionManager.create_new(
        thread_id=regex_wait.thread.id,
        regular_expression=regex_text,
        def_name=function_name,
        text='None'
    )

    regex_wait.set_action(new_action)

    match function_name:
        case 'answer':
            regex_wait.set_stage('answer_text')

        case 'answer_delete_after' | 'answer_yes_no':
            regex_wait.set_stage('time_delay')
            answer_text = 'Введите время удаления'

    bot.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text=answer_text,
        reply_markup=keyboards.back_to_menu_group_markup
    )


# при сообщении от пользователя, от которого ождиается ввод времени удаления
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'time_delay'
)
def on_regex_stage_is_time_delay(message: telebot.types.Message) -> None:
    log(message, logging.INFO)
    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(message.from_user.id)

    if not message.text.isdigit():
        bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            text='Время удаления должно быть целочисленным',
            reply_markup=keyboards.back_to_menu_group_markup
        )

        return

    regex_wait.action.set_delay(int(message.text))
    regex_wait.set_stage('answer_text')

    bot.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text='Введите текст ответа',
        reply_markup=keyboards.back_to_menu_group_markup
    )


# при сообщении от пользователя, от которого ождиается ввод текста для выражения
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'answer_text'
)
def on_regex_stage_is_answer_text(message: telebot.types.Message) -> None:
    log(message, logging.INFO)
    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(message.from_user.id)
    regex_wait.action.set_text(message.text)

    regex_wait.set_stage('name_wait')

    bot.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text='Введите имя для правила',
        reply_markup=keyboards.back_to_menu_group_markup
    )


# при сообщении от пользователя, от которого ождиается ввод имени для правила
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'name_wait'
)
def on_regex_stage_is_answer_text(message: telebot.types.Message) -> None:
    log(message, logging.INFO)
    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(message.from_user.id)
    regex_wait.action.set_name(message.text)

    regex_wait.delete_instance()

    bot.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text='Выражение создано',
        reply_markup=keyboards.back_to_menu_group_markup
    )


"""
    _____________________________________CALLBACK ZONE_____________________________________
"""


# при нажатии на "да"
@bot.callback_query_handler(
    func=lambda call: call.data == 'markup_yes' and
                      call.from_user.id == call.message.reply_to_message.from_user.id
)
def on_press_yes(call: telebot.types.CallbackQuery) -> None:
    log(call, logging.INFO)
    group = DBWorker.GroupManager.get_or_create(
        chat_id=call.message.chat.id,
        title=call.message.chat.title,
        group_type=call.message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=call.message.reply_to_message.message_thread_id
    )

    DBWorker.DeleteListManager.get(message_thread.id, call.message.reply_to_message.message_id).delete_instance()
    DBWorker.DeleteListManager.get(message_thread.id, call.message.message_id).delete_now()


# при нажатии на "нет"
@bot.callback_query_handler(
    func=lambda call: call.data == 'markup_no' and
                      call.from_user.id == call.message.reply_to_message.from_user.id
)
def on_press_yes(call: telebot.types.CallbackQuery) -> None:
    log(call, logging.INFO)
    group = DBWorker.GroupManager.get_or_create(
        chat_id=call.message.chat.id,
        title=call.message.chat.title,
        group_type=call.message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=call.message.reply_to_message.message_thread_id
    )

    DBWorker.DeleteListManager.get(message_thread.id, call.message.reply_to_message.message_id).delete_now()
    DBWorker.DeleteListManager.get(message_thread.id, call.message.message_id).delete_now()


# при нажатии на "вернуться в меню групп"
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_group_menu')
def back_to_group_menu(call: telebot.types.CallbackQuery):
    log(call, logging.INFO)
    if DBWorker.RegexWaitManager.user_in_wait_list(call.from_user.id):
        regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(call.from_user.id)
        if regex_wait.action is not None:
            regex_wait.action.delete_instance()

        regex_wait.delete_instance()

    bot.edit_message_text(
        text='Выберите группу',
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        reply_markup=keyboards.get_group_list_markup()
    )


# при выборе группы
@bot.callback_query_handler(func=lambda call: call.data.startswith('group_select_'))
def on_select_group_pressed(call: telebot.types.CallbackQuery) -> None:
    log(call, logging.INFO)
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
    log(call, logging.INFO)
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
    log(call, logging.INFO)
    thread_id: int = int(call.data.split('_')[-1])

    if 'all_rules' in call.data:
        rules = DBWorker.ActionManager.get_rules_for_thread(thread_id)
        answer: str = 'Правила для треда ' + str(thread_id) + '\n\n'

        if not rules:
            answer = 'Для данного треда правил пока нет'

        for rule in rules:
            answer += f'{rule.name} <b>{rule.regular_expression}</b> <i>{rule.text}</i> <code>{rule.def_name}</code> {rule.time_out_value}\n'

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text=answer,
            reply_markup=keyboards.back_to_menu_group_markup,
            parse_mode='HTML'
        )

    elif 'new_rule' in call.data:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text='Выберите функцию для привязки',
            reply_markup=keyboards.get_function_list(thread_id)
        )

    elif 'clear_rules' in call.data:
        DBWorker.ActionManager.clear_rules_for_thread(thread_id)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text='Правила были удалены',
            reply_markup=keyboards.back_to_menu_group_markup
        )


# при выборе функции привязки
@bot.callback_query_handler(func=lambda call: call.data.startswith('answer'))
def on_function_select(call: telebot.types.CallbackQuery) -> None:
    log(call, logging.INFO)
    call.data = call.data.split('_for_')

    thread_id: int = int(call.data[1])
    function_name: str = call.data[0]

    DBWorker.RegexWaitManager.create_new(
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


# при нажатии на сделать лог-чатом\ сделать обычным
@bot.callback_query_handler(func=lambda call: call.data.startswith('log_'))
def on_log_switch(call: telebot.types.CallbackQuery) -> None:
    log(call, logging.INFO)

    thread_id: int = int(call.data.split('_')[-1])

    DBWorker.MessageThreadManager.set_log_status(thread_id, False if 'off' in call.data else True)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text='Выберите пункт меню',
        reply_markup=keyboards.get_thread_menu(thread_id)
    )


"""
    _____________________________________UNNAMED ZONE_____________________________________
"""


@bot.middleware_handler(
    update_types=['text', 'audio', 'document', 'photo', 'sticker', 'video', 'video_note', 'voice', 'location',
                  'contact', 'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
                  'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created', 'channel_chat_created',
                  'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message', "web_app_data"])
def on_any_action(bot_instance, call):
    log(str(call), logging.INFO)


def start_poll() -> None:
    bot.infinity_polling()
    global stop
    stop = True
