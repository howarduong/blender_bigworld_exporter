# File: __init__.py
# Purpose: BigWorld Exporter 插件主入口
# Notes:
# - 插件注册和注销
# - UI 面板注册
# - 导出操作执行

bl_info = {
    "name": "BigWorld Exporter",
    "author": "BigWorld Team",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar > BigWorld",
    "description": "Export Blender models to BigWorld format",
    "category": "Import-Export",
}

import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    CollectionProperty
)

# 导入UI模块
from .ui.export_panel import BigWorldExportSettings
from .ui.object_panel import (
    BigWorldObjectProperties,
    BigWorldAction,
    BigWorldHardpoint,
    BIGWORLD_PT_object_panel,
    BIGWORLD_OT_validate_object
)
from .ui.preferences_panel import BigWorldAddonPreferences

# 导入UI组件和操作符
from .ui.components.action_list import BIGWORLD_UL_actions
from .ui.components.hardpoint_list import BIGWORLD_UL_hardpoints
from .ui.operators import action_ops, hardpoint_ops

# 导入导出处理器
from .export_processor import ExportProcessor
from .utils.logger import Logger
from .core.schema import ExportSettings
from .writers.audit_writer import AuditLogger


# ==================== 导出操作 ====================

class BigWorldExportOperator(bpy.types.Operator):
    """BigWorld 导出操作"""
    bl_idname = "bigworld.export"
    bl_label = "导出到 BigWorld"
    bl_description = "将选中的对象导出为 BigWorld 格式"
    bl_options = {'REGISTER', 'UNDO'}
    
    # ==================== 文件路径属性 ====================
    filepath: bpy.props.StringProperty(
        name="文件路径",
        description="导出文件的路径",
        subtype='DIR_PATH'
    )
    
    filename_ext = ""  # 不需要扩展名，因为会生成多个文件
    
    # ==================== 导出模式 ====================
    export_mode: bpy.props.EnumProperty(
        name="导出模式",
        description="选择导出模式",
        items=[
            ('SELECTED', '选中导出', '导出当前选中的单个对象'),
            ('ALL', '全部导出', '循环导出多个选中的对象'),
            ('SCENE', '场景导出', '导出场景中所有对象（忽略选择）')
        ],
        default='SELECTED'
    )
    
    # ==================== 导出类型 ====================
    export_type: bpy.props.EnumProperty(
        name="导出类型",
        description="导出数据的类型和内容",
        items=[
            ('STATIC', '静态模型', '基础导出（无骨骼、无蒙皮、无动画）'),
            ('SKINNED', '蒙皮模型', '增强导出（有骨骼、有蒙皮、无动画）'),
            ('CHARACTER', '角色动画', '完整导出（有骨骼、有蒙皮、有动画）')
        ],
        default='STATIC'
    )
    
    # ==================== 文件生成选项 ====================
    export_primitives: bpy.props.BoolProperty(
        name=".primitives",
        description="生成 .primitives 文件",
        default=True
    )
    
    export_visual: bpy.props.BoolProperty(
        name=".visual",
        description="生成 .visual 文件",
        default=True
    )
    
    export_animation: bpy.props.BoolProperty(
        name=".animation",
        description="生成 .animation 文件（角色模型）",
        default=True
    )
    
    export_model: bpy.props.BoolProperty(
        name=".model",
        description="生成 .model 文件",
        default=True
    )
    
    export_manifest: bpy.props.BoolProperty(
        name="manifest.json",
        description="生成 manifest.json 清单",
        default=True
    )
    
    export_audit: bpy.props.BoolProperty(
        name="audit.log",
        description="生成 audit.log 审计日志",
        default=True
    )
    
    # ==================== 批量动画导出 ====================
    batch_export_animations: bpy.props.BoolProperty(
        name="批量导出动画",
        description="导出所有 Action 作为独立动画文件",
        default=True
    )
    
    def execute(self, context):
        """执行导出操作"""
        # 获取场景设置
        scene = context.scene
        prefs = context.preferences.addons[__name__].preferences
        
        # 创建基础日志记录器
        logger = Logger()
        audit_logger = None  # 初始化为None，避免在异常处理时未定义
        
        try:
            # 获取输出目录（优先使用文件浏览器选择的路径）
            import os
            if self.filepath:
                # 用户通过文件浏览器选择的路径
                output_dir = os.path.dirname(self.filepath) if os.path.isfile(self.filepath) else self.filepath
            elif prefs.root_path:
                # 使用Preferences中的root_path
                output_dir = prefs.root_path
            else:
                self.report({'ERROR'}, "请选择导出目录或设置Root Path（Preferences → BigWorld Exporter）")
                return {'CANCELLED'}
            
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 创建审计日志记录器（需要输出目录）
            audit_log_path = os.path.join(output_dir, "audit.log")
            audit_logger = AuditLogger(audit_log_path)
            
            # 创建导出设置
            settings = ExportSettings()
            settings.root_path = prefs.root_path  # 使用偏好设置的Res根目录
            settings.unit_scale = scene.unit_settings.scale_length
            settings.auto_validate = True
            settings.write_audit = self.export_audit
            
            # 获取要导出的对象
            selected_meshes = []
            if self.export_mode == 'SELECTED':
                # 选中导出：只导出第一个选中的网格对象
                for obj in context.selected_objects:
                    if obj.type == 'MESH':
                        selected_meshes.append(obj)
                        break
            elif self.export_mode == 'ALL':
                # 全部导出：导出所有选中的网格对象
                for obj in context.selected_objects:
                    if obj.type == 'MESH':
                        selected_meshes.append(obj)
            elif self.export_mode == 'SCENE':
                # 场景导出：导出场景中所有网格对象
                for obj in scene.objects:
                    if obj.type == 'MESH':
                        selected_meshes.append(obj)
            
            if not selected_meshes:
                self.report({'ERROR'}, "没有找到要导出的网格对象")
                return {'CANCELLED'}
            
            # 记录导出信息
            logger.info(f"导出模式: {self.export_mode}")
            logger.info(f"导出类型: {self.export_type}")
            logger.info(f"检测到 {len(selected_meshes)} 个对象待导出")
            logger.info(f"对象列表: {[obj.name for obj in selected_meshes]}")
            logger.info(f"输出目录: {output_dir}")
            
            # 创建导出处理器
            processor = ExportProcessor(settings, logger, output_dir)
            
            # 循环导出每个对象
            export_count = 0
            for idx, obj in enumerate(selected_meshes):
                logger.info(f"\n{'='*60}")
                logger.info(f"导出对象 {idx + 1}/{len(selected_meshes)}: {obj.name}")
                logger.info(f"{'='*60}")
                
                # 确定资源ID
                if obj.bigworld_props.resource_id:
                    obj_resource_id = obj.bigworld_props.resource_id
                    logger.info(f"使用对象设置的资源ID: {obj_resource_id}")
                else:
                    obj_resource_id = obj.name
                    logger.info(f"使用对象名称作为资源ID: {obj_resource_id}")
                
                # 准备文件选项
                file_options = {
                    'export_primitives': self.export_primitives,
                    'export_visual': self.export_visual,
                    'export_animation': self.export_animation,
                    'export_model': self.export_model,
                    'export_manifest': self.export_manifest,
                    'export_audit': self.export_audit
                }
                
                # 使用ExportProcessor处理对象
                try:
                    success = processor.process_object(obj, self.export_type, file_options)
                    
                    if success:
                        export_count += 1
                        logger.info(f"✅ {obj.name} 导出完成 ({idx + 1}/{len(selected_meshes)})")
                    else:
                        logger.error(f"❌ {obj.name} 导出失败")
                
                except Exception as e:
                    logger.error(f"❌ {obj.name} 导出异常: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            # 保存日志
            audit_logger.save()
            
            # 最终报告
            logger.info(f"\n{'='*60}")
            logger.info(f"导出完成统计")
            logger.info(f"{'='*60}")
            logger.info(f"总对象数: {len(selected_meshes)}")
            logger.info(f"成功导出: {export_count}")
            logger.info(f"失败数量: {len(selected_meshes) - export_count}")
            
            if export_count > 0:
                self.report({'INFO'}, f"导出完成！成功: {export_count}/{len(selected_meshes)}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "所有对象导出失败，请查看 audit.log")
                return {'CANCELLED'}
        
        except Exception as e:
            logger.error(f"导出异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 保存审计日志（如果已创建）
            if audit_logger:
                audit_logger.save()
            
            self.report({'ERROR'}, f"导出异常: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """调用导出对话框"""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        """绘制导出选项UI"""
        layout = self.layout
        
        # 导出模式
        box = layout.box()
        box.label(text="导出模式", icon='EXPORT')
        box.prop(self, "export_mode")
        
        # 导出类型
        box = layout.box()
        box.label(text="导出类型", icon='OUTLINER_DATA_ARMATURE')
        box.prop(self, "export_type")
        
        # 文件生成选项
        box = layout.box()
        box.label(text="文件生成", icon='FILE')
        box.prop(self, "export_primitives")
        box.prop(self, "export_visual")
        box.prop(self, "export_model")
        if self.export_type == 'CHARACTER':
            box.prop(self, "export_animation")
            box.prop(self, "batch_export_animations")
        
        # 日志选项
        box = layout.box()
        box.label(text="日志", icon='TEXT')
        box.prop(self, "export_manifest")
        box.prop(self, "export_audit")


# ==================== 菜单注册 ====================

def menu_func_export(self, context):
    """添加到 File → Export 菜单"""
    self.layout.operator(BigWorldExportOperator.bl_idname, text="BigWorld (.primitives, .visual, .model)")


# ==================== 插件注册 ====================

def register():
    """注册插件"""
    # 注册属性组和数据类
    bpy.utils.register_class(BigWorldAction)
    bpy.utils.register_class(BigWorldHardpoint)
    bpy.utils.register_class(BigWorldObjectProperties)
    bpy.utils.register_class(BigWorldExportSettings)
    bpy.utils.register_class(BigWorldAddonPreferences)
    
    # 注册UI组件
    bpy.utils.register_class(BIGWORLD_UL_actions)
    bpy.utils.register_class(BIGWORLD_UL_hardpoints)
    
    # 注册操作符
    action_ops.register()
    hardpoint_ops.register()
    bpy.utils.register_class(BIGWORLD_OT_validate_object)
    bpy.utils.register_class(BigWorldExportOperator)
    
    # 注册UI面板
    bpy.utils.register_class(BIGWORLD_PT_object_panel)
    
    # 注册到 File → Export 菜单
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
    # 注册其他UI面板并绑定属性
    from .ui.export_panel import register as register_export_panel
    from .ui.object_panel import register as register_object_panel
    from .ui.preferences_panel import register as register_preferences_panel
    
    register_export_panel()
    register_object_panel()  # 绑定Object属性
    register_preferences_panel()
    
    print("BigWorld Exporter 已注册")


def unregister():
    """注销插件"""
    # 注销其他UI面板并解绑属性
    from .ui.export_panel import unregister as unregister_export_panel
    from .ui.object_panel import unregister as unregister_object_panel
    from .ui.preferences_panel import unregister as unregister_preferences_panel
    
    unregister_export_panel()
    unregister_object_panel()  # 解绑Object属性
    unregister_preferences_panel()
    
    # 从 File → Export 菜单移除
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
    # 注销UI面板
    bpy.utils.unregister_class(BIGWORLD_PT_object_panel)
    
    # 注销操作符
    bpy.utils.unregister_class(BigWorldExportOperator)
    bpy.utils.unregister_class(BIGWORLD_OT_validate_object)
    hardpoint_ops.unregister()
    action_ops.unregister()
    
    # 注销UI组件
    bpy.utils.unregister_class(BIGWORLD_UL_hardpoints)
    bpy.utils.unregister_class(BIGWORLD_UL_actions)
    
    # 注销属性组和数据类
    bpy.utils.unregister_class(BigWorldAddonPreferences)
    bpy.utils.unregister_class(BigWorldExportSettings)
    bpy.utils.unregister_class(BigWorldObjectProperties)
    bpy.utils.unregister_class(BigWorldHardpoint)
    bpy.utils.unregister_class(BigWorldAction)
    
    print("BigWorld Exporter 已注销")


if __name__ == "__main__":
    register()