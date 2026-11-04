"""全量冒烟：一次性跑完 11 个算子的离线单元测试（默认）与四条产线端到端联跑（--online）。

用法（项目根执行）：
    python -I operators/_shared_tools/run_all_checks.py            # 离线：全部单测 + 外壳契约测试
    python -I operators/_shared_tools/run_all_checks.py --online  # 追加：四条产线真实 API 链路（需出网，约 5–10 分钟）

退出码：全部通过 0；任一失败 1。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPERATORS = ["meta_clean_slice", "meta_genre_judge", "meta_fact_extract", "meta_field_fill",
             "lay_page_render", "lay_page_detect", "fml_formula_locate", "fml_formula_recognize",
             "img_region_locate", "img_type_classify", "img_struct_describe"]
CHAINS = ["chain_meta", "chain_lay", "chain_fml", "chain_img"]


def run_cmd(desc: str, args: list[str], cwd: Path) -> tuple[bool, float, str]:
    t0 = time.time()
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    dt = time.time() - t0
    tail = (p.stdout + p.stderr).strip().splitlines()[-6:]
    ok = p.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {desc}  ({dt:.1f}s)")
    if not ok:
        for line in tail:
            print("      " + line)
    return ok, dt, desc


def main() -> int:
    py = sys.executable
    results: list[tuple[bool, float, str]] = []

    # 1) 外壳契约测试（三接口模板，覆盖 upload/predict/血缘/阶段 zip/幂等/路径闸门）
    shell_tests = Path(__file__).parent / "tests"
    if (shell_tests / "test_shell.py").exists():
        results.append(run_cmd("外壳契约 test_shell.py",
                               [py, "-m", "pytest", str(shell_tests / "test_shell.py"), "-q"],
                               PROJECT_ROOT))

    # 2) 逐算子离线单测（mock 模型调用，不联网）
    for tag in OPERATORS:
        pkg = PROJECT_ROOT / "operators" / tag
        results.append(run_cmd(f"{tag} 单测",
                               [py, "-m", "pytest", f"{tag}/tests", "-q"], pkg))

    offline_bad = [r for r in results if not r[0]]

    # 3) 在线链路（可选）
    if "--online" in sys.argv:
        for chain in CHAINS:
            script = PROJECT_ROOT / ".scratch" / f"{chain}.py"
            if script.exists():
                results.append(run_cmd(f"链路 {chain}（真实 API）",
                                       [py, "-I", str(script)], PROJECT_ROOT))

    print("\n===== 汇总 =====")
    for ok, dt, desc in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {dt:7.1f}s  {desc}")
    n_fail = sum(1 for r in results if not r[0])
    print(f"共 {len(results)} 项，失败 {n_fail} 项")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
