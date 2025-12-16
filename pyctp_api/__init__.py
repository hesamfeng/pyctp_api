# Pure Python CTP API
# A lightweight Python wrapper for CTP (Comprehensive Transaction Platform)
#
# This package provides direct access to CTP's trading and market data APIs
# without any additional framework dependencies.

from importlib import metadata

# Import CTP APIs
from .api import MdApi, TdApi
from .api.ctp_constant import *

__all__ = ["MdApi", "TdApi"]

try:
    __version__ = metadata.version("pyctp-api")
except metadata.PackageNotFoundError:
    __version__ = "1.0.0"
