#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版焦炭与螺纹钢价差监控程序
包含持仓监控和交易功能（同步下两个合约订单）
"""

import sys
import os
import time
import signal
from datetime import datetime
from threading import Thread, Lock
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


class TradingSpreadMonitor:
    """带交易功能的价差监控"""

    def __init__(self):
        self.symbols = ["hc2601", "rb2601"]
        self.market_data = {}
        self.spread_history = deque(maxlen=100)
        self.positions = {}  # 持仓信息
        self.orders = {}     # 订单信息
        self.running = False
        self.gateway = None
        self.lock = Lock()  # 线程锁

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

        # 启动用户输入处理
        input_thread = Thread(target=self.handle_user_input, daemon=True)
        input_thread.start()

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
            self.gateway.register_callback('order_update', self.on_order_update)
            self.gateway.register_callback('trade_update', self.on_trade_update)
            self.gateway.register_callback('position_update', self.on_position_update)
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

            # 查询持仓
            time.sleep(2)
            self.query_positions()

            # 订阅行情
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
            with self.lock:
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

    def on_order_update(self, data):
        """订单更新回调"""
        order_ref = data.get('OrderRef', '')
        instrument = data.get('InstrumentID', '')
        if instrument in self.symbols:
            with self.lock:
                self.orders[order_ref] = data

    def on_trade_update(self, data):
        """成交更新回调"""
        instrument = data.get('InstrumentID', '')
        if instrument in self.symbols:
            # 成交后查询持仓
            time.sleep(1)
            self.query_positions()

    def on_position_update(self, data):
        """持仓更新回调"""
        instrument = data.get('InstrumentID', '')
        if instrument in self.symbols:
            with self.lock:
                self.positions[instrument] = data

    def on_order(self, order):
        """订单回调"""
        pass

    def on_trade(self, trade):
        """成交回调"""
        pass

    def query_positions(self):
        """查询持仓"""
        if self.gateway and self.gateway.td_logged_in:
            self.gateway.query_positions()

    def calculate_spread(self):
        """计算价差"""
        with self.lock:
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

    def handle_user_input(self):
        """处理用户输入"""
        while self.running:
            try:
                self.show_trading_menu()
                choice = input(f"\n{Colors.YELLOW}请选择操作 (输入数字): {Colors.END}").strip()

                if choice == "1":
                    self.spread_trading()
                elif choice == "2":
                    self.query_positions()
                elif choice == "3":
                    self.query_orders()
                elif choice == "4":
                    self.close_all_positions()
                elif choice == "5":
                    print(f"\n{Colors.GREEN}程序将退出...{Colors.END}")
                    self.stop()
                else:
                    print(f"{Colors.RED}无效选择，请重新输入！{Colors.END}")

                time.sleep(2)

            except (EOFError, KeyboardInterrupt):
                break

    def show_trading_menu(self):
        """显示交易菜单"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}========== 交易菜单 =========={Colors.END}")
        print(f"{Colors.GREEN}1{Colors.END}. 价差交易（同时下两个合约订单）")
        print(f"{Colors.GREEN}2{Colors.END}. 查询持仓")
        print(f"{Colors.GREEN}3{Colors.END}. 查询订单")
        print(f"{Colors.GREEN}4{Colors.END}. 平仓所有持仓")
        print(f"{Colors.RED}5{Colors.END}. 退出程序")
        print(f"{Colors.BOLD}{Colors.CYAN}================================{Colors.END}")

    def spread_trading(self):
        """价差交易"""
        print(f"\n{Colors.BOLD}价差交易操作{Colors.END}")
        print("-" * 50)

        try:
            print(f"\n{Colors.YELLOW}选择交易方向:{Colors.END}")
            print(f"{Colors.GREEN}1{Colors.END}. 买入价差（买rb2601，卖hc2601）")
            print(f"{Colors.RED}2{Colors.END}. 卖出价差（卖rb2601，买hc2601）")
            direction = input("请选择 (1-2): ").strip()

            if direction not in ["1", "2"]:
                print(f"{Colors.RED}无效选择！{Colors.END}")
                return

            volume = int(input("请输入手数: ").strip())
            if volume <= 0:
                print(f"{Colors.RED}无效手数！{Colors.END}")
                return

            price_mode = input("价格模式 (1-限价 2-市价): ").strip()
            use_market_price = price_mode == "2"

            if not use_market_price:
                hc_price = float(input(f"焦炭(hc2601)委托价格: ").strip())
                rb_price = float(input(f"螺纹钢(rb2601)委托价格: ").strip())
            else:
                # 使用最新价
                with self.lock:
                    hc_price = self.market_data.get("hc2601", {}).get("LastPrice", 0)
                    rb_price = self.market_data.get("rb2601", {}).get("LastPrice", 0)

            if hc_price <= 0 or rb_price <= 0:
                print(f"{Colors.RED}无效价格或价格未更新！{Colors.END}")
                return

            # 执行交易
            self.execute_spread_trade(direction, volume, hc_price, rb_price, use_market_price)

        except ValueError:
            print(f"{Colors.RED}输入格式错误！{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}交易失败: {e}{Colors.END}")

    def execute_spread_trade(self, direction, volume, hc_price, rb_price, use_market_price):
        """执行价差交易"""
        print(f"\n{Colors.YELLOW}正在执行价差交易...{Colors.END}")

        # 确定交易方向
        if direction == "1":  # 买入价差
            hc_direction = "SELL"  # 卖焦炭
            rb_direction = "BUY"   # 买螺纹钢
            offset = "OPEN"
            print(f"交易方向: 买入价差（买螺纹钢，卖焦炭）")
        else:  # 卖出价差
            hc_direction = "BUY"   # 买焦炭
            rb_direction = "SELL"  # 卖螺纹钢
            offset = "OPEN"
            print(f"交易方向: 卖出价差（卖螺纹钢，买焦炭）")

        print(f"手数: {volume}")
        print(f"焦炭价格: {hc_price:.2f} | 螺纹钢价格: {rb_price:.2f}")

        # 下第一个订单
        hc_order_ref = self.gateway.send_order(
            symbol="hc2601",
            exchange="SHFE",
            direction=hc_direction,
            offset=offset,
            price=hc_price if not use_market_price else 0,
            volume=volume,
            order_type="MARKET" if use_market_price else "LIMIT"
        )

        if not hc_order_ref:
            print(f"{Colors.RED}❌ 焦炭订单发送失败！{Colors.END}")
            return

        time.sleep(0.5)  # 稍微等待

        # 下第二个订单
        rb_order_ref = self.gateway.send_order(
            symbol="rb2601",
            exchange="SHFE",
            direction=rb_direction,
            offset=offset,
            price=rb_price if not use_market_price else 0,
            volume=volume,
            order_type="MARKET" if use_market_price else "LIMIT"
        )

        if not rb_order_ref:
            print(f"{Colors.RED}❌ 螺纹钢订单发送失败！{Colors.END}")
            # 尝试撤销第一个订单
            self.gateway.cancel_order("hc2601", "SHFE", hc_order_ref)
            return

        print(f"{Colors.GREEN}✅ 价差交易订单已发送！{Colors.END}")
        print(f"   焦炭订单号: {hc_order_ref}")
        print(f"   螺纹钢订单号: {rb_order_ref}")

    def close_all_positions(self):
        """平仓所有持仓"""
        print(f"\n{Colors.YELLOW}正在查询持仓...{Colors.END}")
        self.query_positions()

        time.sleep(2)  # 等待持仓数据更新

        with self.lock:
            if not self.positions:
                print(f"{Colors.GREEN}当前无持仓{Colors.END}")
                return

            print(f"{Colors.CYAN}当前持仓情况:{Colors.END}")
            for instrument, pos in self.positions.items():
                if instrument in self.symbols:
                    position = pos.get("Position", 0)
                    if position != 0:
                        direction = "SELL" if position > 0 else "BUY"
                        print(f"  {instrument}: {position} 手")

            # 执行平仓
            for instrument, pos in self.positions.items():
                if instrument in self.symbols:
                    position = pos.get("Position", 0)
                    if position != 0:
                        volume = abs(position)
                        direction = "SELL" if position > 0 else "BUY"

                        print(f"\n正在平仓 {instrument} {volume} 手...")
                        order_ref = self.gateway.send_order(
                            symbol=instrument,
                            exchange="SHFE",
                            direction=direction,
                            offset="CLOSE",
                            price=0,
                            volume=volume,
                            order_type="MARKET"
                        )

                        if order_ref:
                            print(f"{Colors.GREEN}✅ 平仓订单已发送: {order_ref}{Colors.END}")
                        else:
                            print(f"{Colors.RED}❌ 平仓订单发送失败！{Colors.END}")

    def show_header(self):
        """显示标题"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print("            增强版焦炭(hc2601)与螺纹钢(rb2601)价差监控")
        print("=" * 80)
        print(f" 监控合约: hc2601 (焦炭) | rb2601 (螺纹钢)")
        print(f" 计算公式: 价差 = 螺纹钢价格 - 焦炭价格")
        print(f" 支持功能: 持仓监控 | 价差交易 | 同步下单")
        print(f" 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"{Colors.END}")

    def update_display(self):
        """更新显示"""
        while self.running:
            time.sleep(1)
            self.clear_screen()
            self.show_header()
            self.show_positions()
            self.show_market_data()
            self.show_spread_analysis()
            self.show_status()

    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def show_positions(self):
        """显示持仓信息"""
        print(f"\n{Colors.BOLD}💼 持仓监控{Colors.END}")
        print("-" * 80)
        print(f"{'合约':<12} {'持仓手数':<10} {'可用手数':<10} {'持仓成本':<12} {'当前盈亏':<12}")
        print("-" * 80)

        with self.lock:
            for symbol in self.symbols:
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    position = pos.get("Position", 0)
                    available = pos.get("Available", 0)
                    avg_price = pos.get("PositionCost", 0)

                    # 计算盈亏
                    if position != 0 and symbol in self.market_data:
                        current_price = self.market_data[symbol].get("LastPrice", avg_price)
                        pnl = (current_price - avg_price) * position
                        pnl_color = Colors.GREEN if pnl > 0 else Colors.RED if pnl < 0 else Colors.END
                        pnl_text = f"{pnl:+,.2f}"
                    else:
                        pnl_color = Colors.END
                        pnl_text = "--"

                    print(f"{symbol.upper():<12} {position:<10} {available:<10} {avg_price:<12.2f} {pnl_color}{pnl_text:<12}{Colors.END}")
                else:
                    print(f"{symbol.upper():<12} {'0':<10} {'0':<10} {'--':<12} {'--':<12}")

        print("-" * 80)

    def show_market_data(self):
        """显示行情数据"""
        print(f"\n{Colors.BOLD}📊 最新行情数据{Colors.END}")
        print("-" * 80)
        print(f"{'合约':<12} {'最新价':<10} {'成交量':<10} {'涨跌幅':<10} {'最高':<10} {'最低':<10}")
        print("-" * 80)

        with self.lock:
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
                print(f"{'焦炭 HC2601':<12} {price:<10.2f} {volume:<10,} {change_color}{change:+.2f}%{Colors.END:<8} {high:<10.2f} {low:<10.2f}")
            else:
                print(f"{'焦炭 HC2601':<12} {'--':<10} {'--':<10} {'--':<10} {'--':<10} {'--':<10}")

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
                print(f"{'螺纹钢 RB2601':<12} {price:<10.2f} {volume:<10,} {change_color}{change:+.2f}%{Colors.END:<8} {high:<10.2f} {low:<10.2f}")
            else:
                print(f"{'螺纹钢 RB2601':<12} {'--':<10} {'--':<10} {'--':<10} {'--':<10} {'--':<10}")

        print("-" * 80)

    def show_spread_analysis(self):
        """显示价差分析"""
        print(f"\n{Colors.BOLD}💰 价差分析{Colors.END}")
        print("-" * 80)

        with self.lock:
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

                        # 交易建议
                        if spread < avg_spread - 5:
                            suggestion = "建议: 考虑买入价差（当前价差较低）"
                            suggestion_color = Colors.GREEN
                        elif spread > avg_spread + 5:
                            suggestion = "建议: 考虑卖出价差（当前价差较高）"
                            suggestion_color = Colors.RED
                        else:
                            suggestion = "建议: 观望（价差处于正常范围）"
                            suggestion_color = Colors.YELLOW

                        print(f"   {suggestion_color}{suggestion}{Colors.END}")

            else:
                print("等待数据...")

        print("-" * 80)
        print(f"\n{Colors.YELLOW}按 Ctrl+C 显示交易菜单{Colors.END}")

    def update_status(self, message):
        """更新状态"""
        print(f"\r{message}", end="", flush=True)

    def show_status(self):
        """显示状态信息"""
        if self.running:
            with self.lock:
                position_count = len([s for s in self.symbols if s in self.positions])
                order_count = len(self.orders)
                spread_count = len(self.spread_history)

                if spread_count > 0:
                    last_update = self.spread_history[-1]["time"].strftime("%H:%M:%S")
                    print(f"\n{Colors.CYAN}状态: 监控中 | 最后更新: {last_update} | "
                          f"持仓: {position_count} | 订单: {order_count} | 记录: {spread_count}{Colors.END}")
                else:
                    print(f"\n{Colors.YELLOW}状态: 等待数据连接...{Colors.END}")

    def query_orders(self):
        """查询订单"""
        print(f"\n{Colors.YELLOW}当前活跃订单:{Colors.END}")
        print("-" * 50)

        with self.lock:
            if not self.orders:
                print("无活跃订单")
            else:
                for order_ref, order in self.orders.items():
                    symbol = order.get("InstrumentID", "")
                    direction = order.get("Direction", "")
                    status = order.get("OrderStatus", "")
                    price = order.get("LimitPrice", 0)
                    volume = order.get("VolumeTotalOriginal", 0)

                    direction_text = "买" if direction == "0" else "卖"
                    print(f"{symbol}: {direction_text} {volume}手 @ {price:.2f} - 状态: {status}")

    def stop(self):
        """停止监控"""
        self.running = False
        if self.gateway:
            self.gateway.disconnect()
        print(f"\n{Colors.GREEN}✅ 价差监控已停止{Colors.END}")


def main():
    """主函数"""
    monitor = TradingSpreadMonitor()

    print(f"{Colors.CYAN}欢迎使用增强版焦炭与螺纹钢价差监控程序！{Colors.END}")
    print(f"{Colors.GREEN}功能: 行情监控 | 持仓管理 | 价差交易{Colors.END}")
    print(f"{Colors.YELLOW}注意: 实盘交易请谨慎操作，风险自负{Colors.END}")
    print(f"{Colors.YELLOW}按 Enter 开始监控，按 Ctrl+C 显示交易菜单...{Colors.END}")

    try:
        input()
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
    except EOFError:
        monitor.start()


if __name__ == "__main__":
    main()