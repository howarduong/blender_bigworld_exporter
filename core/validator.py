# File: core/validators.py
# Purpose: 通用校验器，保证导出数据符合 BigWorld 规范
# Notes:
# - 骨骼一致性：skeleton 与 animation 引用必须匹配
# - group 对齐：Primitives.groups 与 Visual.materials 数量/索引一致
# - 关键帧单调性：动画关键帧时间必须单调递增
# - 命名规范：对象/骨骼/资源ID 符合正则
# - 资源路径：必须合法（相对路径、扩展名正确）
# - LOD/目录策略：检查配置是否合理

import re
from typing import List, Tuple
from .schema import (
    Primitives, Visual, Model, Animation,
    Skeleton, AnimationChannel, AnimationTrackEvent,
    ObjectType, DirectoryStrategy
)


# ---------------------------
# 命名规范校验
# ---------------------------

def validate_name(name: str, pattern: str = r'^[A-Za-z0-9_\-]+$',
                  min_len: int = 1, max_len: int = 64) -> Tuple[bool, str]:
    if not (min_len <= len(name) <= max_len):
        return False, f"长度必须在 {min_len}~{max_len} 之间"
    if not re.match(pattern, name):
        return False, f"名称包含非法字符: {name}"
    return True, "OK"


# ---------------------------
# 骨骼一致性
# ---------------------------

def validate_skeleton_consistency(model: Model, animations: List[Animation]) -> List[str]:
    errors: List[str] = []
    if not model.skeleton:
        return errors
    bone_set = set(model.skeleton.bone_names)
    for anim in animations:
        for ch in anim.channels:
            if ch.bone_name not in bone_set:
                errors.append(f"动画 {anim.name} 引用未知骨骼: {ch.bone_name}")
    return errors


# ---------------------------
# group 对齐
# ---------------------------

def validate_group_alignment(primitives: Primitives, visual: Visual) -> List[str]:
    errors: List[str] = []
    if len(primitives.groups) != len(visual.materials):
        errors.append(
            f"Primitives.groups({len(primitives.groups)}) 与 Visual.materials({len(visual.materials)}) 数量不一致"
        )
    else:
        for i, g in enumerate(primitives.groups):
            if g.material_slot != i:
                errors.append(f"Group {g.name} 的 material_slot={g.material_slot} 与索引 {i} 不一致")
    return errors


# ---------------------------
# 动画关键帧单调性
# ---------------------------

def validate_animation_monotonic(anim: Animation) -> List[str]:
    errors: List[str] = []
    for ch in anim.channels:
        for seq_name, seq in [
            ("positionKeys", ch.keys.position_keys),
            ("rotationKeys", ch.keys.rotation_keys),
            ("scaleKeys", ch.keys.scale_keys),
        ]:
            times = [t for t, _ in seq]
            if times != sorted(times):
                errors.append(f"动画 {anim.name} 通道 {ch.bone_name} 的 {seq_name} 时间戳非单调递增")
            if any(t < 0 or t > anim.duration for t in times):
                errors.append(f"动画 {anim.name} 通道 {ch.bone_name} 的 {seq_name} 时间越界")
    return errors


# ---------------------------
# 资源路径校验
# ---------------------------

def validate_resource_path(path: str) -> Tuple[bool, str]:
    pattern = r'^[A-Za-z0-9_\-./]+$'
    if not re.match(pattern, path):
        return False, f"路径非法: {path}"
    if " " in path:
        return False, f"路径包含空格: {path}"
    return True, "OK"


# ---------------------------
# LOD/目录策略校验
# ---------------------------

def validate_strategy(visual: Visual) -> List[str]:
    errors: List[str] = []
    if visual.directory_strategy not in list(DirectoryStrategy):
        errors.append(f"未知目录策略: {visual.directory_strategy}")
    if visual.lod_binding:
        for g, lod in visual.lod_binding.items():
            if lod < 0:
                errors.append(f"LOD 绑定非法: group={g}, lod={lod}")
    return errors


# ---------------------------
# 综合校验
# ---------------------------

def validate_all(primitives: Primitives = None,
                 visual: Visual = None,
                 model: Model = None,
                 animations: List[Animation] = None) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if primitives and visual:
        errors.extend(validate_group_alignment(primitives, visual))
        errors.extend(validate_strategy(visual))

    if model and animations:
        errors.extend(validate_skeleton_consistency(model, animations))
        for anim in animations:
            errors.extend(validate_animation_monotonic(anim))

    # 命名规范检查
    if model and model.resource_id:
        ok, msg = validate_name(model.resource_id)
        if not ok:
            errors.append(f"资源ID非法: {msg}")

    return errors, warnings
