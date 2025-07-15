#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP统一网关

整合MD（行情）和TD（交易）接口，作为统一入口供其他代码调用
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from threading import Event, Lock
from collections import defaultdict

from pyctp_api import MdApi, TdApi
from pyctp_api.api import (
    THOST_FTDC_D_Buy,
    THOST_FTDC_D_Sell,
    THOST_FTDC_OF_Open,
    THOST_FTDC_OF_Close,
    THOST_FTDC_OPT_LimitPrice,
    THOST_FTDC_TC_GFD,
    THOST_FTDC_VC_AV,
    THOST_FTDC_HF_Speculation,
    THOST_FTDC_CC_Immediately,
    THOST_FTDC_FCC_NotForceClose,
    THOST_FTDC_AF_Delete
)


class CtpGateway:
    """CTP统一网关类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化CTP网关
        
        Args:
            config: 配置字典，包含连接参数
        """
        self.config = config
        
        # 请求ID管理
        self._md_req_id = 0
        self._td_req_id = 0
        self._order_ref = 0
        self._req_lock = Lock()
        
        # 连接状态
        self.md_connected = False
        self.md_logged_in = False
        self.td_connected = False
        self.td_logged_in = False
        self.td_authenticated = False
        self.settlement_confirmed = False
        
        # 数据存储
        self.market_data = {}  # 实时行情数据
        self.positions = {}    # 持仓数据
        self.account = {}      # 账户数据
        self.orders = {}       # 订单数据
        self.trades = {}       # 成交数据
        self.instruments = {}  # 合约信息
        
        # 事件回调
        self.callbacks = defaultdict(list)
        
        # 初始化API
        self._init_apis()
        
        print(f"🚀 CTP网关初始化完成")
        print(f"📋 配置信息:")
        print(f"   用户ID: {config.get('用户名', 'N/A')}")
        print(f"   经纪商: {config.get('经纪商代码', 'N/A')}")
        print(f"   行情服务器: {config.get('行情服务器', 'N/A')}")
        print(f"   交易服务器: {config.get('交易服务器', 'N/A')}")

    def _init_apis(self):
        """初始化MD和TD API"""
        # 创建MD API
        self.md_api = self._create_md_api()
        
        # 创建TD API
        self.td_api = self._create_td_api()

    def _create_md_api(self):
        """创建行情API"""
        class GatewayMdApi(MdApi):
            def __init__(self, gateway):
                super().__init__()
                self.gateway = gateway

            def onFrontConnected(self):
                print("🔗 行情服务器连接成功")
                self.gateway.md_connected = True
                self.gateway._trigger_callback('md_connected')
                
                # 自动登录
                self.gateway._md_login()

            def onFrontDisconnected(self, reason: int):
                print(f"❌ 行情服务器连接断开，原因: {reason}")
                self.gateway.md_connected = False
                self.gateway.md_logged_in = False
                self.gateway._trigger_callback('md_disconnected', reason)

            def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到行情登录响应, ReqID: {reqid}")
                if error and error.get("ErrorID", -1) == 0:
                    print(f"✅ 行情服务器登录成功! TradingDay: {data.get('TradingDay', 'N/A')}")
                    self.gateway.md_logged_in = True
                    self.gateway._trigger_callback('md_login_success', data)
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '未知错误'
                    print(f"❌ 行情服务器登录失败: {error_msg}")
                    self.gateway._trigger_callback('md_login_failed', error)

            def onRspError(self, error: dict, reqid: int, last: bool):
                print(f"❌ 行情API错误, ReqID: {reqid}, Error: {error}")
                self.gateway._trigger_callback('md_error', error)

            def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool):
                if error and error.get("ErrorID", -1) == 0:
                    symbol = data.get('InstrumentID', 'N/A')
                    print(f"✅ 行情订阅成功: {symbol}")
                    self.gateway._trigger_callback('subscribe_success', data)
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '未知错误'
                    print(f"❌ 行情订阅失败: {error_msg}")
                    self.gateway._trigger_callback('subscribe_failed', error)

            def onRtnDepthMarketData(self, data: dict):
                symbol = data.get("InstrumentID", "")
                if symbol:
                    self.gateway.market_data[symbol] = data
                    self.gateway._trigger_callback('market_data', data)

        api = GatewayMdApi(self)
        # 重要：先创建底层API实例
        api.createFtdcMdApi("")
        return api

    def _create_td_api(self):
        """创建交易API"""
        class GatewayTdApi(TdApi):
            def __init__(self, gateway):
                super().__init__()
                self.gateway = gateway

            def onFrontConnected(self):
                print("🔗 交易服务器连接成功")
                self.gateway.td_connected = True
                self.gateway._trigger_callback('td_connected')
                
                # 自动认证
                self.gateway._td_authenticate()

            def onFrontDisconnected(self, reason: int):
                print(f"❌ 交易服务器连接断开，原因: {reason}")
                self.gateway.td_connected = False
                self.gateway.td_logged_in = False
                self.gateway.td_authenticated = False
                self.gateway._trigger_callback('td_disconnected', reason)

            def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到认证响应, ReqID: {reqid}")
                if error and error.get("ErrorID", -1) == 0:
                    print("✅ 交易服务器认证成功!")
                    self.gateway.td_authenticated = True
                    self.gateway._trigger_callback('td_auth_success', data)
                    
                    # 自动登录
                    self.gateway._td_login()
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '未知错误'
                    print(f"❌ 交易服务器认证失败: {error_msg}")
                    self.gateway._trigger_callback('td_auth_failed', error)

            def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到交易登录响应, ReqID: {reqid}")
                if error and error.get("ErrorID", -1) == 0:
                    print(f"✅ 交易服务器登录成功! TradingDay: {data.get('TradingDay', 'N/A')}")
                    print(f"   前端编号: {data.get('FrontID', 'N/A')}")
                    print(f"   会话编号: {data.get('SessionID', 'N/A')}")
                    self.gateway.td_logged_in = True
                    self.gateway._trigger_callback('td_login_success', data)
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '未知错误'
                    print(f"❌ 交易服务器登录失败: {error_msg}")
                    self.gateway._trigger_callback('td_login_failed', error)

            def onRspSettlementInfoConfirm(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到结算确认响应, ReqID: {reqid}")
                if error and error.get("ErrorID", -1) == 0:
                    print("✅ 结算单确认成功!")
                    self.gateway.settlement_confirmed = True
                    self.gateway._trigger_callback('settlement_confirmed', data)
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '未知错误'
                    print(f"❌ 结算单确认失败: {error_msg}")
                    self.gateway._trigger_callback('settlement_confirm_failed', error)

            def onRspQryTradingAccount(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到账户查询响应, ReqID: {reqid}, 数据: {bool(data)}, 错误: {error}")
                if (not error or error.get("ErrorID", 0) == 0) and data:
                    self.gateway.account = data
                    print(f"💰 账户信息更新: 可用资金={data.get('Available', 0):.2f}")
                    self.gateway._trigger_callback('account_data', data)
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '无数据'
                    print(f"❌ 账户查询失败: {error_msg}")

            def onRspQryInvestorPosition(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到持仓查询响应, ReqID: {reqid}, 数据: {bool(data)}, 错误: {error}")
                if (not error or error.get("ErrorID", 0) == 0) and data:
                    symbol = data.get('InstrumentID', '')
                    if symbol:
                        self.gateway.positions[symbol] = data
                        self.gateway._trigger_callback('position_data', data)
                        print(f"📦 持仓信息更新: {symbol} 持仓={data.get('Position', 0)}")
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '无数据'
                    print(f"❌ 持仓查询失败: {error_msg}")

            def onRspQryInstrument(self, data: dict, error: dict, reqid: int, last: bool):
                print(f"📥 收到合约查询响应, ReqID: {reqid}, 数据: {bool(data)}, 错误: {error}")
                if (not error or error.get("ErrorID", 0) == 0) and data:
                    symbol = data.get('InstrumentID', '')
                    if symbol:
                        self.gateway.instruments[symbol] = data
                        self.gateway._trigger_callback('instrument_data', data)
                        print(f"🔍 合约信息更新: {symbol}")
                else:
                    error_msg = error.get('ErrorMsg', '未知错误') if error else '无数据'
                    print(f"❌ 合约查询失败: {error_msg}")

            def onRtnOrder(self, data: dict):
                order_sys_id = data.get('OrderSysID', '')
                if order_sys_id:
                    self.gateway.orders[order_sys_id] = data
                    print(f"📋 订单更新: {data.get('InstrumentID', '')} "
                          f"状态={data.get('OrderStatus', '')} "
                          f"价格={data.get('LimitPrice', 0)}")
                    self.gateway._trigger_callback('order_update', data)

            def onRtnTrade(self, data: dict):
                trade_id = data.get('TradeID', '')
                if trade_id:
                    self.gateway.trades[trade_id] = data
                    print(f"💼 成交回报: {data.get('InstrumentID', '')} "
                          f"价格={data.get('Price', 0)} "
                          f"数量={data.get('Volume', 0)}")
                    self.gateway._trigger_callback('trade_update', data)

        api = GatewayTdApi(self)
        # 重要：先创建底层API实例  
        api.createFtdcTraderApi("")
        return api

    def _get_next_req_id(self, api_type: str) -> int:
        """获取下一个请求ID"""
        with self._req_lock:
            if api_type == 'md':
                self._md_req_id += 1
                return self._md_req_id
            else:
                self._td_req_id += 1
                return self._td_req_id

    def _get_next_order_ref(self) -> str:
        """获取下一个订单引用"""
        with self._req_lock:
            self._order_ref += 1
            return str(self._order_ref)

    def _trigger_callback(self, event: str, data: Any = None):
        """触发事件回调"""
        for callback in self.callbacks[event]:
            try:
                if data is not None:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                print(f"❌ 回调函数执行失败: {e}")

    def register_callback(self, event: str, callback: Callable):
        """注册事件回调函数"""
        self.callbacks[event].append(callback)

    def connect(self) -> bool:
        """连接MD和TD服务器"""
        print("🚀 开始连接CTP服务器...")
        
        # 连接行情服务器
        md_address = self.config.get('行情服务器', '')
        if md_address:
            print(f"📡 连接行情服务器: {md_address}")
            self.md_api.registerFront(md_address)
            self.md_api.init()
        
        # 连接交易服务器
        td_address = self.config.get('交易服务器', '')
        if td_address:
            print(f"📡 连接交易服务器: {td_address}")
            self.td_api.registerFront(td_address)
            self.td_api.init()
        
        # 等待连接成功
        max_wait = 10
        wait_time = 0
        while wait_time < max_wait:
            if self.md_connected and self.td_connected:
                print("✅ 所有服务器连接成功")
                return True
            time.sleep(1)
            wait_time += 1
            print(f"⏳ 等待连接... ({wait_time}/{max_wait})")
        
        print("❌ 连接超时")
        return False

    def _md_login(self):
        """行情登录"""
        req = {
            "UserID": self.config.get('用户名', ''),
            "BrokerID": self.config.get('经纪商代码', ''),
            "Password": self.config.get('密码', '')
        }
        req_id = self._get_next_req_id('md')
        print(f"🔐 发送行情登录请求, ReqID: {req_id}")
        self.md_api.reqUserLogin(req, req_id)

    def _td_authenticate(self):
        """交易认证"""
        req = {
            "UserID": self.config.get('用户名', ''),
            "BrokerID": self.config.get('经纪商代码', ''),
            "AppID": self.config.get('产品名称', ''),
            "AuthCode": self.config.get('授权编码', '')
        }
        req_id = self._get_next_req_id('td')
        print(f"🔐 发送交易认证请求, ReqID: {req_id}")
        self.td_api.reqAuthenticate(req, req_id)

    def _td_login(self):
        """交易登录"""
        req = {
            "UserID": self.config.get('用户名', ''),
            "BrokerID": self.config.get('经纪商代码', ''),
            "Password": self.config.get('密码', ''),
            "UserProductInfo": self.config.get('产品信息', '')
        }
        req_id = self._get_next_req_id('td')
        print(f"🔐 发送交易登录请求, ReqID: {req_id}")
        self.td_api.reqUserLogin(req, req_id)

    def wait_for_login(self, timeout: int = 30) -> bool:
        """等待登录完成"""
        print("⏳ 等待登录完成...")
        wait_time = 0
        while wait_time < timeout:
            if self.md_logged_in and self.td_logged_in:
                print("✅ 所有API登录成功")
                return True
            time.sleep(1)
            wait_time += 1
            if wait_time % 5 == 0:
                print(f"⏳ 等待登录... ({wait_time}/{timeout}s) "
                      f"MD:{self.md_logged_in} TD:{self.td_logged_in}")
        
        print("❌ 登录超时")
        return False

    def confirm_settlement(self) -> bool:
        """确认结算单"""
        if not self.td_logged_in:
            print("❌ 交易未登录，无法确认结算单")
            return False
        
        req = {
            "BrokerID": self.config.get('经纪商代码', ''),
            "InvestorID": self.config.get('用户名', ''),
            "ConfirmDate": time.strftime("%Y%m%d"),
            "ConfirmTime": time.strftime("%H:%M:%S")
        }
        req_id = self._get_next_req_id('td')
        print(f"📋 发送结算单确认请求, ReqID: {req_id}")
        self.td_api.reqSettlementInfoConfirm(req, req_id)
        
        # 等待结算确认完成
        max_wait = 10
        wait_time = 0
        while wait_time < max_wait:
            if self.settlement_confirmed:
                return True
            time.sleep(1)
            wait_time += 1
        
        return False

    def subscribe_market_data(self, symbols: List[str]) -> bool:
        """订阅行情数据"""
        if not self.md_logged_in:
            print("❌ 行情未登录，无法订阅")
            return False
        
        print(f"📊 订阅行情: {symbols}")
        # subscribeMarketData需要逐个订阅
        for symbol in symbols:
            self.md_api.subscribeMarketData(symbol)
        return True

    def unsubscribe_market_data(self, symbols: List[str]) -> bool:
        """取消订阅行情数据"""
        if not self.md_logged_in:
            print("❌ 行情未登录")
            return False
        
        print(f"📊 取消订阅行情: {symbols}")
        # unSubscribeMarketData需要逐个取消订阅
        for symbol in symbols:
            self.md_api.unSubscribeMarketData(symbol)
        return True

    def query_account(self) -> bool:
        """查询账户信息"""
        if not self.td_logged_in:
            print("❌ 交易未登录，无法查询账户")
            return False
        
        req = {
            "BrokerID": self.config.get('经纪商代码', ''),
            "InvestorID": self.config.get('用户名', '')
        }
        req_id = self._get_next_req_id('td')
        print(f"💰 发送账户查询请求, ReqID: {req_id}")
        self.td_api.reqQryTradingAccount(req, req_id)
        return True

    def query_positions(self) -> bool:
        """查询持仓信息"""
        if not self.td_logged_in:
            print("❌ 交易未登录，无法查询持仓")
            return False
        
        req = {
            "BrokerID": self.config.get('经纪商代码', ''),
            "InvestorID": self.config.get('用户名', '')
        }
        req_id = self._get_next_req_id('td')
        print(f"📦 发送持仓查询请求, ReqID: {req_id}")
        self.td_api.reqQryInvestorPosition(req, req_id)
        return True

    def query_instruments(self, symbol: str = "") -> bool:
        """查询合约信息"""
        if not self.td_logged_in:
            print("❌ 交易未登录，无法查询合约")
            return False
        
        req = {}
        if symbol:
            req["InstrumentID"] = symbol
            
        req_id = self._get_next_req_id('td')
        print(f"🔍 发送合约查询请求, ReqID: {req_id}, Symbol: {symbol or '全部'}")
        self.td_api.reqQryInstrument(req, req_id)
        return True

    def send_order(self, symbol: str, exchange: str, direction: str, 
                   offset: str, price: float, volume: int, 
                   order_type: str = "LIMIT") -> Optional[str]:
        """发送订单"""
        if not self.td_logged_in or not self.settlement_confirmed:
            print("❌ 交易未就绪，无法发送订单")
            return None
        
        # 方向映射
        direction_map = {
            "BUY": THOST_FTDC_D_Buy,
            "SELL": THOST_FTDC_D_Sell
        }
        
        # 开平映射
        offset_map = {
            "OPEN": THOST_FTDC_OF_Open,
            "CLOSE": THOST_FTDC_OF_Close
        }
        
        order_ref = self._get_next_order_ref()
        
        req = {
            "BrokerID": self.config.get('经纪商代码', ''),
            "InvestorID": self.config.get('用户名', ''),
            "InstrumentID": symbol,
            "ExchangeID": exchange,
            "OrderRef": order_ref,
            "Direction": direction_map.get(direction, THOST_FTDC_D_Buy),
            "CombOffsetFlag": offset_map.get(offset, THOST_FTDC_OF_Open),
            "CombHedgeFlag": THOST_FTDC_HF_Speculation,
            "LimitPrice": price,
            "VolumeTotalOriginal": volume,
            "TimeCondition": THOST_FTDC_TC_GFD,
            "VolumeCondition": THOST_FTDC_VC_AV,
            "OrderPriceType": THOST_FTDC_OPT_LimitPrice,
            "ContingentCondition": THOST_FTDC_CC_Immediately,
            "ForceCloseReason": THOST_FTDC_FCC_NotForceClose,
            "IsAutoSuspend": 0,
            "UserForceClose": 0
        }
        
        req_id = self._get_next_req_id('td')
        print(f"📋 发送订单: {symbol} {direction} {offset} "
              f"价格={price} 数量={volume} ReqID={req_id}")
        
        result = self.td_api.reqOrderInsert(req, req_id)
        if result == 0:
            return order_ref
        else:
            print(f"❌ 订单发送失败, 错误码: {result}")
            return None

    def cancel_order(self, symbol: str, exchange: str, order_sys_id: str) -> bool:
        """撤销订单"""
        if not self.td_logged_in:
            print("❌ 交易未登录，无法撤销订单")
            return False
        
        # 查找订单信息
        order_data = self.orders.get(order_sys_id)
        if not order_data:
            print(f"❌ 未找到订单: {order_sys_id}")
            return False
        
        req = {
            "BrokerID": self.config.get('经纪商代码', ''),
            "InvestorID": self.config.get('用户名', ''),
            "InstrumentID": symbol,
            "ExchangeID": exchange,
            "OrderSysID": order_sys_id,
            "ActionFlag": THOST_FTDC_AF_Delete,
            "FrontID": order_data.get('FrontID', 0),
            "SessionID": order_data.get('SessionID', 0),
            "OrderRef": order_data.get('OrderRef', '')
        }
        
        req_id = self._get_next_req_id('td')
        print(f"🗑️ 发送撤单请求: {order_sys_id} ReqID={req_id}")
        
        result = self.td_api.reqOrderAction(req, req_id)
        return result == 0

    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """获取最新行情数据"""
        return self.market_data.get(symbol)

    def get_account_info(self) -> Dict:
        """获取账户信息"""
        return self.account.copy()

    def get_positions(self) -> Dict:
        """获取持仓信息"""
        return self.positions.copy()

    def get_orders(self) -> Dict:
        """获取订单信息"""
        return self.orders.copy()

    def get_trades(self) -> Dict:
        """获取成交信息"""
        return self.trades.copy()

    def disconnect(self):
        """断开连接"""
        print("🔌 断开CTP连接...")
        if hasattr(self, 'md_api'):
            self.md_api.release()
        if hasattr(self, 'td_api'):
            self.td_api.release()
        print("✅ CTP连接已断开")

    def __del__(self):
        """析构函数"""
        self.disconnect() 