import json
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any

from dotenv import load_dotenv
from web3 import Web3

# 加载环境变量
load_dotenv()

# 节点配置
NODE_CONFIG = {
    'public': 'https://bsc-dataseed.binance.org/',
    'quicknode': os.getenv('QUICKNODE_URL', ''),  # QuickNode URL
    'getblock': os.getenv('GETBLOCK_URL', ''),  # GetBlock URL
    'alchemy': os.getenv('ALCHEMY_URL', '')  # Alchemy URL
}

# 选择节点（默认使用公共节点）
SELECTED_NODE = NODE_CONFIG.get(os.getenv('NODE_TYPE', 'alchemy'))

# 连接到BSC节点
web3 = Web3(Web3.HTTPProvider(
    SELECTED_NODE,
    request_kwargs={
        'timeout': 60,  # 增加超时时间
        'headers': {
            'Content-Type': 'application/json',
            'Authorization': os.getenv('NODE_API_KEY', '')  # 如果需要API密钥
        }
    }
))

# 其他配置
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '2000'))  # 可配置批次大小
DELAY = float(os.getenv('REQUEST_DELAY', '0.5'))  # 可配置请求延迟


def load_contract_abi(file_path: str = 'contract_abi.json') -> List[Dict]:
    with open(file_path, 'r') as f:
        return json.load(f)


# 合约地址
CONTRACT_ADDRESS = '0xBF6Cd8D57ffe3CBe3D78DEd8DA34345A3B736102'
# 需要从BscScan获取完整ABI
CONTRACT_ABI = load_contract_abi()

# 创建合约实例
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)


@dataclass
class ContractEvent:
    event: str
    returnValues: Dict[str, Any]
    blockNumber: int


# 事件缓存
event_cache = {}


def get_cached_events(event_name: str) -> List[Dict]:
    """获取带缓存的事件"""
    if event_name in event_cache:
        return event_cache[event_name]

    events = contract.events[event_name].get_all_entries()
    event_cache[event_name] = events
    return events


def process_events(events: List[ContractEvent]) -> None:
    """处理事件数据"""
    for event in events:
        print(f"[{event.blockNumber}] {event.event}", event.returnValues)


async def get_ownership_transfers() -> None:
    """查询所有权转移事件"""
    try:
        current_block = 46735204
        batch_size = BATCH_SIZE
        latest_block = web3.eth.block_number

        while current_block < latest_block:
            try:
                end_block = min(current_block + batch_size, latest_block)

                events = contract.events.OwnershipTransferred().get_logs(
                    fromBlock=current_block,
                    toBlock=end_block
                )

                for event in events:
                    print(
                        f"所有权转移：旧Owner {event.args.previousOwner} -> "
                        f"新Owner {event.args.newOwner}"
                    )

                current_block = end_block + 1
                time.sleep(DELAY)  # 可配置的延迟

            except Exception as e:
                if "limit exceeded" in str(e):
                    # 如果超出限制，减小批次大小并重试
                    batch_size = max(100, batch_size // 2)
                    print(f"减小批次大小至: {batch_size}")
                    time.sleep(2)
                    continue
                raise e

    except Exception as e:
        print(f"查询所有权事件失败: {e}")


async def get_tax_changes() -> None:
    """查询税率变更事件"""
    try:
        current_block = 46735204
        batch_size = 2000
        latest_block = web3.eth.block_number

        while current_block < latest_block:
            end_block = min(current_block + batch_size, latest_block)

            events = contract.events.BuyTaxSet().get_logs(
                fromBlock=current_block,
                toBlock=end_block
            )

            for event in events:
                print(f"[{event.blockNumber}] 税率变更: {event.args}")

            current_block = end_block + 1
            time.sleep(1)

    except Exception as e:
        print(f"查询税率变更失败: {e}")


async def get_liquidity_pairs_added() -> None:
    """获取所有交易对添加记录"""
    try:
        # 使用get_logs替代get_all_entries
        events = contract.events.LiquidityPairAdded().get_logs(
            fromBlock=46735204
        )

        print('已添加交易对列表：')
        for event in events:
            print(f"- {event.args.pairAddress} (区块 {event.blockNumber})")
    except Exception as e:
        print(f"获取交易对记录失败: {e}")


async def get_all_events_paginated() -> None:
    """分页获取所有事件"""
    batch_size = 100000
    current_block = 46735204
    print(f"当前区块高度: {web3.eth.block_number}")
    latest_block = web3.eth.block_number

    # 创建事件签名到ABI的映射
    event_signatures = {
        web3.keccak(text="Transfer(address,address,uint256)").hex(): contract.events.Transfer,
        web3.keccak(text="Approval(address,address,uint256)").hex(): contract.events.Approval,
        web3.keccak(text="OwnershipTransferred(address,address)").hex(): contract.events.OwnershipTransferred
    }

    print(f"开始获取从 {current_block} 到 {latest_block} 的事件")

    while current_block < latest_block:
        try:
            end_block = min(current_block + batch_size, latest_block)

            # 获取原始日志
            logs = web3.eth.get_logs({
                'fromBlock': current_block,
                'toBlock': end_block,
                'address': CONTRACT_ADDRESS,
                'topics': [list(event_signatures.keys())]  # 所有事件的签名
            })

            # 解析每个日志
            for log in logs:
                # 获取事件签名（第一个topic）
                event_signature = log['topics'][0].hex()
                if event_signature in event_signatures:
                    # 解码事件
                    event = event_signatures[event_signature]().process_log(log)
                    print(f"[{log['blockNumber']}] {event['event']}: {event['args']}")

            print(f"处理完区块范围: {current_block}-{end_block}")
            current_block = end_block + 1
            time.sleep(DELAY)

        except Exception as e:
            if "limit exceeded" in str(e):
                batch_size = batch_size // 2
                print(f"减小批次大小至: {batch_size}")
                time.sleep(2)
            else:
                print(f"获取事件失败 (区块 {current_block}-{end_block}): {e}")
                time.sleep(1)

    print("事件获取完成!")


# 实用工具函数
def get_contract_info() -> None:
    """获取合约基本信息"""
    try:
        # 假设合约实现了name()和symbol()方法
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        total_supply = contract.functions.totalSupply().call()

        print(f"合约信息:")
        print(f"名称: {name}")
        print(f"符号: {symbol}")
        print(f"总供应量: {total_supply}")
    except Exception as e:
        print(f"获取合约信息失败: {e}")


def monitor_events() -> None:
    """实时监控合约事件"""

    def handle_event(event):
        print(f"检测到新事件: {event['event']}")
        print(f"事件数据: {event['args']}")

    # 设置事件过滤器
    event_filter = contract.events.all_events.create_filter(fromBlock='latest')

    # 持续监听新事件
    while True:
        try:
            for event in event_filter.get_new_entries():
                handle_event(event)
            time.sleep(2)  # 每2秒检查一次新事件
        except Exception as e:
            print(f"监控事件出错: {e}")
            time.sleep(5)  # 出错后等待5秒再重试


def get_recent_events(blocks_back: int = 1000) -> None:
    """获取最近的事件"""
    try:
        current_block = web3.eth.block_number
        from_block = max(46735204, current_block - blocks_back)

        print(f"获取最近 {blocks_back} 个区块的事件...")

        # 获取所有已定义的事件
        events_to_get = [
            contract.events.OwnershipTransferred,
            contract.events.Transfer,
            contract.events.Approval
        ]

        for event_type in events_to_get:
            try:
                print(f"\n获取 {event_type.event_name} 事件:")
                events = event_type().get_logs(
                    fromBlock=from_block,
                    toBlock='latest'
                )

                for event in events:
                    print(f"区块 {event.blockNumber}: {event.event}")
                    print(f"  参数: {event.args}")

            except Exception as e:
                print(f"获取 {event_type.event_name} 事件失败: {e}")

    except Exception as e:
        print(f"获取事件失败: {e}")


def list_contract_events():
    """列出合约中定义的所有事件"""
    events = []
    for item in CONTRACT_ABI:
        if item.get('type') == 'event':
            events.append(item.get('name'))
    print("合约定义的事件:", events)


if __name__ == "__main__":
    import asyncio

    list_contract_events()


    async def main():
        # 获取合约基本信息
        get_contract_info()

        # 分页获取所有事件
        print("\n分页获取所有事件:")
        await get_all_events_paginated()
        print("\n任务完成!")


    # 运行异步主函数
    asyncio.run(main())
