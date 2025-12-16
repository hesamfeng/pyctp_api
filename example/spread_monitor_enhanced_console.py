#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版控制台价差监控交易程序
带有清晰的菜单界面和实时更新
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
    BG_BLUE = '\033[44m'


class EnhancedSpreadMonitor:
    """增强版价差监控交易程序"""

    def __init__(self):
        self.symbols = ["hc2601", "rb2601"]
        self.market_data = {}
        self.spread_history = deque(maxlen=100)
        self.positions = {}
        self.orders = {}
        self.running = False
        self.gateway = None
        self.show_menu = False

        # CTP配置
        self.config = load_config()

        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """信号处理器，用于优雅退出"""
        if not self.show_menu:
            print(f"\n{Colors.YELLOW}收到中断信号，显示交易菜单...{Colors.END}")
            self.show_menu = True
        else:
            print(f"\n{Colors.YELLOW}正在停止监控...{Colors.END}")
            self.stop()

    def start(self):
        """开始监控"""
        self.running = True
        self.show_welcome()

        # 启动网关连接
        gateway_thread = Thread(target=self.connect_gateway, daemon=True)
        gateway_thread.start()

        # 启动显示更新线程
        display_thread = Thread(target=self.update_display, daemon=True)
        display_thread.start()

        # 主线程等待
        try:
            while self.running:
                if self.show_menu:
                    self.show_trading_menu()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def show_welcome(self):
        """显示欢迎界面"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print("           增强版焦炭与螺纹钢价差监控交易系统")
        print("=" * 80)
        print(f"  📈 功能特点: 实时行情 | 持仓监控 | 价差分析 | 同步交易")
        print(f"  💡 操作提示: 按 Ctrl+C 显示交易菜单")
        print(f"  ⚠️  风险提示: 实盘交易请谨慎操作，风险自负")
        print("=" * 80)
        print(f"{Colors.END}")

    def connect_gateway(self):
        """连接CTP网关"""
        try:
            self.update_status("正在初始化CTP网关...")
            self.gateway = CtpGateway(self.config)

            # 注册回调
            self.gateway.register_callback('market_data', self.on_market_data)
            self.gateway.register_callback('order', self.on_order)
            self.gateway.register_callback('trade', self.on_trade)
            self.gateway.register_callback('position', self.on_position)
            self.gateway.register_callback('account', self.on_account)

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

            # 查询账户信息
            self.gateway.req_qry_investor_position()
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
        symbol = order.get("InstrumentID", "")
        if symbol in self.symbols:
            order_ref = order.get("OrderRef", "")
            self.orders[order_ref] = {
                "symbol": symbol,
                "direction": order.get("Direction", ""),
                "status": order.get("OrderStatus", ""),
                "price": order.get("LimitPrice", 0),
                "volume": order.get("VolumeTotalOriginal", 0),
                "traded": order.get("VolumeTraded", 0),
                "time": order.get("InsertTime", "")
            }

    def on_trade(self, trade):
        """成交回报回调"""
        print(f"\n{Colors.GREEN}💰 成交回报: {trade.get('InstrumentID', '')} "
              f"{trade.get('Direction', '')} {trade.get('Volume', 0)}手 "
              f"@{trade.get('Price', 0):.2f}{Colors.END}")

    def on_position(self, position):
        """持仓更新回调"""
        symbol = position.get("InstrumentID", "")
        if symbol in self.symbols:
            posi_type = position.get("PosiDirection", "")
            volume = position.get("Position", 0)

            if posi_type == '2':  # 多头
                self.positions[symbol] = {
                    "volume": volume,
                    "avg_price": position.get("PositionCost", 0) / volume / 10 if volume > 0 else 0,
                    "type": "多头"
                }
            elif posi_type == '3':  # 空头
                self.positions[symbol] = {
                    "volume": -volume,
                    "avg_price": position.get("PositionCost", 0) / volume / 10 if volume > 0 else 0,
                    "type": "空头"
                }

    def on_account(self, account):
        """账户信息回调"""
        self.account_info = {
            "balance": account.get("Balance", 0),
            "available": account.get("Available", 0),
            "margin": account.get("CurrMargin", 0),
            "frozen": account.get("FrozenMargin", 0),
            "commission": account.get("Commission", 0),
            "profit": account.get("PositionProfit", 0)
        }

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

    def update_display(self):
        """更新显示"""
        while self.running:
            if not self.show_menu:
                time.sleep(2)
                self.clear_screen()
                self.show_header()
                self.show_market_data()
                self.show_position_info()
                self.show_spread_analysis()
                self.show_trading_suggestions()
                self.show_status()
            else:
                time.sleep(0.5)

    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')

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

    def show_position_info(self):
        """显示持仓信息"""
        print(f"\n{Colors.BOLD}💼 持仓监控{Colors.END}")
        print("-" * 80)

        if hasattr(self, 'account_info'):
            acc = self.account_info
            print(f"账户信息: 总资金 {acc['balance']:.2f} | 可用 {acc['available']:.2f} | "
                  f"保证金 {acc['margin']:.2f} | 浮盈 {acc['profit']:.2f}")
            print("-" * 80)

        for symbol in self.symbols:
            if symbol in self.positions:
                pos = self.positions[symbol]
                symbol_name = "焦炭" if symbol == "hc2601" else "螺纹钢"
                pos_color = Colors.GREEN if pos['volume'] > 0 else Colors.RED if pos['volume'] < 0 else Colors.END
                print(f"{symbol_name}({symbol}): {pos_color}{pos['type']} {abs(pos['volume'])}手 "
                      f"@{pos['avg_price']:.2f}{Colors.END}")
            else:
                symbol_name = "焦炭" if symbol == "hc2601" else "螺纹钢"
                print(f"{symbol_name}({symbol}): 无持仓")

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

        else:
            print("等待数据...")

        print("-" * 80)

    def show_trading_suggestions(self):
        """显示交易建议"""
        print(f"\n{Colors.BOLD}💡 交易建议{Colors.END}")
        print("-" * 80)

        if len(self.spread_history) >= 10:
            spreads = [h["spread"] for h in self.spread_history]
            current_spread = spreads[-1]
            avg_spread = sum(spreads) / len(spreads)
            std_spread = (sum([(s - avg_spread) ** 2 for s in spreads]) / len(spreads)) ** 0.5

            # 基于统计的交易建议
            if current_spread > avg_spread + std_spread:
                suggestion = "价差偏高，考虑: 卖出螺纹钢 + 买入焦炭"
                suggestion_color = Colors.RED
            elif current_spread < avg_spread - std_spread:
                suggestion = "价差偏低，考虑: 买入螺纹钢 + 卖出焦炭"
                suggestion_color = Colors.GREEN
            else:
                suggestion = "价差正常，观望为主"
                suggestion_color = Colors.YELLOW

            print(f"{suggestion_color}{suggestion}{Colors.END}")
            print(f"   当前价差: {current_spread:+.2f} | 均值: {avg_spread:+.2f} | 标准差: {std_spread:.2f}")
        else:
            print("数据不足，请等待更多行情数据...")

        print("-" * 80)

    def show_trading_menu(self):
        """显示交易菜单"""
        self.clear_screen()
        print(f"\n{Colors.BOLD}{Colors.BG_BLUE}")
        print(" " * 25 + "交易菜单" + " " * 25)
        print("=" * 80)
        print(f"{Colors.END}")

        print(f"{Colors.GREEN}1{Colors.END}. 价差交易（同时下两个合约订单）")
        print(f"{Colors.GREEN}2{Colors.END}. 查询持仓")
        print(f"{Colors.GREEN}3{Colors.END}. 查询订单")
        print(f"{Colors.GREEN}4{Colors.END}. 平仓所有持仓")
        print(f"{Colors.GREEN}5{Colors.END}. 返回监控界面")
        print(f"{Colors.RED}6{Colors.END}. 退出程序")

        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("=" * 80)
        print(f"{Colors.END}")

        try:
            choice = input(f"{Colors.YELLOW}请选择操作 (输入数字): {Colors.END}")
            self.handle_menu_choice(choice)
        except (EOFError, KeyboardInterrupt):
            self.show_menu = False

    def handle_menu_choice(self, choice):
        """处理菜单选择"""
        if choice == "1":
            self.execute_spread_trade_menu()
        elif choice == "2":
            self.query_positions()
        elif choice == "3":
            self.query_orders()
        elif choice == "4":
            self.close_all_positions()
        elif choice == "5":
            self.show_menu = False
        elif choice == "6":
            self.stop()
        else:
            print(f"{Colors.RED}无效选择，请重新输入{Colors.END}")
            time.sleep(1)

    def execute_spread_trade_menu(self):
        """执行价差交易菜单"""
        print(f"\n{Colors.BOLD}🔄 价差交易{Colors.END}")
        print("-" * 40)

        try:
            print(f"{Colors.CYAN}选择交易方向:{Colors.END}")
            print("1. 买入螺纹钢 + 卖出焦炭 (看多价差)")
            print("2. 卖出螺纹钢 + 买入焦炭 (看空价差)")
            direction_choice = input("请选择: ")

            if direction_choice not in ["1", "2"]:
                print(f"{Colors.RED}无效选择{Colors.END}")
                return

            volume = int(input("请输入手数: "))
            use_market = input("使用市价单? (y/n): ").lower() == 'y'

            if not use_market:
                hc_price = float(input("焦炭限价: "))
                rb_price = float(input("螺纹钢限价: "))
            else:
                hc_price = rb_price = 0

            direction = "看多价差" if direction_choice == "1" else "看空价差"
            print(f"\n{Colors.YELLOW}确认执行: {direction} {volume}手{Colors.END}")
            confirm = input("确认执行? (y/n): ")

            if confirm.lower() == 'y':
                self.execute_spread_trade(direction_choice, volume, hc_price, rb_price, use_market)
                print(f"{Colors.GREEN}订单已发送{Colors.END}")
            else:
                print(f"{Colors.YELLOW}已取消{Colors.END}")

        except ValueError:
            print(f"{Colors.RED}输入错误{Colors.END}")

        input("按回车键继续...")

    def execute_spread_trade(self, direction, volume, hc_price, rb_price, use_market_price):
        """执行价差交易"""
        try:
            if direction == "1":  # 看多价差
                # 买入螺纹钢
                rb_order_ref = self.gateway.send_order(
                    InstrumentID="rb2601",
                    Direction='0',  # 买
                    OrderPriceType='2' if use_market_price else '2',  # 限价
                    LimitPrice=rb_price if not use_market_price else 0,
                    Volume=volume,
                    TimeCondition='3'  # 当日有效
                )
                # 卖出焦炭
                hc_order_ref = self.gateway.send_order(
                    InstrumentID="hc2601",
                    Direction='1',  # 卖
                    OrderPriceType='2' if use_market_price else '2',
                    LimitPrice=hc_price if not use_market_price else 0,
                    Volume=volume,
                    TimeCondition='3'
                )
            else:  # 看空价差
                # 卖出螺纹钢
                rb_order_ref = self.gateway.send_order(
                    InstrumentID="rb2601",
                    Direction='1',  # 卖
                    OrderPriceType='2' if use_market_price else '2',
                    LimitPrice=rb_price if not use_market_price else 0,
                    Volume=volume,
                    TimeCondition='3'
                )
                # 买入焦炭
                hc_order_ref = self.gateway.send_order(
                    InstrumentID="hc2601",
                    Direction='0',  # 买
                    OrderPriceType='2' if use_market_price else '2',
                    LimitPrice=hc_price if not use_market_price else 0,
                    Volume=volume,
                    TimeCondition='3'
                )

            print(f"{Colors.GREEN}订单已发送: rb2601({rb_order_ref}), hc2601({hc_order_ref}){Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}下单失败: {e}{Colors.END}")

    def query_positions(self):
        """查询持仓"""
        print(f"\n{Colors.BOLD}📊 持仓查询{Colors.END}")
        print("-" * 60)
        self.gateway.req_qry_investor_position()
        time.sleep(2)
        self.show_position_info()
        input("按回车键继续...")

    def query_orders(self):
        """查询订单"""
        print(f"\n{Colors.BOLD}📋 订单查询{Colors.END}")
        print("-" * 60)

        if self.orders:
            for order_ref, order in self.orders.items():
                symbol_name = "焦炭" if order['symbol'] == "hc2601" else "螺纹钢"
                direction_text = "买入" if order['direction'] == '0' else "卖出"
                status_text = self.get_order_status_text(order['status'])

                print(f"{symbol_name} {direction_text} {order['volume']}手 "
                      f"@{order['price']:.2f} | 已成:{order['traded']} | 状态:{status_text}")
        else:
            print("无活动订单")

        input("按回车键继续...")

    def get_order_status_text(self, status):
        """获取订单状态文本"""
        status_map = {
            '0': '全部成交',
            '1': '部分成交',
            '2': '未成交',
            '3': '已撤单',
            '5': '已拒绝'
        }
        return status_map.get(status, '未知')

    def close_all_positions(self):
        """平仓所有持仓"""
        if not any(self.positions.values()):
            print(f"{Colors.YELLOW}当前无持仓{Colors.END}")
            input("按回车键继续...")
            return

        print(f"\n{Colors.BOLD}🔄 平仓所有持仓{Colors.END}")
        print("-" * 40)

        confirm = input(f"{Colors.RED}确认平仓所有持仓? (y/n): {Colors.END}")
        if confirm.lower() != 'y':
            print(f"{Colors.YELLOW}已取消{Colors.END}")
            input("按回车键继续...")
            return

        for symbol, pos in self.positions.items():
            if pos['volume'] != 0:
                # 平仓逻辑
                direction = '1' if pos['volume'] > 0 else '0'  # 多头平仓卖出，空头平仓买入
                self.gateway.send_order(
                    InstrumentID=symbol,
                    Direction=direction,
                    OrderPriceType='2',  # 市价
                    LimitPrice=0,
                    Volume=abs(pos['volume']),
                    TimeCondition='3'
                )

        print(f"{Colors.GREEN}平仓订单已发送{Colors.END}")
        input("按回车键继续...")

    def update_status(self, message):
        """更新状态"""
        print(f"\r{message}", end="", flush=True)

    def show_status(self):
        """显示状态信息"""
        if self.running and len(self.spread_history) > 0:
            last_update = self.spread_history[-1]["time"].strftime("%H:%M:%S")
            print(f"\n{Colors.CYAN}状态: 监控中 | 最后更新: {last_update} | 记录数: {len(self.spread_history)} | "
                  f"按 Ctrl+C 进入交易菜单{Colors.END}")
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
    monitor = EnhancedSpreadMonitor()

    print(f"{Colors.CYAN}欢迎使用增强版焦炭与螺纹钢价差监控交易系统！{Colors.END}")
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