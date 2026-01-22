import os
import re
from typing import Tuple, List


def detect_current_stage(repo_dir: str) -> Tuple[str, int]:
    """
    通过查看 tmp_files/ 里有哪些文件来判断当前执行到哪个阶段
    
    Args:
        repo_dir: 仓库输出目录
    
    Returns:
        <阶段名, 最大迭代次数>
        阶段名包括architecture, skeleton, code
    """
    tmp_dir = os.path.join(repo_dir, "tmp_files")
    
    # 目录不存在，在进行第一步<architecture, 0>
    if not os.path.exists(tmp_dir):
        return "architecture", 0
    
    files = os.listdir(tmp_dir)
    
    # 提取文件中的数字
    def extract_step_numbers(files: List[str], prefix: str) -> List[int]:
        numbers = []
        for f in files:
            if f.startswith(prefix):
                match = re.search(r'_(\d+)\.', f)
                if match:
                    numbers.append(int(match.group(1)))
        return numbers
    
    # 检查代码生成阶段（最后阶段）
    code_numbers = extract_step_numbers(files, "generated_code")
    if code_numbers:
        return "code", max(code_numbers)
    
    # 检查骨架生成阶段
    skeleton_numbers = extract_step_numbers(files, "skeleton")
    if skeleton_numbers:
        return "skeleton", max(skeleton_numbers)
    
    # 检查架构设计阶段
    arch_numbers = extract_step_numbers(files, "architecture")
    if arch_numbers:
        return "architecture", max(arch_numbers)
    
    # 都没有 = 刚开始
    return "architecture", 0


def calculate_progress(stage: str, iteration: int) -> int:
    stage_config = {
        "architecture": {"base": 0, "max": 30, "weight": 10},
        "skeleton": {"base": 30, "max": 60, "weight": 10},
        "code": {"base": 60, "max": 100, "weight": 8}
    }
    
    if stage not in stage_config:
        return 0
    
    config = stage_config[stage]
    progress = config["base"] + min(iteration * config["weight"], config["max"] - config["base"])
    
    return min(95, progress)
