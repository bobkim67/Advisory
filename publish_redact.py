import re
from pathlib import Path

STAGING = Path(r"C:\Users\user\Downloads\python\_publish_advisory")

# 14개 후보 파일 — Grep 결과 + CLAUDE.md
TARGETS = [
    "tdf_2060/CLAUDE.md",  # CLAUDE.md 도 있다면
    "tdf_2060/tdf_engine/tools/build_portfolio.py",
    "tdf_2060/tdf_engine/tools/inspect_db_sources.py",
    "tdf_2060/tdf_engine/reporting/taa_tilt.py",
    "tdf_2060/tdf_engine/config/asset_mapping.yaml",
    "tdf_2060/config_draft/asset_mapping_draft.yaml",
    "tdf_2060/docs/phase_e_output_visualization_redesign.md",
    "tdf_2060/docs/phase_d_decision_brief.md",
    "tdf_2060/docs/phase_c_db_repository.md",
    "tdf_2060/docs/db_schema.md",
    "tdf_2060/docs/tdf_2060_tech_spec.md",
    "tdf_2060/source_review/mvo_source_review.md",
    "research/deep-research-report.md",
    "research/Gemini",
    "research/compass_artifact_wf-d07e5485-2c81-4424-a5df-2d6181dcf459_text_markdown.md",
]

# python/CLAUDE.md 상위 (포함 안 됨 — Advisory/ 가 root 이므로 OK)

PATTERNS = [
    (r"Solution123!", r"${DB_PASSWORD}"),
    (r"192\.168\.195\.55", r"${DB_HOST}"),
    (r"FWC2IZWA5YD459SQ7RJM", r"${ECOS_API_KEY}"),
    # solution 단어는 일반 단어이므로 신중 — yaml/yaml 등 context 에서만
    (r"user=['\"]?solution['\"]?", r"user=${DB_USER}"),
    (r"'solution'", r"'${DB_USER}'"),
    (r'"solution"', r'"${DB_USER}"'),
    (r"sk-[A-Za-z0-9]{20,}", r"${OPENAI_API_KEY}"),
]

modified = []
for rel in TARGETS:
    p = STAGING / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    orig = text
    for pat, repl in PATTERNS:
        text = re.sub(pat, repl, text)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        modified.append(rel)

print(f"modified {len(modified)} files:")
for m in modified:
    print(f"  - {m}")

# 추가 안전 grep 검증
print("\n--- post-redact verification (should be 0 hits) ---")
for pat_label in ("Solution123!", "192.168.195.55", "FWC2IZWA5YD459SQ7RJM"):
    hits = []
    for f in STAGING.rglob("*"):
        if not f.is_file() or f.suffix in (".png", ".pyc", ".xlsx"):
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if pat_label in t:
                hits.append(str(f.relative_to(STAGING)))
        except Exception:
            pass
    print(f"  {pat_label}: {len(hits)} hits")
    for h in hits[:5]:
        print(f"    {h}")