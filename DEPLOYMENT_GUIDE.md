# 배포 가이드 (3가지 방법)

## 방법 1: npx vercel (가장 간단, 추천!)

Vercel CLI 설치 없이 바로 배포 가능합니다.

```bash
# 프로젝트 디렉토리로 이동
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# npx로 직접 실행 (설치 불필요)
npx vercel

# 처음 실행시 질문에 답하기:
# - Set up and deploy? Y
# - Which scope? (본인 계정 선택)
# - Link to existing project? N
# - What's your project's name? bts-photocard-market
# - In which directory is your code located? ./
# - Want to override the settings? N

# 프로덕션 배포
npx vercel --prod
```

**배포 후 자동으로 URL이 생성됩니다!**
예: `https://bts-photocard-market.vercel.app`

---

## 방법 2: GitHub + Vercel 자동 배포 (권장)

GitHub에 push하면 자동으로 배포됩니다.

### Step 1: GitHub 저장소 생성

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# Git 초기화
git init
git add bts_photocard_market.html vercel.json README.md DEPLOYMENT.md
git commit -m "Initial commit: BTS photocard market analysis"

# GitHub에서 새 저장소 생성 후
git remote add origin https://github.com/YOUR_USERNAME/bts-photocard-market.git
git branch -M main
git push -u origin main
```

### Step 2: Vercel 연결

1. https://vercel.com 에서 로그인
2. "New Project" 클릭
3. GitHub 저장소 연결
4. "Import" 클릭
5. 자동으로 배포 완료!

**장점:**
- 코드 수정 후 git push만 하면 자동 재배포
- 프리뷰 URL 자동 생성
- 롤백 가능

---

## 방법 3: 간단한 정적 호스팅 서비스

### Netlify Drop

1. https://app.netlify.com/drop 접속
2. `bts_photocard_market.html` 파일을 드래그 앤 드롭
3. 즉시 배포 완료!

**가장 빠르지만 업데이트가 불편함**

### GitHub Pages

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# docs 폴더로 이동 (또는 직접 index.html로 복사)
cp bts_photocard_market.html index.html

git init
git add index.html
git commit -m "Deploy to GitHub Pages"
git remote add origin https://github.com/YOUR_USERNAME/bts-photocard-market.git
git branch -M main
git push -u origin main

# GitHub 저장소 Settings > Pages 에서:
# - Source: Deploy from a branch
# - Branch: main / (root)
# - Save
```

**URL:** `https://YOUR_USERNAME.github.io/bts-photocard-market`

---

## 빠른 배포 체크리스트

### 1. 배포 전 확인사항
- [ ] 로컬에서 테스트 완료 (`python3 -m http.server 8000`)
- [ ] Google Analytics ID 입력 (선택사항)
- [ ] 파일 크기 확인 (451KB - 정상)

### 2. 배포 명령어 (npx vercel 추천)
```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict
npx vercel --prod
```

### 3. 배포 후 할 일
- [ ] URL 확인 및 테스트
- [ ] 모바일에서 확인
- [ ] Google Analytics 연결
- [ ] URL 공유 (베타 테스터)

---

## 도메인 연결 (선택사항)

Vercel에서 커스텀 도메인 연결 가능:
- 무료: `.vercel.app` 서브도메인
- 유료: 본인 소유 도메인 (예: `photocard.globalbunjang.com`)

### Vercel에서 도메인 설정
1. 프로젝트 > Settings > Domains
2. 도메인 입력 (예: `photocard.globalbunjang.com`)
3. DNS 레코드 추가 (Vercel이 안내)
4. 자동으로 HTTPS 인증서 발급

---

## 문제 해결

### "permission denied" 오류
```bash
# npm 캐시 정리
npm cache clean --force

# 또는 npx 사용 (설치 불필요)
npx vercel
```

### 파일을 찾을 수 없음
```bash
# 현재 디렉토리 확인
pwd
# /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# 파일 존재 확인
ls -la bts_photocard_market.html
```

### Vercel 로그인 필요
```bash
npx vercel login
# 이메일 입력 후 인증 메일 확인
```

---

## 추천 배포 플로우

**가장 빠른 방법 (5분):**
```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict
npx vercel --prod
# URL 복사 → 테스트 → 공유
```

**장기적으로 가장 좋은 방법 (15분):**
1. GitHub 저장소 생성
2. 코드 push
3. Vercel에서 GitHub 연결
4. 자동 배포 완료

---

## 배포 후 모니터링

### Vercel Analytics (무료)
- 실시간 방문자 수
- 페이지 로딩 속도
- 지역별 분포

### Google Analytics
1. https://analytics.google.com 에서 속성 생성
2. 측정 ID 복사 (G-XXXXXXXXXX)
3. `bts_photocard_market.html` 수정:
   - 14줄: `<script async src="https://www.googletagmanager.com/gtag/js?id=G-YOUR_ID"></script>`
   - 19줄: `gtag('config', 'G-YOUR_ID');`
4. 재배포

---

## 데이터 업데이트 방법

### 수동 업데이트
```bash
# 1. 새 데이터 가져오기
python3 bts_photocard_analyzer.py

# 2. HTML 재생성 완료

# 3. 재배포
npx vercel --prod
```

### 자동 업데이트 (GitHub Actions)
`.github/workflows/update.yml` 파일 생성:
```yaml
name: Update BTS Photocard Data
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 새벽 2시
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Update data
        run: python3 bts_photocard_analyzer.py
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add bts_photocard_market.html
          git commit -m "Update photocard data [skip ci]"
          git push
```

Vercel이 자동으로 새 배포를 감지합니다!

---

## 연락처

배포 중 문제가 생기면 Vercel 문서를 참고하세요:
https://vercel.com/docs

또는 Netlify:
https://docs.netlify.com
