# -*- coding: utf-8 -*-
"""
BigWorld 插件偏好设置（重构版 - 核心功能）
移除所有占位功能
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty
)


class BigWorldAddonPreferences(AddonPreferences):
    """BigWorld 插件全局设置（精简核心版）"""
    bl_idname = __package__.split('.')[0]
    
    # ===== 路径设置 =====
    root_path: StringProperty(
        name="Res根目录",
        description="BigWorld资源根目录（所有相对路径都相对于此目录计算）",
        subtype='DIR_PATH',
        default=""
    )
    
    # ===== 坐标系与单位 =====
    axis_mode: EnumProperty(
        name="坐标系转换",
        description="Blender到BigWorld的坐标系转换",
        items=[
            ('Z_UP_TO_Y_UP', 'Z-up → Y-up', 'Blender Z-up转BigWorld Y-up（推荐）'),
            ('NONE', '不转换', '保持原坐标系')
        ],
        default='Z_UP_TO_Y_UP'
    )
    
    unit_scale: FloatProperty(
        name="单位缩放",
        description="导出时的单位缩放（Blender单位 → 米）",
        default=1.0,
        min=0.001,
        max=1000.0
    )
    
    # ===== 导出选项 =====
    auto_validate: BoolProperty(
        name="导出前自动检测",
        description="导出前自动运行数据验证",
        default=True
    )
    
    write_audit: BoolProperty(
        name="写入审计日志",
        description="生成audit.log文件",
        default=True
    )
    
    # ===== UI绘制 =====
    def draw(self, context):
        layout = self.layout
        
        # 路径设置
        box = layout.box()
        box.label(text="路径设置", icon='FILE_FOLDER')
        box.prop(self, "root_path")
        box.label(text="说明：所有导出的相对路径都基于此目录计算", icon='INFO')
        
        # 坐标系与单位
        box = layout.box()
        box.label(text="坐标系与单位", icon='ORIENTATION_GLOBAL')
        box.prop(self, "axis_mode")
        box.prop(self, "unit_scale")
        
        # 导出选项
        box = layout.box()
        box.label(text="导出选项", icon='SETTINGS')
        box.prop(self, "auto_validate")
        box.prop(self, "write_audit")
        
        # 保存设置
        layout.separator()
        layout.operator("wm.save_userpref", text="保存设置")


# ==================== 注册 ====================
# 注意：BigWorldAddonPreferences 在 __init__.py 中注册，这里不需要重复注册

def register():
    pass  # 保留给未来可能的其他注册


def unregister():
    pass  # 保留给未来可能的其他注销


if __name__ == "__main__":
    register()

