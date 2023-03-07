from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

yes_no_markup = InlineKeyboardMarkup()
yes_no_markup.add(InlineKeyboardButton(text='Да', callback_data='markup_yes'))
yes_no_markup.add(InlineKeyboardButton(text='Нет', callback_data='markup_no'))

