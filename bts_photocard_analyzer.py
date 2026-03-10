"""
BTS 포토카드 시세 분석 및 웹페이지 생성 스크립트
"""
import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import statistics
from difflib import SequenceMatcher

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
MEMBER_ORDER = ['뷔', '정국', '진', '지민', 'RM', '슈가', '제이홉', '단체']

# 포카 타입 필터 순서 (필요한 타입만, 실제 데이터에 있는 것 우선)
TYPE_ORDER = ['일반포카', '앨포', '예판포', '미공포', '공포', '위버스포', '럭드포', '시그포', '팬싸포', '트포', '미니포', '비공포']

# 영문 타입 표시명 (data-type는 한글 유지, 필터 표시만 영어)
TYPE_EN = {
    '일반포카': 'Regular', '앨포': 'Album', '예판포': 'Pre-order', '미공포': 'Unlisted',
    '공포': 'Official', '위버스포': 'Weverse', '럭드포': 'Lucky Draw', '시그포': 'Signed',
    '팬싸포': 'Fan sign', '트포': 'Ticket', '미니포': 'Mini', '비공포': 'Unofficial',
}

# 영문 멤버/앨범 표시명
MEMBER_EN = {'RM': 'RM', '진': 'Jin', '슈가': 'Suga', '제이홉': 'J-Hope', '지민': 'Jimin', '뷔': 'V', '정국': 'Jungkook', '단체': 'Group'}
ALBUM_EN = {'기타': 'Etc'}  # 나머지 앨범명은 이미 영문

# KRW → USD 환율 (빌드 시점 기준)
KRW_TO_USD = 1350

# 피드백 수집 웹훅 URL (Google Apps Script 배포 후 여기에 입력)
# 설정 방법: FEEDBACK_SETUP.md 참고
FEEDBACK_WEBHOOK_URL = os.environ.get('FEEDBACK_WEBHOOK_URL', 'https://script.google.com/macros/s/AKfycbzbaKZQOH2aVfMrs1ujKbtsrNk8htpIMORRibDRPm_zjws79PpGQ9FVyOtjKEjtow50Hg/exec')
# 또는 직접 입력: FEEDBACK_WEBHOOK_URL = "https://script.google.com/macros/s/YOUR_ID/exec"

# Google Analytics 4 측정 ID (GA4_SETUP.md 참고)
# 예: G-XXXXXXXXXX
GA4_MEASUREMENT_ID = os.environ.get('GA4_MEASUREMENT_ID', 'G-CP807QMS8V')
# 또는 직접 입력: GA4_MEASUREMENT_ID = "G-XXXXXXXXXX"

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
        'chart_click_hint': '클릭 시 상품 페이지로 이동',
        'no_image': '이미지 없음',
        'items': '개',
        'currency': '원',
        'feedback_thanks': '감사합니다! 소중한 의견 잘 받았습니다.',
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
        'chart_click_hint': 'Click to view product',
        'no_image': 'No image',
        'items': '',
        'currency': 'USD',
        'feedback_thanks': 'Thank you! Your feedback has been received.',
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

# 이벤트/행사 키워드
EVENT_KEYWORDS = {
    '일본콘서트': ['일본콘서트', '일콘', 'japan concert', 'japanese concert'],
    '일본': ['일본', 'japan', 'jpn'],
    '콘서트': ['콘서트', 'concert', '공연'],
    '투어': ['투어', 'tour', 'world tour'],
    '머스터': ['머스터', 'muster', '팬미팅'],
    '페스타': ['페스타', 'festa'],
    '팬미팅': ['팬미팅', 'fanmeeting', 'fan meeting'],
    '페스티벌': ['페스티벌', 'festival'],
}

# 시즌/패키지 키워드
SEASON_KEYWORDS = {
    '시즌그리팅': ['시즌그리팅', 'sg', "season's greetings", 'seasons greetings'],
    '윈터패키지': ['윈터패키지', '윈패', 'winter package', 'winter pkg'],
    '서머패키지': ['서머패키지', '썸패', 'summer package', 'summer pkg'],
    '썸머패키지': ['썸머', 'summer'],
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


def strip_parens(s):
    """상품명에서 괄호 안 내용 제거 (예: (일반포카), (Regular) 등)"""
    return re.sub(r'\s*\([^)]*\)', '', s).strip()


def normalize_title_for_comparison(title):
    """상품명을 비교용으로 정규화 (소문자 변환, 공백/특수문자 제거)"""
    # 괄호 제거
    title = strip_parens(title)
    # 소문자 변환
    title = title.lower()
    # 공백 및 특수문자 제거 (한글, 영문, 숫자만 유지)
    title = re.sub(r'[^\w가-힣]', '', title)
    return title


def calculate_title_similarity(title1, title2):
    """두 상품명 간의 유사도 계산 (0.0 ~ 1.0)

    Returns:
        float: 유사도 점수 (0.0 = 완전히 다름, 1.0 = 완전히 동일)
    """
    # 정규화
    norm1 = normalize_title_for_comparison(title1)
    norm2 = normalize_title_for_comparison(title2)

    # 빈 문자열 처리
    if not norm1 or not norm2:
        return 0.0

    # SequenceMatcher로 유사도 계산
    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_product_tokens(title):
    """상품명에서 핵심 토큰 추출 (멤버, 앨범, 타입 제외한 나머지)"""
    # 정규화된 제목
    norm = normalize_title_for_comparison(title)

    # 멤버명 제거
    for member_keywords in MEMBERS.values():
        for keyword in member_keywords:
            norm = norm.replace(keyword.lower().replace('-', ''), '')

    # 앨범명 제거
    for album_keywords in ALBUMS.values():
        for keyword in album_keywords:
            norm = norm.replace(keyword.lower().replace(' ', '').replace(':', ''), '')

    # 타입명 제거
    for type_keywords in SPECIAL_TYPES.values():
        for keyword in type_keywords:
            norm = norm.replace(keyword.lower().replace(' ', ''), '')

    # BTS 제거
    norm = norm.replace('bts', '').replace('방탄소년단', '')

    return norm.strip()


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


def extract_event(title):
    """이벤트/행사 추출"""
    title_lower = title.lower()
    events = []
    for event_name, keywords in EVENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                events.append(event_name)
                break
    return events


def extract_season(title):
    """시즌/패키지 추출"""
    title_lower = title.lower()
    seasons = []
    for season_name, keywords in SEASON_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                seasons.append(season_name)
                break
    return seasons


def extract_version_number(title):
    """버전/번호 추출 (01, #1, ver.1 등)"""
    import re
    title_lower = title.lower()

    # 패턴들
    patterns = [
        r'ver\.?\s*(\d+)',  # ver.1, ver 1, ver1
        r'version\s*(\d+)',  # version 1
        r'버전\s*(\d+)',  # 버전 1
        r'#\s*(\d+)',  # #1, # 1
        r'\b(\d{2})\b',  # 01, 02 (2자리 숫자)
        r'no\.?\s*(\d+)',  # no.1, no 1
    ]

    for pattern in patterns:
        match = re.search(pattern, title_lower)
        if match:
            return match.group(1).zfill(2)  # 2자리로 통일 (1 -> 01)

    return None

def normalize_photocard(product):
    """포토카드 정보를 정규화 (세밀한 특징 추출)"""
    title = product['상품명']
    member = extract_member(title)
    album = extract_album(title)
    special_types = extract_special_type(title)
    events = extract_event(title)  # 새로 추가
    seasons = extract_season(title)  # 새로 추가
    version = extract_version_number(title)  # 새로 추가

    # 포카 ID 생성 (멤버 + 앨범 + 타입 + 이벤트 + 시즌 + 버전)
    # 이벤트와 시즌도 ID에 포함시켜 세밀하게 구분
    id_parts = [member, album]
    id_parts.extend(sorted(special_types))
    if events:
        id_parts.extend(sorted(events))
    if seasons:
        id_parts.extend(sorted(seasons))
    if version:
        id_parts.append(f"ver{version}")

    photocard_id = '_'.join(id_parts)
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
        'events': events,  # 새로 추가
        'seasons': seasons,  # 새로 추가
        'version': version,  # 새로 추가
        'official_name': f"BTS {member} - {album}",
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


def group_products_by_similarity(products, similarity_threshold=0.9):
    """상품들을 유사도 기반으로 그룹화 (최적화 버전)

    Args:
        products: 정규화된 상품 리스트
        similarity_threshold: 동일 상품으로 취급할 유사도 임계값 (기본: 0.9 = 90%)

    Returns:
        dict: {
            'exact_groups': [[product1, product2, ...], ...],  # 90% 이상 매칭
            'similar_groups': [[product1, product2, ...], ...]  # 50-90% 매칭
        }
    """
    if not products:
        return {'exact_groups': [], 'similar_groups': []}

    # 성능 최적화: 첫 30자가 비슷한 상품끼리만 비교
    def get_title_prefix(title):
        """비교를 위한 타이틀 프리픽스 추출"""
        norm = normalize_title_for_comparison(title)
        return norm[:30] if len(norm) >= 30 else norm

    # 프리픽스별로 상품 그룹화 (빠른 필터링)
    prefix_groups = defaultdict(list)
    for i, prod in enumerate(products):
        prefix = get_title_prefix(prod['original_title'])
        prefix_groups[prefix[:15]].append((i, prod))  # 첫 15자로 대분류

    # 이미 그룹에 할당된 상품들 추적
    assigned_to_exact = set()
    exact_groups = []

    # 1단계: 90% 이상 매칭 → 동일 상품 그룹
    for prefix, candidates in prefix_groups.items():
        if len(candidates) < 2:
            continue

        for idx, (i, prod1) in enumerate(candidates):
            if i in assigned_to_exact:
                continue

            group = [prod1]
            assigned_to_exact.add(i)

            for j, prod2 in candidates[idx+1:]:
                if j in assigned_to_exact:
                    continue

                # 그룹/멤버/앨범/타입/이벤트/시즌/버전이 반드시 일치해야 함
                if (prod1['member'] != prod2['member'] or
                    prod1['album'] != prod2['album'] or
                    set(prod1['types']) != set(prod2['types']) or
                    set(prod1.get('events', [])) != set(prod2.get('events', [])) or
                    set(prod1.get('seasons', [])) != set(prod2.get('seasons', [])) or
                    prod1.get('version') != prod2.get('version')):
                    continue

                # 상품명 유사도 계산
                similarity = calculate_title_similarity(
                    prod1['original_title'],
                    prod2['original_title']
                )

                if similarity >= similarity_threshold:
                    group.append(prod2)
                    assigned_to_exact.add(j)

            if len(group) >= 2:
                exact_groups.append(group)

    # 2단계: exact group에 속하지 않은 상품들 중 50-90% 매칭 → 유사 상품 그룹
    similar_groups = []
    assigned_to_similar = set()

    # Prefix별로 다시 그룹화 (아직 할당되지 않은 것들만)
    unassigned_by_prefix = defaultdict(list)
    for prefix, candidates in prefix_groups.items():
        for i, prod in candidates:
            if i not in assigned_to_exact:
                unassigned_by_prefix[prefix[:10]].append((i, prod))  # 더 넓게 (첫 10자)

    for prefix, candidates in unassigned_by_prefix.items():
        if len(candidates) < 2:
            continue

        for idx, (i, prod1) in enumerate(candidates):
            if i in assigned_to_similar:
                continue

            group = [prod1]
            assigned_to_similar.add(i)

            for j, prod2 in candidates[idx+1:]:
                if j in assigned_to_similar:
                    continue

                # 그룹/멤버/앨범/타입/이벤트/시즌/버전이 반드시 일치해야 함
                if (prod1['member'] != prod2['member'] or
                    prod1['album'] != prod2['album'] or
                    set(prod1['types']) != set(prod2['types']) or
                    set(prod1.get('events', [])) != set(prod2.get('events', [])) or
                    set(prod1.get('seasons', [])) != set(prod2.get('seasons', [])) or
                    prod1.get('version') != prod2.get('version')):
                    continue

                # 상품명 유사도 계산
                similarity = calculate_title_similarity(
                    prod1['original_title'],
                    prod2['original_title']
                )

                if 0.5 <= similarity < similarity_threshold:
                    group.append(prod2)
                    assigned_to_similar.add(j)

            if len(group) >= 2:
                similar_groups.append(group)

    return {
        'exact_groups': exact_groups,
        'similar_groups': similar_groups
    }

def analyze_photocards(data_file, validate_links=True):
    """포토카드 데이터 분석 (유사도 기반 그룹화)"""
    print("데이터 로딩 중...")
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = data['query_result']['data']['rows']
    print(f"총 {len(rows)}개 상품 발견")

    # 1단계: 모든 상품을 정규화
    all_normalized = []
    for row in rows:
        try:
            normalized = normalize_photocard(row)
            all_normalized.append(normalized)
        except Exception as e:
            print(f"처리 오류: {row.get('상품명', 'Unknown')}, {e}")
            continue

    # 2단계: 멤버/앨범/타입/이벤트/시즌 조합별로 대분류
    print(f"상품명 유사도 기반 그룹화 중...")
    rough_groups = defaultdict(list)
    for prod in all_normalized:
        # 대분류 키: 멤버_앨범_타입들_이벤트들_시즌들
        key_parts = [prod['member'], prod['album']]
        key_parts.extend(sorted(prod['types']))
        if prod.get('events'):
            key_parts.extend(sorted(prod['events']))
        if prod.get('seasons'):
            key_parts.extend(sorted(prod['seasons']))
        # 버전은 같은 앨범 내에서도 여러 버전이 있을 수 있으므로 대분류에는 포함 안 함
        key = '_'.join(key_parts)
        rough_groups[key].append(prod)

    # 3단계: 각 대분류 내에서 유사도 기반 정밀 그룹화
    exact_photocard_groups = []  # 90% 이상 매칭
    similar_photocard_groups = []  # 50-90% 매칭

    for products in rough_groups.values():
        if len(products) < 2:
            continue

        grouped = group_products_by_similarity(products, similarity_threshold=0.9)
        exact_photocard_groups.extend(grouped['exact_groups'])
        similar_photocard_groups.extend(grouped['similar_groups'])

    print(f"  → 동일 상품 그룹 (90% 이상 매칭): {len(exact_photocard_groups)}개")
    print(f"  → 유사 상품 그룹 (50-90% 매칭): {len(similar_photocard_groups)}개")

    # 4단계: 각 그룹별 통계 계산
    do_validate = validate_links and HAS_REQUESTS
    if do_validate:
        print("상품 링크 검증 중... (실제 존재하는 상품만 표시)")

    def process_group(products, group_type='exact'):
        """그룹 통계 계산 및 대표 상품 선정"""
        prices = [p['price'] for p in products if p['price'] > 0]
        if not prices:
            return None

        # IQR 기반 이상치 제거
        if len(prices) >= 4:
            q1 = statistics.quantiles(prices, n=4)[0]
            q3 = statistics.quantiles(prices, n=4)[2]
            iqr = q3 - q1
            filtered_prices = [p for p in prices if q1 - 1.5*iqr <= p <= q3 + 1.5*iqr]
            if not filtered_prices:
                filtered_prices = prices
        else:
            filtered_prices = prices

        median_val = calculate_median_price(filtered_prices)

        # 대표 상품 선정: 이미지 있는 것 우선, 중앙가 근접 순
        candidates = sorted(
            [p for p in products if p['price'] > 0],
            key=lambda x: (0 if x.get('image_url') else 1, abs(x['price'] - median_val))
        )
        representative = candidates[0]
        has_valid_link = not do_validate

        if do_validate:
            for cand in candidates:
                if validate_product_url(f"https://globalbunjang.com/product/{cand['product_id']}"):
                    representative = cand
                    has_valid_link = True
                    break

        time_series = [
            {'date': p['created_date'][:10], 'price': p['price'], 'product_id': p['product_id']}
            for p in sorted(products, key=lambda x: x['created_date'])
            if p['price'] > 0
        ]

        # 그룹 ID 생성 (대표 상품 정보 기반)
        group_id = f"{representative['member']}_{representative['album']}_{'_'.join(representative['types'])}_{representative['product_id']}"

        return {
            'id': group_id,
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
            'has_valid_link': has_valid_link,
            'group_type': group_type  # 'exact' 또는 'similar'
        }

    # 동일 상품 그룹 처리
    exact_stats = []
    if do_validate:
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = {ex.submit(process_group, group, 'exact'): i
                      for i, group in enumerate(exact_photocard_groups)}
            for i, fut in enumerate(as_completed(futures)):
                if (i + 1) % 50 == 0:
                    print(f"  동일 상품 검증: {i + 1}/{len(exact_photocard_groups)}")
                result = fut.result()
                if result:
                    exact_stats.append(result)
    else:
        exact_stats = [process_group(g, 'exact') for g in exact_photocard_groups]
        exact_stats = [s for s in exact_stats if s is not None]

    # 유사 상품 그룹 처리
    similar_stats = []
    if do_validate:
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = {ex.submit(process_group, group, 'similar'): i
                      for i, group in enumerate(similar_photocard_groups)}
            for i, fut in enumerate(as_completed(futures)):
                if (i + 1) % 50 == 0:
                    print(f"  유사 상품 검증: {i + 1}/{len(similar_photocard_groups)}")
                result = fut.result()
                if result:
                    similar_stats.append(result)
    else:
        similar_stats = [process_group(g, 'similar') for g in similar_photocard_groups]
        similar_stats = [s for s in similar_stats if s is not None]

    # 거래량 많은 순으로 정렬
    exact_stats.sort(key=lambda x: x['transaction_count'], reverse=True)
    similar_stats.sort(key=lambda x: x['transaction_count'], reverse=True)

    with_img_exact = sum(1 for p in exact_stats if p.get('image_url'))
    with_img_similar = sum(1 for p in similar_stats if p.get('image_url'))

    print(f"\n분석 완료:")
    print(f"  → 동일 상품: {len(exact_stats)}개 (이미지: {with_img_exact}개)")
    print(f"  → 유사 상품: {len(similar_stats)}개 (이미지: {with_img_similar}개)")

    if do_validate:
        valid_exact = sum(1 for p in exact_stats if p.get('has_valid_link'))
        valid_similar = sum(1 for p in similar_stats if p.get('has_valid_link'))
        print(f"  → 링크 검증: 동일 {valid_exact}/{len(exact_stats)}개, 유사 {valid_similar}/{len(similar_stats)}개")

    # exact와 similar를 합쳐서 반환 (exact가 앞에)
    return {'exact': exact_stats, 'similar': similar_stats}

def _format_price(val, locale):
    """가격 포맷 (원 또는 USD)"""
    if locale == 'en':
        usd = val / KRW_TO_USD
        return f"${usd:.2f}" if usd >= 1 else f"${usd:.2f}"
    return f"{int(val):,}원"


def generate_html(photocard_stats_dict, output_file, locale='ko'):
    """HTML 웹페이지 생성 (locale: 'ko' | 'en')

    Args:
        photocard_stats_dict: {'exact': [...], 'similar': [...]} 형식의 딕셔너리
        output_file: 출력 HTML 파일 경로
        locale: 'ko' 또는 'en'
    """
    s = STRINGS[locale]
    is_en = locale == 'en'

    # exact와 similar 리스트 분리
    exact_stats = photocard_stats_dict.get('exact', [])
    similar_stats = photocard_stats_dict.get('similar', [])
    all_stats = exact_stats + similar_stats

    # 멤버별로 그룹화 (순서: MEMBER_ORDER)
    by_member_exact = defaultdict(list)
    by_member_similar = defaultdict(list)

    for pc in exact_stats:
        by_member_exact[pc['member']].append(pc)

    for pc in similar_stats:
        by_member_similar[pc['member']].append(pc)

    # 실제 데이터에 있는 타입만 수집
    all_types = set()
    for pc in all_stats:
        all_types.update(pc['types'])
    type_filters = [t for t in TYPE_ORDER if t in all_types]

    # 평균 시세 (로케일에 따라)
    if all_stats:
        avg_val = int(statistics.mean([pc['median_price'] for pc in all_stats]))
        avg_display = _format_price(avg_val, locale)
    else:
        avg_display = _format_price(0, locale)

    # 베타 배너 문구 준비
    beta_badge = 'BETA' if is_en else '베타'
    if is_en:
        beta_message = "<strong>Experimental Preview:</strong> You're one of the first to explore this market tracker. Your feedback helps us improve!"
    else:
        beta_message = "<strong>실험적 프리뷰:</strong> 시장 분석 도구를 가장 먼저 경험하고 계십니다. 여러분의 의견이 개선에 큰 도움이 됩니다!"

    # 언어 전환 링크 수정
    lang_url = '../bts_photocard_market.html' if is_en else 'en/bts_photocard_market.html'
    lang_text = '🇰🇷 한국어' if is_en else '🇺🇸 English'

    # Open Graph 메타 태그 준비
    og_title = s['title']
    og_description = 'Real-time BTS photocard market analysis based on Bunjang Global transaction data' if is_en else '번장 글로벌 거래 데이터 기반 BTS 포토카드 실시간 시세 분석'
    og_url = 'https://bgzt-bts-price-tracker.vercel.app/'
    og_image = 'https://bgzt-bts-price-tracker.vercel.app/bts_price_tracker.png'

    html = f"""<!DOCTYPE html>
<html lang="{'en' if is_en else 'ko'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{s['title']}</title>

    <!-- Open Graph / Facebook / KakaoTalk -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{og_url}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{og_url}">
    <meta property="twitter:title" content="{og_title}">
    <meta property="twitter:description" content="{og_description}">
    <meta property="twitter:image" content="{og_image}">

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
            padding: 0;
            margin: 0;
        }}

        .beta-banner {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
        }}

        .beta-content {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }}

        .beta-badge {{
            background: rgba(255, 255, 255, 0.25);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            border: 1px solid rgba(255, 255, 255, 0.4);
        }}

        .beta-message {{
            font-size: 0.9em;
            line-height: 1.4;
        }}

        .beta-message strong {{
            font-weight: 600;
        }}

        .lang-switch {{
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.4);
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85em;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
            white-space: nowrap;
        }}

        .lang-switch:hover {{
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.6);
            transform: translateY(-1px);
        }}

        .main-content {{
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

        @media (max-width: 768px) {{
            .beta-banner {{
                flex-direction: column;
                gap: 10px;
                padding: 10px 15px;
            }}

            .beta-content {{
                flex-direction: column;
                text-align: center;
                gap: 8px;
            }}

            .beta-message {{
                font-size: 0.85em;
            }}

            .lang-switch {{
                align-self: stretch;
                text-align: center;
            }}

            .main-content {{
                padding: 15px;
            }}

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

        .photocard[data-hidden="true"] {{
            display: none !important;
        }}

        .member-section[data-hidden="true"] {{
            display: none !important;
        }}

        .load-more-btn {{
            display: none;  /* PC에서는 숨김 */
            margin: 20px auto;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s;
        }}

        .load-more-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }}

        .load-more-btn.hidden {{
            display: none;
        }}

        /* 모바일에서만 lazy-load 적용 */
        @media (max-width: 768px) {{
            .photocard.lazy-load {{
                display: none !important;
            }}

            .load-more-btn {{
                display: block;  /* 모바일에서만 표시 */
            }}
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

        /* 피드백 모달 */
        .feedback-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(4px);
        }}

        .feedback-overlay.show {{
            display: flex;
        }}

        .feedback-modal {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
            max-height: 90vh;
            overflow-y: auto;
        }}

        @keyframes modalSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(-30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .feedback-header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        .feedback-emoji {{
            font-size: 3em;
            margin-bottom: 10px;
        }}

        .feedback-title {{
            font-size: 1.8em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}

        .feedback-subtitle {{
            color: #666;
            font-size: 0.95em;
            line-height: 1.5;
        }}

        .feedback-question {{
            margin-bottom: 25px;
        }}

        .feedback-question-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .feedback-question-number {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85em;
            font-weight: 700;
        }}

        .feedback-options {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .feedback-option {{
            flex: 1;
            min-width: 140px;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            font-weight: 500;
            background: white;
        }}

        .feedback-option:hover {{
            border-color: #667eea;
            background: #f8f9ff;
        }}

        .feedback-option.selected {{
            border-color: #667eea;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .feedback-textarea {{
            width: 100%;
            min-height: 100px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-family: inherit;
            font-size: 0.95em;
            resize: vertical;
            transition: border-color 0.2s;
        }}

        .feedback-textarea:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }}

        .feedback-actions {{
            display: flex;
            gap: 12px;
            margin-top: 30px;
        }}

        .feedback-btn {{
            flex: 1;
            padding: 14px 24px;
            border: none;
            border-radius: 12px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .feedback-btn-submit {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .feedback-btn-submit:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }}

        .feedback-btn-submit:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}

        .feedback-btn-skip {{
            background: #f5f5f5;
            color: #666;
        }}

        .feedback-btn-skip:hover {{
            background: #e8e8e8;
        }}

        .feedback-time {{
            text-align: center;
            color: #999;
            font-size: 0.85em;
            margin-top: 12px;
        }}

        /* 모바일 피드백 팝업 최적화 */
        @media (max-width: 768px) {{
            .feedback-overlay {{
                padding: 10px;
                align-items: flex-start;
                padding-top: 40px;
            }}

            .feedback-modal {{
                padding: 25px 20px;
                max-height: 85vh;
                overflow-y: auto;
                width: 95%;
            }}

            .feedback-header {{
                margin-bottom: 20px;
            }}

            .feedback-emoji {{
                font-size: 2.2em;
                margin-bottom: 8px;
            }}

            .feedback-title {{
                font-size: 1.4em;
            }}

            .feedback-subtitle {{
                font-size: 0.85em;
            }}

            .feedback-question {{
                margin-bottom: 20px;
            }}

            .feedback-question-title {{
                font-size: 0.95em;
                gap: 12px;
                align-items: flex-start;
                line-height: 1.5;
            }}

            .feedback-question-number {{
                flex-shrink: 0;
                min-width: 28px;
                width: 28px;
                height: 28px;
                font-size: 0.9em;
                margin-top: 2px;
            }}

            .feedback-options {{
                gap: 8px;
                flex-wrap: wrap;
            }}

            .feedback-option {{
                padding: 10px 14px;
                font-size: 0.9em;
            }}

            .feedback-textarea {{
                font-size: 0.9em;
                min-height: 80px;
            }}

            .feedback-buttons {{
                flex-direction: column;
                gap: 10px;
                margin-top: 20px;
            }}

            .feedback-btn {{
                width: 100%;
                padding: 12px 20px;
            }}

            .feedback-time {{
                font-size: 0.8em;
                margin-top: 10px;
            }}
        }}

        /* Toast notification */
        .toast {{
            position: fixed;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 32px;
            border-radius: 50px;
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
            font-weight: 500;
            z-index: 10000;
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }}

        .toast.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}

        @media (max-width: 768px) {{
            .feedback-modal {{
                padding: 30px 20px;
            }}

            .feedback-options {{
                flex-direction: column;
            }}

            .feedback-option {{
                min-width: 100%;
            }}

            .feedback-actions {{
                flex-direction: column;
            }}
        }}
    </style>

    <!-- Vercel Analytics (무료 Hobby 플랜) -->
    <script defer src="/_vercel/insights/script.js"></script>
"""

    # Google Analytics 4 추가 (측정 ID가 설정된 경우)
    if GA4_MEASUREMENT_ID:
        html += f"""
    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA4_MEASUREMENT_ID}');
    </script>
"""

    html += f"""
</head>
<body>
    <div class="beta-banner">
        <div class="beta-content">
            <span class="beta-badge">{beta_badge}</span>
            <span class="beta-message">{beta_message}</span>
        </div>
        <a href="{lang_url}" class="lang-switch">
            {lang_text}
        </a>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>{s['title']}</h1>
            <p>{s['subtitle']}</p>

        <div class="stats-summary">
            <div class="stat-box">
                <div class="number">{len(exact_stats)}</div>
                <div class="label">{'Exact Matches' if is_en else '동일 상품'}</div>
            </div>
            <div class="stat-box">
                <div class="number">{len(similar_stats)}</div>
                <div class="label">{'Similar Cards' if is_en else '유사 상품'}</div>
            </div>
            <div class="stat-box">
                <div class="number">{sum(pc['transaction_count'] for pc in all_stats):,}</div>
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
        if member in by_member_exact or member in by_member_similar:
            chip_label = MEMBER_EN.get(member, member) if is_en else member
            html += f'                <button class="filter-btn" onclick="setMemberFilter(\'{member}\')">{chip_label}</button>\n'

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

    # 카드 렌더링 헬퍼 함수
    def render_photocard(pc, member, group_type='exact'):
        """포토카드 HTML 생성"""
        chart_id = f"chart_{pc['id'].replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')}"
        types_str = ','.join(pc['types'])
        album = pc['album']
        types_list = pc['types']
        events_list = pc.get('events', [])
        seasons_list = pc.get('seasons', [])
        version = pc.get('version')

        if is_en:
            name_display = strip_parens(f"BTS {MEMBER_EN.get(member, member)} - {ALBUM_EN.get(album, album)}")
            album_display = ALBUM_EN.get(album, album)
            tags_display = ''.join(f'<span class="tag">{TYPE_EN.get(t, t)}</span>' for t in types_list)
            # 이벤트 태그 추가
            tags_display += ''.join(f'<span class="tag" style="background: #fff3e0; color: #f57c00;">{e}</span>' for e in events_list)
            # 시즌 태그 추가
            tags_display += ''.join(f'<span class="tag" style="background: #e3f2fd; color: #1976d2;">{s}</span>' for s in seasons_list)
            # 버전 태그 추가
            if version:
                tags_display += f'<span class="tag" style="background: #f3e5f5; color: #7b1fa2;">Ver.{version}</span>'
            search_text = f"{name_display} {album_display} {' '.join(TYPE_EN.get(t,t) for t in types_list)} {' '.join(events_list)} {' '.join(seasons_list)}".lower()
        else:
            name_display = strip_parens(pc['official_name'])
            album_display = album
            tags_display = ''.join(f'<span class="tag">{t}</span>' for t in types_list)
            # 이벤트 태그 추가
            tags_display += ''.join(f'<span class="tag" style="background: #fff3e0; color: #f57c00;">{e}</span>' for e in events_list)
            # 시즌 태그 추가
            tags_display += ''.join(f'<span class="tag" style="background: #e3f2fd; color: #1976d2;">{s}</span>' for s in seasons_list)
            # 버전 태그 추가
            if version:
                tags_display += f'<span class="tag" style="background: #f3e5f5; color: #7b1fa2;">Ver.{version}</span>'
            search_text = f"{pc['official_name']} {album} {types_str} {' '.join(events_list)} {' '.join(seasons_list)}".lower()
        img_url = pc.get('image_url') or ''
        if img_url:
            thumb_block = f'<div class="photocard-thumb-wrap"><img class="photocard-thumb" src="{img_url}" alt="" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'"><div class="placeholder" style="display:none">{s["no_image"]}</div></div>'
        else:
            thumb_block = f'<div class="photocard-thumb-wrap"><div class="placeholder">{s["no_image"]}</div></div>'

        median_fmt = _format_price(pc['median_price'], locale)
        min_fmt = _format_price(pc['min_price'], locale)
        max_fmt = _format_price(pc['max_price'], locale)
        trades_label = s['trades_count'].format(pc['transaction_count'])

        # 유사 상품일 경우 시각적 구분
        group_badge = ''
        if group_type == 'similar':
            badge_text = 'Similar' if is_en else '유사'
            group_badge = f'<span class="tag" style="background: #e8ecff; color: #6b7fd7;">{badge_text}</span>'

        return f"""
            <div class="photocard" data-member="{member}" data-types="{types_str}" data-search="{search_text}" data-product-id="{pc['representative_product_id']}" data-group-type="{group_type}">
                {thumb_block}
                <div class="photocard-header">
                    <div class="photocard-name">{name_display}</div>
                    <div class="photocard-meta">
                        <span class="tag">{album_display}</span>
                        {tags_display}
                        {group_badge}
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
            </div>
"""

    # 멤버별 섹션 생성 (MEMBER_ORDER 순)
    items_suffix = s['items']
    for member in MEMBER_ORDER:
        exact_cards = by_member_exact.get(member, [])
        similar_cards = by_member_similar.get(member, [])

        if not exact_cards and not similar_cards:
            continue

        total_count = len(exact_cards) + len(similar_cards)
        member_label = MEMBER_EN.get(member, member) if is_en else member
        count_label = f"({total_count}{items_suffix})" if items_suffix else f"({total_count})"

        html += f"""
    <div class="member-section" data-member="{member}">
        <h2 class="member-title">{member_label} {count_label}</h2>
"""

        # 동일 상품 섹션
        if exact_cards:
            exact_label = 'Exact Matches' if is_en else '동일 상품'
            html += f"""
        <h3 style="color: #666; font-size: 1.2em; margin: 20px 0 15px 10px;">{exact_label} ({len(exact_cards)}{items_suffix if items_suffix else ''})</h3>
        <div class="cards-container" data-section="exact-{member}">
"""
            for idx, pc in enumerate(exact_cards[:100]):
                card_html = render_photocard(pc, member, 'exact')
                # 10개 이후 카드는 lazy-load 클래스 추가 (모바일에서만 적용)
                if idx >= 10:
                    card_html = card_html.replace('<div class="photocard"', '<div class="photocard lazy-load"')
                html += card_html

            # 10개 이상일 경우 "더 보기" 버튼 추가
            if len(exact_cards) > 10:
                load_more_text = 'Load More' if is_en else '더 보기'
                html += f"""
        <button class="load-more-btn" data-target="exact-{member}" onclick="loadMoreCards(this)">{load_more_text}</button>
"""

            html += """
        </div>
"""

        # 유사 상품 섹션
        if similar_cards:
            similar_label = 'Similar Cards' if is_en else '유사 상품'
            html += f"""
        <h3 style="color: #6b7fd7; font-size: 1.2em; margin: 30px 0 15px 10px;">{similar_label} ({len(similar_cards)}{items_suffix if items_suffix else ''})</h3>
        <div class="cards-container" data-section="similar-{member}">
"""
            for idx, pc in enumerate(similar_cards[:100]):
                card_html = render_photocard(pc, member, 'similar')
                # 10개 이후 카드는 lazy-load 클래스 추가 (모바일에서만 적용)
                if idx >= 10:
                    card_html = card_html.replace('<div class="photocard"', '<div class="photocard lazy-load"')
                html += card_html

            # 10개 이상일 경우 "더 보기" 버튼 추가
            if len(similar_cards) > 10:
                load_more_text = 'Load More' if is_en else '더 보기'
                html += f"""
        <button class="load-more-btn" data-target="similar-{member}" onclick="loadMoreCards(this)">{load_more_text}</button>
"""

            html += """
        </div>
"""

        html += """
    </div>
"""

    html += """
    </div>
    </div> <!-- .main-content -->

    <!-- 피드백 모달 -->
    <div class="feedback-overlay" id="feedbackOverlay">
        <div class="feedback-modal">
            <div class="feedback-header">
                <div class="feedback-emoji">✨</div>
                <div class="feedback-title">"""

    if is_en:
        html += """Help Us Build Better!</div>
                <div class="feedback-subtitle">You're exploring the cards! Share your thoughts in 30 seconds to help us improve this tool for you."""
    else:
        html += """더 나은 도구를 만들어주세요!</div>
                <div class="feedback-subtitle">카드를 열심히 탐색하고 계시네요! 30초만 투자해서 여러분이 원하는 기능을 만들 수 있게 도와주세요."""

    html += """
            </div>
        </div>

            <div class="feedback-question">
                <div class="feedback-question-title">
                    <span class="feedback-question-number">1</span>
                    <span>"""

    if is_en:
        html += """Would this price tracking feature make the site more useful for you?"""
    else:
        html += """이 포토카드 시세 기능이 있다면 사이트를 더 유용하게 사용하실 건가요?"""

    html += """</span>
                </div>
                <div class="feedback-options">
                    <div class="feedback-option" data-question="1" data-value="yes">"""

    if is_en:
        html += """Yes, very useful!"""
    else:
        html += """네, 매우 유용해요!"""

    html += """</div>
                    <div class="feedback-option" data-question="1" data-value="maybe">"""

    if is_en:
        html += """Maybe"""
    else:
        html += """글쎄요"""

    html += """</div>
                    <div class="feedback-option" data-question="1" data-value="no">"""

    if is_en:
        html += """Not really"""
    else:
        html += """별로 필요없어요"""

    html += """</div>
                </div>
            </div>

            <div class="feedback-question">
                <div class="feedback-question-title">
                    <span class="feedback-question-number">2</span>
                    <span>"""

    if is_en:
        html += """Any suggestions or improvements? (Optional)"""
    else:
        html += """개선점이나 제안사항이 있으신가요? (선택사항)"""

    html += """</span>
                </div>
                <textarea class="feedback-textarea" id="feedbackText" placeholder=\"""" + ('What would make this tool better for you?' if is_en else '어떤 기능이 추가되면 좋을까요?') + """\"></textarea>
            </div>

            <div class="feedback-actions">
                <button class="feedback-btn feedback-btn-skip feedback-skip">"""

    if is_en:
        html += """Maybe Later"""
    else:
        html += """나중에 할게요"""

    html += """</button>
                <button class="feedback-btn feedback-btn-submit feedback-submit">"""

    if is_en:
        html += """Send Feedback"""
    else:
        html += """의견 보내기"""

    html += """</button>
            </div>

            <div class="feedback-time">"""

    if is_en:
        html += """⏱️ Takes less than 30 seconds"""
    else:
        html += """⏱️ 30초도 안 걸려요"""

    html += """</div>
        </div>
    </div>

    <script>
        // 차트 데이터
        const chartData = {
"""

    # 차트 데이터 추가 (en일 때 가격을 USD로 변환, 각 포인트별 product URL)
    for member in MEMBER_ORDER:
        exact_cards = by_member_exact.get(member, [])
        similar_cards = by_member_similar.get(member, [])
        all_cards = exact_cards + similar_cards

        for pc in all_cards[:200]:  # exact + similar 합쳐서 처리
            chart_id = f"chart_{pc['id'].replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')}"
            series = pc['time_series'][-30:]
            dates = [item['date'] for item in series]
            prices = [item['price'] for item in series]
            urls = [f"https://globalbunjang.com/product/{item['product_id']}" for item in series]
            if is_en:
                prices = [round(p / KRW_TO_USD, 2) for p in prices]

            html += f"""
            '{chart_id}': {{
                labels: {json.dumps(dates)},
                data: {json.dumps(prices)},
                urls: {json.dumps(urls)}
            }},
"""

    chart_tick_cb = "function(value) { return '$' + value.toFixed(1); }" if is_en else "function(value) { return (value/1000).toFixed(0) + 'K'; }"
    chart_tooltip = "return '$' + context.parsed.y.toFixed(2);" if is_en else "return context.parsed.y.toLocaleString() + '원';"
    chart_click_hint = json.dumps(s['chart_click_hint'])

    html += """
        };"""

    html += """

        const chartTickCb = """ + chart_tick_cb + """;
        const chartTooltipCb = function(context) { """ + chart_tooltip + """ };
        const chartClickHint = """ + chart_click_hint + """;

        // 차트 생성 (호버 시 가격 + 클릭 유도, 클릭 시 해당 상품 PDP로 이동)
        Object.keys(chartData).forEach(chartId => {
            const ctx = document.getElementById(chartId);
            if (ctx) {
                ctx.style.cursor = 'pointer';
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
                            pointRadius: 3,
                            pointHoverRadius: 7,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        onClick: (evt, elements, chart) => {
                            if (elements.length > 0 && chartData[chartId] && chartData[chartId].urls) {
                                const idx = elements[0].index;
                                const url = chartData[chartId].urls[idx];
                                if (url) window.open(url, '_blank');
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: chartTooltipCb,
                                    afterLabel: () => chartClickHint
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
            if (currentType === type) type = 'all';
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

        // ====== Load More Cards (Mobile Performance Optimization) ======
        function loadMoreCards(button) {
            const targetSection = button.dataset.target;
            const container = document.querySelector(`[data-section="${targetSection}"]`);
            if (!container) return;

            const lazyCards = container.querySelectorAll('.photocard.lazy-load');
            let loadedCount = 0;
            const BATCH_SIZE = 10;  // 모바일에서 10개씩 로드

            // 다음 10개 카드 표시
            lazyCards.forEach((card, index) => {
                if (loadedCount < BATCH_SIZE) {
                    card.classList.remove('lazy-load');
                    loadedCount++;
                }
            });

            // 남은 카드가 없으면 버튼 숨김
            const remainingCards = container.querySelectorAll('.photocard.lazy-load');
            if (remainingCards.length === 0) {
                button.classList.add('hidden');
            }
        }

        // ====== Feedback System ======
        let feedbackShown = localStorage.getItem('feedbackShown');
        let selectedUsefulness = null;

        console.log('🔍 Feedback system initialized');
        console.log('📦 feedbackShown from localStorage:', feedbackShown);

        // TEST MODE: 항상 팝업 표시 (localStorage 무시)
        // 실제 배포 시: if (!feedbackShown) 로 변경
        console.log('⏱️ Starting 10-second timer for feedback popup...');
        setTimeout(() => {
            console.log('⏰ 10 seconds elapsed! Showing feedback modal...');
            showFeedbackModal();
            localStorage.setItem('feedbackShown', 'true');
        }, 10000);  // 10초 = 10000ms

        function showFeedbackModal() {
            const overlay = document.querySelector('.feedback-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        }

        function closeFeedbackModal() {
            const overlay = document.querySelector('.feedback-overlay');
            if (overlay) {
                overlay.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }

        function showToast(message) {
            // Create toast element if it doesn't exist
            let toast = document.getElementById('feedbackToast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'feedbackToast';
                toast.className = 'toast';
                document.body.appendChild(toast);
            }

            // Set message and show toast
            toast.textContent = message;
            toast.classList.add('show');

            // Hide after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // Handle option selection (radio button behavior)
        document.querySelectorAll('.feedback-option').forEach(option => {
            option.addEventListener('click', function() {
                document.querySelectorAll('.feedback-option').forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');
                selectedUsefulness = this.dataset.value;
            });
        });

        // Handle Skip button
        const skipBtn = document.querySelector('.feedback-skip');
        if (skipBtn) {
            skipBtn.addEventListener('click', closeFeedbackModal);
        }

        // Handle Submit button
        const submitBtn = document.querySelector('.feedback-submit');
        if (submitBtn) {
            submitBtn.addEventListener('click', function() {
                const suggestions = document.getElementById('feedbackText')?.value || '';

                // Prepare feedback data
                const feedbackData = {
                    usefulness: selectedUsefulness,
                    suggestions: suggestions.trim(),
                    locale: """ + json.dumps('en' if is_en else 'ko') + """,
                    timestamp: new Date().toISOString(),
                    url: window.location.href
                };

                const webhookUrl = """ + json.dumps(FEEDBACK_WEBHOOK_URL) + """;

                // Always log to console first for debugging
                console.log('📝 Feedback data:', feedbackData);
                console.log('🔗 Webhook URL:', webhookUrl);

                // Send to Google Apps Script webhook (if configured)
                if (webhookUrl) {
                    fetch(webhookUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'text/plain' },  // Changed to avoid CORS preflight
                        body: JSON.stringify(feedbackData),
                        redirect: 'follow'
                    }).then(response => {
                        console.log('✅ Response status:', response.status);
                        return response.text();
                    }).then(data => {
                        console.log('✅ Response data:', data);
                        console.log('✅ Feedback sent successfully to Google Sheets');
                    }).catch(err => {
                        console.error('❌ Feedback send error:', err);
                        console.log('📋 Feedback data (for manual entry):', feedbackData);
                    });
                } else {
                    // Webhook not configured, just log to console
                    console.log('⚠️ Webhook not configured');
                    console.info('💡 To enable server collection, set FEEDBACK_WEBHOOK_URL in bts_photocard_analyzer.py');
                }

                // Close modal first
                closeFeedbackModal();

                // Show thank you toast message
                const thankYouMessage = """ + json.dumps(s.get('feedback_thanks', '감사합니다! 소중한 의견 잘 받았습니다.') if not is_en else 'Thank you! Your feedback has been received.') + """;
                showToast(thankYouMessage);
            });
        }

        // Close modal when clicking overlay background
        const overlay = document.querySelector('.feedback-overlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeFeedbackModal();
                }
            });
        }
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
    photocard_stats_dict = analyze_photocards(str(data_file), validate_links=not args.skip_validate)

    # HTML 생성
    if args.all_locales:
        out_ko = base_dir / 'bts_photocard_market.html'
        en_dir = base_dir / 'en'
        en_dir.mkdir(exist_ok=True)
        out_en = en_dir / 'bts_photocard_market.html'
        generate_html(photocard_stats_dict, str(out_ko), locale='ko')
        generate_html(photocard_stats_dict, str(out_en), locale='en')
        print(f"\n한국어: {out_ko}")
        print(f"영어:   {out_en}")
    else:
        if args.locale == 'en':
            en_dir = base_dir / 'en'
            en_dir.mkdir(exist_ok=True)
            output_file = en_dir / 'bts_photocard_market.html'
        else:
            output_file = base_dir / 'bts_photocard_market.html'
        generate_html(photocard_stats_dict, str(output_file), locale=args.locale)
        print(f"\n웹페이지: {output_file}")

    total_cards = len(photocard_stats_dict.get('exact', [])) + len(photocard_stats_dict.get('similar', []))
    print(f"\n분석 완료! (총 {total_cards}종: 동일 {len(photocard_stats_dict.get('exact', []))}종, 유사 {len(photocard_stats_dict.get('similar', []))}종)")
