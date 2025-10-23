# File: ui/export_panel.py
# Purpose: BigWorld 导出执行面板
# Notes:
# - 导出类型选择 ✔
# - 几何格式 ◆ 占位保留
# - 生成文件选项 ✔
# - 目录策略、导出预设 ◆ 占位保留
# - 开始导出按钮 ✔

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    EnumProperty,
    BoolProperty,
    StringProperty,
    PointerProperty
)


# ==================== 属性组 ====================

class BigWorldExportSettings(PropertyGroup):
    """导出执行设置"""
    
    # 导出类型 ✔
    export_type: EnumProperty(
        name="导出类型",
        description="导出对象类型",
        items=[
            ('STATIC', '静态模型', '导出静态模型'),
            ('CHARACTER', '角色', '导出角色（带动画）'),
            ('COLLISION', '碰撞体', '仅导出碰撞体'),
            ('PORTAL', '门户', '导出门户'),
            ('GROUP', '组', '导出对象组')
        ],
        default='STATIC'
    )
    
    # 几何格式 ◆ 占位保留
    geometry_format: EnumProperty(
        name="几何格式",
        description="几何数据格式（占位保留）",
        items=[
            ('PRIMITIVES', 'primitives', '标准 primitives 格式'),
            ('PROCESSED', 'processed', '预处理格式（暂未实现）'),
        ],
        default='PRIMITIVES'
    )
    
    # 生成文件选项 ✔
    export_primitives: BoolProperty(
        name=".primitives",
        description="生成 .primitives 文件",
        default=True
    )
    
    export_visual: BoolProperty(
        name=".visual",
        description="生成 .visual 文件",
        default=True
    )
    
    export_animation: BoolProperty(
        name=".animation",
        description="生成 .animation 文件（角色模型）",
        default=True
    )
    
    export_collision: BoolProperty(
        name=".collision",
        description="生成 .collision 文件（占位保留）",
        default=False
    )
    
    export_model: BoolProperty(
        name=".model/.xml",
        description="生成 .model/.xml 文件",
        default=True
    )
    
    export_manifest: BoolProperty(
        name="manifest.json",
        description="生成 manifest.json 清单",
        default=True
    )
    
    export_audit: BoolProperty(
        name="audit.log",
        description="生成 audit.log 审计日志",
        default=True
    )
    
    # 目录策略 ◆ 占位保留
    directory_strategy: EnumProperty(
        name="目录策略",
        description="导出文件的目录组织策略（占位保留）",
        items=[
            ('BY_TYPE', '按类型', '按文件类型分目录'),
            ('BY_PACKAGE', '按包', '按资源包分目录'),
            ('BY_LOD', '按 LOD', '按 LOD 层级分目录')
        ],
        default='BY_TYPE'
    )
    
    # 导出预设 ◆ 占位保留
    export_preset: StringProperty(
        name="导出预设",
        description="保存的导出配置预设（占位保留）",
        default=""
    )


# ==================== 面板（已移除） ====================
# 注意：导出面板已整合到主导出操作符的 draw() 方法中
# 不再使用独立的 Panel，而是在 File → Export → BigWorld 对话框中显示


# ==================== 操作符 ====================
# 注意：导出执行和预设操作符已移至 __init__.py 的主导出操作符中


# ==================== 注册 ====================

def register():
    # 注册属性到 Scene
    # 注意：类本身在 __init__.py 中注册
    bpy.types.Scene.bigworld_export_settings = PointerProperty(type=BigWorldExportSettings)


def unregister():
    # 删除属性
    if hasattr(bpy.types.Scene, 'bigworld_export_settings'):
        del bpy.types.Scene.bigworld_export_settings


if __name__ == "__main__":
    register()

