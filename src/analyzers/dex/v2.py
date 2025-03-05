"""V2 版本的 DEX 分析器"""

from typing import Dict, Optional

from web3 import Web3

from .base import DexAnalyzer


class DexV2Analyzer(DexAnalyzer):
    """V2 版本的 DEX 分析器"""

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
                    if event_signature == self.handler.get_event_signature('PAIR_CREATED'):
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
                        token0_info = await self.get_token_info(token0)
                        token1_info = await self.get_token_info(token1)
                        
                        if token0_info:
                            creation_info['token0_info'] = token0_info
                        if token1_info:
                            creation_info['token1_info'] = token1_info
                            
                        return creation_info

            return creation_info

        except Exception as e:
            self._log_warning(f"分析交易对创建失败: {str(e)}")
            return None 