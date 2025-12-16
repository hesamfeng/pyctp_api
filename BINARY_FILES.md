# CTP 二进制文件获取说明

## 概述
由于CTP接口文件较大，本仓库不包含二进制文件。请按以下步骤获取。

## SimNow 模拟环境
1. 访问 [SimNow官网](http://www.simnow.com.cn/)
2. 注册并下载 CTP API
3. 将以下文件复制到 `pyctp_api/api/` 目录：

### Windows
- `thostmduserapi_se.dll` - 行情接口
- `thosttraderapi_se.dll` - 交易接口

### Linux
- `libthostmduserapi_se.so` - 行情接口
- `libthosttraderapi_se.so` - 交易接口

### macOS
- `thostmduserapi_se.framework/` - 行情接口
- `thosttraderapi_se.framework/` - 交易接口

## 期货公司实盘
请联系您的期货公司获取对应的CTP接口文件。

## 编译 .so 文件（Linux）
如需自己编译，请参考：
1. 从上期技术获取源码
2. 使用 make 编译生成 .so 文件

## 验证安装
运行测试程序验证接口是否正常：
```bash
python test/test_md.py
python test/test_td.py
```