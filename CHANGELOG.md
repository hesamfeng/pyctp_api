# pyctp_api 变更日志

## 1.0.0 版本 (2025-01-15)

### 🎉 项目初始化
- 创建独立的pyctp_api项目，不依赖vnpy框架
- 基于CTP API 6.7.7版本构建

### ✨ 新功能
- **统一CTP网关** (`ctp_gateway.py`) - 整合MD和TD API为单一接口
- **完整功能测试** (`test_ctp.py`) - 10个测试用例，100%通过率
- **实时行情接收** - 支持期货、期权合约行情订阅
- **交易功能** - 下单、撤单、查询等完整交易操作
- **账户管理** - 账户资金查询、持仓查询等
- **数据查询** - 合约信息查询、交易记录查询等

### 🔧 技术特性
- **Python 3.11** - 原生支持最新Python版本
- **SimNow兼容** - 完整支持SimNow模拟交易环境
- **跨平台** - 支持macOS、Linux、Windows
- **异步回调** - 基于事件驱动的异步处理机制
- **错误处理** - 完善的异常处理和日志记录

### 📦 项目结构
```
pyctp_api/
├── ctp_gateway.py     # 统一CTP网关
├── test_ctp.py        # 功能测试程序
├── pyctp_api/         # CTP API核心库
├── test/              # 单元测试
└── README.md          # 项目文档
```

### 🎯 测试覆盖
- ✅ 服务器连接测试
- ✅ 用户认证和登录
- ✅ 结算信息确认
- ✅ 实时行情订阅
- ✅ 账户资金查询
- ✅ 持仓信息查询
- ✅ 合约信息查询
- ✅ 下单交易操作
- ✅ 撤单操作
- ✅ 行情数据获取

### 📋 配置支持
- 支持SimNow模拟环境
- 支持生产环境配置
- 灵活的服务器地址配置
- 完整的认证参数支持

---

## 开发说明

本项目从vnpy_ctp项目重构而来，专注于提供纯净的CTP API Python接口，不依赖vnpy框架。适合需要直接使用CTP API进行量化交易开发的用户。

### 主要改进
1. **独立性** - 移除vnpy框架依赖，可独立使用
2. **简洁性** - 专注核心功能，代码结构清晰
3. **完整性** - 提供完整的测试用例和文档
4. **现代化** - 使用Python 3.11，支持最新语言特性
