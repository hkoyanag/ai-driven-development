from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    @abstractmethod
    def ask_assignment(self, prompt: str) -> str:
        """
        チケット内容とメンバーのコンテキストを受け取り、
        アサインすべきメンバーの氏名をJSON形式の文字列で返却する抽象メソッド。
        """
        pass