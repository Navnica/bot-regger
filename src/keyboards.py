from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database import models

yes_no_markup: InlineKeyboardMarkup = InlineKeyboardMarkup(
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

admin_menu: InlineKeyboardMarkup = InlineKeyboardMarkup(
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
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup()

    [
        kb.add(
            InlineKeyboardButton(
                text=group.title,
                callback_data=f'group_list_for_{group.chat_id}'
            )
        ) for group in models.Group.select()
    ]

    kb.add(
        InlineKeyboardButton(
            text='<',
            callback_data='back_to_admin_menu'
        )
    )

    return kb


def group_settings_generate(group: models.Group) -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup(
        keyboard=[
            [
                InlineKeyboardButton(
                    text='Существующие правила',
                    callback_data=f'exists_rules_for_{group.chat_id}'
                ),
            ]
        ],
    )

    kb.add(
        InlineKeyboardButton(
            text='Новое правило',
            callback_data=f'new_rule_for_{group.chat_id}'
        ),
    )

    kb.add(
        InlineKeyboardButton(
            text='Сбросить правила',
            callback_data=f'clear_rules_for_{group.chat_id}'
        ),
    )

    kb.add(
        InlineKeyboardButton(
            text='<',
            callback_data='back_to_group_list'
        )
    )

    return kb


def threads_list_generate(group: models.Group) -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup()

    for thread in models.MessageThread.select().where(models.MessageThread.group == group):
        kb.add(
            InlineKeyboardButton(
                text=thread.id,
                callback_data=f'select_thread_{thread.thread_id}_for_group_{group.chat_id}'
            )
        )

    kb.add(
        InlineKeyboardButton(
            text='<',
            callback_data='back_to_group_menu'
        )
    )

    return kb