import os
from pathlib import Path
from typing import Dict, Any, List

from core.config import GEMINI_DIR

class SkillsOptimizer:
    """Antigravity 内置技能与前置 Token 预算优化器"""

    GUIDE_SKILL_NAMES = ["antigravity_guide", "migrate-workflows", "agy-customizations"]

    @classmethod
    def get_skills_dir(cls) -> Path:
        return GEMINI_DIR / "builtin" / "skills"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        skills_dir = cls.get_skills_dir()
        if not skills_dir.exists():
            return {"available": False, "skills": [], "total_guide_bytes": 0, "is_pruned": False}

        skills = []
        total_guide_bytes = 0
        pruned_count = 0
        guide_count = 0

        for item in skills_dir.iterdir():
            if item.is_dir():
                clean_name = item.name.replace(".disabled", "")
                is_disabled = item.name.endswith(".disabled")
                is_guide = clean_name in cls.GUIDE_SKILL_NAMES
                size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())

                if is_guide:
                    guide_count += 1
                    total_guide_bytes += size
                    if is_disabled:
                        pruned_count += 1

                skills.append({
                    "name": clean_name,
                    "is_guide": is_guide,
                    "is_disabled": is_disabled,
                    "size_bytes": size,
                    "approx_tokens": int(size / 3.5) # 粗略估算 Token
                })

        is_pruned = guide_count > 0 and pruned_count >= guide_count

        return {
            "available": True,
            "skills": skills,
            "total_guide_bytes": total_guide_bytes,
            "approx_tokens_saved": int(total_guide_bytes / 3.5),
            "is_pruned": is_pruned,
        }

    @classmethod
    def set_pruned(cls, prune: bool) -> bool:
        skills_dir = cls.get_skills_dir()
        if not skills_dir.exists():
            return False

        for name in cls.GUIDE_SKILL_NAMES:
            active_path = skills_dir / name
            disabled_path = skills_dir / f"{name}.disabled"

            if prune:
                if active_path.exists() and not disabled_path.exists():
                    try:
                        active_path.rename(disabled_path)
                    except Exception:
                        pass
            else:
                if disabled_path.exists() and not active_path.exists():
                    try:
                        disabled_path.rename(active_path)
                    except Exception:
                        pass

        return True
