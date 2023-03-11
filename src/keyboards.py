from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.dbworker import DBWorker

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

back_to_menu_group_markup: InlineKeyboardMarkup = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text='<',
                callback_data='back_to_group_menu'
            )
        ]
    ]
)


def get_group_list_markup() -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup()

    for group in DBWorker.GroupManager.get_all_groups():
        kb.add(
            InlineKeyboardButton(
                text=group.title,
                callback_data=f'group_select_{group.id}'
            )
        )

    return kb


def get_threads_linked_group_by_group_id(group_id: int) -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup()

    group = DBWorker.GroupManager.get_group_by_id(id_group=group_id)
    linked_threads = DBWorker.MessageThreadManager.get_all_threads_by_group(group=group)

    for thread in linked_threads:
        kb.add(
            InlineKeyboardButton(
                text='Main' if thread.thread_id is None else str(thread.thread_id),
                callback_data=f'thread_select_{thread.id}'
            )
        )

    return kb


def get_thread_menu(thread_id: int) -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text='Все правила',
                    callback_data=f'thread_menu_all_rules_for_{thread_id}'
                ),

                InlineKeyboardButton(
                    text='Новое правило',
                    callback_data=f'thread_menu_new_rule_for_{thread_id}'
                ),

            ]
        ]
    )

    kb.row(
        InlineKeyboardButton(
            text='Сбросить правила',
            callback_data=f'thread_menu_clear_rules_for_{thread_id}'
        ))

    return kb


def get_function_list(thread_id: int) -> InlineKeyboardMarkup:
    kb: InlineKeyboardMarkup = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            text='answer',
            callback_data=f'answer_for_{thread_id}'
        )
    )

    kb.add(
        InlineKeyboardButton(
            text='answer_delete_after',
            callback_data=f'answer_delete_after_for_{thread_id}'
        )
    )

    kb.add(
        InlineKeyboardButton(
            text='answer_yes_no',
            callback_data=f'answer_yes_no_for_{thread_id}'
        )
    )

    return kb


def get_with_back_button(thread_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text='<',
                    callback_data=f'back_to_function_list_for_{thread_id}'
                )
            ]
        ]
    )
