# 相对路径: validators/hex_diff.py
# 主要功能: 将 Blender 导出的二进制文件与旧 3ds Max 插件产物进行逐字节对比，
#          输出差异报告 (偏移量、旧值、新值)。
#
# 注意:
#   - 必须保证对比结果能精确定位差异，便于开发调试。
#   - 输出报告需包含差异统计信息。
#   - 对比逻辑需支持大文件 (逐块读取)。
#
# 开发前必读参考（每次构建前必须学习研究原 3ds Max 插件代码）:
# BigWorld_MAXScripts GitHub 仓库（宏脚本全集）：
# https://github.com/howarduong/BigWorld_MAXScripts/tree/1b7eb719e475c409afa319877f4550cf5accbafc/BigWorld_MacroScripts

from typing import Dict, List


class HexDiff:
    """十六进制差异比对器"""

    def __init__(self, chunk_size: int = 4096):
        self.chunk_size = chunk_size

    def compare_files(self, file1: str, file2: str, max_diffs: int = 100) -> Dict:
        """
        对比两个二进制文件。
        参数:
            file1: Blender 导出的文件路径
            file2: 旧 3ds Max 插件产物路径
            max_diffs: 最大记录差异数量 (避免输出过大)
        返回:
            {
                "file1": str,
                "file2": str,
                "diffs": List[Dict],
                "total_diffs": int,
                "same": bool
            }
        """
        diffs: List[Dict] = []
        total_diffs = 0
        offset = 0

        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            while True:
                b1 = f1.read(self.chunk_size)
                b2 = f2.read(self.chunk_size)
                if not b1 and not b2:
                    break

                max_len = max(len(b1), len(b2))
                for i in range(max_len):
                    v1 = b1[i] if i < len(b1) else None
                    v2 = b2[i] if i < len(b2) else None
                    if v1 != v2:
                        total_diffs += 1
                        if len(diffs) < max_diffs:
                            diffs.append({
                                "offset": offset + i,
                                "file1_val": f"{v1:02X}" if v1 is not None else "EOF",
                                "file2_val": f"{v2:02X}" if v2 is not None else "EOF"
                            })
                offset += max_len

        return {
            "file1": file1,
            "file2": file2,
            "diffs": diffs,
            "total_diffs": total_diffs,
            "same": total_diffs == 0
        }

    def format_report(self, result: Dict) -> str:
        """
        格式化差异报告为字符串。
        """
        lines = []
        lines.append(f"对比文件: {result['file1']} vs {result['file2']}")
        lines.append(f"总差异数: {result['total_diffs']}")
        if result["same"]:
            lines.append("结果: 两个文件完全一致 ✅")
        else:
            lines.append("结果: 存在差异 ❌")
            for d in result["diffs"]:
                lines.append(
                    f"偏移 {d['offset']:08X}: file1={d['file1_val']} file2={d['file2_val']}"
                )
            if result["total_diffs"] > len(result["diffs"]):
                lines.append(f"... 还有 {result['total_diffs'] - len(result['diffs'])} 处差异未显示")
        return "\n".join(lines)
