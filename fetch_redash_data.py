#!/usr/bin/env python3
"""
Redash BTS 포토카드 쿼리 결과를 가져와 bts_photocard_data.json에 저장합니다.
--analyze 옵션으로 페치 후 HTML까지 한 번에 생성할 수 있습니다.

환경변수:
  REDASH_API_KEY  - Redash API 키 (필수)
  REDASH_QUERY_ID - 쿼리 ID (기본: 23818)
  REDASH_BASE_URL - Redash URL (기본: https://redash.bunjang.io)

사용법:
  REDASH_API_KEY=your_key python fetch_redash_data.py
  REDASH_API_KEY=your_key python fetch_redash_data.py --analyze   # 페치 + HTML 생성
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    base = Path(__file__).resolve().parent
    load_dotenv(base / ".env") or load_dotenv(base / "fandom_dict" / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    print("[ERROR] requests 패키지 필요: pip install requests")
    sys.exit(1)

# 설정
REDASH_BASE = os.environ.get("REDASH_BASE_URL", "https://redash.bunjang.io")
REDASH_QUERY_ID = os.environ.get("REDASH_QUERY_ID", "23818")
REDASH_API_KEY = os.environ.get("REDASH_API_KEY")
DATA_FILE = Path(__file__).resolve().parent / "bts_photocard_data.json"


def fetch_redash_results():
    """Redash API에서 쿼리 결과 조회"""
    if not REDASH_API_KEY:
        print("[ERROR] REDASH_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  export REDASH_API_KEY=your_api_key")
        print("  또는 .env 파일에 REDASH_API_KEY=your_api_key 추가")
        sys.exit(1)

    url = f"{REDASH_BASE}/api/queries/{REDASH_QUERY_ID}/results.json"
    headers = {"Authorization": f"Key {REDASH_API_KEY}"}

    print(f"Redash 쿼리 결과 요청 중... (query_id={REDASH_QUERY_ID})")
    try:
        r = requests.get(url, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Redash API 요청 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  응답: {e.response.text[:500]}")
        sys.exit(1)

    if "query_result" not in data:
        print("[ERROR] 응답 형식 오류: query_result 없음")
        sys.exit(1)

    rows = data.get("query_result", {}).get("data", {}).get("rows", [])
    print(f"  → {len(rows):,}개 상품 로드됨")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"저장 완료: {DATA_FILE}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Redash BTS 포토카드 데이터 페치")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="페치 후 bts_photocard_analyzer 실행하여 HTML 생성",
    )
    args = parser.parse_args()

    fetch_redash_results()

    if args.analyze:
        print("\nHTML 생성 중...")
        script_dir = Path(__file__).resolve().parent
        analyzer = script_dir / "bts_photocard_analyzer.py"
        result = subprocess.run(
            [sys.executable, str(analyzer)],
            cwd=str(script_dir),
        )
        if result.returncode != 0:
            sys.exit(result.returncode)
        print("\n업데이트 완료: 데이터 + HTML")


if __name__ == "__main__":
    main()
