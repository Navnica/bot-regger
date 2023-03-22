import time

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
import pprint

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

FORWARDED_TYPES = [
    'text', 'audio', 'document', 'photo', 'sticker', 'video', 'video_note', 'voice', 'location',
    'contact'
]


def check_regex_in_thread_history(chat_id: int, message_thread_id: int, regex_text: str, checking_thread: int, start_i: int = 0) -> None:
    thread_history = DBWorker.ThreadHistory.get_history_for_thread(checking_thread)
    i: int = 0
    match_list: list = []
    match_num: int = 3
    end_i: int = 0

    for msg in thread_history:
        i += 1
        if i < start_i:
            continue

        if RegexWorker.simple_match(regex_text, msg.text):
            match_list.append(msg)

        if len(match_list) == match_num:
            end_i = i
            break

    if len(match_list) == 0:
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text='Для данного чата не найдено попаданий под правила. Продолжить?',
            reply_markup=keyboards.get_confirm_keyboard(False)
        )

    else:
        text: str = ''
        for msg in match_list:
            text += f'{msg.text}\n\n'

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text=text
        )

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text='Данные сообщения попададут под правило. Продолжить?',
            reply_markup=keyboards.get_confirm_keyboard(True, i+1)
        )


def delete_none(_dict):
    new_dict = {}

    for key, value in _dict.items():
        try:
            new_dict.update(delete_none(value.__dict__))

        except AttributeError:
            if value is not None:
                new_dict.update({key: value})

    return new_dict


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

                except (peewee.OperationalError, telebot.apihelper.ApiTelegramException):
                    log(update=f'Message {msg.message_id} does not exists. Skip', log_level=logging.WARNING)

                msg.delete_instance()


cleaner = threading.Thread(target=message_cleaner)
cleaner.start()

"""
    _____________________________________MESSAGE ZONE_____________________________________
"""


# при любом сообщении в группу
@bot.message_handler(chat_types=['group', 'supergroup'])
def on_group_message(message: telebot.types.Message):
    user = DBWorker.UserManager.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    group = DBWorker.GroupManager.get_or_create(
        chat_id=message.chat.id,
        title=message.chat.title,
        group_type=message.chat.type
    )

    message_thread = DBWorker.MessageThreadManager.get_or_create(
        group=group,
        thread_id=message.message_thread_id
    )

    thread_history = DBWorker.ThreadHistory.create_new(
        thread_id=message_thread.id,
        from_user=user.telegram_id,
        message_id=message.message_id,
        text=message.text
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
    func=lambda message: DBWorker.UserManager.user_is_admin(message.from_user.id, message.from_user.username),
    commands=['register']
)
def on_chat_register(message: telebot.types.Message):
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
    func=lambda message: DBWorker.UserManager.user_is_admin(message.from_user.id, message.from_user.username),
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
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'regex_wait'
)
def on_regex_stage_is_regex_wait(message: telebot.types.Message) -> None:
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

    new_action = DBWorker.ActionManager.create_new(
        thread_id=regex_wait.thread.id,
        regular_expression=regex_text,
        def_name=function_name,
        text='None'
    )

    new_action.save()

    regex_wait.set_action(new_action)
    regex_wait.set_stage('confirm_wait')

    check_regex_in_thread_history(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        regex_text=regex_text,
        checking_thread=regex_wait.thread.id
    )


# при сообщении от пользователя, от которого ождиается ввод времени удаления
@bot.message_handler(
    chat_types=['private'],
    func=lambda message: DBWorker.RegexWaitManager.get_stage(message.from_user.id) == 'time_delay'
)
def on_regex_stage_is_time_delay(message: telebot.types.Message) -> None:
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
    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(message.from_user.id)
    regex_wait.action.set_name(message.text)
    regex_wait.action.set_enable(True)

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


# при нажатии на сделать лог-чатом сделать обычным
@bot.callback_query_handler(func=lambda call: call.data.startswith('log_'))
def on_log_switch(call: telebot.types.CallbackQuery) -> None:
    thread_id: int = int(call.data.split('_')[-1])

    DBWorker.MessageThreadManager.set_log_status(thread_id, False if 'off' in call.data else True)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text='Выберите пункт меню',
        reply_markup=keyboards.get_thread_menu(thread_id)
    )


# при выборе чего-то из меню подтвреждения выражения
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def on_confirm_press(call: telebot.types.CallbackQuery) -> None:
    command: str = call.data.split('_')[1]
    regex_wait = DBWorker.RegexWaitManager.get_by_telegram_id(call.from_user.id)
    answer_text: str = 'Введите текст ответа'

    match command:
        case 'yes':
            match regex_wait.function_name:
                case 'answer':
                    regex_wait.set_stage('answer_text')

                case 'answer_delete_after' | 'answer_yes_no':
                    regex_wait.set_stage('time_delay')
                    answer_text = 'Введите время удаления'

        case 'no':
            regex_wait.set_stage('regex_wait')
            answer_text = 'Введите регулярное выражение'

        case 'continue':
            start_i: int = int(call.data.split('_')[-1])

            check_regex_in_thread_history(
                chat_id=call.message.chat.id,
                message_thread_id=call.message.message_thread_id,
                regex_text=regex_wait.action.regular_expression,
                checking_thread=regex_wait.thread.id,
                start_i=start_i
            )

            return

    bot.send_message(
        chat_id=call.message.chat.id,
        message_thread_id=call.message.message_thread_id,
        text=answer_text,
        reply_markup=keyboards.back_to_menu_group_markup
    )


"""
    _____________________________________UNNAMED ZONE_____________________________________
"""


def log(update: telebot.types.Update | str, log_level: int = logging.INFO):

    if type(update) is not str:
        logging.log(log_level, pprint.pformat(delete_none(update.__dict__)))

    else:
        logging.log(log_level, pprint.pformat(update))

    for log_thread in DBWorker.MessageThreadManager.get_log_threads():
        if type(update) is str:
            bot.send_message(
                chat_id=log_thread.group.chat_id,
                message_thread_id=log_thread.thread_id,
                text=update
            )
            return

        update_dict: dict = delete_none(update.__dict__).copy()

        if update.message is not None:
            update_dict['content_type'] = update.message.content_type

        elif update.edited_message is not None:
            update_dict['content_type'] = update.edited_message.content_type

        if update.message is not None:
            if update.message.content_type in FORWARDED_TYPES:
                forwarded_message: telebot.types.Message = bot.forward_message(
                    chat_id=log_thread.group.chat_id,
                    message_thread_id=log_thread.thread_id,
                    message_id=update.message.message_id,
                    from_chat_id=update.message.chat.id
                )

                i: int = 1

                for text in telebot.util.smart_split(pprint.pformat(update_dict), 5000):
                    try:
                        bot.reply_to(
                            message=forwarded_message,
                            text=text
                        )
                    except telebot.apihelper.ApiTelegramException:
                        time.sleep(5)
                        log('Отказ REST. Ожидание')

            else:
                for text in telebot.util.smart_split(pprint.pformat(update_dict), 5000):
                    bot.send_message(
                        chat_id=log_thread.group.chat_id,
                        message_thread_id=log_thread.thread_id,
                        text=text
                    )

        else:
            for text in telebot.util.smart_split(pprint.pformat(update_dict), 5000):
                bot.send_message(
                    chat_id=log_thread.group.chat_id,
                    message_thread_id=log_thread.thread_id,
                    text=text
                )


@bot.middleware_handler()
def on_any_action(bot_instance: telebot.TeleBot, update: telebot.types.Update):
    if update.message is not None and update.message.content_type not in FORWARDED_TYPES:
        group = DBWorker.GroupManager.get_group_by_chat_id(
            chat_id=update.message.chat.id
        )

        message_thread = DBWorker.MessageThreadManager.get_or_create(
            group=group,
            thread_id=update.message.message_thread_id
        )

        DBWorker.DeleteListManager.create_new(
            thread_id=message_thread,
            message_id=update.message.message_id,
            time_delete=datetime.datetime.now()
        )

    try:
        log(update, logging.INFO)
    except:
        pass


def start_poll() -> None:
    bot.infinity_polling()
    global stop
    stop = True
