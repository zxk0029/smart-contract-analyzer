"""基础分析器类"""

import sys

from ..config import Config
from ..handlers.event_handler import EventHandler
from ..utils.logger import logger


class BaseAnalyzer:
    """基础分析器类，提供共同的初始化和错误处理逻辑"""

    def __init__(self):
        """初始化配置和事件处理器"""
        self.config = Config.from_env()
        self.handler = EventHandler(self.config)

    async def execute(self):
        """执行分析，子类必须实现此方法"""
        raise NotImplementedError

    def _handle_error(self, e: Exception, message: str):
        """统一的错误处理"""
        logger.error(f"{message}: {e}")
        sys.exit(1)

    def _log_info(self, message: str, data: dict = None):
        """统一的信息日志记录"""
        logger.info(message)
        if data:
            for key, value in data.items():
                logger.info(f"{key}: {value}")

    def _log_warning(self, message: str):
        """统一的警告日志记录"""
        logger.warning(message)
