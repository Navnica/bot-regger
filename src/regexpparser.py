import re
from telebot.types import Message


class RegexpParser:
    message: Message = None

    @staticmethod
    def regex_correct(regex: str) -> bool:
        try:
            re.compile(regex)
            return True

        except re.error:
            return False

