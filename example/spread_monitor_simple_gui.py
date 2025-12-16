#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版PyQt界面价差监控程序
适用于远程桌面或命令行环境
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QGroupBox, QStatusBar, QFrame, QTextEdit)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QPalette

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DYLD_FRAMEWORK_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')
os.environ["DYLD_LIBRARY_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')

from ctp_gateway import CtpGateway


class MarketDataThr
from secure_config import load_configead(QThread):
    """行情数据获取线程"""
    data_received = pyqtSignal(dict)  # 行情数据信号
    error_occurred = pyqtSignal(str)  # 错误信号
    connection_status = pyqtSignal(str)  # 连接状态信号

    def __init__(self, config, symbols):
        super().__init__()
        self.config = config
        self.symbols = symbols
        self.gateway = None
        self.running = False

    def run(self):
        """运行行情数据获取"""
        try:
            self.running = True
            self.connection_status.emit("正在初始化CTP网关...")

            # 创建网关
            self.gateway = CtpGateway(self.config)

            # 注册回调
            self.gateway.register_callback('market_data', self.on_market_data)
            self.gateway.register_callback('order', self.on_order)
            self.gateway.register_callback('trade', self.on_trade)

            self.connection_status.emit("正在连接CTP服务器...")

            # 连接服务器
            if not self.gateway.connect():
                self.error_occurred.emit("连接服务器失败")
                return

            # 等待登录
            if not self.gateway.wait_for_login(15):
                self.error_occurred.emit("登录失败")
                return

            # 确认结算单
            self.gateway.confirm_settlement()

            self.connection_status.emit("登录成功！订阅行情...")

            # 订阅行情
            self.gateway.subscribe_market_data(self.symbols)

            self.connection_status.emit("行情订阅成功，开始监控...")

            # 保持运行
            while self.running:
                self.msleep(100)

        except Exception as e:
            self.error_occurred.emit(f"程序异常: {str(e)}")
        finally:
            if self.gateway:
                self.gateway.disconnect()
                self.connection_status.emit("已断开连接")

    def on_market_data(self, data):
        """行情数据回调"""
        symbol = data.get("InstrumentID", "")
        if symbol in self.symbols:
            self.data_received.emit(data)

    def on_order(self, order):
        """订单更新回调"""
        pass  # 过滤掉订单信息

    def on_trade(self, trade):
        """成交回报回调"""
        pass  # 过滤掉成交信息

    def stop(self):
        """停止线程"""
        self.running = False
        if self.gateway:
            self.gateway.disconnect()
        self.wait()


class SimpleSpreadMonitorGUI(QMainWindow):
    """简化版价差监控GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.symbols = ["hc2601", "rb2601"]  # 焦炭和螺纹钢
        self.market_data = {}
        self.spread_history = []
        self.max_history = 200

        # CTP配置
        self.config = load_config()

        self.data_thread = None
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("价差监控 - 简化版")
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 标题
        title = QLabel("焦炭与螺纹钢价差监控")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        main_layout.addWidget(title)

        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # 行情显示区域
        self.create_market_display(main_layout)

        # 价差显示区域
        self.create_spread_display(main_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        # 设置样式
        self.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton#stop {
                background-color: #f44336;
            }
        """)

    def create_market_display(self, layout):
        """创建行情显示"""
        group = QGroupBox("最新行情")
        grid = QGridLayout()

        # 标题行
        grid.addWidget(QLabel("合约"), 0, 0)
        grid.addWidget(QLabel("最新价"), 0, 1)
        grid.addWidget(QLabel("成交量"), 0, 2)
        grid.addWidget(QLabel("涨跌幅"), 0, 3)

        # 焦炭数据
        grid.addWidget(QLabel("焦炭 hc2601:"), 1, 0)
        self.hc_price = QLabel("--")
        self.hc_volume = QLabel("--")
        self.hc_change = QLabel("--")
        grid.addWidget(self.hc_price, 1, 1)
        grid.addWidget(self.hc_volume, 1, 2)
        grid.addWidget(self.hc_change, 1, 3)

        # 螺纹钢数据
        grid.addWidget(QLabel("螺纹钢 rb2601:"), 2, 0)
        self.rb_price = QLabel("--")
        self.rb_volume = QLabel("--")
        self.rb_change = QLabel("--")
        grid.addWidget(self.rb_price, 2, 1)
        grid.addWidget(self.rb_volume, 2, 2)
        grid.addWidget(self.rb_change, 2, 3)

        group.setLayout(grid)
        layout.addWidget(group)

    def create_spread_display(self, layout):
        """创建价差显示"""
        group = QGroupBox("价差分析")
        grid = QGridLayout()

        # 当前价差
        grid.addWidget(QLabel("当前价差:"), 0, 0)
        self.current_spread = QLabel("--")
        self.current_spread.setFont(QFont("Arial", 20, QFont.Bold))
        self.current_spread.setStyleSheet("color: red;")
        grid.addWidget(self.current_spread, 0, 1)
        grid.addWidget(QLabel("(rb2601 - hc2601)"), 0, 2)

        # 统计信息
        grid.addWidget(QLabel("统计信息:"), 1, 0)
        stats_text = QLabel("等待数据...")
        self.stats_label = stats_text
        grid.addWidget(self.stats_label, 1, 1, 1, 2)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        grid.addWidget(line, 2, 0, 1, 3)

        # 历史记录（最后5条）
        grid.addWidget(QLabel("最近价差:"), 3, 0)
        self.history_text = QTextEdit()
        self.history_text.setMaximumHeight(100)
        self.history_text.setReadOnly(True)
        grid.addWidget(self.history_text, 4, 0, 1, 3)

        group.setLayout(grid)
        layout.addWidget(group)

    def start_monitoring(self):
        """开始监控"""
        self.status_bar.showMessage("正在连接...")
        self.data_thread = MarketDataThread(self.config, self.symbols)
        self.data_thread.data_received.connect(self.on_data_received)
        self.data_thread.error_occurred.connect(self.on_error_occurred)
        self.data_thread.connection_status.connect(self.on_status_update)
        self.data_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_monitoring(self):
        """停止监控"""
        if self.data_thread:
            self.data_thread.stop()
            self.data_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("已停止")

    def on_data_received(self, data):
        """处理行情数据"""
        symbol = data.get("InstrumentID", "")
        if symbol in self.symbols:
            self.market_data[symbol] = data

            # 更新行情显示
            self.update_market_display()

            # 如果两个合约都有数据，计算价差
            if len(self.market_data) == 2:
                self.calculate_spread()

    def on_error_occurred(self, error):
        """处理错误"""
        self.status_bar.showMessage(f"错误: {error}")
        self.stop_monitoring()

    def on_status_update(self, status):
        """更新状态"""
        self.status_bar.showMessage(status)

    def update_market_display(self):
        """更新行情显示"""
        # 更新焦炭
        if "hc2601" in self.market_data:
            hc_data = self.market_data["hc2601"]
            price = hc_data.get("LastPrice", 0)
            volume = hc_data.get("Volume", 0)
            open_price = hc_data.get("OpenPrice", price)
            change = ((price - open_price) / open_price * 100) if open_price > 0 else 0

            self.hc_price.setText(f"{price:.2f}")
            self.hc_volume.setText(f"{volume:,}")
            self.hc_change.setText(f"{change:+.2f}%")

        # 更新螺纹钢
        if "rb2601" in self.market_data:
            rb_data = self.market_data["rb2601"]
            price = rb_data.get("LastPrice", 0)
            volume = rb_data.get("Volume", 0)
            open_price = rb_data.get("OpenPrice", price)
            change = ((price - open_price) / open_price * 100) if open_price > 0 else 0

            self.rb_price.setText(f"{price:.2f}")
            self.rb_volume.setText(f"{volume:,}")
            self.rb_change.setText(f"{change:+.2f}%")

    def calculate_spread(self):
        """计算价差"""
        hc_data = self.market_data.get("hc2601", {})
        rb_data = self.market_data.get("rb2601", {})

        hc_price = hc_data.get("LastPrice", 0)
        rb_price = rb_data.get("LastPrice", 0)

        if hc_price > 0 and rb_price > 0:
            spread = rb_price - hc_price
            now = datetime.now().strftime("%H:%M:%S")

            # 保存历史记录
            self.spread_history.append({
                "time": now,
                "spread": spread,
                "hc_price": hc_price,
                "rb_price": rb_price
            })

            # 限制记录数量
            if len(self.spread_history) > self.max_history:
                self.spread_history.pop(0)

            # 更新当前价差
            self.current_spread.setText(f"{spread:+.2f}")
            if spread > 0:
                self.current_spread.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.current_spread.setStyleSheet("color: red; font-weight: bold;")

            # 更新统计信息
            if len(self.spread_history) > 1:
                spreads = [h["spread"] for h in self.spread_history]
                avg = sum(spreads) / len(spreads)
                max_spread = max(spreads)
                min_spread = min(spreads)

                stats_text = f"平均: {avg:+.2f} | 最高: {max_spread:+.2f} | 最低: {min_spread:+.2f} | 区间: {abs(max_spread - min_spread):.2f}"
                self.stats_label.setText(stats_text)

            # 更新历史记录显示
            history_text = ""
            for i, record in enumerate(self.spread_history[-5:]):
                history_text += f"{record['time']} - {record['hc_price']:.2f} | {record['rb_price']:.2f} | 价差: {record['spread']:+.2f}\n"

            self.history_text.setText(history_text)

    def closeEvent(self, event):
        """关闭窗口"""
        if self.data_thread and self.data_thread.isRunning():
            self.stop_monitoring()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle('Fusion')

    window = SimpleSpreadMonitorGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()