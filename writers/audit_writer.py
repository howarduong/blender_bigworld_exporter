# File: writers/audit_writer.py
# Purpose: 生成 audit.log，记录导出过程中的所有操作、错误、警告
# Notes:
# - 错误码体系：GEO001（几何）、UV001（UV）、MAT001（材质）、ANM001（动画）等
# - 严重性：ERROR / WARNING / INFO
# - 格式：时间戳 | 严重性 | 错误码 | 消息 | 对象名

import time
from typing import List, Optional
from ..core.schema import AuditEntry


class AuditLogger:
    """
    AuditLogger
    -----------
    用于生成 audit.log 文件，记录导出过程的所有操作、错误、警告。
    
    使用方式:
        logger = AuditLogger("output/audit.log")
        logger.info("开始导出", "MyObject")
        logger.error("GEO001", "发现非流形几何", "MyMesh")
        logger.warning("UV001", "UV 越界", "MyMesh")
        logger.save()
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.entries: List[AuditEntry] = []
    
    def _add_entry(self, severity: str, message: str, 
                   code: str = "", object_name: Optional[str] = None) -> None:
        """内部方法：添加日志条目"""
        entry = AuditEntry(
            code=code,
            message=message,
            severity=severity,
            object_name=object_name,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
        self.entries.append(entry)
    
    def info(self, message: str, object_name: Optional[str] = None) -> None:
        """记录 INFO 级别日志"""
        self._add_entry("INFO", message, "", object_name)
    
    def warning(self, code: str, message: str, object_name: Optional[str] = None) -> None:
        """记录 WARNING 级别日志"""
        self._add_entry("WARNING", message, code, object_name)
    
    def error(self, code: str, message: str, object_name: Optional[str] = None) -> None:
        """记录 ERROR 级别日志"""
        self._add_entry("ERROR", message, code, object_name)
    
    def save(self) -> None:
        """保存 audit.log 到文件"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("# BigWorld Export Audit Log\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write("# Format: [Timestamp] [Severity] [Code] Message | Object\n")
            f.write("#" + "="*70 + "\n\n")
            
            for entry in self.entries:
                line = f"[{entry.timestamp}] [{entry.severity}]"
                if entry.code:
                    line += f" [{entry.code}]"
                line += f" {entry.message}"
                if entry.object_name:
                    line += f" | Object: {entry.object_name}"
                f.write(line + "\n")
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return any(e.severity == "ERROR" for e in self.entries)
    
    def has_warnings(self) -> bool:
        """检查是否有警告"""
        return any(e.severity == "WARNING" for e in self.entries)
    
    def get_summary(self) -> str:
        """获取摘要"""
        error_count = sum(1 for e in self.entries if e.severity == "ERROR")
        warning_count = sum(1 for e in self.entries if e.severity == "WARNING")
        info_count = sum(1 for e in self.entries if e.severity == "INFO")
        
        return f"导出完成: {error_count} 错误, {warning_count} 警告, {info_count} 信息"


# ==================== 错误码定义 ====================

class ErrorCode:
    """错误码枚举"""
    
    # 几何错误 GEO***
    GEO001 = "GEO001"  # 非流形几何
    GEO002 = "GEO002"  # 法线不一致
    GEO003 = "GEO003"  # 顶点数为0
    GEO004 = "GEO004"  # 三角化失败
    
    # UV 错误 UV***
    UV001 = "UV001"   # UV 越界
    UV002 = "UV002"   # UV 重叠
    UV003 = "UV003"   # UV 缺失
    
    # 材质错误 MAT***
    MAT001 = "MAT001"  # 材质槽缺失
    MAT002 = "MAT002"  # 纹理路径无效
    MAT003 = "MAT003"  # Shader/FX 路径无效
    
    # 命名错误 NAM***
    NAM001 = "NAM001"  # 命名不符合规范
    NAM002 = "NAM002"  # 资源ID缺失
    
    # 动画错误 ANM***
    ANM001 = "ANM001"  # 动画轨道缺失骨骼
    ANM002 = "ANM002"  # 事件标签无效
    ANM003 = "ANM003"  # 关键帧时间非单调
    ANM004 = "ANM004"  # 四元数未归一化
    
    # 碰撞体错误 COL***
    COL001 = "COL001"  # 碰撞体生成失败
    COL002 = "COL002"  # 碰撞层无效
    
    # 门户错误 POR***
    POR001 = "POR001"  # 门户法线方向错误
    POR002 = "POR002"  # 空间ID缺失
    
    # 路径错误 PATH***
    PATH001 = "PATH001"  # 路径不在资源根目录下
    PATH002 = "PATH002"  # 引用文件不存在
    
    # 依赖错误 DEP***
    DEP001 = "DEP001"  # .visual 引用的 .primitives 不存在
    DEP002 = "DEP002"  # .model 引用的 .visual 不存在
    DEP003 = "DEP003"  # .model 引用的 .animation 不存在
    DEP004 = "DEP004"  # PrimitiveGroup 数量与材质槽不一致

