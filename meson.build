project(
  'pyctp_api',
  'cpp',
  version: '1.0.0',
  license: 'MIT',
  meson_version: '>=1.7.0',
  default_options: [
    'buildtype=release',
    'cpp_std=c++17',
    'warning_level=2',
  ],
)

# 导入文件系统和Python模块
fs = import('fs')
py = import('python').find_installation(pure: false)
py_dep = py.dependency()

# 获取pybind11路径
python_cmd = host_machine.system() == 'windows' ? 'python' : 'python3'
pybind11_include_dir = run_command(python_cmd, '-c', 'import pybind11; print(pybind11.get_include())', check: true).stdout().strip()
message('使用pybind11路径: ' + pybind11_include_dir)

# 获取编译器信息
cpp = meson.get_compiler('cpp')
compiler_id = cpp.get_id()

# 输出构建目标系统信息
message('构建目标系统: ' + host_machine.system())

# Windows配置
if host_machine.system() == 'windows'
  message('配置Windows环境...')
  
  # Windows库文件夹路径
  lib_dir = meson.current_source_dir() / 'pyctp_api/api/libs'
  api_dir = meson.current_source_dir() / 'pyctp_api/api'
  
  # 包含路径
  incdir = include_directories(
    'pyctp_api/api/include',
    'pyctp_api/api/vnctp',
  )
  
  # Windows链接库
  if cpp.sizeof('void*') == 8  # 64位
    link_args = [
      lib_dir / 'thosttraderapi_se.lib',
      lib_dir / 'thostmduserapi_se.lib'
    ]
  else  # 32位
    error('暂不支持32位Windows')
  endif
  
  # Windows编译参数
  cpp_args = [
    '-I' + pybind11_include_dir,
    '/DWIN32',
    '/D_WINDOWS',
    '/EHsc',
    '/bigobj'
  ]
  
  link_args += []

# Mac配置
elif host_machine.system() == 'darwin'
  message('配置Mac环境...')
  
  # Mac库文件夹路径
  lib_dir = meson.current_source_dir() / 'pyctp_api/api/libs'
  api_dir = meson.current_source_dir() / 'pyctp_api/api'
  
  # 包含路径
  incdir = include_directories(
    'pyctp_api/api/include/mac',
    'pyctp_api/api/vnctp',
  )
  
  # Mac链接参数
  link_args = [
    '-F', meson.current_source_dir() / 'pyctp_api/api',
    '-framework', 'thostmduserapi_se',
    '-rpath', '@loader_path/../../pyctp_api/api'
  ]
  
  link_args_td = [
    '-F', meson.current_source_dir() / 'pyctp_api/api',
    '-framework', 'thosttraderapi_se',
    '-rpath', '@loader_path/../../pyctp_api/api'
  ]
  
  # Mac编译参数
  cpp_args = [
    '-I' + pybind11_include_dir,
    '-std=c++17',
    '-fvisibility=hidden'
  ]

# Linux配置
else
  message('配置Linux环境...')
  
  # 检查架构
  target_arch = host_machine.cpu_family()
  message('目标架构: ' + target_arch)
  
  if target_arch != 'x86_64'
    error('仅支持x86_64架构')
  endif
  
  # Linux库文件夹路径
  lib_dir = meson.current_source_dir() / 'pyctp_api/api'
  
  # 包含路径
  incdir = include_directories(
    'pyctp_api/api/include',
    'pyctp_api/api/vnctp',
  )
  
  # Linux链接库
  link_args = [
    '-Wl,-rpath,${ORIGIN}',
    lib_dir / 'libthostmduserapi_se.so',
    lib_dir / 'libthosttraderapi_se.so',
  ]
  
  # Linux编译参数
  cpp_args = [
    '-I' + pybind11_include_dir,
    '-fvisibility=hidden'
  ]
endif

# 构建MD API模块
vnctpmd = py.extension_module(
  'vnctpmd',
  sources: ['pyctp_api/api/vnctp/vnctpmd/vnctpmd.cpp'],
  include_directories: incdir,
  dependencies: py_dep,
  cpp_args: cpp_args,
  link_args: host_machine.system() == 'darwin' ? link_args : link_args,
  subdir: 'pyctp_api/api'
)

# 构建TD API模块
vnctptd = py.extension_module(
  'vnctptd',
  sources: ['pyctp_api/api/vnctp/vnctptd/vnctptd.cpp'],
  include_directories: incdir,
  dependencies: py_dep,
  cpp_args: cpp_args,
  link_args: host_machine.system() == 'darwin' ? link_args_td : link_args,
  subdir: 'pyctp_api/api'
)

# 安装Python文件
python_files = [
  ['pyctp_api/__init__.py', 'pyctp_api'],
  ['pyctp_api/api/__init__.py', 'pyctp_api/api'],
  ['pyctp_api/api/ctp_constant.py', 'pyctp_api/api'],
]

foreach file : python_files
  py.install_sources(
    file[0],
    pure: false,
    subdir: file[1]
  )
endforeach

# 安装API动态库文件
if host_machine.system() == 'windows'
  api_libs = [
    'pyctp_api/api/thostmduserapi_se.dll',
    'pyctp_api/api/thosttraderapi_se.dll',
  ]
  
  install_data(
    api_libs,
    install_dir: py.get_install_dir() / 'pyctp_api/api'
  )
elif host_machine.system() == 'darwin'
  # 安装Mac Framework文件夹
  install_subdir(
    'pyctp_api/api/thostmduserapi_se.framework',
    install_dir: py.get_install_dir() / 'pyctp_api/api'
  )
  
  install_subdir(
    'pyctp_api/api/thosttraderapi_se.framework',
    install_dir: py.get_install_dir() / 'pyctp_api/api'
  )
else  # Linux
  api_libs = [
    'pyctp_api/api/libthostmduserapi_se.so',
    'pyctp_api/api/libthosttraderapi_se.so',
  ]
  
  install_data(
    api_libs,
    install_dir: py.get_install_dir() / 'pyctp_api/api'
  )
endif