# 相对路径: core/animation_writer.py
# 功能: 导出动画数据，包括:
#   - 动画轨道 (骨骼关键帧)
#   - 采样数据 (位置/旋转/缩放)
#   - Cue Track 事件 (时间戳、标签、参数)
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - 关键帧采样需与旧插件保持一致 (采样频率、插值方式)。
#   - Cue Track 事件需与 BigWorld 引擎规范对齐。

from typing import List, Dict
import bpy

from .binsection_writer import BinWriter, SectionWriter


class AnimationWriter:
    """动画导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 动画主入口
    # =========================
    def write_animation(self, armature: bpy.types.Object, action: bpy.types.Action, fps: int = 30):
        """
        导出动画轨道。
        参数:
            armature: 骨架对象
            action: Blender 动作 (Action)
            fps: 采样频率 (默认 30)
        """
        self.secw.begin_section(section_id=0x4001)  # 示例 ID，需在 schema 固化

        # 动画名称
        self.binw.write_cstring(action.name if action else "EmptyAnim")

        if action:
            frame_start, frame_end = action.frame_range
            duration = (frame_end - frame_start) / fps
        else:
            frame_start, frame_end, duration = 0, 0, 0.0

        # 动画时长 (秒)
        self.binw.write_f32(duration)

        # 骨骼数量
        bones = armature.data.bones if armature and armature.data else []
        self.binw.write_u32(len(bones))

        # 遍历骨骼，导出关键帧
        if action:
            for bone in bones:
                self._write_bone_track(action, armature, bone, fps)

        self.secw.end_section()

    def _write_bone_track(self, action: bpy.types.Action, armature: bpy.types.Object, bone: bpy.types.Bone, fps: int):
        """导出单个骨骼的动画轨道"""
        self.binw.write_cstring(bone.name)

        frame_start, frame_end = action.frame_range
        num_keys = int(frame_end - frame_start + 1)
        self.binw.write_u32(num_keys)

        for f in range(int(frame_start), int(frame_end) + 1):
            bpy.context.scene.frame_set(f)
            pose_bone = armature.pose.bones.get(bone.name)
            if not pose_bone:
                continue

            loc = pose_bone.location
            rot = pose_bone.rotation_quaternion
            scale = pose_bone.scale

            # 时间戳 (秒)
            t = (f - frame_start) / fps
            self.binw.write_f32(t)

            # 写位置
            self.binw.write_f32(loc[0]); self.binw.write_f32(loc[1]); self.binw.write_f32(loc[2])

            # 写旋转 (四元数)
            self.binw.write_f32(rot.w); self.binw.write_f32(rot.x); self.binw.write_f32(rot.y); self.binw.write_f32(rot.z)

            # 写缩放
            self.binw.write_f32(scale[0]); self.binw.write_f32(scale[1]); self.binw.write_f32(scale[2])

    # =========================
    # Cue Track 事件
    # =========================
    def write_cue_track(self, events: List[Dict]):
        """导出 Cue Track 事件"""
        self.secw.begin_section(section_id=0x4002)  # 示例 ID，需在 schema 固化
        self.binw.write_u32(len(events))
        for ev in events:
            self._write_single_event(ev)
        self.secw.end_section()

    def _write_single_event(self, ev: Dict):
        """导出单个 Cue Track 事件"""
        self.binw.write_f32(float(ev.get("time", 0.0)))
        self.binw.write_cstring(ev.get("label", ""))
        self.binw.write_cstring(ev.get("param", ""))

    # =========================
    # 占位写出接口
    # =========================
    def write_empty_animation_section(self):
        """写出空动画段 (占位)"""
        self.secw.begin_section(section_id=0x4001)
        self.binw.write_cstring("EmptyAnim")
        self.binw.write_f32(0.0)   # 时长
        self.binw.write_u32(0)     # 骨骼数量
        self.secw.end_section()

    def write_empty_cue_track(self):
        """写出空 Cue Track (占位)"""
        self.secw.begin_section(section_id=0x4002)
        self.binw.write_u32(0)     # 事件数量
        self.secw.end_section()
# 相对路径: core/animation_writer.py
# 功能: 导出动画数据，包括:
#   - 动画轨道 (骨骼关键帧)
#   - 采样数据 (位置/旋转/缩放)
#   - Cue Track 事件 (时间戳、标签、参数)
#
# 注意:
#   - 字段顺序、默认值、对齐方式必须与原 3ds Max 插件一致。
#   - 关键帧采样需与旧插件保持一致 (采样频率、插值方式)。
#   - Cue Track 事件需与 BigWorld 引擎规范对齐。

from typing import List, Dict
import bpy

from .binsection_writer import BinWriter, SectionWriter


class AnimationWriter:
    """动画导出器"""

    def __init__(self, binw: BinWriter):
        self.binw = binw
        self.secw = SectionWriter(binw)

    # =========================
    # 动画主入口
    # =========================
    def write_animation(self, action: bpy.types.Action, armature: bpy.types.Object, fps: int = 30):
        """
        导出动画轨道。
        参数:
            action: Blender 动作 (Action)
            armature: 骨架对象
            fps: 采样频率 (默认 30)
        """
        self.secw.begin_section(section_id=0x4001)  # 示例 ID，需在 schema 固化

        # 动画名称
        if action:
            self.binw.write_cstring(action.name)
        else:
            self.binw.write_cstring("EmptyAnim")

        # 动画时长 (秒)
        if action:
            frame_start, frame_end = action.frame_range
            duration = (frame_end - frame_start) / fps
        else:
            frame_start, frame_end = 0, 0
            duration = 0.0
        self.binw.write_f32(duration)

        # 骨骼数量
        if armature and armature.data:
            bones = armature.data.bones
            self.binw.write_u32(len(bones))
        else:
            bones = []
            self.binw.write_u32(0)

        # 遍历骨骼，导出关键帧
        if action and bones:
            for bone in bones:
                self._write_bone_track(action, armature, bone, fps)

        self.secw.end_section()

    def _write_bone_track(self, action: bpy.types.Action, armature: bpy.types.Object, bone: bpy.types.Bone, fps: int):
        """
        导出单个骨骼的动画轨道。
        """
        # 骨骼名称
        self.binw.write_cstring(bone.name)

        # 采样关键帧数量
        frame_start, frame_end = action.frame_range
        num_keys = int(frame_end - frame_start + 1)
        self.binw.write_u32(num_keys)

        # 遍历每一帧
        for f in range(int(frame_start), int(frame_end) + 1):
            bpy.context.scene.frame_set(f)

            # 获取 PoseBone
            pose_bone = armature.pose.bones.get(bone.name)
            if not pose_bone:
                # 如果没有对应的 PoseBone，写默认值
                t = (f - frame_start) / fps
                self.binw.write_f32(t)
                self.binw.write_f32(0.0); self.binw.write_f32(0.0); self.binw.write_f32(0.0)  # loc
                self.binw.write_f32(1.0); self.binw.write_f32(0.0); self.binw.write_f32(0.0); self.binw.write_f32(0.0)  # rot
                self.binw.write_f32(1.0); self.binw.write_f32(1.0); self.binw.write_f32(1.0)  # scale
                continue

            # 分解矩阵为位置/旋转/缩放
            loc = pose_bone.location
            rot = pose_bone.rotation_quaternion
            scale = pose_bone.scale

            # 时间戳 (秒)
            t = (f - frame_start) / fps
            self.binw.write_f32(t)

            # 写位置
            self.binw.write_f32(loc[0])
            self.binw.write_f32(loc[1])
            self.binw.write_f32(loc[2])

            # 写旋转 (四元数)
            self.binw.write_f32(rot.w)
            self.binw.write_f32(rot.x)
            self.binw.write_f32(rot.y)
            self.binw.write_f32(rot.z)

            # 写缩放
            self.binw.write_f32(scale[0])
            self.binw.write_f32(scale[1])
            self.binw.write_f32(scale[2])

    # =========================
    # Cue Track 事件
    # =========================
    def write_cue_track(self, events: List[Dict]):
        """
        导出 Cue Track 事件。
        参数:
            events: 事件列表，每个事件为 dict:
                {
                    "time": float,   # 时间戳 (秒)
                    "label": str,    # 事件标签
                    "param": str     # 附加参数
                }
        """
        self.secw.begin_section(section_id=0x4002)  # 示例 ID，需在 schema 固化

        # 写事件数量
        self.binw.write_u32(len(events))

        # 遍历事件
        for ev in events:
            self._write_single_event(ev)

        self.secw.end_section()

    def _write_single_event(self, ev: Dict):
        """
        导出单个 Cue Track 事件。
        """
        # 时间戳
        self.binw.write_f32(float(ev.get("time", 0.0)))

        # 标签
        self.binw.write_cstring(ev.get("label", ""))

        # 参数
        self.binw.write_cstring(ev.get("param", ""))

    # =========================
    # 占位写出接口
    # =========================
    def write_empty_animation_section(self):
        """
        写出空动画段 (占位)。
        """
        self.secw.begin_section(section_id=0x4001)
        self.binw.write_cstring("EmptyAnim")
        self.binw.write_f32(0.0)   # 时长
        self.binw.write_u32(0)     # 骨骼数量
        self.secw.end_section()

    def write_empty_cue_track(self):
        """
        写出空 Cue Track (占位)。
        """
        self.secw.begin_section(section_id=0x4002)
        self.binw.write_u32(0)     # 事件数量
        self.secw.end_section()
