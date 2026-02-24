"""
STEP 4: Claude API로 원문 텍스트에서 신조어/약어 추출 및 분류
- Reddit, 위버스샵 원문 텍스트를 Claude API로 처리
- STEP 1 결과(claude_seed.json)와 중복 항목은 confidence를 "verified"로 업데이트
- 신규 항목만 추가
- 결과: data/raw/classified.json 저장
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    """Claude API 클라이언트 (Reddit 처리 시에만 사용, lazy 로드)"""
    global _client
    if _client is None:
        try:
            from anthropic import Anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            _client = Anthropic(api_key=key) if key else None
        except Exception:
            _client = None
    return _client

# 청킹 크기 (문자 수)
CHUNK_SIZE = 500
# 청크당 API 호출 간격 (초)
API_DELAY = 0.8
WEVERSE_SOURCE = "weverse"
REDDIT_SOURCE = "reddit"
EBAY_SOURCE = "ebay"

# eBay 규칙 기반 추출용: 2~6자 영문 대문자 약어 패턴
ABBREV_PATTERN = re.compile(r"\b[A-Z]{2,6}\b")


CLASSIFY_SYSTEM_PROMPT = """당신은 K-pop 굿즈 거래 전문 언어 분석가입니다.
주어진 텍스트에서 K-pop 굿즈 거래 관련 신조어, 약어, 아이돌 그룹/멤버 약칭을 추출합니다.
일반적인 영어 단어나 문법어는 추출하지 마세요.
반드시 JSON 배열만 응답하고 다른 텍스트는 포함하지 마세요."""

CLASSIFY_PROMPT_TEMPLATE = """아래 텍스트에서 K-pop 굿즈 거래 관련 신조어/약어/아이돌 약칭만 추출해줘.

텍스트:
{text}

각 항목을 아래 JSON 구조로 추출해줘. 해당 없으면 null로 표기.
term_type은 "slang"(신조어), "abbreviation"(약어), "standard"(표준어), "typo"(오타추정) 중 하나.
goods_type은 "포토카드", "슬로건", "공식MD", "앨범", "응원봉", "기타", null 중 하나.
confidence는 "high"(명확), "medium"(보통), "low"(불확실) 중 하나.

[
  {{
    "original_term": "추출된 용어",
    "language": "ko/en/mixed",
    "term_type": "slang/abbreviation/standard/typo",
    "standard_ko": "표준 한국어 표현",
    "standard_en": "표준 영어 표현",
    "group": "관련 그룹명 또는 null",
    "member": "관련 멤버명 또는 null",
    "goods_type": "굿즈유형 또는 null",
    "source": "{source}",
    "confidence": "high/medium/low"
  }}
]

K-pop과 무관한 일반 단어(the, is, a, and, 등)는 제외해줘.
K-pop 굿즈 거래에 특화된 용어만 추출해줘."""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """텍스트를 chunk_size 단위로 분할 (단어 경계 존중)"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        # 공백에서 자르기
        space_pos = text.rfind(" ", start, end)
        if space_pos > start:
            end = space_pos
        chunks.append(text[start:end])
        start = end
    return chunks


def parse_json_response(text: str) -> list[dict]:
    """LLM 응답에서 JSON 배열 파싱"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return []


def extract_terms_from_chunk(text: str, source: str) -> list[dict]:
    """단일 청크에서 신조어/약어 추출 (Claude API 사용)"""
    client = _get_client()
    if not client:
        return []
    prompt = CLASSIFY_PROMPT_TEMPLATE.format(text=text, source=source)
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=CLASSIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json_response(response.content[0].text)
    except Exception as e:
        print(f"    [ERROR] API 호출 실패: {e}")
        return []


def _extract_terms_rulebased(text: str, seed_lookup: dict) -> list[dict]:
    """텍스트에서 규칙 기반 용어 추출 (Claude 없이)"""
    terms = []
    seen = set()
    tokens = re.findall(r"[A-Za-z가-힣0-9]+", text)
    for token in tokens:
        if len(token) < 2:
            continue
        key = token.lower()
        if key in seen:
            continue
        if key in seed_lookup:
            mapped = seed_lookup[key]
            terms.append({
                "original_term": token,
                "language": "en" if token.isascii() else "ko",
                "term_type": mapped.get("term_type", "abbreviation"),
                "standard_ko": mapped["standard_ko"],
                "standard_en": mapped["standard_en"],
                "group": mapped.get("group"),
                "member": mapped.get("member"),
                "goods_type": mapped.get("goods_type"),
                "source": REDDIT_SOURCE,
                "confidence": "verified",
            })
            seen.add(key)
        elif re.match(r"^[A-Z]{2,6}$", token):
            terms.append({
                "original_term": token,
                "language": "en",
                "term_type": "abbreviation",
                "standard_ko": "",
                "standard_en": token,
                "group": None,
                "member": None,
                "goods_type": None,
                "source": REDDIT_SOURCE,
                "confidence": "low",
            })
            seen.add(key)
    return terms


def process_reddit_posts(posts: list[dict], seed_lookup: Optional[dict] = None) -> list[dict]:
    """Reddit 게시물에서 신조어 추출 (Claude 있으면 LLM, 없으면 규칙 기반)"""
    trade_posts = [p for p in posts if p.get("is_trade_post")]
    other_posts = [p for p in posts if not p.get("is_trade_post")]
    target_posts = trade_posts + other_posts[:100]
    print(f"  Reddit 처리: 거래글 {len(trade_posts)}개 + 일반글 {min(len(other_posts), 100)}개 = {len(target_posts)}개")

    use_claude = _get_client() is not None
    if use_claude:
        print(f"    → Claude API로 추출")
    else:
        print(f"    → 규칙 기반 추출 (API 불필요)")
        seed_lookup = seed_lookup or {}

    all_terms = []
    for i, post in enumerate(target_posts):
        full_text = post.get("title", "") + "\n" + post.get("selftext", "")
        comments = post.get("top_comments", [])
        if comments:
            full_text += "\n" + "\n".join(comments[:10])
        if len(full_text.strip()) < 10:
            continue

        if use_claude:
            chunks = chunk_text(full_text)
            for chunk in chunks:
                for t in extract_terms_from_chunk(chunk, REDDIT_SOURCE):
                    t["source"] = REDDIT_SOURCE
                    all_terms.append(t)
                time.sleep(API_DELAY)
        else:
            for t in _extract_terms_rulebased(full_text, seed_lookup):
                all_terms.append(t)

        if (i + 1) % 20 == 0:
            print(f"    진행: {i+1}/{len(target_posts)} (추출 {len(all_terms)}개)")

    return all_terms


def process_ebay_titles(ebay_items: list[dict], seed_lookup: dict) -> list[dict]:
    """
    eBay 상품 제목에서 용어 추출 (Claude 없이 규칙 기반)
    - 시드에 있는 용어 발견 시 매핑 적용
    - 2~6자 대문자 약어(WTS, POB 등) 추출 → 신규 시 confidence=low
    """
    terms = []
    seen = set()

    for item in ebay_items:
        title = item.get("title", "")
        if len(title) < 5:
            continue

        # 단어 단위로 분리 (공백, 괄호, 슬래시 등)
        tokens = re.findall(r"[A-Za-z가-힣0-9]+", title)

        for token in tokens:
            if len(token) < 2:
                continue
            key = token.lower()
            if key in seen:
                continue

            # 시드에 있으면 매핑 적용
            if key in seed_lookup:
                mapped = seed_lookup[key]
                terms.append({
                    "original_term": token,
                    "language": "en" if token.isascii() else "ko",
                    "term_type": mapped.get("term_type", "abbreviation"),
                    "standard_ko": mapped["standard_ko"],
                    "standard_en": mapped["standard_en"],
                    "group": mapped.get("group"),
                    "member": mapped.get("member"),
                    "goods_type": mapped.get("goods_type"),
                    "source": EBAY_SOURCE,
                    "confidence": "verified",
                })
                seen.add(key)
                continue

            # 2~6자 대문자 약어 추출 (시드에 없는 경우)
            if re.match(r"^[A-Z]{2,6}$", token):
                terms.append({
                    "original_term": token,
                    "language": "en",
                    "term_type": "abbreviation",
                    "standard_ko": "",
                    "standard_en": token,
                    "group": None,
                    "member": None,
                    "goods_type": None,
                    "source": EBAY_SOURCE,
                    "confidence": "low",
                })
                seen.add(key)

    return terms


def process_weverse_products(products: list[dict]) -> list[dict]:
    """
    위버스샵 상품을 표준어 항목으로 변환
    (Claude API 호출 없이 직접 변환 - 공식 명칭은 이미 표준어)
    """
    terms = []
    for p in products:
        name = p.get("product_name", "").strip()
        if not name:
            continue

        lang = p.get("language", "ko")
        # 한글 포함 여부로 언어 판별
        has_korean = any("\uAC00" <= c <= "\uD7A3" for c in name)
        has_english = any("a" <= c.lower() <= "z" for c in name)
        if has_korean and has_english:
            lang = "mixed"
        elif has_korean:
            lang = "ko"
        else:
            lang = "en"

        # 영어 이름이 있으면 활용
        en_name = p.get("product_name_en", name if lang == "en" else "")

        terms.append({
            "original_term": name,
            "language": lang,
            "term_type": "standard",
            "standard_ko": name if lang in ("ko", "mixed") else "",
            "standard_en": en_name or name,
            "group": p.get("artist_slug") if p.get("artist_slug") != "general" else None,
            "member": None,
            "goods_type": p.get("category"),
            "source": WEVERSE_SOURCE,
            "confidence": "high",
        })

    return terms


def merge_with_existing(
    new_terms: list[dict],
    existing_terms: list[dict],
) -> tuple[list[dict], int]:
    """
    기존 항목(claude_seed)과 신규 항목 병합
    - 중복 항목: confidence를 "verified"로 업데이트
    - 신규 항목만 추가
    Returns: (병합된 전체 목록, verified 업데이트 수)
    """
    # 기존 항목 인덱스 (original_term + language 기준)
    existing_map: dict[str, int] = {}
    merged = list(existing_terms)  # 복사본

    for i, entry in enumerate(merged):
        key = f"{entry['original_term'].lower()}_{entry['language']}"
        existing_map[key] = i

    verified_count = 0
    added_count = 0

    for term in new_terms:
        if not term.get("original_term"):
            continue

        key = f"{term['original_term'].lower()}_{term.get('language', 'ko')}"

        if key in existing_map:
            # 기존 항목 있으면 confidence만 verified로 업데이트
            idx = existing_map[key]
            merged[idx]["confidence"] = "verified"
            # 표준어 정보가 비어있으면 보완
            if not merged[idx].get("standard_en") and term.get("standard_en"):
                merged[idx]["standard_en"] = term["standard_en"]
            verified_count += 1
        else:
            # 신규 항목 추가
            term.setdefault("confidence", "medium")
            merged.append(term)
            existing_map[key] = len(merged) - 1
            added_count += 1

    print(f"  병합 결과: {verified_count}개 verified 업데이트, {added_count}개 신규 추가")
    return merged, verified_count


def validate_entry(entry: dict) -> bool:
    """유효한 항목인지 검증"""
    if not entry.get("original_term"):
        return False
    # 너무 짧거나 긴 용어 제외
    term = entry["original_term"]
    if len(term) < 2 or len(term) > 50:
        return False
    # 일반 영어 단어 필터 (너무 일반적인 것들)
    generic_words = {"the", "a", "an", "is", "are", "was", "were", "i", "you", "he", "she", "it", "we", "they"}
    if term.lower() in generic_words:
        return False
    return True


def classify(
    seed_path: str = "data/raw/claude_seed.json",
    reddit_path: str = "data/raw/reddit_raw.json",
    weverse_path: str = "data/raw/weverse_raw.json",
    output_path: str = "data/raw/classified.json",
) -> list[dict]:
    """
    전체 분류 파이프라인 실행
    Returns: 최종 병합된 항목 리스트
    """
    print("[classifier] 분류 파이프라인 시작")

    # ── STEP 4-1: 기존 씨드 로드 ──────────────────────────
    existing_terms: list[dict] = []
    if os.path.exists(seed_path):
        with open(seed_path, encoding="utf-8") as f:
            existing_terms = json.load(f)
        print(f"  씨드 사전 로드: {len(existing_terms)}개 항목")
    else:
        print(f"  [WARN] 씨드 사전 없음: {seed_path}")

    all_new_terms: list[dict] = []

    # ── STEP 4-2: 위버스샵 표준어 처리 ────────────────────
    if os.path.exists(weverse_path):
        with open(weverse_path, encoding="utf-8") as f:
            weverse_data = json.load(f)
        print(f"\n  위버스샵 데이터 처리: {len(weverse_data)}개 상품")
        weverse_terms = process_weverse_products(weverse_data)
        print(f"  → {len(weverse_terms)}개 표준어 변환")
        all_new_terms.extend(weverse_terms)
    else:
        print(f"  [WARN] 위버스샵 데이터 없음: {weverse_path}")

    # 시드 용어 룩업 (Reddit/eBay 규칙 기반 추출용)
    seed_lookup = {e.get("original_term", "").lower(): e for e in existing_terms if e.get("original_term")}

    # ── STEP 4-3: Reddit 원문 처리 ─────────────────────────
    if os.path.exists(reddit_path):
        with open(reddit_path, encoding="utf-8") as f:
            reddit_data = json.load(f)
        print(f"\n  Reddit 데이터 처리: {len(reddit_data)}개 게시물")
        reddit_terms = process_reddit_posts(reddit_data, seed_lookup=seed_lookup)
        reddit_terms = [t for t in reddit_terms if validate_entry(t)]
        print(f"  → {len(reddit_terms)}개 용어 추출")
        all_new_terms.extend(reddit_terms)
    else:
        print(f"  [INFO] Reddit 데이터 없음 (API 없이 실행 시 정상)")

    # ── STEP 4-3b: eBay 제목 처리 (Claude 없이 규칙 기반) ─
    ebay_path = os.path.join(os.path.dirname(seed_path), "ebay_raw.json")
    if os.path.exists(ebay_path):
        with open(ebay_path, encoding="utf-8") as f:
            ebay_data = json.load(f)
        print(f"\n  eBay 데이터 처리: {len(ebay_data)}개 제목 (규칙 기반, API 불필요)")
        ebay_terms = process_ebay_titles(ebay_data, seed_lookup)
        ebay_terms = [t for t in ebay_terms if validate_entry(t)]
        print(f"  → {len(ebay_terms)}개 용어 추출")
        all_new_terms.extend(ebay_terms)
    else:
        print(f"  [INFO] eBay 데이터 없음: {ebay_path}")

    # ── STEP 4-4: 기존 씨드와 병합 ────────────────────────
    print(f"\n  병합 시작: 기존 {len(existing_terms)}개 + 신규 {len(all_new_terms)}개")
    merged, verified_count = merge_with_existing(all_new_terms, existing_terms)

    # ── STEP 4-5: 결과 저장 ────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # 통계
    ko_count = sum(1 for t in merged if t.get("language") in ("ko", "mixed"))
    en_count = sum(1 for t in merged if t.get("language") in ("en", "mixed"))
    low_conf = sum(1 for t in merged if t.get("confidence") == "low")
    typo_count = sum(1 for t in merged if t.get("term_type") == "typo")
    review_count = low_conf + typo_count

    print(f"\n[classifier] 완료")
    print(f"  총 항목: {len(merged)}개")
    print(f"  KO/Mixed: {ko_count}개 | EN/Mixed: {en_count}개")
    print(f"  verified 업데이트: {verified_count}개")
    print(f"  검토 필요: {review_count}개 (low confidence + typo)")
    print(f"  저장: {output_path}")

    return merged


if __name__ == "__main__":
    result = classify()
    print(f"\n분류 완료: {len(result)}개 항목")
