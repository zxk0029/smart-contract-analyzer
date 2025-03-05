"""V3 版本的 DEX 分析器"""

from typing import Dict, Optional

from web3 import Web3

from .base import DexAnalyzer


class DexV3Analyzer(DexAnalyzer):
    """V3 版本的 DEX 分析器"""

    async def get_pool_info(
        self,
        pool_address: str,
        dex_name: str,
        quote_token_name: str,
        quote_token_address: str,
        fee: int
    ) -> Optional[Dict]:
        """获取 V3 池子信息
        
        Args:
            pool_address: 池子合约地址
            dex_name: DEX 名称
            quote_token_name: 计价代币名称
            quote_token_address: 计价代币地址
            fee: 费率
            
        Returns:
            包含池子信息的字典，如果获取失败则返回 None
        """
        try:
            pool_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(pool_address),
                abi=self.POOL_V3_ABI
            )

            # 获取流动性
            liquidity = pool_contract.functions.liquidity().call()
            slot0 = pool_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]

            # 获取代币精度
            token_contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=self.TOKEN_ABI
            )
            quote_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(quote_token_address),
                abi=self.TOKEN_ABI
            )

            token_decimals = token_contract.functions.decimals().call()
            quote_decimals = quote_contract.functions.decimals().call()

            # 计算价格
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            adjusted_price = price * (10 ** token_decimals) / (10 ** quote_decimals)

            return {
                'dex': dex_name,
                'pool_address': pool_address,
                'fee': f"{fee/10000}%",
                'liquidity': {
                    'amount': liquidity,
                    'price': f"{adjusted_price:.6f} {quote_token_name}"
                }
            }

        except Exception as e:
            self._log_warning(f"获取池子信息失败: {str(e)}")
            return None 