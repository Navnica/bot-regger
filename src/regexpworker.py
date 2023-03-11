from src.dbworker import DBWorker
import re


class RegexWorker:
    @staticmethod
    def regex_is_correct(regex: str) -> bool:
        try:
            re.compile(regex)
            return True
        except re.error:
            return False

    @staticmethod
    def message_match(thread_id: int, message_text: str):
        actions_for_thread = DBWorker.ActionManager.get_rules_for_thread(thread_id)

        for rule in actions_for_thread:
            if re.match(rule.regular_expression, message_text) is not None:
                return rule

        return None
