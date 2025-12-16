#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全配置加载模块
自动加载配置信息，如不存在则提供默认值
"""

import os
import sys

def get_default_config():
    """获取默认配置（使用SimNow测试环境）"""
    return {
        "用户名": os.getenv("CTP_USERNAME", "your_simnow_username"),
        "密码": os.getenv("CTP_PASSWORD", "your_simnow_password"),
        "经纪商代码": "9999",
        "交易服务器": "tcp://182.254.243.31:30001",
        "行情服务器": "tcp://182.254.243.31:30011",
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000",
        "产品信息": ""
    }

def load_config():
    """加载配置信息"""
    try:
        # 尝试导入本地配置文件
        if os.path.exists("config.py"):
            import config
            if hasattr(config, 'get_config'):
                return config.get_config()
            elif hasattr(config, 'SIMNOW_CONFIG'):
                return config.SIMNOW_CONFIG

        # 如果配置文件不存在，使用默认配置
        return get_default_config()

    except ImportError:
        # 如果导入失败，使用默认配置
        print("⚠️  警告: 未找到 config.py，使用默认配置")
        print("请复制 config.py.template 为 config.py 并填入您的账户信息")
        return get_default_config()