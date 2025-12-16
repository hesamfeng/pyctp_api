# PyCTP API

一个纯粹的Python CTP (Comprehensive Transaction Platform) API封装，无需任何额外框架依赖。

## 简介

PyCTP API 是对上海期货信息技术有限公司CTP交易接口的轻量级Python封装。它提供了：

- ✅ **纯净无依赖** - 无需VeighNa或其他量化框架
- ✅ **直接API访问** - 直接使用CTP原生API
- ✅ **跨平台支持** - 支持Windows/Linux/MacOS
- ✅ **完整功能** - 行情订阅、交易下单、查询等全功能支持
- ✅ **简单易用** - 最小化的学习成本

## 安装

### 基础安装
```bash
pip install pyctp-api
```

### 安全配置

#### 🔐 配置账户信息（重要）
为保护您的账户安全，本框架使用配置文件管理敏感信息：

**方法1: 使用配置文件**
```bash
# 1. 复制配置模板
cp config.py.template config.py

# 2. 编辑配置文件
nano config.py

# 3. 填入您的SimNow账户信息
SIMNOW_CONFIG = {
    "用户名": "your_username",
    "密码": "your_password",
    # ...
}
```

**方法2: 使用环境变量**
```bash
# 设置环境变量
export CTP_USERNAME="your_simnow_username"
export CTP_PASSWORD="your_simnow_password"

# 运行程序
python example/spread_monitor_console.py
```

#### ⚠️ 安全提示
- ❌ **不要**将包含真实密码的 `config.py` 提交到Git
- ✅ **必须**使用 `config.py.template` 作为模板
- ✅ **推荐**使用环境变量管理敏感信息
- ✅ **建议**使用SimNow模拟账户进行测试

### 平台特定配置

#### macOS (已验证)
- 无需额外配置，可直接运行示例程序
- 支持 Intel 和 Apple Silicon 芯片

#### Windows
```bash
# 1. 下载 CTP 接口文件
# 2. 复制到 pyctp_api/api/ 目录
# 3. 设置环境变量
export PATH=$PATH:$(pwd)/pyctp_api/api

# 4. 运行示例
python example/spread_monitor_console.py
```

#### Linux
```bash
# 可能需要安装额外依赖
sudo apt-get install build-essential

# 编译 CTP 接口为 .so 文件
# 具体步骤请参考 CTP 官方文档
```

## 快速开始

### 配置验证
```python
from secure_config import load_config

config = load_config()
print("用户名:", config["用户名"])  # 应该显示您的用户名或占位符
```

### 行情订阅

```python
from secure_config import load_config
from pyctp_api import MdApi

class MyMdApi(MdApi):
    def onFrontConnected(self):
        print("行情服务器连接成功")

    def onRspUserLogin(self, data, error, reqid, last):
        if error['ErrorID'] == 0:
            print("登录成功")
            # 订阅行情
            self.subscribeMarketData(["rb2509"])

    def onRtnDepthMarketData(self, data):
        print(f"收到行情: {data['InstrumentID']} 价格: {data['LastPrice']}")

# 创建行情API
api = MyMdApi()
api.createFtdcMdApi("")
api.registerFront("tcp://182.254.243.31:30011")  # SimNow行情服务器
api.init()

# 获取配置并登录
config = load_config()
login_req = {
    "UserID": config["用户名"],
    "BrokerID": config["经纪商代码"],
    "Password": config["密码"]
}
api.reqUserLogin(login_req, 1)
```

### 交易下单

```python
from pyctp_api import TdApi
from pyctp_api.api import THOST_FTDC_D_Buy, THOST_FTDC_OF_Open

class MyTdApi(TdApi):
    def onFrontConnected(self):
        print("交易服务器连接成功")
        
    def onRspUserLogin(self, data, error, reqid, last):
        if error['ErrorID'] == 0:
            print("登录成功")
            
    def onRtnOrder(self, data):
        print(f"委托回报: {data['InstrumentID']} 状态: {data['OrderStatus']}")

# 创建交易API
api = MyTdApi()
api.createFtdcTraderApi("")
api.registerFront("tcp://182.254.243.31:30001")  # SimNow交易服务器
api.init()

# 登录和下单...
```

## 主要功能

### 行情API (MdApi)
- 连接行情服务器
- 用户登录
- 行情订阅/退订
- 实时行情推送

### 交易API (TdApi)
- 连接交易服务器
- 用户授权和登录
- 委托下单
- 委托撤单
- 账户查询
- 持仓查询
- 成交查询

### CTP常量
从 `pyctp_api.api` 可以导入所有CTP常量，如：
- `THOST_FTDC_D_Buy` - 买入方向
- `THOST_FTDC_D_Sell` - 卖出方向
- `THOST_FTDC_OF_Open` - 开仓标志
- `THOST_FTDC_OF_Close` - 平仓标志
- 等等...

## 测试

项目包含完整的测试示例：

```bash
# 测试行情功能
python test/test_md.py

# 测试交易功能
python test/test_td.py

# 或使用pytest运行完整测试
pytest test/
```

## SimNow模拟环境

可以使用上期技术的SimNow模拟环境进行测试：

- **行情服务器**: `tcp://182.254.243.31:30011`
- **交易服务器**: `tcp://182.254.243.31:30001`
- **注册地址**: http://www.simnow.com.cn/

## 系统要求

- Python 3.10+
- Windows/Linux/MacOS

## 跨平台兼容性说明

### ✅ macOS 系统
- 本框架已在 macOS (Apple Silicon M1/M2) 上完成编译和测试
- 可直接运行，无需额外配置
- 示例程序已验证可在 macOS 上正常运行

### ⚠️ Windows 系统
如需在 Windows 系统上运行，请按以下步骤操作：

1. **获取 CTP 接口文件**
   - 下载官方 CTP 接口：[CTP接口下载](http://www.ctp.cn/tdxAPI.html)
   - 或从期货公司获取对应版本的接口文件

2. **替换接口文件**
   ```bash
   # 将下载的 CTP 接口文件复制到以下目录：
   pyctp_api/api/
   ```

3. **必需的接口文件**
   - `thostmduserapi_se.dll` - 行情接口
   - `thosttraderapi_se.dll` - 交易接口

4. **环境变量设置**
   ```python
   import os

   # 添加到环境变量
   os.environ["PATH"] += os.pathsep + os.path.join(os.getcwd(), "pyctp_api", "api")
   ```

5. **验证安装**
   ```bash
   python test/test_md.py  # 测试行情接口
   python test/test_td.py  # 测试交易接口
   ```

## 许可证

MIT License

## 注意事项

1. **跨平台兼容性**
   - macOS：已编译完成，可直接使用
   - Windows：需先获取并配置CTP接口文件
   - Linux：可能需要编译对应的.so文件

2. **CTP接口文件**
   - 不同的期货公司可能提供不同版本的CTP接口
   - 建议使用最新稳定版本的接口
   - 接口版本不匹配可能导致连接失败

3. **测试环境**
   - 使用前请先在SimNow等模拟环境进行充分测试
   - 实盘交易需要相应的期货账户和授权

4. **风险提示**
   - 实盘交易存在风险，请谨慎操作
   - 建议在充分测试后再进行实盘交易

5. **合规要求**
   - 请遵守相关法律法规和交易所规则
   - 本API仅用于合法的期货交易活动

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。