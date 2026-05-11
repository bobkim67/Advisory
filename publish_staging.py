import shutil
from pathlib import Path

SRC = Path(r"C:\Users\user\Downloads\python\Advisory")
DST = Path(r"C:\Users\user\Downloads\python\_publish_advisory")

if DST.exists():
    shutil.rmtree(DST)
DST.mkdir(parents=True)

EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".claude", ".venv", ".git"}
EXCLUDE_FILES = {
    "0. 정리 - GlidePath 값.xlsx",
    "RegimeAnalysis_2602.xlsx",
    "ECI_Neo_202603.xlsx",
}
OUT_INCLUDE = {"db_review_relaxed_e62"}  # tdf_2060/out/ 중 포함할 것만

def ignore_func(dir_path, names):
    ignored = []
    dir_p = Path(dir_path)
    for name in names:
        if name in EXCLUDE_FILES or name.startswith("~$") or name in EXCLUDE_NAMES:
            ignored.append(name)
            continue
        if dir_p.name == "out" and dir_p.parent.name == "tdf_2060":
            if name not in OUT_INCLUDE:
                ignored.append(name)
    return ignored

shutil.copytree(SRC, DST, ignore=ignore_func, dirs_exist_ok=True)
print(f"staging done: {DST}")
print(f"files: {sum(1 for _ in DST.rglob('*') if _.is_file())}")