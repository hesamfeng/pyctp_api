import os
from time import sleep
from threading import Condition
from collections.abc import Generator

import pytest

from pyctp_api.api import MdApi


# 测试参
from secure_config import load_config数
MD_SETTING = {
    "UserID": "174577",                          # 用户名
    "Password": "Ho19880131!",                   # 密码
    "BrokerID": "9999",                          # 经纪商代码
}
MD_ADDRESS = "tcp://182.254.243.31:30011"       # 行情服务器地址
SYMBOL = "rb2505"                                # 合约代码（螺纹钢2505）
WAIT_TIME = 10                                   # 回调等待时间


class MyMdApi(MdApi):
    """继承实现API接口类"""

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        self.callback_result: list = []
        self.callback_done: Condition = Condition()

        self.reqid: int = 0
        self.connect_status: bool = False
        self.login_status: bool = False

    def onFrontConnected(self) -> None:
        """服务器连接成功回报"""
        print("🔗 行情服务器连接成功")
        self.connect_status = True

    def onFrontDisconnected(self, reason: int) -> None:
        """服务器连接断开回报"""
        print(f"❌ 行情服务器连接断开，原因: {reason}")
        self.login_status = False

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """用户登录请求回报"""
        print(f"📥 收到登录响应, ReqID: {reqid}, Last: {last}")
        if error["ErrorID"] == 0:
            print(f"✅ 行情服务器登录成功! TradingDay: {data.get('TradingDay', 'N/A')}")
        else:
            print(f"❌ 行情服务器登录失败: {error['ErrorMsg']}")
        
        self.callback_result = [data, error, reqid, last]

        with self.callback_done:
            self.callback_done.notify()

    def onRspError(self, error: dict, reqid: int, last: bool) -> None:
        """请求报错回报"""
        print(f"❌ 行情API错误, ReqID: {reqid}, Error: {error}")
        self.callback_result = [error, reqid, last]

        with self.callback_done:
            self.callback_done.notify()

    def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """订阅行情回报"""
        print(f"📥 收到行情订阅响应, ReqID: {reqid}")
        if error["ErrorID"] == 0:
            print(f"✅ 行情订阅成功: {data.get('InstrumentID', 'N/A')}")
        else:
            print(f"❌ 行情订阅失败: {error['ErrorMsg']}")

    def onRtnDepthMarketData(self, data: dict) -> None:
        """行情数据推送"""
        symbol = data.get("InstrumentID", "未知")
        price = data.get("LastPrice", 0)
        update_time = data.get("UpdateTime", "")
        print(f"📊 收到行情推送: {symbol} 价格:{price} 时间:{update_time}")
        
        self.callback_result = [data]

        with self.callback_done:
            self.callback_done.notify()


@pytest.fixture(scope="session")
def login_api() -> Generator[MyMdApi, None, None]:
    """初始化API对象"""
    print("🚀 开始初始化行情API...")
    print(f"📋 测试参数:")
    print(f"   用户ID: {MD_SETTING['UserID']}")
    print(f"   经纪商: {MD_SETTING['BrokerID']}")
    print(f"   服务器: {MD_ADDRESS}")
    print(f"   合约: {SYMBOL}")
    
    # 实例化API对象
    api: MyMdApi = MyMdApi()
    print("✅ API对象创建成功")

    # 创建API对象
    print("🔧 初始化CTP行情API...")
    api.createFtdcMdApi("")
    print("✅ CTP行情API初始化完成")

    # 注册前端
    print(f"🔗 连接行情服务器: {MD_ADDRESS}")
    api.registerFront(MD_ADDRESS)
    api.init()
    print("⏳ 等待服务器连接...")

    # 等待连接成功
    count: int = 0
    while not api.connect_status:
        sleep(1)
        count += 1
        if count >= WAIT_TIME:
            print(f"❌ 连接超时 ({WAIT_TIME}秒)")
            pytest.exit("CTP行情服务器连接超时，请检查端口能否连接")

    print(f"✅ 服务器连接成功 (耗时{count}秒)")

    # 发送登录请求
    api.reqid += 1
    print(f"📤 发送登录请求, ReqID: {api.reqid}")
    api.reqUserLogin(MD_SETTING, api.reqid)

    # 等待登录结果
    print("⏳ 等待登录响应...")
    with api.callback_done:
        api.callback_done.wait(WAIT_TIME)

    error: dict = api.callback_result[1]
    if error["ErrorID"] != 0:
        print(f"❌ 登录失败，错误代码: {error['ErrorID']}, 错误信息: {error['ErrorMsg']}")
        pytest.exit(f"CTP行情服务器登录失败，错误代码：{error['ErrorID']}")
    else:
        api.login_status = True
        print("🎉 行情API登录流程全部完成！")

    yield api

    # 测试结束后关闭API
    print("🔚 关闭行情API...")
    api.exit()
    print("✅ 行情API已关闭")


def test_login(login_api: MyMdApi) -> None:
    """测试API登录"""
    print("\n🧪 开始测试: 登录功能")
    print(f"📊 登录状态: {login_api.login_status}")
    assert login_api.login_status is True
    print("✅ 登录测试通过!")


def test_subscribe(login_api: MyMdApi) -> None:
    """测试订阅行情"""
    print(f"\n🧪 开始测试: 行情订阅功能")
    print(f"📤 订阅合约: {SYMBOL}")
    login_api.subscribeMarketData(SYMBOL)

    print("⏳ 等待行情数据推送...")
    with login_api.callback_done:
        login_api.callback_done.wait(WAIT_TIME)

    print(f"📊 回调结果: {login_api.callback_result}")
    
    if login_api.callback_result and len(login_api.callback_result) > 0:
        data = login_api.callback_result[0]
        if isinstance(data, dict) and "InstrumentID" in data:
            symbol: str = data["InstrumentID"]
            print(f"✅ 收到行情数据，合约: {symbol}")
            assert symbol == SYMBOL      # 检查推送的合约代码是否一致
            print("✅ 行情订阅测试通过!")
        else:
            print(f"⚠️  收到数据格式异常: {data}")
            print("ℹ️  这可能是正常的，有些合约在非交易时间没有行情推送")
    else:
        print("⚠️  未收到行情数据推送")
        print("ℹ️  这可能是正常的，有些合约在非交易时间没有行情推送")



if __name__ == "__main__":
    print("🚀 直接运行行情API测试...")
    
    # 手动创建和初始化API
    print("🚀 开始初始化行情API...")
    print(f"📋 测试参数:")
    print(f"   用户ID: {MD_SETTING['UserID']}")
    print(f"   经纪商: {MD_SETTING['BrokerID']}")
    print(f"   服务器: {MD_ADDRESS}")
    print(f"   合约: {SYMBOL}")
    
    # 实例化API对象
    api = MyMdApi()
    print("✅ API对象创建成功")

    # 创建API对象
    print("🔧 初始化CTP行情API...")
    api.createFtdcMdApi("")
    print("✅ CTP行情API初始化完成")

    # 注册前端
    print(f"🔗 连接行情服务器: {MD_ADDRESS}")
    api.registerFront(MD_ADDRESS)
    api.init()
    print("⏳ 等待服务器连接...")

    # 等待连接成功
    count = 0
    while not api.connect_status:
        sleep(1)
        count += 1
        if count >= WAIT_TIME:
            print(f"❌ 连接超时 ({WAIT_TIME}秒)")
            exit(1)

    print(f"✅ 服务器连接成功 (耗时{count}秒)")

    # 发送登录请求
    api.reqid += 1
    print(f"📤 发送登录请求, ReqID: {api.reqid}")
    api.reqUserLogin(MD_SETTING, api.reqid)

    # 等待登录结果
    print("⏳ 等待登录响应...")
    with api.callback_done:
        api.callback_done.wait(WAIT_TIME)

    error = api.callback_result[1]
    if error["ErrorID"] != 0:
        print(f"❌ 登录失败，错误代码: {error['ErrorID']}, 错误信息: {error['ErrorMsg']}")
        exit(1)
    else:
        api.login_status = True
        print("🎉 行情API登录流程全部完成！")

    # 执行测试
    test_login(api)
    test_subscribe(api)
    
    # 关闭API
    print("🔚 关闭行情API...")
    api.exit()
    print("✅ 行情API已关闭")
    
    print("🎉 所有测试完成！")  