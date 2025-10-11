# 相对路径: __init__.py
# 功能: 插件入口，负责:
#   - 注册/注销所有模块 (UI、导出器、Preferences)
#   - 集成到 Blender 菜单 (File > Export)
#   - 确保 BigWorldObjectSettings 正确挂载到 Object

bl_info = {
    "name": "BigWorld Exporter",
    "author": "Rick + Copilot",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "File > Export > BigWorld 资源",
    "description": "导出 BigWorld 引擎兼容的模型/材质/骨骼/动画/碰撞/门户/预制/Hitbox",
    "category": "Import-Export",
}

import bpy

# 导入子模块
from .preferences import BigWorldAddonPreferences
from .ui_panel import BIGWORLD_PT_sidebar, BigWorldObjectSettings
from .export_operator import EXPORT_OT_bigworld


# 菜单集成
def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_bigworld.bl_idname, text="BigWorld 资源 (.model)")


# 注册类
classes = (
    BigWorldAddonPreferences,
    BigWorldObjectSettings,   # 必须先注册 PropertyGroup
    BIGWORLD_PT_sidebar,
    EXPORT_OT_bigworld,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # 挂载到 Object
    bpy.types.Object.bw_settings = bpy.props.PointerProperty(type=BigWorldObjectSettings)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    # 删除属性
    del bpy.types.Object.bw_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
