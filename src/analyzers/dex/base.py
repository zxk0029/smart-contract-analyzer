"""DEX 分析器基类"""

from typing import Dict, Optional, Tuple

from web3 import Web3
from web3.contract import Contract

from ..base import BaseAnalyzer
from ...config.constants import (
    DEX_CONFIGS,
    CHAINS,
    STABLECOINS,
    TOKEN_ABI,
    FACTORY_ABI,
    FACTORY_V3_ABI,
    PAIR_ABI,
    POOL_V3_ABI,
    EVENT_SIGNATURES
)


class DexAnalyzer(BaseAnalyzer):
    """DEX 分析器基类，提供共享的 DEX 分析功能"""

    def __init__(self, contract_address: str = None):
        """初始化 DEX 分析器
        
        Args:
            contract_address: 要分析的合约地址
        """
        super().__init__()
        self.contract_address = Web3.to_checksum_address(contract_address) if contract_address else None
        self.web3 = None
        self.chain_id = None
        self.chain_key = None

    async def analyze_pair_creation(self, tx_hash: str) -> Optional[Dict]:
        """分析交易对创建事件
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            包含创建信息的字典，如果分析失败则返回 None
        """
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            tx = self.web3.eth.get_transaction(tx_hash)

            creation_info = {
                'block_number': receipt['blockNumber'],
                'from': tx['from'],
                'to': tx['to'],
                'value': tx['value']
            }

            # 解析创建事件
            for log in receipt['logs']:
                if len(log['topics']) > 0:
                    event_signature = log['topics'][0].hex()
                    if event_signature == EVENT_SIGNATURES['PAIR_CREATED']:
                        token0 = self.web3.to_checksum_address('0x' + log['topics'][1].hex()[26:])
                        token1 = self.web3.to_checksum_address('0x' + log['topics'][2].hex()[26:])
                        
                        data = log['data']
                        if isinstance(data, (bytes, bytearray)):
                            data = data.hex()
                        if data.startswith('0x'):
                            data = data[2:]
                        
                        pair = self.web3.to_checksum_address('0x' + data[:64][-40:])
                        
                        creation_info['pair_info'] = {
                            'token0': token0,
                            'token1': token1,
                            'pair': pair
                        }
                        
                        # 获取代币信息
                        token0_info = self.get_token_info(token0)
                        token1_info = self.get_token_info(token1)
                        
                        if token0_info:
                            creation_info['token0_info'] = token0_info
                        if token1_info:
                            creation_info['token1_info'] = token1_info
                            
                        return creation_info

            return creation_info

        except Exception as e:
            self._log_warning(f"分析交易对创建失败: {str(e)}")
            return None

    async def check_dex_pools(self, chain_id: int) -> bool:
        """检查指定链上所有 DEX 的池子
        
        Args:
            chain_id: 链 ID
            
        Returns:
            是否找到任何池子
        """
        found_pools = False
        
        # 获取链配置
        self.chain_key = next((k for k, v in CHAINS.items() if v['chain_id'] == chain_id), None)
        if not self.chain_key or self.chain_key not in DEX_CONFIGS:
            self._log_warning(f"未找到链 ID {chain_id} 的 DEX 配置")
            return False

        chain_info = CHAINS[self.chain_key]
        dexes = DEX_CONFIGS[self.chain_key]
        wrapped_native = chain_info['wrapped_native']
        stables = STABLECOINS[self.chain_key]

        # 准备要检查的代币列表
        tokens_to_check = [(wrapped_native, 'Wrapped Native')] + [
            (addr, name) for name, addr in stables.items()
        ]

        for dex_id, dex_info in dexes.items():
            try:
                factory_address = self.web3.to_checksum_address(dex_info['factory'])
                factory = self.web3.eth.contract(
                    address=factory_address,
                    abi=FACTORY_ABI if dex_info['version'] == 2 else FACTORY_V3_ABI
                )

                for token_address, token_name in tokens_to_check:
                    token_address = self.web3.to_checksum_address(token_address)
                    
                    if dex_info['version'] == 2:
                        pair = factory.functions.getPair(self.contract_address, token_address).call()
                        if pair != '0x0000000000000000000000000000000000000000':
                            found_pools = True
                            pair_info = await self.get_pair_info(pair, dex_info['name'], token_name, token_address)
                            if pair_info:
                                self._log_info(f"\n✓ 在 {dex_info['name']} 上发现 {token_name} 交易对:", pair_info)
                    else:  # V3
                        fee_tiers = [100, 500, 3000, 10000]
                        for fee in fee_tiers:
                            pool = factory.functions.getPool(self.contract_address, token_address, fee).call()
                            if pool != '0x0000000000000000000000000000000000000000':
                                found_pools = True
                                self._log_info(f"✓ 在 {dex_info['name']} 上发现 {token_name} 池子 (费率: {fee/10000}%)")
                                # TODO: 实现 V3 池子信息获取

            except Exception as e:
                self._log_warning(f"检查 {dex_info['name']} 时出错: {str(e)}")
                continue

        return found_pools

    async def get_pair_info(
        self,
        pair_address: str,
        dex_name: str,
        quote_token_name: str,
        quote_token_address: str
    ) -> Dict:
        """获取交易对信息
        
        Args:
            pair_address: 交易对合约地址
            dex_name: DEX 名称
            quote_token_name: 计价代币名称
            quote_token_address: 计价代币地址
            
        Returns:
            包含交易对信息的字典
        """
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
            
            return {
                'dex': dex_name,
                'pair_address': pair_address,
                'reserves': {
                    'token': token_reserve,
                    'quote': quote_reserve,
                    'token_formatted': f"{token_reserve / (10 ** token_decimals):.4f}",
                    'quote_formatted': f"{quote_reserve / (10 ** quote_decimals):.4f}",
                    'price': f"{price:.6f} {quote_token_name}"
                },
                'has_liquidity': token_reserve > 0 and quote_reserve > 0
            }

        except Exception as e:
            self._log_warning(f"获取交易对信息失败: {str(e)}")
            return None

    def get_token_info(self, token_address: str) -> Optional[Dict]:
        """获取代币信息
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            包含代币信息的字典，如果获取失败则返回 None
        """
        try:
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address),
                abi=TOKEN_ABI
            )

            return {
                'name': contract.functions.name().call(),
                'symbol': contract.functions.symbol().call(),
                'decimals': contract.functions.decimals().call(),
                'total_supply': contract.functions.totalSupply().call()
            }

        except Exception as e:
            self._log_warning(f"获取代币信息失败: {str(e)}")
            return None 