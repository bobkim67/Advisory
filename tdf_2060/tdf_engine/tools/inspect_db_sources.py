"""SCIP back_dataset 후보 탐색 — read-only.

운영자가 db_sources.yaml::assets 의 dataset_id 를 채우기 전에
SCIP DB에서 매칭되는 dataset 을 검색하기 위한 CLI.

예:
  python -m tdf_engine.tools.inspect_db_sources --query "Treasury"
  python -m tdf_engine.tools.inspect_db_sources --query "30"
  python -m tdf_engine.tools.inspect_db_sources --query "High Yield"
  python -m tdf_engine.tools.inspect_db_sources --query "KIS"

옵션:
  --query KEYWORD       : back_dataset.name 또는 symbol 부분일치
  --dataset-id ID       : 특정 dataset 의 시리즈/시점 정보만 보기
  --top N               : 출력 row 수 제한 (default 30)
  --include-series      : 매칭 dataset 별 dataseries 정보도 함께 출력
  --semantic-guess      : 이름 기반 semantic_type 추정 표기

read-only. credential 은 build_portfolio 와 동일 환경변수 사용.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from typing import Any

logger = logging.getLogger(__name__)


# ── semantic guess 휴리스틱 ────────────────────────────────────────────


_GUESS_RULES = [
    # (regex, semantic_type, return_transform)
    (r"\bTotal\s+Return", "total_return_index", "pct_change"),
    (r"\bTR\b|\bTRI\b", "total_return_index", "pct_change"),
    (r"\bNAV\b", "nav", "pct_change"),
    (r"\bPrice\s+Index", "price_index", "pct_change"),
    (r"\bYield|\bYTM|\bUSGG\d|\bKPGB\d", "yield", "duration_proxy"),
    (r"\bSpread|\bOAS", "spread", "diff"),
    (r"\bCPI|\bGDP|\bUnemployment|\bInflation|\bMEI|\bCLI", "macro_indicator", "not_allowed"),
    (r"ETF|Vanguard|iShares|SPDR|Invesco", "nav", "pct_change"),
]


def guess_semantic(name: str) -> tuple[str | None, str | None]:
    if not name:
        return None, None
    for pattern, st, rt in _GUESS_RULES:
        if re.search(pattern, name, re.IGNORECASE):
            return st, rt
    return None, None


# ── DB query helpers ──────────────────────────────────────────────────


def _connect():
    """SCIP 접속. credential 은 환경변수."""
    import pymysql

    return pymysql.connect(
        host=os.environ.get("TDF_DB_HOST", "${DB_HOST}"),
        user=os.environ.get("TDF_DB_USER", \"${DB_USER}\"),
        password=os.environ.get("TDF_DB_PASSWORD", "${DB_PASSWORD}"),
        db=os.environ.get("TDF_DB_NAME", "SCIP"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def search_datasets(conn, query: str, top: int = 30) -> list[dict]:
    """back_dataset.name LIKE / symbol LIKE / ISIN LIKE 검색."""
    like = f"%{query}%"
    sql = """
        SELECT id, name, ISIN, symbol
        FROM back_dataset
        WHERE name LIKE %s OR symbol LIKE %s OR ISIN LIKE %s
        ORDER BY id
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (like, like, like, int(top)))
        return list(cur.fetchall())


def dataset_series_info(conn, dataset_id: int) -> list[dict]:
    """해당 dataset 의 dataseries 별 row count + start/end date + sample."""
    sql_series = """
        SELECT DISTINCT dp.dataseries_id, ds.name AS dataseries_name
        FROM back_datapoint dp
        JOIN back_dataseries ds ON dp.dataseries_id = ds.id
        WHERE dp.dataset_id = %s
        ORDER BY dp.dataseries_id
    """
    with conn.cursor() as cur:
        cur.execute(sql_series, (int(dataset_id),))
        series_rows = list(cur.fetchall())

    out: list[dict] = []
    for sr in series_rows:
        sr_id = int(sr["dataseries_id"])
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MIN(timestamp_observation) AS start_date,
                       MAX(timestamp_observation) AS end_date,
                       COUNT(*) AS row_count
                FROM back_datapoint
                WHERE dataset_id = %s AND dataseries_id = %s
                """,
                (int(dataset_id), sr_id),
            )
            stats = cur.fetchone()
            cur.execute(
                """
                SELECT timestamp_observation, data
                FROM back_datapoint
                WHERE dataset_id = %s AND dataseries_id = %s
                ORDER BY timestamp_observation DESC
                LIMIT 3
                """,
                (int(dataset_id), sr_id),
            )
            samples = list(cur.fetchall())
        from tdf_engine.repositories._blob import parse_data_blob

        parsed_samples = []
        for s in samples:
            v = None
            try:
                v = parse_data_blob(s["data"])
            except Exception:
                v = "<parse_error>"
            parsed_samples.append({"date": str(s["timestamp_observation"]), "value": v})

        out.append(
            {
                "dataseries_id": sr_id,
                "dataseries_name": sr["dataseries_name"],
                "start_date": str(stats["start_date"]) if stats["start_date"] else None,
                "end_date": str(stats["end_date"]) if stats["end_date"] else None,
                "row_count": int(stats["row_count"]),
                "sample_recent": parsed_samples,
            }
        )
    return out


# ── 출력 ──────────────────────────────────────────────────────────────


def format_dataset_table(datasets: list[dict], with_guess: bool = True) -> str:
    lines = []
    if not datasets:
        return "(no match)"
    header = ["id", "name", "ISIN", "symbol"]
    if with_guess:
        header.extend(["semantic_guess", "transform_guess"])
    widths = [4, 50, 14, 18, 22, 18]
    lines.append(" | ".join(h.ljust(w) for h, w in zip(header, widths)))
    lines.append("-+-".join("-" * w for w in widths))
    for d in datasets:
        st, rt = (None, None)
        if with_guess:
            st, rt = guess_semantic(d.get("name") or "")
        row = [
            str(d.get("id", ""))[:widths[0]].ljust(widths[0]),
            (d.get("name") or "")[:widths[1]].ljust(widths[1]),
            (d.get("ISIN") or "-")[:widths[2]].ljust(widths[2]),
            (d.get("symbol") or "-")[:widths[3]].ljust(widths[3]),
        ]
        if with_guess:
            row.append((st or "-")[:widths[4]].ljust(widths[4]))
            row.append((rt or "-")[:widths[5]].ljust(widths[5]))
        lines.append(" | ".join(row))
    return "\n".join(lines)


def format_series_section(dataset: dict, series: list[dict]) -> str:
    lines = [
        "",
        f"=== dataset_id={dataset['id']} name={dataset.get('name')} ===",
        f"    ISIN={dataset.get('ISIN') or '-'}  symbol={dataset.get('symbol') or '-'}",
        "    --- series ---",
    ]
    for s in series:
        lines.append(
            f"    [series {s['dataseries_id']:>3} {s['dataseries_name'][:40]:<40}] "
            f"rows={s['row_count']:>8} {s['start_date']} ~ {s['end_date']}"
        )
        for sm in s["sample_recent"]:
            lines.append(f"      sample {sm['date']}: {sm['value']}")
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCIP back_dataset 후보 탐색 (read-only)")
    parser.add_argument("--query", type=str, default=None,
                        help="back_dataset.name / symbol / ISIN 부분일치 키워드")
    parser.add_argument("--dataset-id", type=int, default=None,
                        help="특정 dataset id 의 series 정보만 출력")
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--include-series", action="store_true",
                        help="매칭 dataset 별 dataseries/sample 까지 출력")
    parser.add_argument("--no-semantic-guess", action="store_true",
                        help="semantic_type 추정 컬럼 숨김")
    args = parser.parse_args(argv)

    if args.query is None and args.dataset_id is None:
        parser.error("--query 또는 --dataset-id 중 하나는 필수")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        conn = _connect()
    except Exception as e:
        print(f"[error] DB 접속 실패: {e}\n"
              f"        host/credential 환경변수 (TDF_DB_HOST/USER/PASSWORD/NAME) 확인.",
              file=sys.stderr)
        return 2

    try:
        if args.query:
            datasets = search_datasets(conn, args.query, top=args.top)
            print(format_dataset_table(datasets, with_guess=not args.no_semantic_guess))
            if args.include_series:
                for d in datasets:
                    series = dataset_series_info(conn, int(d["id"]))
                    print(format_series_section(d, series))
        elif args.dataset_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, ISIN, symbol FROM back_dataset WHERE id = %s",
                    (int(args.dataset_id),),
                )
                d = cur.fetchone()
            if not d:
                print(f"[error] dataset_id={args.dataset_id} 미존재", file=sys.stderr)
                return 1
            print(format_dataset_table([d], with_guess=not args.no_semantic_guess))
            series = dataset_series_info(conn, int(args.dataset_id))
            print(format_series_section(d, series))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
