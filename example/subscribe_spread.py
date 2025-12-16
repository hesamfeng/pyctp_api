#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
订阅hc2601和rb2601行情数据，并显示差价
焦炭和螺纹钢的价差分析
"""

import os
import sys
import time
from datetime import datetime

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DYLD_FRAMEWORK_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')
os.environ["DYLD_LIBRARY_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')

from ctp_gateway import CtpGateway


class SpreadMonitor:
    """价差监控类"""

    def __init__(self):
        """初始化"""
        # CTP配置
        self.config = load_config()

        # 订阅的合约
        self.symbols = ["hc2601", "rb2601"]  # 焦炭和螺纹钢

        # 存储最新行情
        self.market_data = {}

        # 价差历史记录
        self.spread_history = []
        self.max_history = 100  # 最多保存100条记录

        # 创建网关
        self.gateway = None

        print("=" * 60)
        print("焦炭(hc2601)与螺纹钢(rb2601)价差监控程序")
        print("=" * 60)
        print(f"订阅合约: {self.symbols}")
        print("注意: 价差 = 螺纹钢价格 - 焦炭价格")
        print("=" * 60)

    def on_market_data(self, data):
        """行情数据回调"""
        symbol = data.get("InstrumentID", "")
        if symbol in self.symbols:
            # 保存最新行情
            self.market_data[symbol] = {
                "LastPrice": data.get("LastPrice", 0),
                "Volume": data.get("Volume", 0),
                "OpenPrice": data.get("OpenPrice", 0),
                "HighestPrice": data.get("HighestPrice", 0),
                "LowestPrice": data.get("LowestPrice", 0),
                "UpdateTime": data.get("UpdateTime", ""),
                "ActionDay": data.get("ActionDay", "")
            }

            # 如果两个合约都有数据，计算并显示价差
            if len(self.market_data) == 2:
                self.calculate_and_display_spread()

    def on_order(self, order):
        """订单更新回调 - 过滤掉不需要的订单信息"""
        # 只处理我们关注的合约的订单信息
        symbol = order.get("InstrumentID", "")
        if symbol in self.symbols:
            # 这里可以处理关注合约的订单信息
            pass
        # 其他合约的订单信息直接忽略，不显示

    def on_trade(self, trade):
        """成交回报回调 - 过滤掉不需要的成交信息"""
        # 只处理我们关注的合约的成交信息
        symbol = trade.get("InstrumentID", "")
        if symbol in self.symbols:
            # 这里可以处理关注合约的成交信息
            pass
        # 其他合约的成交信息直接忽略，不显示

    def calculate_and_display_spread(self):
        """计算并显示价差"""
        hc_data = self.market_data.get("hc2601", {})
        rb_data = self.market_data.get("rb2601", {})

        hc_price = hc_data.get("LastPrice", 0)
        rb_price = rb_data.get("LastPrice", 0)

        if hc_price > 0 and rb_price > 0:
            # 计算价差 (螺纹钢 - 焦炭)
            spread = rb_price - hc_price

            # 获取当前时间
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 保存历史记录
            self.spread_history.append({
                "time": now,
                "spread": spread,
                "hc_price": hc_price,
                "rb_price": rb_price,
                "hc_volume": hc_data.get("Volume", 0),
                "rb_volume": rb_data.get("Volume", 0)
            })

            # 限制历史记录数量
            if len(self.spread_history) > self.max_history:
                self.spread_history.pop(0)

            # 清屏（在macOS上）
            os.system('clear')

            # 显示标题
            print("=" * 60)
            print(f"焦炭(hc2601)与螺纹钢(rb2601)价差监控 - {now}")
            print("=" * 60)

            # 显示最新行情
            print(f"\n📊 最新行情:")
            print(f"{'合约':<10} {'最新价':<10} {'成交量':<10} {'涨跌幅':<10} {'最高':<10} {'最低':<10}")
            print("-" * 60)

            # 焦炭
            hc_change = self._calculate_change(hc_data.get("OpenPrice", hc_price), hc_price)
            print(f"{'hc2601':<10} {hc_price:<10.2f} {hc_data.get('Volume', 0):<10} {hc_change:<10.2f} {hc_data.get('HighestPrice', 0):<10.2f} {hc_data.get('LowestPrice', 0):<10.2f}")

            # 螺纹钢
            rb_change = self._calculate_change(rb_data.get("OpenPrice", rb_price), rb_price)
            print(f"{'rb2601':<10} {rb_price:<10.2f} {rb_data.get('Volume', 0):<10} {rb_change:<10.2f} {rb_data.get('HighestPrice', 0):<10.2f} {rb_data.get('LowestPrice', 0):<10.2f}")

            # 显示价差
            print("\n" + "=" * 60)
            print(f"💰 价差分析 (rb2601 - hc2601):")
            print(f"   当前价差: {spread:.2f}")
            print(f"   价差说明: 螺纹钢比焦炭贵 {spread:.2f} 元")

            # 价差统计
            if len(self.spread_history) > 1:
                spreads = [h["spread"] for h in self.spread_history]
                avg_spread = sum(spreads) / len(spreads)
                max_spread = max(spreads)
                min_spread = min(spreads)

                print(f"\n📈 价差统计 (最近{len(self.spread_history)}条):")
                print(f"   平均价差: {avg_spread:.2f}")
                print(f"   最高价差: {max_spread:.2f}")
                print(f"   最低价差: {min_spread:.2f}")
                print(f"   价差区间: {max_spread - min_spread:.2f}")

                # 价差趋势
                if len(spreads) >= 5:
                    recent_avg = sum(spreads[-5:]) / 5
                    if spread > recent_avg:
                        trend = "↗️ 扩大"
                    elif spread < recent_avg:
                        trend = "↘️ 收缩"
                    else:
                        trend = "→ 持平"
                    print(f"   短期趋势: {trend}")

            print("\n按 Ctrl+C 退出程序")
            print("=" * 60)

    def _calculate_change(self, open_price, current_price):
        """计算涨跌幅"""
        if open_price == 0:
            return 0
        return ((current_price - open_price) / open_price) * 100

    def run(self):
        """运行监控程序"""
        try:
            # 创建网关
            print("初始化CTP网关...")
            self.gateway = CtpGateway(self.config)

            # 注册回调
            self.gateway.register_callback('market_data', self.on_market_data)
            self.gateway.register_callback('order', self.on_order)
            self.gateway.register_callback('trade', self.on_trade)

            # 连接服务器
            print("连接CTP服务器...")
            if not self.gateway.connect():
                print("❌ 连接服务器失败")
                return

            # 等待登录
            print("等待登录...")
            if not self.gateway.wait_for_login(15):
                print("❌ 登录失败")
                return

            # 确认结算单
            self.gateway.confirm_settlement()
            print("登录成功！")

            # 订阅行情
            print(f"\n订阅行情: {self.symbols}")
            self.gateway.subscribe_market_data(self.symbols)

            # 运行监控
            print("\n开始监控价差...")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n用户中断，程序退出")
        except Exception as e:
            print(f"\n程序异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.gateway:
                print("\n断开连接...")
                self.gateway.disconnect()


def main():
    """主函数"""
    monitor = SpreadMonitor()
    monit
from secure_config import load_configor.run()


if __name__ == "__main__":
    main()