"""
BTS 포토카드 시세 분석 및 웹페이지 생성 스크립트
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import statistics

try:
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# 멤버 이름 매핑
MEMBERS = {
    'RM': ['rm', '알엠', '남준', 'namjoon'],
    '진': ['진', 'jin', '석진', 'seokjin'],
    '슈가': ['슈가', 'suga', '윤기', 'yoongi', '민윤기'],
    '제이홉': ['제이홉', 'jhope', 'j-hope', '호석', 'hoseok', '정호석'],
    '지민': ['지민', 'jimin', '박지민'],
    '뷔': ['뷔', 'v', '태형', 'taehyung', '김태형'],
    '정국': ['정국', 'jungkook', 'jk', '전정국']
}

# 앨범/시즌 키워드
ALBUMS = {
    'PROOF': ['proof', '프루프'],
    'MAP OF THE SOUL: 7': ['mots', 'map of the soul', '7', '맵솔'],
    'BE': ['be', '비이'],
    'LOVE YOURSELF': ['love yourself', '러브 유어셀프', '러브유어셀프', 'ly', '결', '전', '답'],
    'WINGS': ['wings', '윙스'],
    'YOU NEVER WALK ALONE': ['you never walk alone', 'ynwa'],
    'THE MOST BEAUTIFUL MOMENT IN LIFE': ['hyyh', '화양연화', '화연'],
    'DARK & WILD': ['dark', 'wild', '다크'],
    'Butter': ['butter', '버터'],
    'Dynamite': ['dynamite', '다이너마이트'],
    'Permission to Dance': ['ptd', 'permission'],
    'Life Goes On': ['lgo', 'life goes on'],
    'ON': ['on', '온'],
    'Black Swan': ['black swan', '블랙스완'],
    'Boy With Luv': ['bwl', 'boy with luv', '작은것들'],
    'IDOL': ['idol', '아이돌'],
    'DNA': ['dna'],
    'MIC Drop': ['mic drop', '마이크드랍'],
    'Spring Day': ['spring day', '봄날'],
    'Blood Sweat & Tears': ['bst', 'blood sweat', '피땀눈물'],
}

# 멤버 표시 순서 (전체 제외, 단체는 맨 뒤)
MEMBER_ORDER = ['RM', '진', '슈가', '제이홉', '지민', '뷔', '정국', '단체']

# 포카 타입 필터 순서 (필요한 타입만, 실제 데이터에 있는 것 우선)
TYPE_ORDER = ['일반포카', '앨포', '예판포', '미공포', '공포', '위버스포', '럭드포', '시그포', '팬싸포', '트포', '미니포', '비공포']

# 영문 타입 표시명 (data-type는 한글 유지, 필터 표시만 영어)
TYPE_EN = {
    '일반포카': 'Regular', '앨포': 'Album', '예판포': 'Pre-order', '미공포': 'Unlisted',
    '공포': 'Official', '위버스포': 'Weverse', '럭드포': 'Lucky Draw', '시그포': 'Signed',
    '팬싸포': 'Fan sign', '트포': 'Ticket', '미니포': 'Mini', '비공포': 'Unofficial',
}

# KRW → USD 환율 (빌드 시점 기준)
KRW_TO_USD = 1350

# 로케일별 UI 문자열
STRINGS = {
    'ko': {
        'title': 'BTS 포토카드 시세 분석',
        'subtitle': '글로벌번장 실거래 데이터 기반 시세 정보',
        'photocard_types': '포토카드 종류',
        'total_trades': '총 거래 수',
        'avg_price': '평균 시세',
        'search_placeholder': '포토카드명, 앨범, 타입으로 검색...',
        'all': '전체',
        'type_filter': '포카 종류',
        'type_filter_title': '타입 필터',
        'min': '최저',
        'max': '최고',
        'trades_count': '거래 {0}건',
        'example': '예시',
        'view_product': '상품 보러가기 →',
        'no_image': '이미지 없음',
        'items': '개',
        'currency': '원',
    },
    'en': {
        'title': 'BTS Photocard Price Guide',
        'subtitle': 'Market prices based on Bunjang Global transaction data',
        'photocard_types': 'Photocard types',
        'total_trades': 'Total trades',
        'avg_price': 'Avg price',
        'search_placeholder': 'Search by name, album, type...',
        'all': 'All',
        'type_filter': 'PC Type',
        'type_filter_title': 'Type filter',
        'min': 'Low',
        'max': 'High',
        'trades_count': '{0} deals',
        'example': 'e.g.',
        'view_product': 'View product →',
        'no_image': 'No image',
        'items': '',
        'currency': 'USD',
    },
}

# 특수 포카 타입
SPECIAL_TYPES = {
    '럭드포': ['럭드', '럭키드로우', 'lucky draw'],
    '위버스포': ['위버스', 'weverse'],
    '공포': ['공포', '공식포토'],
    '비공포': ['비공포', '비공식포토'],
    '미공포': ['미공포', '미공식포토'],
    '시그포': ['시그', '사인', 'sign'],
    '예판포': ['예판', '예약판매'],
    '팬싸포': ['팬싸', '팬사인회'],
    '앨포': ['앨포', '앨범포토'],
    '트포': ['트포', '트레카'],
    '미니포': ['미니포토'],
}

def build_bunjang_image_url(product_id, created_date_str, modified_date_str, image_count):
    """글로벌번장 이미지 URL 구성 (상품등록일자/수정일시 기반)"""
    if not image_count or image_count < 1:
        return None
    for date_str in (modified_date_str, created_date_str):
        if not date_str:
            continue
        try:
            s = date_str.replace('Z', '+00:00')
            if 'T' in s:
                dt = datetime.fromisoformat(s)
            else:
                dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
            ts = int(dt.timestamp())
            return f"https://media.bunjang.co.kr/product/{product_id}_1_{ts}_w640.jpg"
        except (ValueError, TypeError):
            continue
    return None


# 삭제/판매완료 페이지 판별용 키워드 (이 중 하나라도 있으면 해당 상품은 표시하지 않음)
# - deleted: "This item is no longer available", "it may have been removed"
# - sold: "Sold out on Bunjang" / "Sold on Bunjang" (페이지 제목)
# - EmptyCase: 번장 빈 상품 UI
_AVAILABILITY_BAD_KEYWORDS = (
    'this item is no longer available',
    'it may have been removed',
    'check out other products or go back to home',
    'sold out on bunjang',
    'sold on bunjang',
    'emptycase',
    'product-error/deleted',
)


def validate_product_url(url, timeout=8):
    """상품 페이지 존재 및 판매중 여부 확인 (실제 PDP로 이동 가능한 상품만 True)"""
    if not HAS_REQUESTS:
        return True  # 검증 불가 시 일단 표시
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; FandomDictBot/1.0)'}
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers)
        if r.status_code != 200:
            return False
        # redirect된 경우 (예: product-error/deleted)
        if 'product-error' in r.url:
            return False
        text = (r.text or '').lower()
        for kw in _AVAILABILITY_BAD_KEYWORDS:
            if kw in text:
                return False
        return True
    except Exception:
        return False


def extract_member(title):
    """상품명에서 멤버 추출"""
    title_lower = title.lower()
    for member, keywords in MEMBERS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return member
    return '단체'

def extract_album(title):
    """상품명에서 앨범/시즌 추출"""
    title_lower = title.lower()
    for album, keywords in ALBUMS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return album
    return '기타'

def extract_special_type(title):
    """특수 포카 타입 추출"""
    title_lower = title.lower()
    types = []
    for type_name, keywords in SPECIAL_TYPES.items():
        for keyword in keywords:
            if keyword in title_lower:
                types.append(type_name)
                break
    return types if types else ['일반포카']

def normalize_photocard(product):
    """포토카드 정보를 정규화"""
    title = product['상품명']
    member = extract_member(title)
    album = extract_album(title)
    special_types = extract_special_type(title)

    # 포카 ID 생성 (멤버 + 앨범 + 타입)
    photocard_id = f"{member}_{album}_{'_'.join(special_types)}"
    product_id = product['상품id']
    created = product.get('상품등록일자') or ''
    modified = product.get('수정일시') or ''
    image_count = product.get('이미지수', 0)
    image_url = build_bunjang_image_url(product_id, created, modified, image_count) if (created or modified) else None

    return {
        'id': photocard_id,
        'member': member,
        'album': album,
        'types': special_types,
        'official_name': f"BTS {member} - {album} ({', '.join(special_types)})",
        'original_title': title,
        'price': product['상품가격'],
        'product_id': product_id,
        'created_date': created,
        'image_count': image_count,
        'image_url': image_url
    }

def calculate_median_price(prices):
    """중앙값 계산"""
    if not prices:
        return 0
    return statistics.median(prices)

def analyze_photocards(data_file, validate_links=True):
    """포토카드 데이터 분석"""
    print("데이터 로딩 중...")
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = data['query_result']['data']['rows']
    print(f"총 {len(rows)}개 상품 발견")

    # 포토카드별로 그룹화
    photocard_groups = defaultdict(list)
    total_groups = 0

    for row in rows:
        try:
            normalized = normalize_photocard(row)
            photocard_groups[normalized['id']].append(normalized)
        except Exception as e:
            print(f"처리 오류: {row.get('상품명', 'Unknown')}, {e}")
            continue

    # 각 포토카드별 통계 계산
    photocard_stats = []
    group_items = [(k, v) for k, v in photocard_groups.items() if len(v) >= 2]
    do_validate = validate_links and HAS_REQUESTS
    if do_validate:
        print("상품 링크 검증 중... (실제 존재하는 상품만 표시)")

    def process_group(item):
        photocard_id, products = item
        prices = [p['price'] for p in products if p['price'] > 0]
        if not prices:
            return None
        q1 = statistics.quantiles(prices, n=4)[0]
        q3 = statistics.quantiles(prices, n=4)[2]
        iqr = q3 - q1
        filtered_prices = [p for p in prices if q1 - 1.5*iqr <= p <= q3 + 1.5*iqr]
        if not filtered_prices:
            filtered_prices = prices
        median_val = calculate_median_price(filtered_prices)
        # 1) 썸네일(이미지) 있는 상품 우선, 2) 중앙가 대비 가격 근접 순
        # → 검증 통과한 상품 중 썸네일+링크 동일한(판매중) 상품 우선 선택
        candidates = sorted(
            [p for p in products if p['price'] > 0],
            key=lambda x: (0 if x.get('image_url') else 1, abs(x['price'] - median_val))
        )
        representative = candidates[0]
        has_valid_link = not do_validate  # 검증 생략 시 링크 표시
        if do_validate:
            for cand in candidates:
                if validate_product_url(f"https://globalbunjang.com/product/{cand['product_id']}"):
                    representative = cand
                    has_valid_link = True
                    break
        time_series = [
            {'date': p['created_date'][:10], 'price': p['price']}
            for p in sorted(products, key=lambda x: x['created_date'])
            if p['price'] > 0
        ]
        return (
            photocard_id, products, representative, has_valid_link,
            filtered_prices, time_series
        )

    if do_validate:
        processed = []
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = {ex.submit(process_group, item): item for item in group_items}
            for i, fut in enumerate(as_completed(futures)):
                if (i + 1) % 50 == 0:
                    print(f"  검증 진행: {i + 1}/{len(group_items)}")
                result = fut.result()
                if result:
                    processed.append(result)
    else:
        processed = [r for r in (process_group(it) for it in group_items) if r is not None]

    for photocard_id, products, representative, has_valid_link, filtered_prices, time_series in processed:
        photocard_stats.append({
            'id': photocard_id,
            'official_name': representative['official_name'],
            'member': representative['member'],
            'album': representative['album'],
            'types': representative['types'],
            'median_price': int(calculate_median_price(filtered_prices)),
            'min_price': int(min(filtered_prices)),
            'max_price': int(max(filtered_prices)),
            'avg_price': int(statistics.mean(filtered_prices)),
            'transaction_count': len(filtered_prices),
            'time_series': time_series,
            'representative_product_id': representative['product_id'],
            'sample_title': representative['original_title'],
            'image_url': representative.get('image_url'),
            'has_valid_link': has_valid_link
        })

    # 거래량 많은 순으로 정렬
    photocard_stats.sort(key=lambda x: x['transaction_count'], reverse=True)

    with_img = sum(1 for p in photocard_stats if p.get('image_url'))
    print(f"\n분석 완료: {len(photocard_stats)}개 포토카드 종류")
    if do_validate:
        valid_count = sum(1 for p in photocard_stats if p.get('has_valid_link'))
        print(f"  → 상품 링크 검증: {valid_count}/{len(photocard_stats)}개 (존재하는 상품만 표시)")
    print(f"  → 이미지 URL: {with_img}개")
    return photocard_stats

def _format_price(val, locale):
    """가격 포맷 (원 또는 USD)"""
    if locale == 'en':
        usd = val / KRW_TO_USD
        return f"${usd:.2f}" if usd >= 1 else f"${usd:.2f}"
    return f"{int(val):,}원"


def generate_html(photocard_stats, output_file, locale='ko'):
    """HTML 웹페이지 생성 (locale: 'ko' | 'en')"""
    s = STRINGS[locale]
    is_en = locale == 'en'

    # 멤버별로 그룹화 (순서: MEMBER_ORDER)
    by_member = defaultdict(list)
    for pc in photocard_stats:
        by_member[pc['member']].append(pc)

    # 실제 데이터에 있는 타입만 수집
    all_types = set()
    for pc in photocard_stats:
        all_types.update(pc['types'])
    type_filters = [t for t in TYPE_ORDER if t in all_types]

    # 평균 시세 (로케일에 따라)
    avg_val = int(statistics.mean([pc['median_price'] for pc in photocard_stats]))
    avg_display = _format_price(avg_val, locale)

    html = f"""<!DOCTYPE html>
<html lang="{'en' if is_en else 'ko'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{s['title']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #ffeef8 0%, #e6f3ff 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 20px;
            margin-bottom: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        }}

        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 99%, #fad0c4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}

        .header p {{
            color: #666;
            font-size: 1.1em;
        }}

        .stats-summary {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}

        .stat-box {{
            background: white;
            padding: 20px 30px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }}

        .stat-box .number {{
            font-size: 2em;
            font-weight: bold;
            color: #ff9a9e;
        }}

        .stat-box .label {{
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }}

        .member-section {{
            margin-bottom: 60px;
        }}

        .member-title {{
            font-size: 2em;
            color: #333;
            margin-bottom: 30px;
            padding-left: 10px;
            border-left: 5px solid #ff9a9e;
        }}

        .cards-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}

        .photocard {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}

        .photocard:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        }}

        .photocard-thumb-wrap {{
            position: relative;
            width: 100%;
            aspect-ratio: 1;
            border-radius: 12px;
            background: #f5f5f8;
            margin-bottom: 12px;
            overflow: hidden;
        }}

        .photocard-thumb {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 12px;
        }}

        .photocard-thumb-wrap .placeholder {{
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #bbb;
            font-size: 0.85em;
            background: #f5f5f8;
        }}

        .photocard-header {{
            margin-bottom: 15px;
        }}

        .photocard-name {{
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            line-height: 1.4;
        }}

        .photocard-meta {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }}

        .tag {{
            background: #ffeef8;
            color: #ff6b9d;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }}

        .price-info {{
            background: linear-gradient(135deg, #fff5f7 0%, #f0f4ff 100%);
            padding: 15px;
            border-radius: 15px;
            margin-bottom: 15px;
        }}

        .median-price {{
            font-size: 1.8em;
            font-weight: bold;
            color: #ff6b9d;
            margin-bottom: 8px;
        }}

        .price-range {{
            font-size: 0.85em;
            color: #666;
            display: flex;
            justify-content: space-between;
        }}

        .transaction-count {{
            text-align: center;
            color: #999;
            font-size: 0.85em;
            margin-top: 5px;
        }}

        .chart-container {{
            position: relative;
            height: 150px;
            margin-top: 15px;
        }}

        .sample-title {{
            font-size: 0.75em;
            color: #999;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #f0f0f0;
            font-style: italic;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}

            .cards-container {{
                grid-template-columns: 1fr;
            }}

            .member-title {{
                font-size: 1.5em;
            }}

            .stats-summary {{
                flex-direction: column;
                align-items: center;
            }}
        }}

        .filter-buttons {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            background: white;
            color: #666;
            border: 2px solid #ffeef8;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1em;
        }}

        .filter-btn:hover {{
            background: #ffeef8;
            color: #ff6b9d;
        }}

        .filter-btn.active {{
            background: #ff6b9d;
            color: white;
            border-color: #ff6b9d;
        }}

        .search-box {{
            margin: 24px 0 16px;
            display: flex;
            justify-content: center;
            padding: 0 20px;
        }}

        .search-box input {{
            padding: 16px 24px;
            font-size: 1.1em;
            border: 2px solid #e8d5e0;
            border-radius: 16px;
            width: 100%;
            max-width: 680px;
            outline: none;
            transition: border-color 0.3s, box-shadow 0.3s;
        }}

        .search-box input::placeholder {{
            color: #aaa;
        }}

        .search-box input:focus {{
            border-color: #ff6b9d;
            box-shadow: 0 0 0 4px rgba(255, 107, 157, 0.15);
        }}

        .filter-section {{
            margin: 15px 0;
        }}

        .filter-section .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
            text-align: center;
        }}

        .member-row {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
            margin: 0 0 20px;
            padding: 0 20px;
        }}

        .member-chips {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .sample-link {{
            display: block;
            font-size: 0.75em;
            color: #ff6b9d;
            margin-top: 6px;
            text-decoration: none;
        }}

        .sample-link:hover {{
            text-decoration: underline;
        }}

        .photocard[data-hidden="true"] {{
            display: none !important;
        }}

        .member-section[data-hidden="true"] {{
            display: none !important;
        }}

        /* 포카 종류 드롭다운 (멤버칩과 다른 형태) */
        .type-dropdown-wrap {{
            position: relative;
            display: inline-block;
        }}

        .type-dropdown-trigger {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: linear-gradient(135deg, #6b7fd7 0%, #8b9ae8 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(107, 127, 215, 0.35);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .type-dropdown-trigger:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(107, 127, 215, 0.4);
        }}

        .type-dropdown-trigger .chevron {{
            font-size: 0.75em;
            opacity: 0.9;
            transition: transform 0.3s;
        }}

        .type-dropdown-trigger.expanded .chevron {{
            transform: rotate(180deg);
        }}

        .type-dropdown-panel {{
            position: absolute;
            top: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: white;
            border-radius: 14px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06);
            padding: 16px;
            min-width: 280px;
            z-index: 100;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s, transform 0.2s;
        }}

        .type-dropdown-panel.open {{
            opacity: 1;
            visibility: visible;
        }}

        .type-dropdown-panel::before {{
            content: '';
            position: absolute;
            top: -6px;
            left: 50%;
            transform: translateX(-50%) rotate(45deg);
            width: 12px;
            height: 12px;
            background: white;
            box-shadow: -2px -2px 4px rgba(0,0,0,0.05);
        }}

        .type-dropdown-title {{
            font-size: 0.8em;
            color: #888;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .type-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}

        .type-option {{
            padding: 8px 12px;
            font-size: 0.85em;
            background: #f5f5f8;
            border: 1px solid #e8e8ec;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .type-option:hover {{
            background: #ebeef8;
            border-color: #c8d0f0;
        }}

        .type-option.selected {{
            background: linear-gradient(135deg, #e8ecff 0%, #dfe6ff 100%);
            border-color: #6b7fd7;
            color: #4a5cc7;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <p style="text-align:right; margin-bottom:-20px;"><a href="{'../index.html' if is_en else 'en/bts_photocard_market.html'}" style="color:#999; font-size:0.85em;">{'한국어' if is_en else 'English'}</a></p>
        <h1>{s['title']}</h1>
        <p>{s['subtitle']}</p>

        <div class="stats-summary">
            <div class="stat-box">
                <div class="number">{len(photocard_stats)}</div>
                <div class="label">{s['photocard_types']}</div>
            </div>
            <div class="stat-box">
                <div class="number">{sum(pc['transaction_count'] for pc in photocard_stats):,}</div>
                <div class="label">{s['total_trades']}</div>
            </div>
            <div class="stat-box">
                <div class="number">{avg_display}</div>
                <div class="label">{s['avg_price']}</div>
            </div>
        </div>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="{s['search_placeholder']}" oninput="applyFilters()">
        </div>

        <div class="member-row">
            <div class="member-chips" id="memberFilters">
                <button class="filter-btn active" onclick="setMemberFilter('all')">{s['all']}</button>
"""

    # 멤버칩: 전체 → MEMBER_ORDER 순 (단체 마지막)
    for member in MEMBER_ORDER:
        if member in by_member:
            html += f'                <button class="filter-btn" onclick="setMemberFilter(\'{member}\')">{member}</button>\n'

    html += f"""            </div>
            <div class="type-dropdown-wrap">
                <button type="button" class="type-dropdown-trigger" id="typeDropdownBtn" onclick="toggleTypeDropdown(event)" aria-expanded="false">
                    <span>{s['type_filter']}</span>
                    <span class="chevron">▾</span>
                </button>
                <div class="type-dropdown-panel" id="typeDropdownPanel">
                    <div class="type-dropdown-title">{s['type_filter_title']}</div>
                    <div class="type-grid" id="typeFilters">
                        <div class="type-option selected" data-type="all" onclick="setTypeFilter('all')">{s['all']}</div>
"""

    for t in type_filters:
        label = TYPE_EN.get(t, t) if is_en else t
        html += f'                        <div class="type-option" data-type="{t}" onclick="setTypeFilter(\'{t}\')">{label}</div>\n'

    html += """                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="content">
"""

    # 멤버별 섹션 생성 (MEMBER_ORDER 순)
    items_suffix = s['items']
    for member in MEMBER_ORDER:
        if member not in by_member:
            continue
        photocards = by_member[member]
        count_label = f"({len(photocards)}{items_suffix})" if items_suffix else f"({len(photocards)})"
        html += f"""
    <div class="member-section" data-member="{member}">
        <h2 class="member-title">{member} {count_label}</h2>
        <div class="cards-container">
"""

        for pc in photocards[:100]:
            chart_id = f"chart_{pc['id'].replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')}"
            types_str = ','.join(pc['types'])
            search_text = f"{pc['official_name']} {pc['album']} {types_str}".lower()
            has_link = pc.get('has_valid_link', True)
            product_url = f"https://globalbunjang.com/product/{pc['representative_product_id']}"
            img_url = pc.get('image_url') or ''
            if img_url:
                thumb_block = f'<div class="photocard-thumb-wrap"><img class="photocard-thumb" src="{img_url}" alt="" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'"><div class="placeholder" style="display:none">{s["no_image"]}</div></div>'
            else:
                thumb_block = f'<div class="photocard-thumb-wrap"><div class="placeholder">{s["no_image"]}</div></div>'

            median_fmt = _format_price(pc['median_price'], locale)
            min_fmt = _format_price(pc['min_price'], locale)
            max_fmt = _format_price(pc['max_price'], locale)
            trades_label = s['trades_count'].format(pc['transaction_count'])
            view_link = f'<a class="sample-link" href="{product_url}" target="_blank" rel="noopener">{s["view_product"]}</a>' if has_link else ''

            html += f"""
            <div class="photocard" data-member="{member}" data-types="{types_str}" data-search="{search_text}" data-product-id="{pc['representative_product_id']}">
                {thumb_block}
                <div class="photocard-header">
                    <div class="photocard-name">{pc['official_name']}</div>
                    <div class="photocard-meta">
                        <span class="tag">{pc['album']}</span>
                        {''.join(f'<span class="tag">{t}</span>' for t in pc['types'])}
                    </div>
                </div>

                <div class="price-info">
                    <div class="median-price">{median_fmt}</div>
                    <div class="price-range">
                        <span>{s['min']}: {min_fmt}</span>
                        <span>{s['max']}: {max_fmt}</span>
                    </div>
                    <div class="transaction-count">{trades_label}</div>
                </div>

                <div class="chart-container">
                    <canvas id="{chart_id}"></canvas>
                </div>

                <div class="sample-title">
                    {s['example']}: {pc['sample_title'][:50]}...
                    {view_link}
                </div>
            </div>
"""

        html += """
        </div>
    </div>
"""

    html += """
    </div>

    <script>
        // 차트 데이터
        const chartData = {
"""

    # 차트 데이터 추가 (en일 때 가격을 USD로 변환)
    for member in MEMBER_ORDER:
        if member not in by_member:
            continue
        photocards = by_member[member]
        for pc in photocards[:100]:
            chart_id = f"chart_{pc['id'].replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')}"
            dates = [item['date'] for item in pc['time_series'][-30:]]
            prices = [item['price'] for item in pc['time_series'][-30:]]
            if is_en:
                prices = [round(p / KRW_TO_USD, 2) for p in prices]

            html += f"""
            '{chart_id}': {{
                labels: {json.dumps(dates)},
                data: {json.dumps(prices)}
            }},
"""

    chart_tick_cb = "function(value) { return '$' + value.toFixed(1); }" if is_en else "function(value) { return (value/1000).toFixed(0) + 'K'; }"
    chart_tooltip = "return '$' + context.parsed.y.toFixed(2);" if is_en else "return context.parsed.y.toLocaleString() + '원';"

    html += """
        };"""

    html += """

        const chartTickCb = """ + chart_tick_cb + """;
        const chartTooltipCb = function(context) { """ + chart_tooltip + """ };

        // 차트 생성
        Object.keys(chartData).forEach(chartId => {
            const ctx = document.getElementById(chartId);
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: chartData[chartId].labels,
                        datasets: [{
                            data: chartData[chartId].data,
                            borderColor: '#ff9a9e',
                            backgroundColor: 'rgba(255, 154, 158, 0.1)',
                            borderWidth: 2,
                            tension: 0.4,
                            pointRadius: 2,
                            pointHoverRadius: 5,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: chartTooltipCb
                                }
                            }
                        },
                        scales: {
                            x: { display: false },
                            y: {
                                display: true,
                                ticks: {
                                    callback: chartTickCb,
                                    font: { size: 10 }
                                },
                                grid: { color: 'rgba(0,0,0,0.05)' }
                            }
                        }
                    }
                });
            }
        });

        // 필터 상태
        let currentMember = 'all';
        let currentType = 'all';
        const searchInput = document.getElementById('searchInput');

        const allLabel = """ + json.dumps(s['all']) + """;
        function setMemberFilter(member) {
            currentMember = member;
            document.querySelectorAll('#memberFilters .filter-btn').forEach(btn => {
                btn.classList.toggle('active', btn.textContent.trim() === (member === 'all' ? allLabel : member));
            });
            applyFilters();
        }

        function setTypeFilter(type) {
            currentType = type;
            document.querySelectorAll('#typeFilters .type-option').forEach(el => {
                el.classList.toggle('selected', el.dataset.type === type);
            });
            applyFilters();
        }

        function toggleTypeDropdown(e) {
            e.stopPropagation();
            const btn = document.getElementById('typeDropdownBtn');
            const panel = document.getElementById('typeDropdownPanel');
            const isOpen = panel.classList.toggle('open');
            btn.classList.toggle('expanded', isOpen);
            btn.setAttribute('aria-expanded', isOpen);
        }

        document.addEventListener('click', (e) => {
            const wrap = document.querySelector('.type-dropdown-wrap');
            if (wrap && wrap.contains(e.target)) return;
            const panel = document.getElementById('typeDropdownPanel');
            if (panel && panel.classList.contains('open')) {
                panel.classList.remove('open');
                const btn = document.getElementById('typeDropdownBtn');
                if (btn) btn.classList.remove('expanded');
            }
        });

        function applyFilters() {
            const searchTerm = (searchInput?.value || '').trim().toLowerCase();
            const cards = document.querySelectorAll('.photocard');
            const sections = document.querySelectorAll('.member-section');

            cards.forEach(card => {
                const matchMember = currentMember === 'all' || card.dataset.member === currentMember;
                const matchType = currentType === 'all' || (card.dataset.types || '').includes(currentType);
                const matchSearch = !searchTerm || (card.dataset.search || '').includes(searchTerm);
                card.dataset.hidden = (matchMember && matchType && matchSearch) ? 'false' : 'true';
            });

            sections.forEach(section => {
                const visibleCards = section.querySelectorAll('.photocard[data-hidden="false"]');
                section.dataset.hidden = visibleCards.length === 0 ? 'true' : 'false';
            });
        }

        if (searchInput) searchInput.addEventListener('input', applyFilters);
    </script>
</body>
</html>
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nHTML 파일 생성 완료: {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BTS 포토카드 시세 분석')
    parser.add_argument('--skip-validate', action='store_true',
                        help='링크 검증 생략 (빠르지만 삭제된 상품 링크가 포함될 수 있음)')
    parser.add_argument('--locale', choices=['ko', 'en'], default='ko',
                        help='출력 로케일: ko(한국어+원), en(영어+USD)')
    parser.add_argument('--all-locales', action='store_true',
                        help='ko, en 두 버전 모두 생성')
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_file = base_dir / 'bts_photocard_data.json'

    print("=" * 60)
    print("BTS 포토카드 시세 분석 시작")
    print("=" * 60)

    if args.skip_validate:
        print("[주의] --skip-validate: 링크 검증 생략 → 일부 '상품 보러가기'가 삭제된 상품일 수 있습니다.\n")

    # 데이터 분석
    photocard_stats = analyze_photocards(str(data_file), validate_links=not args.skip_validate)

    # HTML 생성
    if args.all_locales:
        out_ko = base_dir / 'bts_photocard_market.html'
        en_dir = base_dir / 'en'
        en_dir.mkdir(exist_ok=True)
        out_en = en_dir / 'bts_photocard_market.html'
        generate_html(photocard_stats, str(out_ko), locale='ko')
        generate_html(photocard_stats, str(out_en), locale='en')
        print(f"\n한국어: {out_ko}")
        print(f"영어:   {out_en}")
    else:
        if args.locale == 'en':
            en_dir = base_dir / 'en'
            en_dir.mkdir(exist_ok=True)
            output_file = en_dir / 'bts_photocard_market.html'
        else:
            output_file = base_dir / 'bts_photocard_market.html'
        generate_html(photocard_stats, str(output_file), locale=args.locale)
        print(f"\n웹페이지: {output_file}")

    print(f"\n분석 완료! (포토카드 {len(photocard_stats)}종)")
