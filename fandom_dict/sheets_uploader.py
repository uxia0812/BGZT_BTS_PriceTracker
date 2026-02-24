"""
STEP 5: 구글 시트 자동 업로드
- gspread 라이브러리 사용
- 단일 시트 "팬덤사전": 표준어 기준 1:M 구조 (1개 표준어 → 여러 동의어/약어/신조어)

구글 서비스 계정 설정 방법:
  1. https://console.cloud.google.com 접속
  2. 새 프로젝트 생성 (또는 기존 프로젝트 선택)
  3. API 및 서비스 → 라이브러리 → "Google Sheets API" 활성화
  4. API 및 서비스 → 라이브러리 → "Google Drive API" 활성화
  5. API 및 서비스 → 사용자 인증 정보 → 서비스 계정 만들기
  6. 서비스 계정 → 키 → 키 추가 → JSON 형식 다운로드
  7. 다운로드한 JSON 파일을 fandom_dict/credentials.json으로 저장
  8. 구글 시트를 새로 만들고, 시트 공유 → 서비스 계정 이메일(xxx@xxx.iam.gserviceaccount.com)에 편집자 권한 부여
  9. .env에 GOOGLE_SHEET_ID=<시트 URL의 /d/와 /edit 사이 긴 ID 문자열> 추가
"""

import json
import os
from datetime import date, datetime, timezone

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# ── 구글 API 스코프 ────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── 단일 시트 (표준어 기준 1:M 구조) ──────────────────────
SHEET_MAIN = "팬덤사전"

# ── 컬럼 헤더: 표준어 1개 → 동의어/약어/신조어 다수 (1:M) ─────
HEADERS = [
    "표준어(KO)",
    "표준어(EN)",
    "원본 용어",
    "동의어(KR)",
    "동의어(EN)",
    "굿즈유형",
    "용어유형",
    "확신도",
    "출처",
    "등록일",
]

COL_STD_KO = 0
COL_STD_EN = 1
COL_ORIGINAL = 2   # 수집된 원본 용어 전체 (쉼표 구분)
COL_SYN_KO = 3
COL_SYN_EN = 4
COL_GOODS = 5
COL_TYPE = 6
COL_CONF = 7
COL_SOURCE = 8
COL_DATE = 9


def get_credentials(creds_path: str = "credentials.json") -> Credentials:
    """서비스 계정 자격 증명 로드"""
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json을 찾을 수 없습니다: {creds_path}\n"
            "구글 서비스 계정 설정 방법은 이 파일 상단 docstring을 참고하세요."
        )
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)


def _has_korean(text: str) -> bool:
    return any("\uAC00" <= c <= "\uD7A3" for c in text)


def _has_english(text: str) -> bool:
    return any("a" <= c.lower() <= "z" for c in text)


def group_by_standard_term(entries: list[dict]) -> list[dict]:
    """
    표준어 기준으로 1:M 그룹화.
    동일한 (표준어KO, 표준어EN)에 매핑되는 원본 용어들을 동의어로 집계.
    Returns: [{"standard_ko", "standard_en", "synonyms_ko", "synonyms_en", "originals", ...}]
    """
    groups: dict[tuple[str, str], dict] = {}

    for e in entries:
        std_ko = (e.get("standard_ko") or "").strip()
        std_en = (e.get("standard_en") or "").strip()
        orig = (e.get("original_term") or "").strip()
        if not std_ko and not std_en:
            continue
        if not std_ko:
            std_ko = std_en
        if not std_en:
            std_en = std_ko

        key = (std_ko, std_en)
        if key not in groups:
            groups[key] = {
                "standard_ko": std_ko,
                "standard_en": std_en,
                "originals": set(),
                "synonyms_ko": set(),
                "synonyms_en": set(),
                "goods_type": e.get("goods_type"),
                "term_types": set(),
                "confidences": set(),
                "sources": set(),
            }

        g = groups[key]
        if orig:
            g["originals"].add(orig)
            # 표준어와 동일하면 동의어 목록에는 제외, 다르면 해당 언어 동의어에 포함
            if orig != std_ko and orig != std_en:
                if _has_korean(orig):
                    g["synonyms_ko"].add(orig)
                if _has_english(orig):
                    g["synonyms_en"].add(orig)

        if e.get("term_type"):
            g["term_types"].add(e["term_type"])
        if e.get("confidence"):
            g["confidences"].add(e["confidence"])
        if e.get("source"):
            g["sources"].add(e["source"])

    result = []
    for (std_ko, std_en), g in groups.items():
        # 용어유형: 여러 개면 쉼표로
        term_type = ",".join(sorted(g["term_types"])) if g["term_types"] else "standard"
        # 확신도: verified > high > medium > low
        conf_order = {"verified": 4, "high": 3, "medium": 2, "low": 1}
        conf = max(g["confidences"], key=lambda c: conf_order.get(c, 0)) if g["confidences"] else ""
        result.append({
            "standard_ko": std_ko,
            "standard_en": std_en,
            "originals": ", ".join(sorted(g["originals"])),
            "synonyms_ko": ", ".join(sorted(g["synonyms_ko"])),
            "synonyms_en": ", ".join(sorted(g["synonyms_en"])),
            "goods_type": g["goods_type"] or "",
            "term_type": term_type,
            "confidence": conf,
            "source": ", ".join(sorted(g["sources"])) if g["sources"] else "",
        })
    return result


def grouped_entry_to_row(grouped: dict, today: str) -> list:
    """그룹화된 항목을 시트 행으로 변환"""
    return [
        grouped.get("standard_ko", ""),
        grouped.get("standard_en", ""),
        grouped.get("originals", ""),
        grouped.get("synonyms_ko", ""),
        grouped.get("synonyms_en", ""),
        grouped.get("goods_type", "") or "",
        grouped.get("term_type", ""),
        grouped.get("confidence", ""),
        grouped.get("source", ""),
        today,
    ]


def get_or_create_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> gspread.Worksheet:
    """시트 가져오기 또는 생성"""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=10000, cols=len(HEADERS))
        ws.append_row(HEADERS)
        ws.format(f"A1:{chr(ord('A') + len(HEADERS) - 1)}1", {"textFormat": {"bold": True}})
        return ws


def load_existing_standard_terms(worksheet: gspread.Worksheet) -> dict[tuple, int]:
    """
    시트에서 기존 항목 로드 (표준어 기준)
    Returns: {(표준어KO, 표준어EN): row_number}
    """
    try:
        all_values = worksheet.get_all_values()
    except Exception:
        return {}

    key_to_row: dict = {}
    for i, row in enumerate(all_values[1:], start=2):
        if row and len(row) > COL_STD_EN:
            std_ko = row[COL_STD_KO].strip()
            std_en = row[COL_STD_EN].strip()
            if std_ko or std_en:
                key_to_row[(std_ko, std_en)] = i
    return key_to_row


def upload_grouped_to_sheet(
    worksheet: gspread.Worksheet,
    grouped_entries: list[dict],
    today: str,
    batch_size: int = 50,
) -> dict[str, int]:
    """
    그룹화된 항목을 시트에 업로드 (표준어 기준)
    - 기존 표준어 행이 있으면 동의어 컬럼만 업데이트 (확장)
    - 신규 표준어만 append
    """
    existing = load_existing_standard_terms(worksheet)
    stats = {"added": 0, "updated": 0, "skipped": 0}

    new_rows = []
    update_cells = []  # (row_num, col_num, value)

    for g in grouped_entries:
        key = (g["standard_ko"], g["standard_en"])
        row_data = grouped_entry_to_row(g, today)

        if key in existing:
            row_num = existing[key]
            # 원본 용어, 동의어(KR), 동의어(EN), 확신도 업데이트 (gspread 1-based)
            update_cells.append((row_num, COL_ORIGINAL + 1, row_data[COL_ORIGINAL]))
            update_cells.append((row_num, COL_SYN_KO + 1, row_data[COL_SYN_KO]))
            update_cells.append((row_num, COL_SYN_EN + 1, row_data[COL_SYN_EN]))
            update_cells.append((row_num, COL_CONF + 1, row_data[COL_CONF]))
            stats["updated"] += 1
        else:
            new_rows.append(row_data)
            existing[key] = -1
            stats["added"] += 1

    if update_cells:
        # 중복 제거 (같은 셀 여러 번 업데이트 방지)
        seen = set()
        unique_cells = []
        for r, c, v in update_cells:
            k = (r, c)
            if k not in seen:
                seen.add(k)
                unique_cells.append((r, c, v))
        try:
            cells = [gspread.Cell(row=r, col=c, value=v) for r, c, v in unique_cells]
            worksheet.update_cells(cells)
        except Exception as e:
            print(f"    [WARN] 업데이트 실패: {e}")

    if new_rows:
        for i in range(0, len(new_rows), batch_size):
            batch = new_rows[i : i + batch_size]
            try:
                worksheet.append_rows(batch, value_input_option="RAW")
            except Exception as e:
                print(f"    [WARN] append 실패: {e}")

    return stats


def upload_all(
    classified_path: str = "data/raw/classified.json",
    creds_path: str = "credentials.json",
) -> dict:
    """
    전체 업로드 파이프라인
    Returns: 시트별 통계
    """
    sheet_id = (os.environ.get("GOOGLE_SHEET_ID") or "").strip()
    if not sheet_id:
        raise ValueError(
            "GOOGLE_SHEET_ID 환경변수가 설정되지 않았습니다.\n"
            ".env 파일에 GOOGLE_SHEET_ID=<시트 ID> 추가 후 재실행해주세요."
        )

    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json을 찾을 수 없습니다: {creds_path}\n"
            "현재 작업 디렉토리: " + os.getcwd()
        )
    if not os.path.exists(classified_path):
        raise FileNotFoundError(f"분류 결과 파일이 없습니다: {classified_path}")

    print("[sheets_uploader] 구글 시트 업로드 시작")
    print(f"  시트 ID: {sheet_id[:20]}... (길이: {len(sheet_id)})")

    # credentials.json에서 서비스 계정 이메일 확인
    with open(creds_path, encoding="utf-8") as f:
        creds_data = json.load(f)
    service_email = creds_data.get("client_email", "")
    print(f"  서비스 계정: {service_email}")
    print(f"  → 위 이메일에 구글 시트 '편집자' 권한이 있는지 확인하세요.")

    # 데이터 로드
    with open(classified_path, encoding="utf-8") as f:
        entries = json.load(f)
    print(f"  로드된 항목: {len(entries)}개")

    # 자격 증명 및 클라이언트 초기화
    creds = get_credentials(creds_path)
    gc = gspread.authorize(creds)

    try:
        spreadsheet = gc.open_by_key(sheet_id)
    except PermissionError as e:
        raise RuntimeError(
            f"시트 접근 권한 없음 (403).\n\n"
            f"서비스 계정 '{service_email}' 에 구글 시트 편집 권한을 부여해야 합니다.\n\n"
            f"해결 방법:\n"
            f"  1. 업로드할 구글 시트를 열기\n"
            f"  2. 우측 상단 '공유' 버튼 클릭\n"
            f"  3. '사용자 추가'에 아래 이메일을 **정확히** 붙여넣기:\n"
            f"     {service_email}\n"
            f"  4. 권한을 '편집자'로 선택 후 '보내기' 클릭\n"
            f"  5. (선택) '알림 보내기' 체크 해제 후 진행 가능\n\n"
            f"※ 링크 공유만으로는 안 됩니다. 반드시 이메일로 직접 추가해야 합니다."
        ) from e
    except SpreadsheetNotFound as e:
        raise RuntimeError(
            f"시트를 찾을 수 없습니다 (404). 시트 ID가 올바른지 확인하세요."
        ) from e
    except APIError as e:
        err_msg = str(e)
        if "403" in err_msg or "permission" in err_msg.lower():
            raise RuntimeError(
                f"시트 접근 권한 없음. 구글 시트 '공유'에 '{service_email}' 편집자로 추가했는지 확인하세요."
            ) from e
        raise RuntimeError(f"구글 API 호출 실패: {e}") from e

    print(f"  시트 연결 성공: {spreadsheet.title}")

    # 표준어 기준 1:M 그룹화
    grouped = group_by_standard_term(entries)
    print(f"  표준어 기준 그룹화: {len(entries)}개 항목 → {len(grouped)}개 표준어")

    today = date.today().isoformat()
    ws = get_or_create_sheet(spreadsheet, SHEET_MAIN)

    # 기존 시트 헤더 확인 후 형식이 다르면 업데이트
    try:
        existing = ws.row_values(1)
        if not existing or existing[0] != HEADERS[0]:
            ws.update(f"A1:{chr(ord('A') + len(HEADERS) - 1)}1", [HEADERS])
            print(f"  [INFO] 헤더 행 업데이트 완료")
    except Exception:
        pass

    stats = upload_grouped_to_sheet(ws, grouped, today)
    print(f"\n  [팬덤사전] 추가: {stats['added']}개, 업데이트: {stats['updated']}개")

    print(f"\n[sheets_uploader] 완료")
    return {SHEET_MAIN: stats}


if __name__ == "__main__":
    stats = upload_all()
    print("\n=== 업로드 요약 ===")
    for sheet_name, s in stats.items():
        print(f"  {sheet_name}: +{s['added']}개 추가, {s['updated']}개 업데이트")
