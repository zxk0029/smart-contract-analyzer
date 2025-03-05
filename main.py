"""主程序入口"""

import asyncio
import sys

from src.analyzers import ContractInfoAnalyzer, OwnershipAnalyzer, PoolAnalyzer, ChainDetector
from src.utils import logger


async def main(quick_mode: bool = False):
    """主程序入口"""
    try:
        # 基本信息分析
        await ContractInfoAnalyzer().execute()

        # 所有权分析
        await OwnershipAnalyzer(quick_mode=quick_mode).execute()

        # 池子分析
        await PoolAnalyzer().execute()

    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


async def analyze_specific_transaction(tx_hash: str):
    """分析特定交易"""
    try:
        await PoolAnalyzer(tx_hash).execute()
    except Exception as e:
        logger.error(f"交易分析失败: {e}")
        sys.exit(1)


async def auto_detect(contract_address: str):
    """自动检测合约"""
    try:
        await ChainDetector(contract_address).execute()
    except Exception as e:
        logger.error(f"自动检测失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 可以根据命令行参数选择执行不同的分析
    # 例如: python main.py --tx 0x4d5c91a107fcd297be9b239816fd0c1eecce8d0c1bef74547b923cc5b9650a4e
    # python main.py --contract 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 根据传入的合约，检测
    # python main.py --contract 0xBF6Cd8D57ffe3CBe3D78DEd8DA34345A3B736102 根据传入的合约，检测
    import argparse

    parser = argparse.ArgumentParser(description='合约分析工具')
    parser.add_argument('--tx', help='要分析的交易哈希')
    parser.add_argument('--quick', action='store_true', help='使用快速检查模式')
    parser.add_argument('--contract', help='要检测的合约地址')

    args = parser.parse_args()
    
    if args.contract:
        asyncio.run(auto_detect(args.contract))
    elif args.tx:
        asyncio.run(analyze_specific_transaction(args.tx))
    else:
        asyncio.run(main(quick_mode=args.quick))
