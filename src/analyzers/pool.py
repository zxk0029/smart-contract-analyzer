"""池子分析器"""

from .base import BaseAnalyzer
from ..config.constants import (
    DEX_CONFIGS,
    EVENT_SIGNATURES,
    FACTORY_ABI,
    PAIR_ABI,
    TOKEN_ABI
)


class PoolAnalyzer(BaseAnalyzer):
    """DEX 池子分析器"""

    def __init__(self, tx_hash: str = None):
        """初始化池子分析器
        
        Args:
            tx_hash: 可选的交易哈希，用于分析特定交易
        """
        super().__init__()
        self.tx_hash = tx_hash

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
        found_pools = False

        for chain_id, dexes in DEX_CONFIGS.items():
            for dex_id, dex_info in dexes.items():
                try:
                    self._log_info(f"\n检查 {dex_info['name']}...")
                    factory_address = self.handler.web3.to_checksum_address(dex_info['factory'])
                    self._log_info(f"Factory 地址: {factory_address}")

                    factory = self.handler.web3.eth.contract(
                        address=factory_address,
                        abi=FACTORY_ABI
                    )

                    contract_address = self.handler.web3.to_checksum_address(self.config.contract_address)
                    
                    # 检查 WBNB 交易对
                    wbnb_address = self.handler.web3.to_checksum_address(dex_info['wrapped_native'])
                    self._log_info(f"查询 WBNB 交易对: Token={contract_address}, WBNB={wbnb_address}")
                    wbnb_pair = factory.functions.getPair(contract_address, wbnb_address).call()
                    
                    # 检查 USDT 交易对
                    usdt_address = self.handler.web3.to_checksum_address(dex_info['stablecoins']['USDT'])
                    self._log_info(f"查询 USDT 交易对: Token={contract_address}, USDT={usdt_address}")
                    usdt_pair = factory.functions.getPair(contract_address, usdt_address).call()

                    if wbnb_pair != '0x0000000000000000000000000000000000000000':
                        found_pools = True
                        await self._get_pair_info(wbnb_pair, dex_info['name'], 'WBNB', dex_info['router'])

                    if usdt_pair != '0x0000000000000000000000000000000000000000':
                        found_pools = True
                        await self._get_pair_info(usdt_pair, dex_info['name'], 'USDT', dex_info['router'])

                    if wbnb_pair == '0x0000000000000000000000000000000000000000' and \
                       usdt_pair == '0x0000000000000000000000000000000000000000':
                        self._log_info(f"✗ 在 {dex_info['name']} 上未找到交易对")

                except Exception as e:
                    self._log_warning(f"检查 {dex_info['name']} 时出错: {str(e)}")
                    continue

        if not found_pools:
            self._log_warning("✗ 未在主要DEX上发现交易对")

    async def _get_pair_info(self, pair_address: str, dex_name: str, quote_token: str, router: str):
        """获取交易对信息"""
        pair_info = {
            'dex': dex_name,
            'pair_address': pair_address,
            'router': router,
            'quote_token': quote_token
        }

        # 获取池子信息
        pair_contract = self.handler.web3.eth.contract(
            address=self.handler.web3.to_checksum_address(pair_address),
            abi=PAIR_ABI
        )
        reserves = pair_contract.functions.getReserves().call()

        # 确定代币位置
        token0 = pair_contract.functions.token0().call()
        is_token0 = token0.lower() == self.config.contract_address.lower()

        token_reserve = reserves[0] if is_token0 else reserves[1]
        quote_reserve = reserves[1] if is_token0 else reserves[0]

        pair_info['reserves'] = {
            'token': token_reserve,
            'quote': quote_reserve
        }

        # 检查是否有流动性
        has_liquidity = token_reserve > 0 and quote_reserve > 0
        pair_info['has_liquidity'] = has_liquidity

        # 显示信息
        self._log_info(f"\n✓ 在 {dex_name} 上发现 {quote_token} 交易对:", pair_info)
        
        if has_liquidity:
            # 获取代币精度
            token_contract = self.handler.web3.eth.contract(
                address=self.handler.web3.to_checksum_address(self.config.contract_address),
                abi=TOKEN_ABI
            )
            token_decimals = token_contract.functions.decimals().call()
            
            # 获取计价代币精度
            quote_address = self.handler.web3.to_checksum_address(
                DEX_CONFIGS['BSC'][dex_name.upper()]['stablecoins'][quote_token]
                if quote_token == 'USDT'
                else DEX_CONFIGS['BSC'][dex_name.upper()]['wrapped_native']
            )
            quote_contract = self.handler.web3.eth.contract(
                address=quote_address,
                abi=TOKEN_ABI
            )
            quote_decimals = quote_contract.functions.decimals().call()
            
            # 计算代币价格
            price = (quote_reserve / (10 ** quote_decimals)) / (token_reserve / (10 ** token_decimals))
            formatted_price = f"{price:.6f}"
            
            self._log_info("流动性状态: ✓ 已添加流动性")
            self._log_info("代币价格:", {
                f'每个代币价格（{quote_token}）': formatted_price,
                '代币数量': f"{token_reserve / (10 ** token_decimals):.4f}",
                f'{quote_token}数量': f"{quote_reserve / (10 ** quote_decimals):.4f}"
            })
        else:
            self._log_warning("流动性状态: ✗ 尚未添加流动性")

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
            self._parse_log(log)

    def _parse_log(self, log: dict):
        """解析交易日志"""
        self._log_info("合约地址:", {'address': log['address']})

        if not log['topics']:
            return

        event_signature = log['topics'][0].hex()
        event_name = self._get_event_name(event_signature)
        self._log_info("事件:", {'name': event_name})

        if event_name == 'PAIR_CREATED':
            self._parse_pair_created_log(log)
        elif event_name == 'TRANSFER':
            self._parse_transfer_log(log)
        elif event_name == 'APPROVAL':
            self._parse_approval_log(log)

    def _parse_pair_created_log(self, log: dict):
        """解析池子创建事件日志"""
        try:
            # 从 topics 中获取 token0 和 token1
            token0 = self.handler.web3.to_checksum_address('0x' + log['topics'][1].hex()[26:])
            token1 = self.handler.web3.to_checksum_address('0x' + log['topics'][2].hex()[26:])
            
            # 从 data 中获取 pair 地址
            data = log['data']
            if isinstance(data, (bytes, bytearray)):
                data = data.hex()
            if data.startswith('0x'):
                data = data[2:]
            
            # pair 地址在数据的前 32 字节（64 个字符）
            pair = self.handler.web3.to_checksum_address('0x' + data[:64][-40:])
            
            self._log_info("创建交易对:", {
                'token0': token0,
                'token1': token1,
                'pair': pair
            })
            
            # 检查是否是我们关注的代币对
            our_token = self.handler.web3.to_checksum_address(self.config.contract_address)
            wbnb = self.handler.web3.to_checksum_address(DEX_CONFIGS['BSC']['PANCAKESWAP_V2']['wrapped_native'])
            
            if (token0.lower() == our_token.lower() and token1.lower() == wbnb.lower()) or \
               (token1.lower() == our_token.lower() and token0.lower() == wbnb.lower()):
                self._log_info("✓ 这是我们要找的交易对！")
                self._log_info("交易对地址:", {'address': pair})
        except Exception as e:
            self._log_warning(f"解析 PAIR_CREATED 事件失败: {str(e)}")

    def _get_event_name(self, signature: str) -> str:
        """获取事件名称"""
        for name, sig in EVENT_SIGNATURES.items():
            if sig == signature:
                return name
        return 'Unknown'

    def _parse_approval_log(self, log: dict):
        """解析授权事件日志"""
        owner = '0x' + log['topics'][1].hex()[26:]
        spender = '0x' + log['topics'][2].hex()[26:]
        value = int(log['data'].hex(), 16)
        self._log_info("授权详情:", {
            '所有者': owner,
            '授权给': spender,
            '金额': value
        })

    def _parse_transfer_log(self, log: dict):
        """解析转账事件日志"""
        from_addr = '0x' + log['topics'][1].hex()[26:]
        to_addr = '0x' + log['topics'][2].hex()[26:]
        value = int(log['data'].hex(), 16)
        self._log_info("转账详情:", {
            '从': from_addr,
            '到': to_addr,
            '金额': value
        })
