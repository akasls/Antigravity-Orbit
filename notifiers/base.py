from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    @abstractmethod
    def send(self, project_name: str, status: str, summary: str) -> bool:
        """发送通知，成功返回 True，失败返回 False"""
        pass

    @abstractmethod
    def test(self) -> tuple[bool, str]:
        """测试通道连通性，返回 (是否成功, 详细信息)"""
        pass
