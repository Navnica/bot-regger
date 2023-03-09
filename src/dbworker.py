"""
    Просто класс-обёртка для более удобного и инкапсулированного работы с бд
"""

from src.database.models import *


class DBWorker:
    class UserManager:
        @staticmethod
        def user_is_admin(telegram_id: int = 0) -> None:
            return User.get_or_create(telegram_id=telegram_id)[0].power_level >= 1 # не забыть изменить потом на 2

    class GroupManager:
        @staticmethod
        def get_all_groups() -> tuple[Group]:
            return Group.select()

        @staticmethod
        def get_group_by_id(id_group: int) -> Group | None:
            return Group.get_or_none(Group.id == id_group)

        @staticmethod
        def get_or_create(chat_id: int, title: str, group_type: str) -> Group:
            return Group.get_or_create(
                chat_id=chat_id,
                title=title,
                type=group_type
            )[0]

    class MessageThreadManager:
        @staticmethod
        def get_thread_by_id(thread_id: int) -> MessageThread | None:
            return MessageThread.get_or_none(MessageThread.id == thread_id)

        @staticmethod
        def get_all_threads_by_group(group: Group) -> tuple[MessageThread]:
            return MessageThread.select().where(MessageThread.group == group)

        @staticmethod
        def get_or_create(group: Group, thread_id: int) -> MessageThread:
            return MessageThread.get_or_create(
                group=group,
                thread_id=thread_id
            )[0]
