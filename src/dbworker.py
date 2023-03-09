"""
    Просто класс-обёртка для более удобного и инкапсулированного работы с бд
"""

from src.database.models import *


class DBWorker:
    class UserManager:
        @staticmethod
        def get_by_telegram_id(telegram_id: int) -> User:
            return User.get(User.telegram_id == telegram_id)

        @staticmethod
        def user_is_admin(telegram_id: int = 0) -> None:
            return User.get_or_create(telegram_id=telegram_id)[0].power_level >= 1  # не забыть изменить потом на 2

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

    class RegexpWaitManager:
        @staticmethod
        def get_by_telegram_id(telegram_id: int) -> RegexpWait:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            return RegexpWait.get(RegexpWait.user == user)

        @staticmethod
        def user_in_wait_list(telegram_id: int) -> bool:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            return True if RegexpWait.get_or_none(RegexpWait.user == user) is not None else False

        @staticmethod
        def create_new(thread_id: int, telegram_id: int, function_name: str) -> RegexpWait:
            thread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            user = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            new_regex: RegexpWait = RegexpWait.create(
                thread=thread,
                user=user,
                function_name=function_name
            )

            new_regex.save()

            return new_regex

        @staticmethod
        def delete_by_telegram_id(telegram_id: int) -> None:
            DBWorker.RegexpWaitManager.get_by_telegram_id(telegram_id).delete_instance()

    class ActionManager:
        @staticmethod
        def create_new() -> Action:
            pass