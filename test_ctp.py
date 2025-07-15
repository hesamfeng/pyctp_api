#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP网关测试程序

测试ctp_gateway.py中所有接口功能
"""

import time
import threading
from typing import Dict, Any
from ctp_gateway import CtpGateway


class CtpGatewayTester:
    """CTP网关测试类"""

    def __init__(self):
        # 配置信息 - 使用规则中提供的配置
        self.config = {
            "用户名": "174577",
            "密码": "Ho19880131!",
            "经纪商代码": "9999",
            "交易服务器": "tcp://182.254.243.31:30001",
            "行情服务器": "tcp://182.254.243.31:30011",
            "产品名称": "simnow_client_test",
            "授权编码": "0000000000000000",
            "产品信息": ""
        }
        
        # 测试参数
        self.test_symbols = ["rb2510", "ag2507", "au2508"]  # 测试合约
        self.test_exchange = "SHFE"  # 上海期货交易所
        self.test_price = 3000.0     # 测试价格（设置较低，避免成交）
        self.test_volume = 1         # 测试数量
        
        # 测试状态记录
        self.test_results = {}
        self.callback_data = {}
        
        # 创建网关实例
        self.gateway = None
        
        print("🧪 CTP网关测试程序初始化完成")
        print(f"📋 测试配置:")
        print(f"   用户: {self.config['用户名']}")
        print(f"   经纪商: {self.config['经纪商代码']}")
        print(f"   测试合约: {self.test_symbols}")

    def setup_callbacks(self):
        """设置回调函数来监听事件"""
        print("📞 设置事件回调函数...")
        
        # 连接事件
        self.gateway.register_callback('md_connected', self._on_md_connected)
        self.gateway.register_callback('td_connected', self._on_td_connected)
        self.gateway.register_callback('md_disconnected', self._on_md_disconnected)
        self.gateway.register_callback('td_disconnected', self._on_td_disconnected)
        
        # 登录事件
        self.gateway.register_callback('md_login_success', self._on_md_login_success)
        self.gateway.register_callback('td_login_success', self._on_td_login_success)
        self.gateway.register_callback('md_login_failed', self._on_md_login_failed)
        self.gateway.register_callback('td_login_failed', self._on_td_login_failed)
        
        # 认证事件
        self.gateway.register_callback('td_auth_success', self._on_td_auth_success)
        self.gateway.register_callback('td_auth_failed', self._on_td_auth_failed)
        
        # 结算确认事件
        self.gateway.register_callback('settlement_confirmed', self._on_settlement_confirmed)
        
        # 行情事件
        self.gateway.register_callback('subscribe_success', self._on_subscribe_success)
        self.gateway.register_callback('market_data', self._on_market_data)
        
        # 数据查询事件
        self.gateway.register_callback('account_data', self._on_account_data)
        self.gateway.register_callback('position_data', self._on_position_data)
        self.gateway.register_callback('instrument_data', self._on_instrument_data)
        
        # 交易事件
        self.gateway.register_callback('order_update', self._on_order_update)
        self.gateway.register_callback('trade_update', self._on_trade_update)
        
        print("✅ 回调函数设置完成")

    # ========== 回调函数 ==========
    def _on_md_connected(self):
        print("📅 回调：行情服务器连接成功")
        self.test_results['md_connect'] = True

    def _on_td_connected(self):
        print("📅 回调：交易服务器连接成功")
        self.test_results['td_connect'] = True

    def _on_md_disconnected(self, reason):
        print(f"📅 回调：行情服务器连接断开，原因：{reason}")
        self.test_results['md_disconnect'] = True

    def _on_td_disconnected(self, reason):
        print(f"📅 回调：交易服务器连接断开，原因：{reason}")
        self.test_results['td_disconnect'] = True

    def _on_md_login_success(self, data):
        print(f"📅 回调：行情登录成功，交易日：{data.get('TradingDay', 'N/A')}")
        self.test_results['md_login'] = True
        self.callback_data['md_login'] = data

    def _on_td_login_success(self, data):
        print(f"📅 回调：交易登录成功，交易日：{data.get('TradingDay', 'N/A')}")
        self.test_results['td_login'] = True
        self.callback_data['td_login'] = data

    def _on_md_login_failed(self, error):
        print(f"📅 回调：行情登录失败：{error.get('ErrorMsg', 'N/A')}")
        self.test_results['md_login'] = False

    def _on_td_login_failed(self, error):
        print(f"📅 回调：交易登录失败：{error.get('ErrorMsg', 'N/A')}")
        self.test_results['td_login'] = False

    def _on_td_auth_success(self, data):
        print("📅 回调：交易认证成功")
        self.test_results['td_auth'] = True
        self.callback_data['td_auth'] = data

    def _on_td_auth_failed(self, error):
        print(f"📅 回调：交易认证失败：{error.get('ErrorMsg', 'N/A')}")
        self.test_results['td_auth'] = False

    def _on_settlement_confirmed(self, data):
        print("📅 回调：结算单确认成功")
        self.test_results['settlement'] = True
        self.callback_data['settlement'] = data

    def _on_subscribe_success(self, data):
        symbol = data.get('InstrumentID', 'N/A')
        print(f"📅 回调：行情订阅成功：{symbol}")
        self.test_results[f'subscribe_{symbol}'] = True

    def _on_market_data(self, data):
        symbol = data.get('InstrumentID', '')
        price = data.get('LastPrice', 0)
        volume = data.get('Volume', 0)
        print(f"📅 回调：收到行情数据 {symbol} 价格:{price} 成交量:{volume}")
        if 'market_data_count' not in self.test_results:
            self.test_results['market_data_count'] = 0
        self.test_results['market_data_count'] += 1
        self.callback_data[f'market_data_{symbol}'] = data

    def _on_account_data(self, data):
        available = data.get('Available', 0)
        balance = data.get('Balance', 0)
        print(f"📅 回调：账户数据更新 可用:{available:.2f} 余额:{balance:.2f}")
        self.test_results['account_query'] = True
        self.callback_data['account'] = data

    def _on_position_data(self, data):
        symbol = data.get('InstrumentID', '')
        position = data.get('Position', 0)
        print(f"📅 回调：持仓数据更新 {symbol} 持仓:{position}")
        self.test_results['position_query'] = True
        if 'positions' not in self.callback_data:
            self.callback_data['positions'] = {}
        self.callback_data['positions'][symbol] = data

    def _on_instrument_data(self, data):
        symbol = data.get('InstrumentID', '')
        print(f"📅 回调：合约信息 {symbol}")
        if 'instrument_count' not in self.test_results:
            self.test_results['instrument_count'] = 0
        self.test_results['instrument_count'] += 1

    def _on_order_update(self, data):
        symbol = data.get('InstrumentID', '')
        status = data.get('OrderStatus', '')
        price = data.get('LimitPrice', 0)
        print(f"📅 回调：订单更新 {symbol} 状态:{status} 价格:{price}")
        self.test_results['order_insert'] = True
        if 'orders' not in self.callback_data:
            self.callback_data['orders'] = []
        self.callback_data['orders'].append(data)

    def _on_trade_update(self, data):
        symbol = data.get('InstrumentID', '')
        price = data.get('Price', 0)
        volume = data.get('Volume', 0)
        print(f"📅 回调：成交回报 {symbol} 价格:{price} 数量:{volume}")
        self.test_results['trade_update'] = True
        if 'trades' not in self.callback_data:
            self.callback_data['trades'] = []
        self.callback_data['trades'].append(data)

    # ========== 测试方法 ==========
    def test_initialization(self):
        """测试1：初始化网关"""
        print("\n" + "="*50)
        print("🧪 测试1：初始化CTP网关")
        print("="*50)
        
        try:
            self.gateway = CtpGateway(self.config)
            self.setup_callbacks()
            print("✅ 网关初始化成功")
            self.test_results['initialization'] = True
            return True
        except Exception as e:
            print(f"❌ 网关初始化失败：{e}")
            self.test_results['initialization'] = False
            return False

    def test_connection(self):
        """测试2：连接服务器"""
        print("\n" + "="*50)
        print("🧪 测试2：连接CTP服务器")
        print("="*50)
        
        try:
            success = self.gateway.connect()
            self.test_results['connection'] = success
            
            if success:
                print("✅ 服务器连接成功")
                return True
            else:
                print("❌ 服务器连接失败")
                return False
        except Exception as e:
            print(f"❌ 连接过程异常：{e}")
            self.test_results['connection'] = False
            return False

    def test_login(self):
        """测试3：登录验证"""
        print("\n" + "="*50)
        print("🧪 测试3：等待登录完成")
        print("="*50)
        
        try:
            success = self.gateway.wait_for_login(timeout=30)
            self.test_results['login'] = success
            
            if success:
                print("✅ 登录验证成功")
                return True
            else:
                print("❌ 登录验证失败")
                return False
        except Exception as e:
            print(f"❌ 登录过程异常：{e}")
            self.test_results['login'] = False
            return False

    def test_settlement(self):
        """测试4：结算单确认"""
        print("\n" + "="*50)
        print("🧪 测试4：确认结算单")
        print("="*50)
        
        try:
            success = self.gateway.confirm_settlement()
            self.test_results['settlement'] = success
            
            if success:
                print("✅ 结算单确认成功")
                return True
            else:
                print("❌ 结算单确认失败")
                return False
        except Exception as e:
            print(f"❌ 结算确认过程异常：{e}")
            self.test_results['settlement'] = False
            return False

    def test_market_data_subscription(self):
        """测试5：行情订阅"""
        print("\n" + "="*50)
        print("🧪 测试5：订阅行情数据")
        print("="*50)
        
        try:
            # 订阅行情
            success = self.gateway.subscribe_market_data(self.test_symbols)
            
            if success:
                print("✅ 行情订阅请求发送成功")
                
                # 等待一段时间接收行情数据
                print("⏳ 等待接收行情数据...")
                time.sleep(10)
                
                # 检查是否收到行情数据
                market_data_count = self.test_results.get('market_data_count', 0)
                if market_data_count > 0:
                    print(f"✅ 成功接收到 {market_data_count} 条行情数据")
                    self.test_results['market_subscription'] = True
                    return True
                else:
                    print("⚠️ 未收到行情数据推送")
                    self.test_results['market_subscription'] = False
                    return False
            else:
                print("❌ 行情订阅请求失败")
                self.test_results['market_subscription'] = False
                return False
                
        except Exception as e:
            print(f"❌ 行情订阅过程异常：{e}")
            self.test_results['market_subscription'] = False
            return False

    def test_data_queries(self):
        """测试6：数据查询"""
        print("\n" + "="*50)
        print("🧪 测试6：查询账户、持仓、合约信息")
        print("="*50)
        
        try:
            # 查询账户信息
            print("💰 查询账户信息...")
            self.gateway.query_account()
            time.sleep(2)
            
            # 查询持仓信息
            print("📦 查询持仓信息...")
            self.gateway.query_positions()
            time.sleep(2)
            
            # 查询合约信息（查询第一个测试合约）
            print(f"🔍 查询合约信息: {self.test_symbols[0]}...")
            self.gateway.query_instruments(self.test_symbols[0])
            time.sleep(3)
            
            # 检查查询结果
            account_ok = self.test_results.get('account_query', False)
            position_ok = self.test_results.get('position_query', False)
            instrument_count = self.test_results.get('instrument_count', 0)
            
            success_count = sum([account_ok, position_ok, instrument_count > 0])
            
            print(f"📊 数据查询结果:")
            print(f"   账户查询: {'✅' if account_ok else '❌'}")
            print(f"   持仓查询: {'✅' if position_ok else '❌'}")
            print(f"   合约查询: {'✅' if instrument_count > 0 else '❌'} ({instrument_count}条)")
            
            if success_count >= 2:
                print("✅ 数据查询测试通过")
                self.test_results['data_queries'] = True
                return True
            else:
                print("❌ 数据查询测试失败")
                self.test_results['data_queries'] = False
                return False
                
        except Exception as e:
            print(f"❌ 数据查询过程异常：{e}")
            self.test_results['data_queries'] = False
            return False

    def test_order_operations(self):
        """测试7：订单操作（下单和撤单）"""
        print("\n" + "="*50)
        print("🧪 测试7：订单操作测试")
        print("="*50)
        
        try:
            # 发送测试订单（使用很低的价格，确保不会成交）
            test_symbol = self.test_symbols[0]
            print(f"📋 发送测试订单: {test_symbol}")
            print(f"   买入开仓，价格: {self.test_price}, 数量: {self.test_volume}")
            
            order_ref = self.gateway.send_order(
                symbol=test_symbol,
                exchange=self.test_exchange,
                direction="BUY",
                offset="OPEN",
                price=self.test_price,
                volume=self.test_volume
            )
            
            if order_ref:
                print(f"✅ 订单发送成功，订单引用: {order_ref}")
                
                # 等待订单回报
                print("⏳ 等待订单回报...")
                time.sleep(5)
                
                # 检查是否收到订单回报
                order_insert_ok = self.test_results.get('order_insert', False)
                
                if order_insert_ok:
                    print("✅ 收到订单回报")
                    
                    # 尝试撤单（如果有订单数据）
                    orders = self.callback_data.get('orders', [])
                    if orders:
                        last_order = orders[-1]
                        order_sys_id = last_order.get('OrderSysID', '')
                        
                        if order_sys_id:
                            print(f"🗑️ 尝试撤销订单: {order_sys_id}")
                            cancel_success = self.gateway.cancel_order(
                                symbol=test_symbol,
                                exchange=self.test_exchange,
                                order_sys_id=order_sys_id
                            )
                            
                            if cancel_success:
                                print("✅ 撤单请求发送成功")
                                time.sleep(3)
                            else:
                                print("❌ 撤单请求失败")
                        else:
                            print("⚠️ 订单系统ID为空，无法撤单")
                    
                    self.test_results['order_operations'] = True
                    return True
                else:
                    print("❌ 未收到订单回报")
                    self.test_results['order_operations'] = False
                    return False
            else:
                print("❌ 订单发送失败")
                self.test_results['order_operations'] = False
                return False
                
        except Exception as e:
            print(f"❌ 订单操作过程异常：{e}")
            self.test_results['order_operations'] = False
            return False

    def test_data_access(self):
        """测试8：数据访问接口"""
        print("\n" + "="*50)
        print("🧪 测试8：数据访问接口")
        print("="*50)
        
        try:
            # 测试获取行情数据
            print("📊 测试行情数据获取...")
            for symbol in self.test_symbols:
                market_data = self.gateway.get_market_data(symbol)
                if market_data:
                    price = market_data.get('LastPrice', 0)
                    print(f"   {symbol}: 最新价 {price}")
                else:
                    print(f"   {symbol}: 无行情数据")
            
            # 测试获取账户信息
            print("💰 测试账户信息获取...")
            account_info = self.gateway.get_account_info()
            if account_info:
                available = account_info.get('Available', 0)
                balance = account_info.get('Balance', 0)
                print(f"   可用资金: {available:.2f}")
                print(f"   账户余额: {balance:.2f}")
            else:
                print("   无账户信息")
            
            # 测试获取持仓信息
            print("📦 测试持仓信息获取...")
            positions = self.gateway.get_positions()
            if positions:
                print(f"   持仓数量: {len(positions)} 个")
                for symbol, pos_data in list(positions.items())[:3]:  # 只显示前3个
                    position = pos_data.get('Position', 0)
                    print(f"   {symbol}: 持仓 {position}")
            else:
                print("   无持仓信息")
            
            # 测试获取订单信息
            print("📋 测试订单信息获取...")
            orders = self.gateway.get_orders()
            if orders:
                print(f"   订单数量: {len(orders)} 个")
                for order_id, order_data in list(orders.items())[:3]:  # 只显示前3个
                    symbol = order_data.get('InstrumentID', '')
                    status = order_data.get('OrderStatus', '')
                    print(f"   {order_id}: {symbol} 状态 {status}")
            else:
                print("   无订单信息")
            
            # 测试获取成交信息
            print("💼 测试成交信息获取...")
            trades = self.gateway.get_trades()
            if trades:
                print(f"   成交数量: {len(trades)} 个")
                for trade_id, trade_data in list(trades.items())[:3]:  # 只显示前3个
                    symbol = trade_data.get('InstrumentID', '')
                    price = trade_data.get('Price', 0)
                    print(f"   {trade_id}: {symbol} 价格 {price}")
            else:
                print("   无成交信息")
            
            print("✅ 数据访问接口测试完成")
            self.test_results['data_access'] = True
            return True
            
        except Exception as e:
            print(f"❌ 数据访问测试异常：{e}")
            self.test_results['data_access'] = False
            return False

    def test_unsubscribe(self):
        """测试9：取消订阅"""
        print("\n" + "="*50)
        print("🧪 测试9：取消行情订阅")
        print("="*50)
        
        try:
            # 取消行情订阅
            success = self.gateway.unsubscribe_market_data(self.test_symbols)
            
            if success:
                print("✅ 取消订阅请求发送成功")
                time.sleep(2)
                self.test_results['unsubscribe'] = True
                return True
            else:
                print("❌ 取消订阅请求失败")
                self.test_results['unsubscribe'] = False
                return False
                
        except Exception as e:
            print(f"❌ 取消订阅过程异常：{e}")
            self.test_results['unsubscribe'] = False
            return False

    def test_disconnection(self):
        """测试10：断开连接"""
        print("\n" + "="*50)
        print("🧪 测试10：断开连接")
        print("="*50)
        
        try:
            self.gateway.disconnect()
            print("✅ 连接断开成功")
            self.test_results['disconnection'] = True
            return True
            
        except Exception as e:
            print(f"❌ 断开连接异常：{e}")
            self.test_results['disconnection'] = False
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始CTP网关完整功能测试")
        print("="*60)
        
        test_methods = [
            ('初始化', self.test_initialization),
            ('连接', self.test_connection),
            ('登录', self.test_login),
            ('结算确认', self.test_settlement),
            ('行情订阅', self.test_market_data_subscription),
            ('数据查询', self.test_data_queries),
            ('订单操作', self.test_order_operations),
            ('数据访问', self.test_data_access),
            ('取消订阅', self.test_unsubscribe),
            ('断开连接', self.test_disconnection)
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_name, test_method in test_methods:
            try:
                success = test_method()
                if success:
                    passed_tests += 1
                    print(f"✅ {test_name}测试：通过")
                else:
                    print(f"❌ {test_name}测试：失败")
                    
                # 在某些关键测试失败时停止
                if not success and test_name in ['初始化', '连接', '登录']:
                    print(f"⚠️ 关键测试 '{test_name}' 失败，停止后续测试")
                    break
                    
            except Exception as e:
                print(f"❌ {test_name}测试异常：{e}")
        
        # 打印测试总结
        self.print_test_summary(passed_tests, total_tests)

    def print_test_summary(self, passed: int, total: int):
        """打印测试总结"""
        print("\n" + "="*60)
        print("📋 测试总结报告")
        print("="*60)
        
        print(f"📊 测试统计:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        print(f"   通过率: {passed/total*100:.1f}%")
        
        print(f"\n📝 详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        if passed == total:
            print(f"\n🎉 所有测试通过！CTP网关功能正常")
        elif passed >= total * 0.8:
            print(f"\n✅ 大部分测试通过，CTP网关基本功能正常")
        else:
            print(f"\n⚠️ 多个测试失败，请检查配置和网络连接")
        
        print("="*60)


def main():
    """主函数"""
    print("🧪 CTP网关测试程序启动")
    print("="*60)
    
    try:
        # 创建测试实例
        tester = CtpGatewayTester()
        
        # 运行所有测试
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试程序异常：{e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 测试程序结束")


if __name__ == "__main__":
    main() 