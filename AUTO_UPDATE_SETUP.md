# 🤖 자동 업데이트 설정 가이드

BTS 포토카드 시세 데이터를 **매일 자동으로 업데이트**하도록 설정하는 방법입니다.

## 📋 개요

- **실행 시간**: 매일 오전 3시 (UTC) = 한국시간 12시
- **작업 내용**:
  1. Redash에서 최신 데이터 가져오기
  2. 상품명 유사도 분석 및 그룹화
  3. HTML 생성 (한국어 + 영어)
  4. GitHub에 자동 커밋 & 푸시
  5. Vercel 자동 배포

## ⚙️ 설정 방법

### 1️⃣ GitHub Secrets 설정

GitHub 저장소에서 다음 환경변수를 설정해야 합니다:

1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 버튼 클릭
4. 다음 3개 시크릿 추가:

| Name | Value | 설명 |
|------|-------|------|
| `REDASH_API_KEY` | `your_redash_api_key` | Redash API 키 |
| `REDASH_QUERY_ID` | `23818` | 쿼리 ID (기본값) |
| `REDASH_BASE_URL` | `https://redash.bunjang.io` | Redash URL |

#### Redash API 키 찾는 방법:
1. https://redash.bunjang.io 로그인
2. 우측 상단 프로필 아이콘 클릭
3. **Settings** → **API Key** 확인

### 2️⃣ GitHub Actions 활성화 확인

1. GitHub 저장소의 **Actions** 탭으로 이동
2. "Update BTS Photocard Data" workflow가 보이는지 확인
3. 활성화되지 않았다면 **Enable workflow** 클릭

### 3️⃣ 첫 실행 테스트 (수동)

자동 스케줄을 기다리지 않고 바로 테스트하려면:

1. **Actions** 탭 → "Update BTS Photocard Data" 클릭
2. **Run workflow** 버튼 클릭
3. **Run workflow** 확인
4. 실행 로그를 확인하여 성공 여부 확인

### 4️⃣ Vercel 자동 배포 연결 (선택)

GitHub에 푸시되면 Vercel이 자동으로 배포하도록 설정:

1. [Vercel Dashboard](https://vercel.com/dashboard) 접속
2. **Add New** → **Project**
3. GitHub 저장소 연결
4. **Deploy** 클릭

이제 GitHub Actions가 데이터를 업데이트하면 Vercel이 자동으로 배포합니다!

## 📊 실행 스케줄

```yaml
# 매일 오전 3시 (UTC) 실행
cron: '0 3 * * *'
```

한국 시간으로는:
- **여름 (서머타임)**: 오후 12시
- **겨울**: 오후 12시

## 🔧 스케줄 변경하기

실행 시간을 바꾸려면 `.github/workflows/update-photocards.yml` 파일의 cron 표현식을 수정하세요:

```yaml
schedule:
  # 매일 오전 2시 (UTC) = 한국시간 11시
  - cron: '0 2 * * *'

  # 매일 오후 6시 (UTC) = 한국시간 오전 3시
  - cron: '0 18 * * *'

  # 12시간마다 (0시, 12시 UTC)
  - cron: '0 0,12 * * *'
```

### Cron 표현식 형식:
```
* * * * *
│ │ │ │ │
│ │ │ │ └─ 요일 (0-6, 0=일요일)
│ │ │ └─── 월 (1-12)
│ │ └───── 일 (1-31)
│ └─────── 시 (0-23)
└───────── 분 (0-59)
```

도움이 되는 도구: [Crontab.guru](https://crontab.guru/)

## 📁 생성되는 파일

자동 업데이트 시 다음 파일들이 갱신됩니다:

- `bts_photocard_data.json` - Redash에서 가져온 원본 데이터
- `bts_photocard_market.html` - 한국어 시세 페이지
- `en/bts_photocard_market.html` - 영어 시세 페이지

## 🔍 실행 로그 확인

1. GitHub 저장소 → **Actions** 탭
2. 최근 실행된 workflow 클릭
3. 각 단계별 로그 확인 가능

## ⚠️ 문제 해결

### "Error: Process completed with exit code 1"
→ GitHub Secrets가 올바르게 설정되었는지 확인하세요.

### "Redash API 요청 실패"
→ `REDASH_API_KEY`가 만료되었을 수 있습니다. Redash에서 새 키를 발급받으세요.

### "No changes detected"
→ 데이터가 변경되지 않았습니다. 정상 동작입니다.

### 수동 실행 방법
```bash
# 로컬에서 수동 실행
export REDASH_API_KEY="your_key"
python fetch_redash_data.py
python bts_photocard_analyzer.py --all-locales
```

## 📊 모니터링

GitHub Actions는 실행 실패 시 자동으로 이메일을 보냅니다.
추가 알림이 필요하면 `.github/workflows/update-photocards.yml`에 Slack/Discord 알림을 추가할 수 있습니다.

## 🎯 다음 단계

- [ ] GitHub Secrets 설정 완료
- [ ] 첫 수동 실행 테스트
- [ ] Vercel 자동 배포 연결
- [ ] 실행 스케줄 확인 (다음날 12시에 자동 실행되는지)

---

궁금한 점이 있으면 `.github/workflows/update-photocards.yml` 파일을 확인하세요!
