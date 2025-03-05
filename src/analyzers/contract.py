"""合约信息分析器"""

from datetime import datetime

from .base import BaseAnalyzer


class ContractInfoAnalyzer(BaseAnalyzer):
    """合约基本信息分析器"""

    async def execute(self):
        """获取并显示合约基本信息"""
        try:
            contract_info = await self.handler.get_contract_info()
            self._log_info("\n合约信息:", contract_info)
        except Exception as e:
            self._handle_error(e, "获取合约信息失败")


class OwnershipAnalyzer(BaseAnalyzer):
    """合约所有权分析器"""

    def __init__(self, quick_mode: bool = False):
        """初始化所有权分析器
        
        Args:
            quick_mode: 是否使用快速检查模式，默认为 False
        """
        super().__init__()
        self.quick_mode = quick_mode

    async def execute(self):
        """分析合约所有权状态"""
        try:
            if self.quick_mode:
                ownership_info = await self.handler.quick_check_ownership()
                self._display_quick_info(ownership_info)
            else:
                ownership_info = await self.handler.check_ownership()
                self._display_ownership_info(ownership_info)
        except Exception as e:
            self._handle_error(e, "检查所有权失败")

    def _display_quick_info(self, info: dict):
        """显示快速检查的所有权信息"""
        if info['is_renounced']:
            self._log_warning("合约所有权已被放弃！")
            self._log_info("当前 owner 是零地址")
        else:
            self._log_info("当前 owner:", {'address': info['current_owner']})

    def _display_ownership_info(self, info: dict):
        """显示完整的所有权信息"""
        if info['is_renounced']:
            self._log_warning("合约所有权已被放弃！")
            self._log_info("最后的 owner 已将所有权转移给了零地址")
        else:
            self._log_info("当前 owner:", {'address': info['current_owner']})

        self._log_info("\n所有权转移历史:")
        for event in info['transfer_history']:
            timestamp = datetime.fromtimestamp(event['timestamp'])
            self._log_info(
                f"区块 {event['block_number']} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})",
                {
                    '交易哈希': event['tx_hash'],
                    '执行者': event['from_address'],
                    '转移': f"{event['previous_owner']} -> {event['new_owner']}"
                }
            )
