"""池子分析器"""

from typing import Dict, Optional

from web3 import Web3

from .base import BaseAnalyzer
from .dex.base import DexAnalyzer
from ..config.constants import EVENT_SIGNATURES


class PoolAnalyzer(BaseAnalyzer):
    """DEX 池子分析器"""

    def __init__(self, tx_hash: str = None):
        """初始化池子分析器
        
        Args:
            tx_hash: 可选的交易哈希，用于分析特定交易
        """
        super().__init__()
        self.tx_hash = tx_hash
        self.web3 = None
        self.chain_id = None
        self.dex_analyzer = None

    async def execute(self):
        """执行池子分析"""
        try:
            if self.tx_hash:
                await self._analyze_pool_creation()
            else:
                await self._check_all_pools()
        except Exception as e:
            self._handle_error(e, "池子分析失败")

    async def _check_all_pools(self):
        """检查所有 DEX 的池子状态"""
        self._log_info("\n流动性状态:")

        # 获取当前链信息
        current_chain_id = self.handler.web3.eth.chain_id
        self.chain_id = current_chain_id
        self.web3 = self.handler.web3

        # 初始化分析器
        self.dex_analyzer = DexAnalyzer(self.config.contract_address)
        self.dex_analyzer.web3 = self.web3
        self.dex_analyzer.chain_id = self.chain_id

        # 检查池子
        found_pools = await self.dex_analyzer.check_dex_pools(self.chain_id)
        if not found_pools:
            self._log_warning("✗ 未在主要DEX上发现交易对")

    async def _analyze_pool_creation(self):
        """分析池子创建交易"""
        if not self.tx_hash:
            self._log_warning("未提供交易哈希")
            return

        self._log_info(f"分析交易: {self.tx_hash}")

        # 获取交易详情
        receipt = self.handler.web3.eth.get_transaction_receipt(self.tx_hash)
        tx = self.handler.web3.eth.get_transaction(self.tx_hash)

        self._log_info("\n交易基本信息:", {
            '区块号': receipt['blockNumber'],
            '发送者': tx['from'],
            '接收者': tx['to'],
            'Value': tx['value']
        })

        # 解析交易日志
        self._log_info("\n交易日志:")
        for i, log in enumerate(receipt['logs']):
            self._log_info(f"\n日志 #{i + 1}:")
            await self._parse_log(log)

    async def _parse_log(self, log: dict):
        """解析交易日志"""
        self._log_info("合约地址:", {'address': log['address']})

        if not log['topics']:
            return

        event_signature = log['topics'][0].hex()
        event_name = self._get_event_name(event_signature)
        self._log_info("事件:", {'name': event_name})

        if event_name == 'PAIR_CREATED':
            # 初始化分析器
            if not self.dex_analyzer:
                self.dex_analyzer = DexAnalyzer()
                self.dex_analyzer.web3 = self.handler.web3
                self.dex_analyzer.chain_id = self.handler.web3.eth.chain_id

            # 分析创建事件
            creation_info = await self.dex_analyzer.analyze_pair_creation(self.tx_hash)
            if creation_info:
                self._log_info("创建交易对:", creation_info)

    def _get_event_name(self, signature: str) -> str:
        """获取事件名称"""
        for name, sig in EVENT_SIGNATURES.items():
            if sig == signature:
                return name
        return 'Unknown'
