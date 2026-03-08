# 📝 피드백 수집 설정 가이드

BTS 포토카드 시세 페이지에서 사용자 피드백을 Google Sheets로 자동 수집하는 방법입니다.

## 🎯 개요

사용자가 카드에 3번 이상 호버하면 피드백 팝업이 표시되고, 제출된 응답이 Google Sheets에 자동으로 기록됩니다.

**수집 데이터:**
- 유용성 평가 (Yes/Maybe/No)
- 개선 제안 (자유 텍스트)
- 언어 (ko/en)
- 타임스탬프
- 페이지 URL

## 📋 설정 단계

### 1️⃣ Google Sheets 생성

1. [Google Sheets](https://sheets.google.com) 접속
2. **새 스프레드시트 만들기** 클릭
3. 이름: `BTS Photocard Feedback` (또는 원하는 이름)

### 2️⃣ Apps Script 설정

1. 스프레드시트 상단 메뉴: **확장 프로그램** → **Apps Script**
2. 기본 코드 삭제
3. `feedback_script.gs` 파일 내용 전체 복사 → 붙여넣기
4. 저장 (💾 아이콘 또는 Ctrl+S)

### 3️⃣ 웹 앱 배포

1. Apps Script 편집기 우측 상단: **배포** → **새 배포** 클릭
2. 설정:
   - **유형 선택**: ⚙️ 아이콘 → **웹 앱** 선택
   - **설명**: `피드백 수집 웹앱 v1`
   - **실행 권한**: **나**
   - **액세스 권한**: **모든 사용자 (익명 사용자 포함)**
3. **배포** 클릭
4. 권한 승인:
   - 계정 선택
   - "안전하지 않음" 경고 시: **고급** → **{프로젝트명}(으)로 이동** 클릭
   - **허용** 클릭
5. **웹 앱 URL** 복사 (예: `https://script.google.com/macros/s/.../exec`)

### 4️⃣ Python 스크립트에 URL 설정

`bts_photocard_analyzer.py` 파일을 열어서 **웹 앱 URL을 추가**하세요:

```python
# 파일 상단 (STRINGS 딕셔너리 전)에 추가:
FEEDBACK_WEBHOOK_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
```

위의 `YOUR_DEPLOYMENT_ID` 부분을 3단계에서 복사한 실제 URL로 교체하세요.

### 5️⃣ HTML 재생성

터미널에서 실행:
```bash
python3 bts_photocard_analyzer.py --skip-validate --all-locales
```

### 6️⃣ 테스트

1. 생성된 HTML 파일 열기 (`bts_photocard_market.html`)
2. 카드에 3번 이상 호버
3. 피드백 팝업이 나타나면 응답 작성 후 제출
4. Google Sheets로 돌아가서 데이터가 기록되었는지 확인

## 📊 수집된 데이터 확인

Google Sheets에 다음과 같은 형태로 저장됩니다:

| Timestamp | Locale | Usefulness | Suggestions | URL | User Agent | IP Address |
|-----------|--------|------------|-------------|-----|------------|------------|
| 2026-03-09T12:34:56.789Z | ko | yes | 멤버별 필터가 유용해요! | https://... | Mozilla/5.0... | 123.45.67.89 |

**색상 구분:**
- 🟢 초록색: Yes (유용함)
- 🟡 노란색: Maybe (보통)
- 🔴 빨간색: No (불필요)

## 🔧 문제 해결

### "배포 권한이 없습니다" 오류
→ Apps Script 편집기에서 **파일** → **프로젝트 속성** → 소유자 확인

### 피드백이 시트에 기록되지 않음
1. Apps Script 편집기에서 **실행** → `doPost` 함수 테스트
2. 에러 로그 확인: **실행** → **실행 로그 보기**
3. 웹 앱 URL이 Python 스크립트에 정확히 입력되었는지 확인
4. 브라우저 개발자 도구 (F12) → Console 탭에서 네트워크 에러 확인

### CORS 에러 발생
→ Apps Script 웹 앱은 기본적으로 CORS를 허용합니다.
→ 만약 에러가 발생하면 `doPost` 함수 상단에 추가:
```javascript
// Apps Script에서는 불필요하지만, 혹시 모를 CORS 이슈 해결용
const output = ContentService.createTextOutput(JSON.stringify(result));
output.setMimeType(ContentService.MimeType.JSON);
output.setHeader('Access-Control-Allow-Origin', '*');
return output;
```

### 데이터가 중복 저장됨
→ 사용자가 여러 번 제출했거나, localStorage가 작동하지 않을 수 있습니다.
→ 브라우저 개발자 도구 → Application → Local Storage 확인

## 🔒 보안 팁

1. **스프레드시트 공유 설정**: 피드백에 민감한 정보가 있을 수 있으므로 신뢰할 수 있는 사람에게만 공유
2. **정기적인 모니터링**: 스팸이나 악의적인 응답 확인
3. **IP 필터링**: 필요시 Apps Script에서 특정 IP 차단 로직 추가

## 📈 데이터 분석 팁

### 유용성 통계
```
=COUNTIF(C:C, "yes") / COUNTA(C:C)  # Yes 비율
```

### 언어별 응답 수
```
=COUNTIF(B:B, "ko")  # 한국어 응답
=COUNTIF(B:B, "en")  # 영어 응답
```

### 최근 7일 응답
```
=FILTER(A:G, A:A >= TODAY()-7)
```

## 🚀 다음 단계

- [ ] Google Sheets에서 피드백 스프레드시트 생성
- [ ] Apps Script 웹 앱 배포
- [ ] Python 스크립트에 웹 앱 URL 설정
- [ ] HTML 재생성 및 테스트
- [ ] 실제 사용자 피드백 수집 시작!

---

궁금한 점이 있으면 `feedback_script.gs` 파일의 주석을 참고하세요!
