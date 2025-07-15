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

```bash
pip install pyctp-api
```

## 快速开始

### 行情订阅

```python
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

# 登录
login_req = {
    "UserID": "your_user_id",
    "BrokerID": "9999",
    "Password": "your_password"
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

## 许可证

MIT License

## 注意事项

1. 本包仅为CTP API的Python封装，不提供策略框架功能
2. 使用前请先在SimNow等模拟环境进行充分测试
3. 实盘交易需要相应的期货账户和授权
4. 请遵守相关法律法规和交易所规则

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。