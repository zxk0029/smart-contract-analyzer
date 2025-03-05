"""常量配置文件"""
# 区块相关
DEPLOYMENT_BLOCK = 46735204

# 支持的链配置
CHAINS = {
    'ETH': {
        'name': 'Ethereum',
        'chain_id': 1,
        'rpc': {
            'default': 'https://eth-mainnet.g.alchemy.com/v2/',
            'public': 'https://ethereum.publicnode.com',
        },
        'block_time': 12,  # 秒
        'explorer': 'https://etherscan.io',
        'native_token': 'ETH',
        'wrapped_native': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'  # WETH
    },
    'BSC': {
        'name': 'BSC',
        'chain_id': 56,
        'rpc': {
            'default': 'https://bsc-mainnet.g.alchemy.com/v2/',
            'public': 'https://bsc-dataseed.binance.org'
        },
        'block_time': 3,
        'explorer': 'https://bscscan.com',
        'native_token': 'BNB',
        'wrapped_native': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'  # WBNB
    },
    'POLYGON': {
        'name': 'Polygon',
        'chain_id': 137,
        'rpc': {
            'default': 'https://polygon-mainnet.g.alchemy.com/v2/',
            'public': 'https://polygon-rpc.com'
        },
        'block_time': 2,
        'explorer': 'https://polygonscan.com',
        'native_token': 'MATIC',
        'wrapped_native': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'  # WMATIC
    }
}

# DEX 配置
DEX_CONFIGS = {
    'ETH': {
        'UNISWAP_V2': {
            'name': 'Uniswap V2',
            'factory': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
            'router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'version': 2
        },
        'UNISWAP_V3': {
            'name': 'Uniswap V3',
            'factory': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
            'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
            'version': 3
        },
        'SUSHISWAP': {
            'name': 'SushiSwap',
            'factory': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac',
            'router': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
            'version': 2
        }
    },
    'BSC': {
        'PANCAKESWAP_V2': {
            'name': 'PancakeSwap V2',
            'factory': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
            'router': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
            'version': 2
        },
        'PANCAKESWAP_V3': {
            'name': 'PancakeSwap V3',
            'factory': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865',
            'router': '0x13f4EA83D0bd40E75C8222255bc855a974568Dd4',
            'version': 3
        },
        'BISWAP': {
            'name': 'BiSwap',
            'factory': '0x858E3312ed3A876947EA49d572A7C42DE08af7EE',
            'router': '0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8',
            'version': 2
        }
    },
    'POLYGON': {
        'QUICKSWAP': {
            'name': 'QuickSwap',
            'factory': '0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32',
            'router': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',
            'version': 2
        },
        'SUSHISWAP': {
            'name': 'SushiSwap',
            'factory': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
            'router': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
            'version': 2
        }
    }
}

# 常用稳定币地址
STABLECOINS = {
    'ETH': {
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    },
    'BSC': {
        'USDT': '0x55d398326f99059fF775485246999027B3197955',
        'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
        'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
    },
    'POLYGON': {
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'
    }
}

# 合约 ABI
FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "type": "address", "name": "token0"},
            {"indexed": True, "type": "address", "name": "token1"},
            {"indexed": False, "type": "address", "name": "pair"},
            {"indexed": False, "type": "uint256", "name": ""}
        ],
        "name": "PairCreated",
        "type": "event"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"name": "pair", "type": "address"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

# V3 Factory ABI
FACTORY_V3_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

PAIR_ABI = [
    {"constant": True, "inputs": [], "name": "token0",
     "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "token1",
     "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "getReserves",
     "outputs": [{"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
                 {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
                 {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "payable": False,
     "stateMutability": "view", "type": "function"}
]

# V3 Pool ABI
POOL_V3_ABI = [
    {"inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "liquidity", "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "slot0", "outputs": [
        {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
        {"internalType": "int24", "name": "tick", "type": "int24"},
        {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
        {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
        {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
        {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
        {"internalType": "bool", "name": "unlocked", "type": "bool"}
    ], "stateMutability": "view", "type": "function"}
]

# 基础 ERC20 ABI
TOKEN_ABI = [
    {"constant": True, "inputs": [], "name": "name",
     "outputs": [{"name": "", "type": "string"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "payable": False,
     "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply",
     "outputs": [{"name": "", "type": "uint256"}], "payable": False,
     "stateMutability": "view", "type": "function"}
]

# 事件签名
EVENT_SIGNATURES = {
    'APPROVAL': '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925',
    'TRANSFER': '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
    'PAIR_CREATED': '0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9',
    'POOL_CREATED': '0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118',
    'SYNC': '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1',
    'MINT': '0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
}
