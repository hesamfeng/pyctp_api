#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制台版焦炭与螺纹钢价差监控程序
带有彩色显示和实时更新界面
"""

import sys
import os
import time
import signal
from datetime import datetime
from threading import Thread
from collections import deque

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DYLD_FRAMEWORK_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')
os.environ["DYLD_LIBRARY_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')

from ctp_gateway import CtpGateway


class Colors:
    
from secure_config import load_config"""终端颜色控制"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    # 背景色
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_WHITE = '\033[47m'


class SpreadMonitorConsole:
    """控制台版价差监控"""

    def __init__(self):
        self.symbols = ["hc2601", "rb2601"]
        self.market_data = {}
        self.spread_history = deque(maxlen=100)
        self.running = False
        self.gateway = None

        # CTP配置
        self.config = load_config()

        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """信号处理器，用于优雅退出"""
        print(f"\n{Colors.YELLOW}收到中断信号，正在停止监控...{Colors.END}")
        self.stop()

    def start(self):
        """开始监控"""
        self.running = True
        self.show_header()

        # 启动网关连接
        gateway_thread = Thread(target=self.connect_gateway, daemon=True)
        gateway_thread.start()

        # 启动显示更新线程
        display_thread = Thread(target=self.update_display, daemon=True)
        display_thread.start()

        # 主线程等待
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def connect_gateway(self):
        """连接CTP网关"""
        try:
            self.update_status("正在初始化CTP网关...")
            self.gateway = CtpGateway(self.config)

            # 注册回调
            self.gateway.register_callback('market_data', self.on_market_data)
            self.gateway.register_callback('order', self.on_order)
            self.gateway.register_callback('trade', self.on_trade)

            self.update_status("正在连接CTP服务器...")
            if not self.gateway.connect():
                self.update_status(f"{Colors.RED}❌ 连接服务器失败{Colors.END}")
                return

            self.update_status("等待登录...")
            if not self.gateway.wait_for_login(15):
                self.update_status(f"{Colors.RED}❌ 登录失败{Colors.END}")
                return

            self.gateway.confirm_settlement()
            self.update_status(f"{Colors.GREEN}✅ 登录成功！{Colors.END}")

            self.update_status("订阅行情...")
            self.gateway.subscribe_market_data(self.symbols)
            self.update_status(f"{Colors.GREEN}✅ 开始监控价差...{Colors.END}")

            # 保持连接
            while self.running:
                time.sleep(1)

        except Exception as e:
            self.update_status(f"{Colors.RED}❌ 程序异常: {e}{Colors.END}")

    def on_market_data(self, data):
        """行情数据回调"""
        symbol = data.get("InstrumentID", "")
        if symbol in self.symbols:
            self.market_data[symbol] = {
                "LastPrice": data.get("LastPrice", 0),
                "Volume": data.get("Volume", 0),
                "OpenPrice": data.get("OpenPrice", 0),
                "HighestPrice": data.get("HighestPrice", 0),
                "LowestPrice": data.get("LowestPrice", 0),
                "UpdateTime": data.get("UpdateTime", ""),
                "ActionDay": data.get("ActionDay", "")
            }

            # 计算价差
            if len(self.market_data) == 2:
                self.calculate_spread()

    def on_order(self, order):
        """订单更新回调"""
        pass  # 过滤掉

    def on_trade(self, trade):
        """成交回报回调"""
        pass  # 过滤掉

    def calculate_spread(self):
        """计算价差"""
        hc_data = self.market_data.get("hc2601", {})
        rb_data = self.market_data.get("rb2601", {})

        hc_price = hc_data.get("LastPrice", 0)
        rb_price = rb_data.get("LastPrice", 0)

        if hc_price > 0 and rb_price > 0:
            spread = rb_price - hc_price
            now = datetime.now()

            # 保存历史记录
            self.spread_history.append({
                "time": now,
                "spread": spread,
                "hc_price": hc_price,
                "rb_price": rb_price,
                "hc_volume": hc_data.get("Volume", 0),
                "rb_volume": rb_data.get("Volume", 0)
            })

    def show_header(self):
        """显示标题"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print("                    焦炭(hc2601)与螺纹钢(rb2601)价差监控")
        print("=" * 80)
        print(f" 监控合约: hc2601 (焦炭) | rb2601 (螺纹钢)")
        print(f" 计算公式: 价差 = 螺纹钢价格 - 焦炭价格")
        print(f" 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"{Colors.END}")

    def update_display(self):
        """更新显示"""
        while self.running:
            time.sleep(1)  # 每秒更新一次
            self.clear_screen()
            self.show_header()
            self.show_market_data()
            self.show_spread_analysis()
            self.show_status()

    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def show_market_data(self):
        """显示行情数据"""
        print(f"\n{Colors.BOLD}📊 最新行情数据{Colors.END}")
        print("-" * 80)
        print(f"{'合约':<12} {'最新价':<10} {'成交量':<10} {'涨跌幅':<10} {'最高':<10} {'最低':<10}")
        print("-" * 80)

        # 显示焦炭数据
        if "hc2601" in self.market_data:
            hc_data = self.market_data["hc2601"]
            price = hc_data.get("LastPrice", 0)
            volume = hc_data.get("Volume", 0)
            open_price = hc_data.get("OpenPrice", price)
            high = hc_data.get("HighestPrice", 0)
            low = hc_data.get("LowestPrice", 0)
            change = ((price - open_price) / open_price * 100) if open_price > 0 else 0

            change_color = Colors.GREEN if change > 0 else Colors.RED if change < 0 else Colors.END
            print(f"{'焦炭 hc2601':<12} {price:<10.2f} {volume:<10,} {change_color}{change:+.2f}%{Colors.END:<8} {high:<10.2f} {low:<10.2f}")
        else:
            print(f"{'焦炭 hc2601':<12} {'--':<10} {'--':<10} {'--':<10} {'--':<10} {'--':<10}")

        # 显示螺纹钢数据
        if "rb2601" in self.market_data:
            rb_data = self.market_data["rb2601"]
            price = rb_data.get("LastPrice", 0)
            volume = rb_data.get("Volume", 0)
            open_price = rb_data.get("OpenPrice", price)
            high = rb_data.get("HighestPrice", 0)
            low = rb_data.get("LowestPrice", 0)
            change = ((price - open_price) / open_price * 100) if open_price > 0 else 0

            change_color = Colors.GREEN if change > 0 else Colors.RED if change < 0 else Colors.END
            print(f"{'螺纹钢 rb2601':<12} {price:<10.2f} {volume:<10,} {change_color}{change:+.2f}%{Colors.END:<8} {high:<10.2f} {low:<10.2f}")
        else:
            print(f"{'螺纹钢 rb2601':<12} {'--':<10} {'--':<10} {'--':<10} {'--':<10} {'--':<10}")

        print("-" * 80)

    def show_spread_analysis(self):
        """显示价差分析"""
        print(f"\n{Colors.BOLD}💰 价差分析{Colors.END}")
        print("-" * 80)

        if len(self.spread_history) > 0:
            latest = self.spread_history[-1]
            spread = latest["spread"]
            hc_price = latest["hc_price"]
            rb_price = latest["rb_price"]

            # 当前价差显示
            if spread > 0:
                spread_color = Colors.GREEN
                spread_text = f"螺纹钢比焦炭贵 {abs(spread):.2f} 元"
            else:
                spread_color = Colors.RED
                spread_text = f"螺纹钢比焦炭便宜 {abs(spread):.2f} 元"

            print(f"当前价差: {spread_color}{spread:+.2f}{Colors.END} 元")
            print(f"说明: {spread_color}{spread_text}{Colors.END}")

            # 统计分析
            if len(self.spread_history) > 1:
                spreads = [h["spread"] for h in self.spread_history]
                avg_spread = sum(spreads) / len(spreads)
                max_spread = max(spreads)
                min_spread = min(spreads)

                print(f"\n{Colors.BOLD}📈 价差统计 (最近{len(self.spread_history)}条记录):{Colors.END}")
                print(f"   平均价差: {avg_spread:+.2f} 元")
                print(f"   最高价差: {max_spread:+.2f} 元")
                print(f"   最低价差: {min_spread:+.2f} 元")
                print(f"   价差区间: {abs(max_spread - min_spread):.2f} 元")

                # 趋势分析
                if len(spreads) >= 5:
                    recent_avg = sum(spreads[-5:]) / 5
                    if spread > recent_avg + 1:
                        trend = "↗️ 价差扩大"
                        trend_color = Colors.GREEN
                    elif spread < recent_avg - 1:
                        trend = "↘️ 价差收缩"
                        trend_color = Colors.RED
                    else:
                        trend = "→ 价差持平"
                        trend_color = Colors.YELLOW

                    print(f"   短期趋势: {trend_color}{trend}{Colors.END}")

            # 最近价差记录
            print(f"\n{Colors.BOLD}📋 最近价差记录:{Colors.END}")
            print("-" * 80)
            for i in range(min(5, len(self.spread_history))):
                record = self.spread_history[-(5-i)]
                time_str = record["time"].strftime("%H:%M:%S")
                spread = record["spread"]
                spread_color = Colors.GREEN if spread > 0 else Colors.RED
                print(f"   {time_str} - 焦炭: {record['hc_price']:.2f} | 螺纹钢: {record['rb_price']:.2f} | "
                      f"价差: {spread_color}{spread:+.2f}{Colors.END}")

        else:
            print("等待数据...")

        print("-" * 80)
        print(f"\n{Colors.YELLOW}按 Ctrl+C 退出程序{Colors.END}")

    def update_status(self, message):
        """更新状态（可以添加状态栏显示）"""
        print(f"\r{message}", end="", flush=True)

    def show_status(self):
        """显示状态信息"""
        if self.running and len(self.spread_history) > 0:
            last_update = self.spread_history[-1]["time"].strftime("%H:%M:%S")
            print(f"\n{Colors.CYAN}状态: 监控中 | 最后更新: {last_update} | 记录数: {len(self.spread_history)}{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}状态: 等待数据连接...{Colors.END}")

    def stop(self):
        """停止监控"""
        self.running = False
        if self.gateway:
            self.gateway.disconnect()
        print(f"\n{Colors.GREEN}✅ 价差监控已停止{Colors.END}")


def main():
    """主函数"""
    monitor = SpreadMonitorConsole()

    print(f"{Colors.CYAN}欢迎使用焦炭与螺纹钢价差监控程序！{Colors.END}")
    print(f"{Colors.YELLOW}注意: 本程序只进行行情监控，不会执行任何交易操作{Colors.END}")
    print(f"{Colors.YELLOW}按 Enter 开始监控，按 Ctrl+C 退出...{Colors.END}")

    try:
        input()
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
    except EOFError:
        # 处理管道输入结束
        monitor.start()


if __name__ == "__main__":
    main()