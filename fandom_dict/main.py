"""
Fandom Query Dictionary 자동 구축 파이프라인
실행: python main.py [--skip-seed] [--skip-reddit] [--skip-weverse] [--skip-classify] [--skip-upload]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def print_banner():
    print("=" * 60)
    print("  Fandom Query Dictionary Builder")
    print("  K-pop 굿즈 팬덤 언어 ↔ 표준어 매핑 사전 자동 구축")
    print("=" * 60)
    print()


def print_summary(seed_data, reddit_data, weverse_data, classified_data):
    """최종 요약 출력"""
    print("\n" + "=" * 60)
    print("  실행 완료 요약")
    print("=" * 60)

    total = len(classified_data) if classified_data else 0

    # 소스별 집계
    source_counts = {}
    lang_counts = {"ko": 0, "en": 0, "mixed": 0}
    review_count = 0

    for entry in (classified_data or []):
        src = entry.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

        lang = entry.get("language", "")
        if lang in lang_counts:
            lang_counts[lang] += 1

        if entry.get("confidence") == "low" or entry.get("term_type") == "typo":
            review_count += 1

    print(f"\n  총 수집 항목: {total}개")
    print("\n  소스별 항목:")
    for src, cnt in sorted(source_counts.items()):
        print(f"    - {src}: {cnt}개")

    print("\n  언어별 항목:")
    print(f"    - KO(한국어):  {lang_counts['ko']}개")
    print(f"    - EN(영어):    {lang_counts['en']}개")
    print(f"    - Mixed(혼합): {lang_counts['mixed']}개")

    print(f"\n  검토 필요 항목: {review_count}개")
    print("=" * 60)


def check_env(skip_seed: bool, skip_reddit: bool):
    """
    필수 환경변수 확인.
    - Claude: STEP 1(씨드 생성)에서만 필요. --skip-seed 시 정적 시드 사용.
    - Reddit: API 불필요 (JSON 피드). 분류는 Claude 있으면 LLM, 없으면 규칙 기반.
    """
    if not skip_seed and not os.environ.get("ANTHROPIC_API_KEY"):
        print("[ERROR] 시드 생성에 Claude API 필요: ANTHROPIC_API_KEY")
        print("  .env에 추가하거나 --skip-seed 로 정적 시드 사용.")
        return False
    return True


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="팬덤 사전 자동 구축 파이프라인")
    parser.add_argument("--skip-seed", action="store_true", help="STEP 1 (Claude) 건너뛰기 → 정적 시드 사용")
    parser.add_argument("--skip-weverse", action="store_true", help="STEP 2 (위버스샵) 건너뛰기")
    parser.add_argument("--skip-reddit", action="store_true", help="STEP 3 (Reddit) 건너뛰기")
    parser.add_argument("--ebay", action="store_true", help="eBay 수집 추가 (API 불필요)")
    parser.add_argument("--skip-classify", action="store_true", help="STEP 4 (분류) 건너뛰기")
    parser.add_argument("--skip-upload", action="store_true", help="STEP 5 (시트 업로드) 건너뛰기")
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="데이터 저장 디렉토리 (기본: data/raw)",
    )
    args = parser.parse_args()

    # .env 로드
    from dotenv import load_dotenv
    load_dotenv()

    if not check_env(args.skip_seed, args.skip_reddit):
        sys.exit(1)

    os.makedirs(args.data_dir, exist_ok=True)

    data_dir = args.data_dir
    seed_path = os.path.join(data_dir, "claude_seed.json")
    static_seed_path = os.path.join(data_dir, "static_seed.json")
    reddit_path = os.path.join(data_dir, "reddit_raw.json")
    ebay_path = os.path.join(data_dir, "ebay_raw.json")
    weverse_path = os.path.join(data_dir, "weverse_raw.json")
    classified_path = os.path.join(data_dir, "classified.json")

    seed_data = []
    reddit_data = []
    weverse_data = []
    classified_data = []

    # ── STEP 1: 시드 사전 (Claude API 또는 정적 시드) ───────
    if not args.skip_seed:
        print("\n[STEP 1/5] Claude API 초기 사전 생성")
        print("-" * 40)
        from generators.claude_seed import generate_seed_dictionary
        seed_data = generate_seed_dictionary(output_path=seed_path)
    else:
        print("\n[STEP 1/5] 건너뜀 (--skip-seed)")
        # claude_seed 없거나 비어있으면 static_seed 사용 (API 없이 바로 실행 가능)
        if os.path.exists(seed_path):
            with open(seed_path, encoding="utf-8") as f:
                seed_data = json.load(f)
        if not seed_data and os.path.exists(static_seed_path):
            print(f"  claude_seed 비어있음 → 정적 시드 사용 (API 불필요)")
            with open(static_seed_path, encoding="utf-8") as f:
                seed_data = json.load(f)
            seed_path = static_seed_path  # classifier가 이 파일 사용
        print(f"  시드 로드: {len(seed_data)}개 항목")

    # ── STEP 2: 위버스샵 크롤링 ────────────────────────────
    if not args.skip_weverse:
        print("\n[STEP 2/5] 위버스샵 상품명 수집")
        print("-" * 40)
        from crawlers.weverse_crawler import crawl_weverse
        weverse_data = crawl_weverse(output_path=weverse_path)
    else:
        print("\n[STEP 2/5] 건너뜀 (--skip-weverse)")
        if os.path.exists(weverse_path):
            with open(weverse_path, encoding="utf-8") as f:
                weverse_data = json.load(f)
            print(f"  기존 파일 로드: {len(weverse_data)}개 항목")

    # ── STEP 3: Reddit 크롤링 (API 불필요, JSON 피드 사용) ───
    if not args.skip_reddit:
        print("\n[STEP 3/5] Reddit 크롤링 (API 키 불필요)")
        print("-" * 40)
        from crawlers.reddit_crawler import crawl_reddit
        reddit_data = crawl_reddit(output_path=reddit_path)
    else:
        print("\n[STEP 3/5] 건너뜀 (--skip-reddit)")
        if os.path.exists(reddit_path):
            with open(reddit_path, encoding="utf-8") as f:
                reddit_data = json.load(f)
            print(f"  기존 파일 로드: {len(reddit_data)}개 항목")

    # ── STEP 2.5: eBay 수집 (선택, API 불필요) ─────────────────
    if args.ebay:
        print("\n[STEP 2.5] eBay 상품 제목 수집 (API 불필요)")
        print("-" * 40)
        from crawlers.ebay_crawler import crawl_ebay
        crawl_ebay(output_path=ebay_path)

    # ── STEP 4: 분류 ───────────────────────────────────────
    if not args.skip_classify:
        print("\n[STEP 4/5] 신조어 추출 및 분류")
        print("-" * 40)
        from classifier import classify
        classified_data = classify(
            seed_path=seed_path,
            reddit_path=reddit_path,
            weverse_path=weverse_path,
            output_path=classified_path,
        )
    else:
        print("\n[STEP 4/5] 건너뜀 (--skip-classify)")
        if os.path.exists(classified_path):
            with open(classified_path, encoding="utf-8") as f:
                classified_data = json.load(f)
            print(f"  기존 파일 로드: {len(classified_data)}개 항목")

    # ── STEP 5: 구글 시트 업로드 ───────────────────────────
    if not args.skip_upload:
        print("\n[STEP 5/5] 구글 시트 업데이트")
        print("-" * 40)
        sheet_env_ok = bool(os.environ.get("GOOGLE_SHEET_ID"))
        creds_ok = os.path.exists("credentials.json")

        if not sheet_env_ok:
            print("  [WARN] GOOGLE_SHEET_ID 미설정 → STEP 5 건너뜀")
            print("  .env에 GOOGLE_SHEET_ID=<시트ID> 추가 후 재실행")
        elif not creds_ok:
            print("  [WARN] credentials.json 없음 → STEP 5 건너뜀")
            print("  구글 서비스 계정 설정 방법은 sheets_uploader.py 상단 참고")
        else:
            from sheets_uploader import upload_all
            try:
                upload_stats = upload_all(
                    classified_path=classified_path,
                    creds_path="credentials.json",
                )
            except Exception as e:
                print(f"  [ERROR] 시트 업로드 실패: {e}")
    else:
        print("\n[STEP 5/5] 건너뜀 (--skip-upload)")

    # ── 최종 요약 ──────────────────────────────────────────
    print_summary(seed_data, reddit_data, weverse_data, classified_data)


if __name__ == "__main__":
    main()
