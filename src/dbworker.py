"""
    Просто класс-обёртка для более удобного и инкапсулированного работы с бд
"""

from src.database.models import *
from datetime import datetime


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
        def get_group_by_id(id_group: int) -> Group:
            return Group.get_or_none(Group.id == id_group)

        @staticmethod
        def get_group_by_chat_id(chat_id: int) -> Group | None:
            return Group.get(Group.chat_id == chat_id)

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

        @staticmethod
        def get_log_threads() -> tuple[MessageThread] | None:
            return MessageThread.select().where(MessageThread.is_log_chat == True)

        @staticmethod
        def thread_is_log(thread_id: int) -> bool:
            return DBWorker.MessageThreadManager.get_thread_by_id(thread_id).is_log_chat

        @staticmethod
        def set_log_status(thread_id: int, is_log: bool):
            thread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            thread.is_log_chat = is_log
            thread.save()

    class RegexWaitManager:
        @staticmethod
        def get_by_telegram_id(telegram_id: int) -> RegexWait:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            return RegexWait.get(RegexWait.user == user)

        @staticmethod
        def user_in_wait_list(telegram_id: int) -> bool:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            return True if RegexWait.get_or_none(RegexWait.user == user) is not None else False

        @staticmethod
        def get_stage(telegram_id: int) -> str | None:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)
            r = RegexWait.get_or_none(RegexWait.user == user)

            return r.stage if r is not None else None

        @staticmethod
        def set_stage(telegram_id: int, new_stage: str) -> None:
            user: User = DBWorker.UserManager.get_by_telegram_id(telegram_id)
            r: RegexWait = RegexWait.get_or_none(RegexWait.user == user)
            r.stage = new_stage
            r.save()

        @staticmethod
        def create_new(thread_id: int, telegram_id: int, function_name: str, delay=None) -> RegexWait:
            thread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            user = DBWorker.UserManager.get_by_telegram_id(telegram_id)

            new_regex: RegexWait = RegexWait.create(
                thread=thread,
                user=user,
                function_name=function_name,
                delay=delay
            )

            new_regex.save()

            return new_regex

        @staticmethod
        def delete_by_telegram_id(telegram_id: int) -> None:
            DBWorker.RegexWaitManager.get_by_telegram_id(telegram_id).delete_instance()

    class ActionManager:
        @staticmethod
        def get_by_id(action_id: int) -> Action:
            return Action.get(Action.id == action_id)

        @staticmethod
        def create_new(thread_id: int, regular_expression: str, def_name: str, text: str) -> Action:
            thread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)

            new_action = Action.create(
                thread=thread,
                regular_expression=regular_expression,
                def_name=def_name,
                text=text
            )

            new_action.save()

            return new_action

        @staticmethod
        def set_text(action_id: int, text: str):
            action = DBWorker.ActionManager.get_by_id(action_id)
            action.text = text
            action.save()

        @staticmethod
        def get_rules_for_thread(thread_id: int) -> tuple[Action] | None:
            thread: MessageThread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            return Action.select().where(Action.thread == thread)

        @staticmethod
        def clear_rules_for_thread(thread_id: int) -> None:
            thread: MessageThread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            actions: tuple[Action] = Action.select().where(Action.thread == thread)

            for action in actions:
                action.delete_instance()

    class DeleteListManager:
        @staticmethod
        def create_new(thread_id: int, message_id: int, time_delete: datetime) -> DeleteList:
            thread: MessageThread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            new_delete_list: DeleteList = DeleteList.create(
                thread=thread,
                message_id=message_id,
                time_delete=time_delete
            )

            new_delete_list.save()

            return new_delete_list

        @staticmethod
        def get_all_delete_list() -> tuple[DeleteList]:
            return DeleteList.select()

        @staticmethod
        def get(thread_id: int, message_id: int) -> DeleteList:
            thread: MessageThread = DBWorker.MessageThreadManager.get_thread_by_id(thread_id)
            return DeleteList.get(
                DeleteList.thread == thread,
                DeleteList.message_id == message_id
            )
