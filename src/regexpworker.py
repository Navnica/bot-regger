from src import dbworker
import re


class RegexWorker:
    @staticmethod
    def regex_is_correct(regex: str) -> bool:
        try:
            re.compile(regex)
            return True
        except re.error:
            return False