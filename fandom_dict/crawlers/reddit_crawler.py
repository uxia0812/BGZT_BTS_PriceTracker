"""
Reddit 크롤링 (API 키 불필요)
- Reddit JSON 피드 사용: URL 뒤에 .json 붙이면 공개 JSON 반환
- requests만 사용 (PRAW 불필요)
- 수집 결과: data/raw/reddit_raw.json

URL 예: https://www.reddit.com/r/KpopMerch/new.json
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FandomDictCrawler/1.0; +https://github.com)",
    "Accept": "application/json",
}

SUBREDDITS = [
    "KpopMerch",
    "photocard",
    "bangtan",
    "aespa",
    "NewJeans_",
    "kpop",
]

TRADE_KEYWORDS = ["WTS", "WTB", "WTT", "LF", "LFB", "SELLING", "BUYING", "TRADING", "ISO"]
DAYS_BACK = 90
MAX_POSTS_PER_SUB = 50
DELAY_SEC = 2.0  # Reddit rate limit 고려


def fetch_json(url: str, session: requests.Session) -> Optional[dict]:
    """JSON 피드 가져오기"""
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    [WARN] 요청 실패: {e}")
    return None


def is_trade_post(title: str) -> bool:
    """거래 게시물 여부"""
    return any(kw in title.upper() for kw in TRADE_KEYWORDS)


def parse_listing(data: dict, subreddit: str) -> list[dict]:
    """Reddit JSON 응답에서 게시물 목록 파싱"""
    posts = []
    try:
        children = data.get("data", {}).get("children", [])
        for child in children:
            d = child.get("data", {})
            if not d or d.get("removed_by_category"):
                continue
            title = d.get("title", "")
            selftext = d.get("selftext", "")
            if selftext in ("[deleted]", "[removed]"):
                selftext = ""
            posts.append({
                "id": d.get("id", ""),
                "subreddit": subreddit,
                "title": title,
                "selftext": selftext,
                "score": d.get("score", 0),
                "created_utc": d.get("created_utc", 0),
                "created_date": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                "is_trade_post": is_trade_post(title),
                "url": f"https://reddit.com{d.get('permalink', '')}",
                "top_comments": [],  # JSON 피드에는 댓글 없음 (별도 요청 필요)
                "collected_at": datetime.now(tz=timezone.utc).isoformat(),
            })
    except Exception as e:
        print(f"    [WARN] 파싱 실패: {e}")
    return posts


def crawl_subreddit(
    session: requests.Session,
    subreddit: str,
    max_posts: int = MAX_POSTS_PER_SUB,
    days_back: int = DAYS_BACK,
) -> list[dict]:
    """서브레딧 크롤링 (new + search for WTS/WTB/WTT)"""
    cutoff_ts = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).timestamp()
    all_posts = []
    seen_ids = set()

    # 1) new 피드
    url_new = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
    data = fetch_json(url_new, session)
    if data:
        for p in parse_listing(data, subreddit):
            if p["id"] not in seen_ids and p.get("created_utc", 0) >= cutoff_ts:
                seen_ids.add(p["id"])
                all_posts.append(p)

    time.sleep(DELAY_SEC)

    # 2) 거래 키워드 검색 (WTS, WTB, WTT)
    for kw in ["WTS", "WTB", "WTT"]:
        url_search = f"https://www.reddit.com/r/{subreddit}/search.json?q={kw}&sort=new&restrict_sr=on&limit=25"
        data = fetch_json(url_search, session)
        if data:
            for p in parse_listing(data, subreddit):
                if p["id"] not in seen_ids and p.get("created_utc", 0) >= cutoff_ts:
                    seen_ids.add(p["id"])
                    all_posts.append(p)
        time.sleep(DELAY_SEC)

    trade_count = sum(1 for p in all_posts if p["is_trade_post"])
    print(f"    [{subreddit}] {len(all_posts)}개 (거래글: {trade_count}개)")
    return all_posts[:max_posts]


def crawl_reddit(output_path: str = "data/raw/reddit_raw.json") -> list[dict]:
    """전체 Reddit 크롤링 (API 키 불필요)"""
    print(f"[reddit_crawler] Reddit JSON 피드 크롤링 ({len(SUBREDDITS)}개 서브레딧, API 불필요)")

    session = requests.Session()
    all_posts = []

    for sub in SUBREDDITS:
        try:
            posts = crawl_subreddit(session, sub)
            all_posts.extend(posts)
        except Exception as e:
            print(f"  [ERROR] {sub} 실패: {e}")
        time.sleep(DELAY_SEC)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    trade_total = sum(1 for p in all_posts if p["is_trade_post"])
    print(f"[reddit_crawler] 완료: {len(all_posts)}개 (거래글: {trade_total}개) → {output_path}")
    return all_posts


if __name__ == "__main__":
    crawl_reddit()
