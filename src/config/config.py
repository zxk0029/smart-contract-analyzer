"""配置模块"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict

from dotenv import load_dotenv


@dataclass
class Config:
    """配置类"""
    # 节点配置
    node_type: str = 'alchemy'
    node_url: str = 'https://rpc.ankr.com/bsc'
    api_key: Optional[str] = None
    bscscan_api_key: Optional[str] = None  # BSCScan API 密钥

    # 合约配置
    contract_address: str = '0xBF6Cd8D57ffe3CBe3D78DEd8DA34345A3B736102'
    abi_file: str = 'contract_abi.json'
    deployment_block: Optional[int] = None  # 合约部署区块

    # 查询配置
    batch_size: int = 1000
    delay: float = 0.5
    timeout: int = 60

    # 重试配置
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 3600

    # 使用 field(default_factory=dict) 替代 dict = {}
    headers: Dict = field(default_factory=dict)

    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        load_dotenv()

        # 获取节点URL
        node_type = os.getenv('NODE_TYPE', 'public')
        node_urls = {
            'public': 'https://bsc-dataseed.binance.org/',
            'public2': 'https://rpc.ankr.com/bsc',
            'quicknode': os.getenv('QUICKNODE_URL', ''),
            'getblock': os.getenv('GETBLOCK_URL', ''),
            'alchemy': os.getenv('ALCHEMY_URL', '')
        }

        node_url = node_urls.get(node_type, node_urls['public'])
        headers = {}

        # 从环境变量或常量获取部署区块
        from .constants import DEPLOYMENT_BLOCK
        deployment_block = int(os.getenv('DEPLOYMENT_BLOCK', DEPLOYMENT_BLOCK))

        return cls(
            node_type=node_type,
            node_url=node_url,
            api_key=os.getenv('NODE_API_KEY'),
            bscscan_api_key=os.getenv('BSCSCAN_API_KEY'),
            deployment_block=deployment_block,
            batch_size=int(os.getenv('BATCH_SIZE', '1000')),
            delay=float(os.getenv('REQUEST_DELAY', '0.5')),
            retry_attempts=int(os.getenv('RETRY_ATTEMPTS', '3')),
            cache_enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            headers=headers
        )
