"""
STEP 1: Claude API로 K-pop 팬덤 사전 초기 생성
- 굿즈 거래 신조어/약어 300~500개 베이스라인 확보
"""

import json
import os
import time
from datetime import date
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SEED_PROMPTS = [
    {
        "category": "거래 용어 (영어 약어)",
        "prompt": """K-pop 굿즈 거래 커뮤니티(Reddit, 트위터, 디스코드 등)에서 사용하는 영어 약어와 거래 신조어 목록을 생성해줘.
예시: WTS (Want To Sell), WTB (Want To Buy), WTT (Want To Trade), PC (Photocard), troca (포르투갈어 교환), LFB (Looking For Bundle) 등.
최대한 많은 항목을 포함해줘 (50개 이상).
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "WTS",
    "language": "en",
    "term_type": "abbreviation",
    "standard_ko": "판매",
    "standard_en": "Want To Sell",
    "group": null,
    "member": null,
    "goods_type": null,
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
    {
        "category": "한국어 굿즈 신조어",
        "prompt": """K-pop 굿즈 거래에서 사용하는 한국어 신조어와 약어 목록을 생성해줘.
예시: 포카(포토카드), 공봉(공식 응원봉), 응봉(응원봉), 슬로건, 뱃지, 키링, 미니앨(미니앨범), 정규앨(정규앨범), 단독(단독 특전), 팬싸(팬 사인회) 등.
굿즈 유형별로 최대한 많이 포함해줘 (50개 이상).
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "포카",
    "language": "ko",
    "term_type": "abbreviation",
    "standard_ko": "포토카드",
    "standard_en": "Photocard",
    "group": null,
    "member": null,
    "goods_type": "포토카드",
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
    {
        "category": "거래 상태/조건 신조어",
        "prompt": """K-pop 굿즈 거래에서 상태, 조건, 가격 관련 신조어 목록을 생성해줘.
예시: 민트(새것 수준), 새상(새 상품), 중고, 포장개봉, 직구, 구매대행, 합배(합산 배송), 묶배(묶음 배송), 선불, 후불, 직거래, 택배거래, 에코(에코백), 입고(입고 예정), 품절, 재입고, OOS(Out Of Stock), NFS(Not For Sale) 등.
50개 이상 생성해줘.
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "민트",
    "language": "ko",
    "term_type": "slang",
    "standard_ko": "새것 같은 상태",
    "standard_en": "Mint condition",
    "group": null,
    "member": null,
    "goods_type": null,
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
    {
        "category": "그룹 약칭 (BTS, 블랙핑크 등 메이저)",
        "prompt": """주요 K-pop 그룹의 팬덤 약칭과 별명 목록을 생성해줘. 특히 굿즈/거래 커뮤니티에서 자주 쓰이는 것들.
예시: 방탄(BTS), 포방원(BTS 방탄소년단), 아미(ARMY), 블핑(BLACKPINK), 뉴진스, 에스파(aespa), 세블(SEVENTEEN), 르세라핌(LE SSERAFIM), 아이브(IVE), 스트레이키즈(Stray Kids), 엔하이픈(ENHYPEN), 투어스(TWS), 트바엽(TOMORROW X TOGETHER/TXT), NCT드림, 위에화(WayV) 등.
각 그룹의 한국어 약칭, 영어 약칭, 팬덤명까지 포함해서 100개 이상 생성해줘.
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "방탄",
    "language": "ko",
    "term_type": "abbreviation",
    "standard_ko": "방탄소년단",
    "standard_en": "BTS",
    "group": "BTS",
    "member": null,
    "goods_type": null,
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
    {
        "category": "앨범/시대 관련 신조어",
        "prompt": """K-pop 팬덤에서 앨범, 컴백 시대, 버전 관련 신조어 목록을 생성해줘.
예시: 컴백(comeback), 미니앨(미니앨범), 정규(정규 앨범), 리팩(리패키지), 스페셜 에디션, 시즌그리팅(Season's Greetings), 하반기(H2 release), 업로드(Weverse 업로드 특전), 팬미팅 특전, 투어 특전(concert exclusive), 위버스(Weverse), 팬싸(팬 사인회), 랜덤(random photocard) 등.
50개 이상 생성해줘.
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "시즌그리팅",
    "language": "ko",
    "term_type": "abbreviation",
    "standard_ko": "시즌 그리팅",
    "standard_en": "Season's Greetings",
    "group": null,
    "member": null,
    "goods_type": "공식MD",
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
    {
        "category": "영어권 팬덤 신조어 (Reddit/Twitter)",
        "prompt": """영어권 K-pop 팬덤 커뮤니티(Reddit r/KpopMerch, Twitter/X, Discord 등)에서 굿즈 거래 시 사용하는 영어 신조어와 은어 목록을 생성해줘.
예시: pc (photocard), pob (pre-order benefit), lof (lot of), lfb (looking for bundle), ot4/ot5 (all members), bias (최애), bias wrecker, poca/poca set, unreleased pc, fansign pc, event pc, solo pc, group pc, unit pc, inclusions, inclus, era, comeback stage, official md, merch drop, mass order (공동구매), GO (group order), sealed (봉인), unsealed 등.
50개 이상 생성해줘.
반드시 아래 JSON 배열 형식으로만 응답해줘:
[
  {
    "original_term": "pob",
    "language": "en",
    "term_type": "abbreviation",
    "standard_ko": "선주문 특전",
    "standard_en": "Pre-order Benefit",
    "group": null,
    "member": null,
    "goods_type": "포토카드",
    "source": "claude_seed",
    "confidence": "high"
  }
]""",
    },
]


def parse_json_response(text: str) -> list[dict]:
    """LLM 응답에서 JSON 배열 파싱 (마크다운 코드블록 처리 포함)"""
    text = text.strip()
    # 마크다운 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json 또는 ```) 및 마지막 줄(```) 제거
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        # JSON 배열 부분만 추출 시도
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    print(f"  [WARN] JSON 파싱 실패, 응답 일부: {text[:200]}")
    return []


def validate_entry(entry: dict) -> bool:
    """필수 필드 검증"""
    required = ["original_term", "language", "term_type", "standard_ko", "standard_en", "source"]
    return all(entry.get(f) for f in required)


def normalize_entry(entry: dict) -> dict:
    """누락 필드 기본값 채우기"""
    defaults = {
        "group": None,
        "member": None,
        "goods_type": None,
        "confidence": "high",
        "source": "claude_seed",
    }
    for k, v in defaults.items():
        entry.setdefault(k, v)
    return entry


def generate_seed_dictionary(output_path: str = "data/raw/claude_seed.json") -> list[dict]:
    """
    Claude API를 호출해 초기 팬덤 사전 생성
    Returns: 생성된 항목 리스트
    """
    all_entries: list[dict] = []
    seen_terms: set[str] = set()

    print(f"[claude_seed] 초기 사전 생성 시작 ({len(SEED_PROMPTS)}개 카테고리)")

    for i, item in enumerate(SEED_PROMPTS, 1):
        category = item["category"]
        print(f"  [{i}/{len(SEED_PROMPTS)}] {category} 생성 중...")

        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": item["prompt"]}],
            )
            raw_text = response.content[0].text
            entries = parse_json_response(raw_text)

            valid_count = 0
            for entry in entries:
                entry = normalize_entry(entry)
                if not validate_entry(entry):
                    continue
                term_key = f"{entry['original_term']}_{entry['language']}"
                if term_key in seen_terms:
                    continue
                seen_terms.add(term_key)
                all_entries.append(entry)
                valid_count += 1

            print(f"    → {valid_count}개 항목 추가 (누적: {len(all_entries)}개)")

        except Exception as e:
            print(f"    [ERROR] {category} 생성 실패: {e}")

        # API rate limit 방지
        if i < len(SEED_PROMPTS):
            time.sleep(1)

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"[claude_seed] 완료: 총 {len(all_entries)}개 항목 → {output_path}")
    return all_entries


if __name__ == "__main__":
    entries = generate_seed_dictionary()
    print(f"\n생성 완료: {len(entries)}개 항목")
