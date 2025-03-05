"""链检测器模块"""

import asyncio
from typing import Dict, Optional

from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import geth_poa_middleware

from .base import BaseAnalyzer
from .dex.base import DexAnalyzer
from ..config.constants import CHAINS


class ChainDetector(BaseAnalyzer):
    """链检测器类"""

    def __init__(self, contract_address: str):
        """初始化链检测器
        
        Args:
            contract_address: 要检测的合约地址
        """
        super().__init__()
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.detected_chain = None
        self.contract_code = None
        self.web3 = None
        self.chain_id = None
        self.dex_analyzer = None

    async def execute(self):
        """执行链检测"""
        try:
            # 1. 检测合约所在的链
            chain_info = await self._detect_chain()
            if not chain_info:
                self._log_warning("未能确定合约所在的链")
                return

            self.detected_chain = chain_info
            self.chain_id = chain_info['chain_id']  # 使用数字 chain_id
            self._log_info(f"\n合约所在链: {chain_info['name']}")

            # 2. 初始化 Web3 实例
            self.web3 = self._init_web3(chain_info['rpc']['public'])
            if not self.web3:
                self._log_warning("无法连接到链")
                return

            # 3. 检查合约代码
            if not await self._check_contract_code():
                self._log_warning("该地址不是合约地址")
                return

            # 4. 初始化 DEX 分析器
            self.dex_analyzer = DexAnalyzer(self.contract_address)
            self.dex_analyzer.web3 = self.web3
            self.dex_analyzer.chain_id = self.chain_id

            # 5. 获取合约基本信息
            token_info = self.dex_analyzer.get_token_info(self.contract_address)
            if token_info:
                self._log_info("\n代币信息:", token_info)
            else:
                self._log_warning("无法读取代币信息，可能不是标准的ERC20代币")

            # 6. 检查所有DEX的池子
            found_pools = await self.dex_analyzer.check_dex_pools(self.chain_id)
            if not found_pools:
                self._log_warning("\n✗ 未在主要DEX上发现交易对")

        except Exception as e:
            self._handle_error(e, "链检测失败")

    def _init_web3(self, rpc_url: str) -> Optional[Web3]:
        """初始化Web3实例"""
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # 添加 POA 中间件
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if not web3.is_connected():
                return None
                
            return web3
            
        except Exception as e:
            self._log_warning(f"初始化 Web3 失败: {e}")
            return None

    async def _detect_chain(self) -> Optional[Dict]:
        """检测合约所在的链"""
        self._log_info("\n开始检测合约所在链...")
        
        for chain_id, chain_info in CHAINS.items():
            try:
                web3 = Web3(Web3.HTTPProvider(chain_info['rpc']['public']))
                web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                # 检查连接
                if not web3.is_connected():
                    continue

                # 尝试获取合约代码
                code = web3.eth.get_code(self.contract_address)
                if code and code != '0x':
                    self._log_info(f"✓ 在 {chain_info['name']} 上发现合约")
                    return chain_info

            except Exception:
                continue

        return None

    async def _check_contract_code(self) -> bool:
        """检查合约代码"""
        try:
            self.contract_code = self.web3.eth.get_code(self.contract_address)
            return bool(self.contract_code and self.contract_code != '0x')
        except Exception as e:
            self._log_warning(f"获取合约代码失败: {e}")
            return False 