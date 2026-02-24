"""
eBay K-pop 굿즈 검색 결과 수집 (API 불필요, 스크래핑만 사용)
- 검색어별 상품 제목 수집 → 원본 용어 추출에 활용
- 수집 결과: data/raw/ebay_raw.json

주의: eBay robots.txt 및 이용약관 확인 후 사용. 적절한 딜레이 유지.
"""

import json
import os
import time
from typing import Optional
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
}

# K-pop 굿즈 검색어 (영어)
SEARCH_QUERIES = [
    "kpop photocard",
    "kpop pob",
    "bts photocard",
    "blackpink photocard",
    "kpop album",
    "kpop lightstick",
]

MAX_PAGES_PER_QUERY = 2  # 검색어당 최대 페이지 수
PAGE_SIZE = 48
DELAY_SEC = 2.0  # 요청 간격 (과도한 요청 방지)


def fetch_page(url: str, session: requests.Session) -> Optional[str]:
    """페이지 HTML 가져오기"""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"    [WARN] 요청 실패: {e}")
    return None


def extract_titles_from_html(html: str, query: str) -> list[dict]:
    """eBay 검색 결과 HTML에서 상품 제목 추출"""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # eBay 검색 결과 구조 (변경될 수 있음)
    # .s-item__title 또는 [class*="s-item__title"]
    for el in soup.select(".s-item__title, [class*='s-item__title']"):
        title = el.get_text(strip=True)
        if title and len(title) > 3 and "Shop on eBay" not in title:
            items.append({
                "title": title,
                "query": query,
                "collected_at": datetime.now(tz=timezone.utc).isoformat(),
            })
    return items


def crawl_ebay(output_path: str = "data/raw/ebay_raw.json") -> list[dict]:
    """
    eBay K-pop 굿즈 검색 결과 수집
    Returns: 수집된 상품 제목 리스트
    """
    print("[ebay_crawler] eBay 수집 시작 (API 불필요)...")

    session = requests.Session()
    all_items = []

    for query in SEARCH_QUERIES:
        print(f"  검색: '{query}'")
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            # eBay 검색 URL (국가별 도메인은 .com 사용)
            url = (
                f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(query)}"
                f"&_pgn={page}"
            )
            html = fetch_page(url, session)
            if html:
                items = extract_titles_from_html(html, query)
                all_items.extend(items)
                print(f"    페이지 {page}: {len(items)}개 수집")
            time.sleep(DELAY_SEC)

    # 중복 제목 제거 (query는 유지)
    seen = set()
    unique = []
    for item in all_items:
        t = item["title"]
        if t not in seen:
            seen.add(t)
            unique.append(item)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"[ebay_crawler] 완료: {len(unique)}개 상품 제목 → {output_path}")
    return unique


if __name__ == "__main__":
    crawl_ebay()
