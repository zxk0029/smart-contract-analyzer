"""链检测器模块"""

import asyncio
from typing import Dict, List, Optional, Tuple

from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import geth_poa_middleware

from .base import BaseAnalyzer
from ..config.constants import (
    CHAINS,
    DEX_CONFIGS,
    STABLECOINS,
    TOKEN_ABI,
    FACTORY_ABI,
    FACTORY_V3_ABI,
    PAIR_ABI,
    POOL_V3_ABI
)
from ..utils.logger import logger


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

    async def execute(self):
        """执行链检测"""
        try:
            # 1. 检测合约所在的链
            chain_info = await self._detect_chain()
            if not chain_info:
                self._log_warning("未能确定合约所在的链")
                return

            self.detected_chain = chain_info
            self.chain_id = next(k for k, v in CHAINS.items() if v == chain_info)
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

            # 4. 获取合约基本信息
            await self._get_contract_info()

            # 5. 检查所有DEX的池子
            await self._check_all_dexes()

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

    async def _get_contract_info(self):
        """获取合约基本信息"""
        try:
            contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=TOKEN_ABI
            )

            info = {
                'name': contract.functions.name().call(),
                'symbol': contract.functions.symbol().call(),
                'decimals': contract.functions.decimals().call(),
                'total_supply': contract.functions.totalSupply().call()
            }

            self._log_info("\n代币信息:", info)

        except ContractLogicError:
            self._log_warning("无法读取代币信息，可能不是标准的ERC20代币")
        except Exception as e:
            self._log_warning(f"获取代币信息时出错: {e}")

    async def _check_all_dexes(self):
        """检查所有DEX的池子状态"""
        self._log_info("\n开始检查DEX池子...")
        
        if self.chain_id not in DEX_CONFIGS:
            self._log_warning(f"未找到 {self.chain_id} 的DEX配置")
            return

        dexes = DEX_CONFIGS[self.chain_id]
        stables = STABLECOINS[self.chain_id]
        wrapped_native = self.detected_chain['wrapped_native']

        for dex_id, dex_info in dexes.items():
            self._log_info(f"\n检查 {dex_info['name']}...")
            
            if dex_info['version'] == 2:
                await self._check_v2_pools(dex_info, wrapped_native, stables)
            elif dex_info['version'] == 3:
                await self._check_v3_pools(dex_info, wrapped_native, stables)

    async def _check_v2_pools(self, dex_info: Dict, wrapped_native: str, stables: Dict):
        """检查V2版本的池子"""
        factory = self.web3.eth.contract(
            address=self.web3.to_checksum_address(dex_info['factory']),
            abi=FACTORY_ABI
        )

        # 检查主要交易对
        pairs_to_check = [(wrapped_native, 'Wrapped Native')] + [
            (addr, name) for name, addr in stables.items()
        ]

        found_pairs = False
        for token_address, token_name in pairs_to_check:
            try:
                pair_address = factory.functions.getPair(
                    self.contract_address,
                    self.web3.to_checksum_address(token_address)
                ).call()

                if pair_address != '0x0000000000000000000000000000000000000000':
                    found_pairs = True
                    await self._get_v2_pair_info(
                        pair_address,
                        dex_info['name'],
                        token_name,
                        token_address
                    )
            except Exception as e:
                self._log_warning(f"检查 {token_name} 交易对时出错: {e}")

        if not found_pairs:
            self._log_info(f"✗ 在 {dex_info['name']} 上未找到交易对")

    async def _check_v3_pools(self, dex_info: Dict, wrapped_native: str, stables: Dict):
        """检查V3版本的池子"""
        factory = self.web3.eth.contract(
            address=self.web3.to_checksum_address(dex_info['factory']),
            abi=FACTORY_V3_ABI
        )

        # V3支持多个费率
        fee_tiers = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
        pairs_to_check = [(wrapped_native, 'Wrapped Native')] + [
            (addr, name) for name, addr in stables.items()
        ]

        found_pools = False
        for token_address, token_name in pairs_to_check:
            for fee in fee_tiers:
                try:
                    pool_address = factory.functions.getPool(
                        self.contract_address,
                        self.web3.to_checksum_address(token_address),
                        fee
                    ).call()

                    if pool_address != '0x0000000000000000000000000000000000000000':
                        found_pools = True
                        await self._get_v3_pool_info(
                            pool_address,
                            dex_info['name'],
                            token_name,
                            token_address,
                            fee
                        )
                except Exception as e:
                    self._log_warning(f"检查 {token_name} {fee/10000}% 池子时出错: {e}")

        if not found_pools:
            self._log_info(f"✗ 在 {dex_info['name']} 上未找到池子")

    async def _get_v2_pair_info(
        self,
        pair_address: str,
        dex_name: str,
        quote_token_name: str,
        quote_token_address: str
    ):
        """获取V2交易对信息"""
        try:
            pair_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(pair_address),
                abi=PAIR_ABI
            )

            # 获取池子信息
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call()
            
            # 确定代币位置
            is_token0 = token0.lower() == self.contract_address.lower()
            token_reserve = reserves[0] if is_token0 else reserves[1]
            quote_reserve = reserves[1] if is_token0 else reserves[0]

            # 获取代币精度
            token_contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=TOKEN_ABI
            )
            quote_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(quote_token_address),
                abi=TOKEN_ABI
            )

            token_decimals = token_contract.functions.decimals().call()
            quote_decimals = quote_contract.functions.decimals().call()

            # 计算价格
            price = (quote_reserve / (10 ** quote_decimals)) / (token_reserve / (10 ** token_decimals))
            
            self._log_info(f"\n✓ 发现 {quote_token_name} 交易对:", {
                'DEX': dex_name,
                '交易对地址': pair_address,
                '流动性': {
                    '代币数量': f"{token_reserve / (10 ** token_decimals):.4f}",
                    f'{quote_token_name}数量': f"{quote_reserve / (10 ** quote_decimals):.4f}",
                    '代币价格': f"{price:.6f} {quote_token_name}"
                }
            })

        except Exception as e:
            self._log_warning(f"获取交易对信息失败: {e}")

    async def _get_v3_pool_info(
        self,
        pool_address: str,
        dex_name: str,
        quote_token_name: str,
        quote_token_address: str,
        fee: int
    ):
        """获取V3池子信息"""
        try:
            pool_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(pool_address),
                abi=POOL_V3_ABI
            )

            # 获取流动性
            liquidity = pool_contract.functions.liquidity().call()
            slot0 = pool_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]

            # 获取代币精度
            token_contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=TOKEN_ABI
            )
            quote_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(quote_token_address),
                abi=TOKEN_ABI
            )

            token_decimals = token_contract.functions.decimals().call()
            quote_decimals = quote_contract.functions.decimals().call()

            # 计算价格
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            adjusted_price = price * (10 ** token_decimals) / (10 ** quote_decimals)

            self._log_info(f"\n✓ 发现 {quote_token_name} 池子:", {
                'DEX': dex_name,
                '池子地址': pool_address,
                '费率': f"{fee/10000}%",
                '流动性': {
                    '流动性数量': liquidity,
                    '代币价格': f"{adjusted_price:.6f} {quote_token_name}"
                }
            })

        except Exception as e:
            self._log_warning(f"获取池子信息失败: {e}") 