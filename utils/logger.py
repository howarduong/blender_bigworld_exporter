# File: core/logger.py
# Purpose: 提供统一的日志接口，支持控制台输出与文件输出，并可与 AuditLogger 对接。
# 模块简介：
# - Logger: 统一日志类，支持 info/warning/error
# - 可选绑定 AuditLogger，将日志写入 audit.log
# - 用途: 导出过程中的调试、错误追踪、CI 校验

import sys
import time
from typing import Optional, TYPE_CHECKING

# 避免循环导入
if TYPE_CHECKING:
    from writers.audit_writer import AuditLogger


class Logger:
    """
    Logger
    ------
    提供统一的日志接口。
    - 支持级别: INFO / WARNING / ERROR
    - 输出到控制台 (stdout/stderr)
    - 可选绑定 AuditLogger，将日志写入 audit.log
    """

    def __init__(self, audit_logger: Optional["AuditLogger"] = None, verbose: bool = True):
        self.audit_logger = audit_logger
        self.verbose = verbose

    def _log(self, level: str, message: str, context: Optional[str] = None) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] [{level}] {message}"
        if context:
            line += f" | Context: {context}"

        # 控制台输出
        if self.verbose:
            if level == "ERROR":
                print(line, file=sys.stderr)
            else:
                print(line, file=sys.stdout)

        # 写入 audit.log
        if self.audit_logger:
            if level == "INFO":
                self.audit_logger.info(message, context)
            elif level == "WARNING":
                self.audit_logger.warning(message, context)
            elif level == "ERROR":
                self.audit_logger.error(message, context)

    def info(self, message: str, context: Optional[str] = None) -> None:
        """记录 INFO 日志"""
        self._log("INFO", message, context)

    def warning(self, message: str, context: Optional[str] = None) -> None:
        """记录 WARNING 日志"""
        self._log("WARNING", message, context)

    def error(self, message: str, context: Optional[str] = None) -> None:
        """记录 ERROR 日志"""
        self._log("ERROR", message, context)
