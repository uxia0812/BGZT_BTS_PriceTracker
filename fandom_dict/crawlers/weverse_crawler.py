"""
STEP 3: 위버스샵 상품명 수집
- shop.weverse.io에서 공식 MD 명칭 수집
- 공식 표준어 기준점 확보용
- 수집 원문: data/raw/weverse_raw.json 저장

참고:
  위버스샵은 SPA(Single Page App)로 직접 HTML 파싱이 어렵습니다.
  이 크롤러는 두 가지 방식을 시도합니다:
  1. 공개 API 엔드포인트 탐색
  2. requests + BeautifulSoup으로 정적 HTML 파싱 (일부 페이지)
  JavaScript 렌더링이 필요한 경우 Playwright 방식도 주석으로 제공합니다.
"""

import json
import os
import time
from typing import Optional
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://shop.weverse.io/",
}

# 수집 대상 아티스트 슬러그 (위버스샵 URL 기준)
ARTIST_SLUGS = [
    "bts",
    "blackpink",
    "newjeans",
    "aespa",
    "lesserafim",
    "ive",
    "seventeen",
    "straykids",
    "enhypen",
    "txt",
    "nct-dream",
    "taeyeon",
    "ateez",
    "monsta-x",
    "got7",
]

BASE_URL = "https://shop.weverse.io"

# 위버스샵 내부 API (비공식, 변경될 수 있음)
API_BASE = "https://weverse-shop-api.weverse.io"


def fetch_with_retry(url: str, session: requests.Session, retries: int = 3, delay: float = 2.0) -> Optional[requests.Response]:
    """재시도 포함 HTTP GET"""
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                wait = delay * (attempt + 1) * 2
                print(f"    [RATE LIMIT] {wait}초 대기 후 재시도...")
                time.sleep(wait)
            elif resp.status_code in (403, 404):
                return None
            else:
                time.sleep(delay)
        except requests.RequestException as e:
            print(f"    [WARN] 요청 실패 (시도 {attempt+1}/{retries}): {e}")
            time.sleep(delay)
    return None


def parse_product_from_html(html: str, artist_slug: str) -> list[dict]:
    """HTML에서 상품 정보 추출 (정적 렌더링된 경우)"""
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # 상품명이 포함될 수 있는 일반적인 선택자들 시도
    selectors = [
        "span.ProductName",
        "p.product-name",
        "div.product-title",
        "[class*='productName']",
        "[class*='product_name']",
        "[class*='item-name']",
        "h2.title",
        "h3.title",
    ]

    found_names = set()
    for selector in selectors:
        for el in soup.select(selector):
            name = el.get_text(strip=True)
            if name and len(name) > 2 and name not in found_names:
                found_names.add(name)
                products.append({
                    "product_name": name,
                    "artist_slug": artist_slug,
                    "category": None,
                    "source_url": f"{BASE_URL}/en/artist/{artist_slug}",
                    "language": "ko" if any("\uAC00" <= c <= "\uD7A3" for c in name) else "en",
                    "collected_at": datetime.now(tz=timezone.utc).isoformat(),
                })

    return products


def scrape_artist_page(session: requests.Session, artist_slug: str) -> list[dict]:
    """아티스트 상품 페이지 스크래핑"""
    products = []

    # 한국어/영어 페이지 모두 시도
    for lang_path in [f"/ko/artist/{artist_slug}", f"/en/artist/{artist_slug}"]:
        url = f"{BASE_URL}{lang_path}"
        resp = fetch_with_retry(url, session)
        if not resp:
            continue

        parsed = parse_product_from_html(resp.text, artist_slug)
        products.extend(parsed)
        time.sleep(1.5)

    return products


def scrape_sitemap_products(session: requests.Session) -> list[dict]:
    """
    사이트맵에서 상품 URL 수집 후 상품명 추출
    위버스샵이 sitemap.xml을 제공하는 경우 활용
    """
    products = []
    sitemap_urls = [
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/sitemap-ko.xml",
        f"{BASE_URL}/sitemap-en.xml",
    ]

    for sitemap_url in sitemap_urls:
        resp = fetch_with_retry(sitemap_url, session)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "xml")
        locs = [loc.get_text() for loc in soup.find_all("loc")]
        print(f"    사이트맵 {sitemap_url}: {len(locs)}개 URL 발견")

        # 상품 URL 필터링 (product 포함)
        product_urls = [u for u in locs if "/product/" in u or "/item/" in u]
        print(f"    → 상품 URL: {len(product_urls)}개")

        for i, url in enumerate(product_urls[:200]):  # 최대 200개
            resp = fetch_with_retry(url, session)
            if not resp:
                continue

            soup_page = BeautifulSoup(resp.text, "html.parser")

            # og:title 메타태그에서 상품명 추출
            og_title = soup_page.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                name = og_title["content"].strip()
                if name:
                    products.append({
                        "product_name": name,
                        "artist_slug": "unknown",
                        "category": None,
                        "source_url": url,
                        "language": "ko" if any("\uAC00" <= c <= "\uD7A3" for c in name) else "en",
                        "collected_at": datetime.now(tz=timezone.utc).isoformat(),
                    })

            if i % 20 == 0:
                print(f"    진행: {i+1}/{min(len(product_urls), 200)}")
            time.sleep(0.8)

        break  # 첫 번째 성공한 sitemap만 처리

    return products


def build_manual_standard_terms() -> list[dict]:
    """
    웹 스크래핑이 제한될 때를 대비한 공식 굿즈 표준어 기본 목록
    위버스샵에서 공통적으로 사용하는 공식 카테고리/상품 유형 명칭
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    terms = [
        # 포토카드 관련
        ("포토카드", "Photocard", "포토카드"),
        ("랜덤 포토카드", "Random Photocard", "포토카드"),
        ("유닛 포토카드", "Unit Photocard", "포토카드"),
        ("그룹 포토카드", "Group Photocard", "포토카드"),
        ("멤버 포토카드", "Member Photocard", "포토카드"),
        # 응원봉
        ("공식 응원봉", "Official Light Stick", "응원봉"),
        ("응원봉", "Light Stick", "응원봉"),
        ("응원봉 스트랩", "Light Stick Strap", "응원봉"),
        # 앨범
        ("미니 앨범", "Mini Album", "앨범"),
        ("정규 앨범", "Full Album", "앨범"),
        ("리패키지 앨범", "Repackage Album", "앨범"),
        ("싱글 앨범", "Single Album", "앨범"),
        ("스페셜 앨범", "Special Album", "앨범"),
        # MD
        ("키링", "Key Ring", "공식MD"),
        ("폰케이스", "Phone Case", "공식MD"),
        ("파우치", "Pouch", "공식MD"),
        ("에코백", "Eco Bag", "공식MD"),
        ("슬로건", "Slogan", "슬로건"),
        ("타월 슬로건", "Towel Slogan", "슬로건"),
        ("미니 슬로건", "Mini Slogan", "슬로건"),
        ("뱃지", "Badge", "공식MD"),
        ("핀 버튼", "Pin Button", "공식MD"),
        ("스티커", "Sticker", "공식MD"),
        ("아크릴 스탠드", "Acrylic Stand", "공식MD"),
        ("아크릴 키링", "Acrylic Key Ring", "공식MD"),
        ("엽서", "Postcard", "공식MD"),
        ("포스터", "Poster", "공식MD"),
        ("티셔츠", "T-Shirt", "공식MD"),
        ("후드티", "Hoodie", "공식MD"),
        ("모자", "Cap / Hat", "공식MD"),
        ("담요", "Blanket", "공식MD"),
        ("머그컵", "Mug", "공식MD"),
        # 시즌 상품
        ("시즌 그리팅", "Season's Greetings", "공식MD"),
        ("미니 데스크 캘린더", "Mini Desk Calendar", "공식MD"),
        ("다이어리", "Diary", "공식MD"),
        ("포토북", "Photobook", "공식MD"),
        # 특전
        ("선주문 특전", "Pre-order Benefit", "포토카드"),
        ("팬싸인회 특전", "Fansign Benefit", "포토카드"),
        ("행사 특전", "Event Exclusive", "포토카드"),
    ]

    result = []
    for ko_name, en_name, category in terms:
        lang = "ko" if any("\uAC00" <= c <= "\uD7A3" for c in ko_name) else "en"
        result.append({
            "product_name": ko_name,
            "product_name_en": en_name,
            "artist_slug": "general",
            "category": category,
            "source_url": BASE_URL,
            "language": lang,
            "collected_at": now,
            "is_manual": True,
        })

    return result


def crawl_weverse(output_path: str = "data/raw/weverse_raw.json") -> list[dict]:
    """
    위버스샵 상품명 수집 실행
    Returns: 수집된 상품 정보 리스트
    """
    print("[weverse_crawler] 위버스샵 크롤링 시작...")

    session = requests.Session()
    all_products: list[dict] = []

    # 1) 사이트맵 기반 수집 시도
    print("  [1/3] 사이트맵 기반 수집 시도...")
    sitemap_products = scrape_sitemap_products(session)
    if sitemap_products:
        print(f"    → {len(sitemap_products)}개 상품 수집")
        all_products.extend(sitemap_products)
    else:
        print("    → 사이트맵 접근 불가 (SPA 제한)")

    # 2) 아티스트별 페이지 스크래핑 시도
    print(f"  [2/3] 아티스트별 페이지 스크래핑 ({len(ARTIST_SLUGS)}개 아티스트)...")
    for artist_slug in ARTIST_SLUGS:
        products = scrape_artist_page(session, artist_slug)
        if products:
            print(f"    [{artist_slug}] {len(products)}개 상품 수집")
            all_products.extend(products)
        else:
            print(f"    [{artist_slug}] 정적 HTML 파싱 불가 (JS 렌더링 필요)")
        time.sleep(1)

    # 3) 수동 표준어 목록 추가 (항상 포함)
    print("  [3/3] 공식 표준어 기본 목록 추가...")
    manual_terms = build_manual_standard_terms()
    all_products.extend(manual_terms)
    print(f"    → {len(manual_terms)}개 기본 표준어 추가")

    # 중복 제거 (상품명 기준)
    seen_names: set[str] = set()
    unique_products = []
    for p in all_products:
        name = p.get("product_name", "")
        if name and name not in seen_names:
            seen_names.add(name)
            unique_products.append(p)

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_products, f, ensure_ascii=False, indent=2)

    print(f"[weverse_crawler] 완료: 총 {len(unique_products)}개 상품 → {output_path}")
    return unique_products


# ── Playwright 방식 (JS 렌더링 필요 시 대안) ────────────────
# pip install playwright && playwright install chromium
#
# async def crawl_weverse_playwright(artist_slug: str) -> list[dict]:
#     from playwright.async_api import async_playwright
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await browser.new_page()
#         await page.goto(f"https://shop.weverse.io/en/artist/{artist_slug}")
#         await page.wait_for_load_state("networkidle")
#         # 상품명 선택자 (실제 클래스명은 변경될 수 있음)
#         names = await page.locator("[class*='ProductName'], [class*='product-name']").all_inner_texts()
#         await browser.close()
#         return [{"product_name": n, "artist_slug": artist_slug} for n in names if n.strip()]


if __name__ == "__main__":
    products = crawl_weverse()
    print(f"\n수집 완료: {len(products)}개 상품")
