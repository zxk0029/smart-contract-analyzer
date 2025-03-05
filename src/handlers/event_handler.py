import asyncio
import json
from typing import List, Dict

from web3 import Web3

from ..config import Config
from ..utils.logger import logger
from ..utils.retry import async_retry
from ..config.constants import (
    DEX_CONFIGS,
    EVENT_SIGNATURES,
    FACTORY_ABI,
    FACTORY_V3_ABI,
    PAIR_ABI,
    POOL_V3_ABI,
    TOKEN_ABI,
    CHAINS
)


class EventHandler:
    def __init__(self, config: Config):
        self.config = config
        self.web3 = self._init_web3()
        self.contract = self._init_contract()

    def _init_web3(self) -> Web3:
        logger.info(f"Initializing web3 instance, node_url: {self.config.node_url}")
        """初始化Web3连接"""
        provider = Web3.HTTPProvider(
            self.config.node_url,
            request_kwargs={
                'timeout': self.config.timeout,
                'headers': {
                    'Content-Type': 'application/json',
                }
            }
        )
        w3 = Web3(provider)

        # 添加 POA 中间件，BSC 的区块头中的 extraData 字段大小与标准以太坊不同，需要使用POA 中间件特殊处理。
        from web3.middleware import geth_poa_middleware
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        # 验证连接
        try:
            if not w3.is_connected():
                raise ConnectionError("无法连接到节点")
            logger.info(f"成功连接到节点，当前区块: {w3.eth.block_number}")
        except Exception as e:
            logger.error(f"连接节点失败: {e}")
            raise

        return w3

    def _init_contract(self):
        """初始化合约实例"""
        abi = self._load_abi()
        # 确保地址是 checksum 格式
        checksum_address = Web3.to_checksum_address(self.config.contract_address)
        return self.web3.eth.contract(
            address=checksum_address,
            abi=abi
        )

    @async_retry(retries=3, delay=1.0)
    async def get_contract_info(self) -> Dict:
        """获取合约信息"""
        return {
            'name': self.contract.functions.name().call(),
            'symbol': self.contract.functions.symbol().call(),
            'total_supply': self.contract.functions.totalSupply().call()
        }

    def _load_abi(self) -> List[Dict]:
        """加载合约ABI"""
        try:
            with open(self.config.abi_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载ABI失败: {e}")
            raise

    async def _get_contract_deployment_block(self) -> int:
        """获取合约部署区块"""
        # 如果配置中指定了部署区块，直接使用
        if self.config.deployment_block is not None:
            logger.info(f"使用配置中指定的部署区块: {self.config.deployment_block}")
            return self.config.deployment_block

        try:
            # 获取合约代码，确认是合约地址
            code = self.web3.eth.get_code(self.contract.address)
            if code == b'':
                raise ValueError("地址上没有合约代码")

            # 如果配置了 BSCScan API，优先使用它（最快）
            if self.config.bscscan_api_key:
                logger.info("使用 BSCScan API 查询合约部署区块")
                import requests
                # https://docs.etherscan.io/etherscan-v2
                url = f"https://api.etherscan.io/v2/api"
                params = {
                    "chainid": "56",
                    "module": "contract",
                    "action": "getcontractcreation",
                    "contractaddresses": self.contract.address,
                    "apikey": self.config.bscscan_api_key
                }

                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "1" and data["result"]:
                        tx_hash = data["result"][0]["txHash"]
                        tx = self.web3.eth.get_transaction(tx_hash)
                        deployment_block = tx["blockNumber"]
                        logger.info(f"通过 BSCScan API 找到合约创建交易: {tx_hash}")
                        logger.info(f"合约部署区块: {deployment_block}")
                        return deployment_block

            # 如果没有 BSCScan API 或者查询失败，使用 RPC 方法
            # 获取当前区块作为结束点
            end_block = self.web3.eth.block_number
            # 使用配置的批次大小
            batch_size = self.config.batch_size

            for start_block in range(end_block, 0, -batch_size):
                current_start = max(0, start_block - batch_size)
                logger.info(f"搜索区块范围: {current_start} - {start_block}")

                # 获取区块范围内的交易
                filter_params = {
                    'fromBlock': current_start,
                    'toBlock': start_block,
                    'address': self.contract.address
                }

                # 获取该地址的所有交易日志
                logs = self.web3.eth.get_logs(filter_params)

                if logs:
                    # 找到最早的交易日志
                    earliest_log = min(logs, key=lambda x: x['blockNumber'])
                    earliest_block = earliest_log['blockNumber']
                    earliest_tx = earliest_log['transactionHash']

                    # 获取交易收据以确认是否是合约创建
                    receipt = self.web3.eth.get_transaction_receipt(earliest_tx)
                    if (receipt['contractAddress']
                            and receipt['contractAddress'].lower() == self.contract.address.lower()):
                        logger.info(f"找到合约创建交易: {earliest_tx}")
                        logger.info(f"合约部署区块: {earliest_block}")
                        return earliest_block

                    # 如果找到了交易但不是创建交易，继续向前搜索
                    continue

            raise ValueError("未找到合约创建交易")

        except Exception as e:
            logger.error(f"获取合约部署区块失败: {e}")
            # 如果获取失败，返回一个保守的默认值
            return 46735204

    @async_retry(retries=3, delay=1.0)
    async def get_events(
            self,
            event_types: List[str] = None,
            from_block: int = None,
            to_block: int = None,
            batch_size: int = 10000
    ) -> List[Dict]:
        """获取合约事件

        Args:
            event_types: 要查询的事件类型列表，None表示所有事件
            from_block: 起始区块，None表示从合约部署区块开始
            to_block: 结束区块，None表示最新区块
            batch_size: 每批次查询的区块数
        """
        if from_block is None:
            from_block = await self._get_contract_deployment_block()

        if to_block is None:
            to_block = self.web3.eth.block_number

        # 创建事件签名映射
        event_signatures = {
            self.web3.keccak(text="Transfer(address,address,uint256)").hex(): self.contract.events.Transfer,
            self.web3.keccak(text="Approval(address,address,uint256)").hex(): self.contract.events.Approval,
            self.web3.keccak(
                text="OwnershipTransferred(address,address)").hex(): self.contract.events.OwnershipTransferred,
        }

        # 如果指定了事件类型，只查询指定的事件
        if event_types:
            event_signatures = {
                k: v for k, v in event_signatures.items()
                if v.event_name in event_types
            }

        results = []
        current_block = from_block

        # 使用动态批次大小
        initial_batch_size = batch_size
        current_batch_size = initial_batch_size

        while current_block < to_block:
            end_block = current_block  # 初始化 end_block
            try:
                # 确保end_block不超过目标区块
                end_block = min(current_block + current_batch_size - 1, to_block)

                # 确保不超过当前最新区块
                latest_block = self.web3.eth.block_number
                if end_block > latest_block:
                    end_block = latest_block
                    to_block = latest_block  # 更新目标区块为最新区块

                # 如果已经处理完所有区块，退出循环
                if current_block > end_block:
                    break

                # 构建符合 FilterParams 类型的参数
                filter_params = {
                    'fromBlock': current_block,
                    'toBlock': end_block,
                    'address': Web3.to_checksum_address(self.config.contract_address),
                    'topics': [list(event_signatures.keys())]
                }

                # 获取事件日志
                logs = self.web3.eth.get_logs(filter_params)

                for log in logs:
                    event_signature = log['topics'][0].hex()
                    if event_signature in event_signatures:
                        event = event_signatures[event_signature]().process_log(log)
                        results.append(event)

                # 成功后逐步增加批次大小，但不超过初始值
                current_batch_size = min(initial_batch_size, current_batch_size * 2)
                logger.info(f"处理完区块范围: {current_block}-{end_block} (批次大小: {current_batch_size})")

                current_block = end_block + 1
                await asyncio.sleep(self.config.delay)

            except Exception as e:
                logger.error(f"处理区块 {current_block}-{end_block} 失败: {e}")
                if "limit exceeded" in str(e):
                    # 遇到限制时减小批次大小
                    current_batch_size = max(self.config.batch_size // 10, current_batch_size // 2)  # 最小不低于配置的十分之一
                    logger.info(f"减小批次大小至: {current_batch_size}")
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(1)
                    continue

        return results

    @async_retry(retries=3, delay=1.0)
    async def get_ownership_transfers(self, from_block: int, to_block: int = None) -> List[Dict]:
        """获取所有权转移事件"""
        return await self.get_events(
            event_types=['OwnershipTransferred'],
            from_block=from_block,
            to_block=to_block
        )

    @async_retry(retries=3, delay=1.0)
    async def quick_check_ownership(self) -> Dict:
        """快速检查合约所有权状态（只返回当前状态，不包含历史记录）"""
        try:
            owner = self.contract.functions.owner().call()
            return {
                'current_owner': owner,
                'is_renounced': owner == '0x0000000000000000000000000000000000000000'
            }
        except Exception as e:
            logger.error(f"快速检查所有权状态失败: {e}")
            raise

    @async_retry(retries=3, delay=1.0)
    async def get_transfers(self, from_block: int, to_block: int = None) -> List[Dict]:
        """获取转账事件"""
        return await self.get_events(
            event_types=['Transfer'],
            from_block=from_block,
            to_block=to_block
        )

    @async_retry(retries=3, delay=1.0)
    async def get_approvals(self, from_block: int, to_block: int = None) -> List[Dict]:
        """获取授权事件"""
        return await self.get_events(
            event_types=['Approval'],
            from_block=from_block,
            to_block=to_block
        )

    async def check_ownership(self) -> Dict:
        """检查合约所有权状态"""
        try:
            # 获取当前 owner
            current_owner = self.contract.functions.owner().call()

            # 获取所有权转移历史
            ownership_transfers = await self.get_events(
                event_types=['OwnershipTransferred'],
                batch_size=self.config.batch_size
            )

            # 按区块号排序
            ownership_transfers.sort(key=lambda x: x['blockNumber'])

            # 获取每个事件的交易详情
            transfer_details = []
            for event in ownership_transfers:
                tx_hash = event['transactionHash'].hex()
                tx = self.web3.eth.get_transaction(tx_hash)
                transfer_details.append({
                    'block_number': event['blockNumber'],
                    'tx_hash': tx_hash,
                    'from_address': tx['from'],
                    'previous_owner': event['args']['previousOwner'],
                    'new_owner': event['args']['newOwner'],
                    'timestamp': self.web3.eth.get_block(event['blockNumber'])['timestamp']
                })

            return {
                'current_owner': current_owner,
                'is_renounced': current_owner == '0x0000000000000000000000000000000000000000',
                'transfer_history': transfer_details
            }

        except Exception as e:
            logger.error(f"检查所有权状态失败: {e}")
            raise

    async def quick_check_contract(self) -> Dict:
        """快速检查合约状态"""
        try:
            results = {}

            # 1. 检查所有权
            owner = self.contract.functions.owner().call()
            results['ownership'] = {
                'current_owner': owner,
                'is_renounced': owner == '0x0000000000000000000000000000000000000000'
            }

            # 2. 检查各个DEX的池子
            results['liquidity'] = []

            # 获取当前链的 DEX 配置
            current_chain_id = self.web3.eth.chain_id
            chain_key = next((k for k, v in CHAINS.items() if v['chain_id'] == current_chain_id), None)
            if not chain_key or chain_key not in DEX_CONFIGS:
                logger.warning(f"未找到链 {chain_key} 的 DEX 配置")
                return results

            dexes = DEX_CONFIGS[chain_key]
            wrapped_native = CHAINS[chain_key]['wrapped_native']

            # 检查每个DEX
            for dex_id, dex_info in dexes.items():
                try:
                    if dex_info['version'] == 2:
                        # 检查 V2 版本
                        factory = self.web3.eth.contract(
                            address=Web3.to_checksum_address(dex_info['factory']),
                            abi=FACTORY_ABI
                        )

                        pair_address = factory.functions.getPair(
                            self.config.contract_address,
                            wrapped_native
                        ).call()

                        if pair_address != '0x0000000000000000000000000000000000000000':
                            pair_info = {
                                'dex': dex_info['name'],
                                'version': 'V2',
                                'pair_address': pair_address,
                                'router': dex_info['router']
                            }

                            # 获取池子信息
                            pair_contract = self.web3.eth.contract(
                                address=pair_address,
                                abi=PAIR_ABI
                            )
                            reserves = pair_contract.functions.getReserves().call()

                            # 确定代币位置
                            is_token0 = pair_contract.functions.token0().call().lower() == self.config.contract_address.lower()

                            pair_info['reserves'] = {
                                'token': reserves[0] if is_token0 else reserves[1],
                                'bnb': reserves[1] if is_token0 else reserves[0]
                            }

                            results['liquidity'].append(pair_info)

                    elif dex_info['version'] == 3:
                        # 检查 V3 版本
                        factory = self.web3.eth.contract(
                            address=Web3.to_checksum_address(dex_info['factory']),
                            abi=FACTORY_V3_ABI
                        )

                        # V3 支持多个费率
                        fee_tiers = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
                        for fee in fee_tiers:
                            pool_address = factory.functions.getPool(
                                self.config.contract_address,
                                wrapped_native,
                                fee
                            ).call()

                            if pool_address != '0x0000000000000000000000000000000000000000':
                                pool_info = {
                                    'dex': dex_info['name'],
                                    'version': 'V3',
                                    'pool_address': pool_address,
                                    'router': dex_info['router'],
                                    'fee_tier': fee
                                }

                                # 获取池子信息
                                pool_contract = self.web3.eth.contract(
                                    address=pool_address,
                                    abi=POOL_V3_ABI
                                )
                                
                                # 获取流动性
                                liquidity = pool_contract.functions.liquidity().call()
                                slot0 = pool_contract.functions.slot0().call()
                                
                                pool_info['liquidity'] = liquidity
                                pool_info['sqrt_price_x96'] = slot0[0]
                                pool_info['tick'] = slot0[1]

                                results['liquidity'].append(pool_info)

                except Exception as e:
                    logger.warning(f"检查 {dex_info['name']} 时出错: {str(e)}")
                    continue

            return results

        except Exception as e:
            logger.error(f"快速检查失败: {e}")
            raise

