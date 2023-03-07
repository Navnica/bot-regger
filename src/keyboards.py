from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database import models

yes_no_markup = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text='Да',
                callback_data='markup_yes'
            ),

            InlineKeyboardButton(
                text='Нет',
                callback_data='markup_no'
            )
        ]
    ]
)

admin_menu = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text='Список групп',
                callback_data='group_list'
            )
        ]
    ]
)


def group_list_generate() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()

    [
        kb.add(
            InlineKeyboardButton(
                text=group.title,
                callback_data=f'group_{group.chat_id}',
                data=group
            )
        ) for group in models.Group.select()
    ]

    return kb
