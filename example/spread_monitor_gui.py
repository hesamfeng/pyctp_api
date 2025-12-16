#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt界面版焦炭与螺纹钢价差监控程序
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QGridLayout, QGroupBox, QStatusBar, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QPalette
import pyqtgraph as pg
import numpy as np

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DYLD_FRAMEWORK_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')
os.environ["DYLD_LIBRARY_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyctp_api', 'api')

from ctp_gateway import CtpGateway


class MarketDataThrea
from secure_config import load_configd(QThread):
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


class SpreadMonitorGUI(QMainWindow):
    """价差监控GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.symbols = ["hc2601", "rb2601"]  # 焦炭和螺纹钢
        self.market_data = {}
        self.spread_history = []
        self.max_history = 200  # 最多保存200条记录

        # CTP配置
        self.config = load_config()

        # 市场数据线程
        self.data_thread = None

        # 初始化界面
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("焦炭与螺纹钢价差监控 - PyQt版")
        self.setGeometry(100, 100, 1200, 800)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 创建主布局
        main_layout = QVBoxLayout(main_widget)

        # 创建标题
        title_label = QLabel("焦炭(hc2601)与螺纹钢(rb2601)价差实时监控")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)

        # 创建控制按钮
        self.create_control_buttons(main_layout)

        # 创建行情显示区域
        self.create_market_display(main_layout)

        # 创建价差显示区域
        self.create_spread_display(main_layout)

        # 创建图表区域
        self.create_chart_area(main_layout)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        # 设置样式
        self.set_styles()

    def create_control_buttons(self, layout):
        """创建控制按钮"""
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("开始监控")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")

        self.stop_button = QPushButton("停止监控")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")

        self.clear_button = QPushButton("清除数据")
        self.clear_button.clicked.connect(self.clear_data)
        self.clear_button.setStyleSheet("QPushButton { background-color: #ff9800; color: white; font-weight: bold; }")

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def create_market_display(self, layout):
        """创建行情显示区域"""
        market_group = QGroupBox("最新行情")
        market_layout = QGridLayout()

        # 创建表格
        self.market_table = QTableWidget()
        self.market_table.setRowCount(2)
        self.market_table.setColumnCount(6)
        self.market_table.setHorizontalHeaderLabels(["合约", "最新价", "成交量", "涨跌幅", "最高价", "最低价"])

        # 设置表格样式
        header = self.market_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.market_table.setFont(QFont("Arial", 10))

        # 设置行标签
        self.market_table.setVerticalHeaderLabels(["焦炭 hc2601", "螺纹钢 rb2601"])

        market_layout.addWidget(self.market_table)
        market_group.setLayout(market_layout)
        layout.addWidget(market_group)

    def create_spread_display(self, layout):
        """创建价差显示区域"""
        spread_group = QGroupBox("价差分析")
        spread_layout = QVBoxLayout()

        # 当前价差显示
        current_spread_layout = QHBoxLayout()
        current_spread_layout.addWidget(QLabel("当前价差:"))

        self.spread_label = QLabel("--")
        self.spread_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.spread_label.setStyleSheet("color: red;")
        current_spread_layout.addWidget(self.spread_label)

        current_spread_layout.addWidget(QLabel("(rb2601 - hc2601)"))
        current_spread_layout.addStretch()

        spread_layout.addLayout(current_spread_layout)

        # 价差统计
        stats_layout = QGridLayout()

        # 创建统计标签
        self.avg_spread_label = QLabel("--")
        self.max_spread_label = QLabel("--")
        self.min_spread_label = QLabel("--")
        self.spread_range_label = QLabel("--")
        self.trend_label = QLabel("--")

        stats_layout.addWidget(QLabel("平均价差:"), 0, 0)
        stats_layout.addWidget(self.avg_spread_label, 0, 1)
        stats_layout.addWidget(QLabel("最高价差:"), 0, 2)
        stats_layout.addWidget(self.max_spread_label, 0, 3)

        stats_layout.addWidget(QLabel("最低价差:"), 1, 0)
        stats_layout.addWidget(self.min_spread_label, 1, 1)
        stats_layout.addWidget(QLabel("价差区间:"), 1, 2)
        stats_layout.addWidget(self.spread_range_label, 1, 3)

        stats_layout.addWidget(QLabel("短期趋势:"), 2, 0)
        stats_layout.addWidget(self.trend_label, 2, 1)

        spread_layout.addLayout(stats_layout)
        spread_group.setLayout(spread_layout)
        layout.addWidget(spread_group)

    def create_chart_area(self, layout):
        """创建图表区域"""
        chart_group = QGroupBox("价差走势图")
        chart_layout = QVBoxLayout()

        # 创建图表
        self.spread_plot = pg.PlotWidget(title="价差变化趋势")
        self.spread_plot.setLabel('left', '价差', units='元')
        self.spread_plot.setLabel('bottom', '时间')
        self.spread_plot.showGrid(x=True, y=True)
        self.spread_plot.setBackground('w')

        # 创建数据系列
        self.spread_curve = self.spread_plot.plot(pen=pg.mkPen(color='b', width=2))

        chart_layout.addWidget(self.spread_plot)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

    def set_styles(self):
        """设置界面样式"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                font-size: 12px;
            }
            QTableWidget {
                gridline-color: #cccccc;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)

    def start_monitoring(self):
        """开始监控"""
        if self.data_thread and self.data_thread.isRunning():
            return

        # 创建并启动数据线程
        self.data_thread = MarketDataThread(self.config, self.symbols)
        self.data_thread.data_received.connect(self.on_data_received)
        self.data_thread.error_occurred.connect(self.on_error_occurred)
        self.data_thread.connection_status.connect(self.on_status_update)
        self.data_thread.start()

        # 更新按钮状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_bar.showMessage("正在连接服务器...")

    def stop_monitoring(self):
        """停止监控"""
        if self.data_thread:
            self.data_thread.stop()
            self.data_thread = None

        # 更新按钮状态
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("监控已停止")

    def clear_data(self):
        """清除数据"""
        self.market_data = {}
        self.spread_history = []

        # 清空表格
        for row in range(self.market_table.rowCount()):
            for col in range(self.market_table.columnCount()):
                self.market_table.setItem(row, col, QTableWidgetItem("--"))

        # 重置标签
        self.spread_label.setText("--")
        self.avg_spread_label.setText("--")
        self.max_spread_label.setText("--")
        self.min_spread_label.setText("--")
        self.spread_range_label.setText("--")
        self.trend_label.setText("--")

        # 清空图表
        self.spread_curve.setData([], [])

        self.status_bar.showMessage("数据已清除")

    def on_data_received(self, data):
        """处理接收到的行情数据"""
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

            # 更新行情表格
            self.update_market_table()

    def on_error_occurred(self, error_msg):
        """处理错误"""
        self.status_bar.showMessage(f"错误: {error_msg}")
        self.stop_monitoring()

    def on_status_update(self, status):
        """更新状态"""
        self.status_bar.showMessage(status)

    def update_market_table(self):
        """更新行情表格"""
        row_mapping = {"hc2601": 0, "rb2601": 1}

        for symbol, data in self.market_data.items():
            row = row_mapping.get(symbol, -1)
            if row >= 0:
                price = data.get("LastPrice", 0)
                volume = data.get("Volume", 0)
                open_price = data.get("OpenPrice", price)
                high = data.get("HighestPrice", 0)
                low = data.get("LowestPrice", 0)

                # 计算涨跌幅
                change = ((price - open_price) / open_price * 100) if open_price > 0 else 0

                # 更新表格
                self.market_table.setItem(row, 0, QTableWidgetItem(symbol.upper()))
                self.market_table.setItem(row, 1, QTableWidgetItem(f"{price:.2f}"))
                self.market_table.setItem(row, 2, QTableWidgetItem(f"{volume:,}"))
                self.market_table.setItem(row, 3, QTableWidgetItem(f"{change:+.2f}%"))
                self.market_table.setItem(row, 4, QTableWidgetItem(f"{high:.2f}"))
                self.market_table.setItem(row, 5, QTableWidgetItem(f"{low:.2f}"))

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
            now = datetime.now().strftime("%H:%M:%S")

            # 保存历史记录
            self.spread_history.append({
                "time": now,
                "spread": spread,
                "hc_price": hc_price,
                "rb_price": rb_price
            })

            # 限制历史记录数量
            if len(self.spread_history) > self.max_history:
                self.spread_history.pop(0)

            # 更新价差显示
            self.update_spread_display(spread)

    def update_spread_display(self, current_spread):
        """更新价差显示"""
        # 更新当前价差
        self.spread_label.setText(f"{current_spread:+.2f}")

        # 根据价差正负设置颜色
        if current_spread > 0:
            self.spread_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.spread_label.setStyleSheet("color: red; font-weight: bold;")

        # 计算统计信息
        if len(self.spread_history) > 1:
            spreads = [h["spread"] for h in self.spread_history]
            avg_spread = sum(spreads) / len(spreads)
            max_spread = max(spreads)
            min_spread = min(spreads)

            # 更新统计显示
            self.avg_spread_label.setText(f"{avg_spread:+.2f}")
            self.max_spread_label.setText(f"{max_spread:+.2f}")
            self.min_spread_label.setText(f"{min_spread:+.2f}")
            self.spread_range_label.setText(f"{abs(max_spread - min_spread):.2f}")

            # 计算趋势
            if len(spreads) >= 5:
                recent_avg = sum(spreads[-5:]) / 5
                if current_spread > recent_avg + 1:
                    trend = "↗️ 扩大"
                    color = "green"
                elif current_spread < recent_avg - 1:
                    trend = "↘️ 收缩"
                    color = "red"
                else:
                    trend = "→ 持平"
                    color = "blue"

                self.trend_label.setText(trend)
                self.trend_label.setStyleSheet(f"color: {color}; font-weight: bold;")

            # 更新图表
            self.update_chart()

    def update_chart(self):
        """更新图表"""
        if len(self.spread_history) > 0:
            times = list(range(len(self.spread_history)))
            spreads = [h["spread"] for h in self.spread_history]
            self.spread_curve.setData(times, spreads)

    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.data_thread and self.data_thread.isRunning():
            self.stop_monitoring()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle('Fusion')

    # 创建并显示主窗口
    window = SpreadMonitorGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()