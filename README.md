# Smart Contract Analyzer

一个功能强大的智能合约分析工具，用于检查和分析区块链上的智能合约。

## 功能特点

- 🔍 合约基本信息分析
- 👤 所有权分析
- 💧 流动性池分析
- 🔗 链上交易分析
- 🤖 自动合约检测

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/zxk0029/smart-contract-analyzer.git
cd smart-contract-analyzer
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

## 使用方法

### 基本分析
```bash
python main.py
```

### 快速检查模式
```bash
python main.py --quick
```

### 分析特定交易
```bash
python main.py --tx <交易哈希>
```

### 检测特定合约
```bash
python main.py --contract <合约地址>
```

## 项目结构

```
smart-contract-analyzer/
├── main.py              # 主程序入口
├── omina.py            # 核心分析逻辑
├── src/                # 源代码目录
│   ├── analyzers/     # 分析器模块
│   └── utils/         # 工具函数
├── tests/             # 测试目录
└── contract_abi.json  # 合约 ABI 定义
```

## 注意事项

- 使用前请确保已正确配置环境变量
- 建议在测试网络上先进行测试
- 分析结果仅供参考，请勿用于生产环境的唯一依据

## License

MIT License 