import telebot
import json
import regexpparser
import threading
import models

bot = telebot.TeleBot(json.load(open('config.json', encoding='utf-8'))['token'])


@bot.message_handler(content_types=['text'])
def get_text_messages(message: telebot.types.Message) -> None:
    if not models.User.get(models.User.telegram_id == message.from_user.id):
        models.User.create(telegram_id=message.from_user.id)

    if message.text.startswith('regex'):
        regexpparser.RegexpParser(message).parse_regex()
    else:
        answer_text = regexpparser.RegexpParser(message).parse_message()

        if answer_text:
            bot.send_message(
                text=answer_text,
                chat_id=message.chat.id,
                message_thread_id=message.message_thread_id
            )
