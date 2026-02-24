# 🚀 빠른 배포 가이드 (npm 오류 우회)

## 현재 상황
npm 캐시 권한 문제로 `npx vercel` 명령어가 실행되지 않습니다.
아래 3가지 대체 방법 중 하나를 선택하세요.

---

## 방법 1: Vercel 웹 UI (가장 쉬움, 5분) ⭐ 추천

### Step 1: GitHub에 업로드

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# Git 초기화 (이미 했으면 생략)
git init

# 파일 추가
git add bts_photocard_market.html vercel.json README.md

# 커밋
git commit -m "BTS photocard market analysis website"

# GitHub에 새 저장소 생성 후 (https://github.com/new)
# 저장소 이름: bts-photocard-market
# Public/Private: Private 권장

# 원격 저장소 연결 (YOUR_USERNAME을 실제 GitHub 아이디로 변경)
git remote add origin https://github.com/YOUR_USERNAME/bts-photocard-market.git
git branch -M main
git push -u origin main
```

### Step 2: Vercel에 배포

1. https://vercel.com 접속
2. **"Sign Up"** (GitHub 계정으로 로그인)
3. **"Add New Project"** 클릭
4. **"Import Git Repository"** 선택
5. GitHub에서 `bts-photocard-market` 저장소 선택
6. **"Import"** 클릭
7. 설정은 기본값 그대로 **"Deploy"** 클릭

**배포 완료! URL이 자동으로 생성됩니다.**
예: `https://bts-photocard-market.vercel.app`

---

## 방법 2: Netlify Drop (가장 빠름, 2분)

1. https://app.netlify.com/drop 접속
2. 로그인 (GitHub/Google/Email)
3. `bts_photocard_market.html` 파일을 드래그 앤 드롭
4. 즉시 배포 완료!

**단점:** 파일 업데이트시 매번 수동으로 드래그 앤 드롭 필요

---

## 방법 3: GitHub Pages (무료, 10분)

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# index.html로 복사 (GitHub Pages는 index.html을 찾음)
cp bts_photocard_market.html index.html

# Git 설정
git init
git add index.html
git commit -m "Deploy BTS photocard market"

# GitHub 저장소에 푸시
git remote add origin https://github.com/YOUR_USERNAME/bts-photocard-market.git
git branch -M main
git push -u origin main
```

### GitHub Pages 활성화
1. GitHub 저장소 페이지로 이동
2. **Settings** > **Pages** 메뉴
3. **Source**: Deploy from a branch
4. **Branch**: main / (root)
5. **Save** 클릭
6. 약 1분 후 배포 완료

**URL:** `https://YOUR_USERNAME.github.io/bts-photocard-market`

---

## npm 오류 해결 (선택사항)

나중에 `npx vercel`을 사용하고 싶다면:

```bash
# 1. npm 캐시 폴더 소유권 변경 (비밀번호 입력 필요)
sudo chown -R $(whoami) ~/.npm

# 2. 캐시 정리
npm cache clean --force

# 3. 다시 시도
npx vercel --prod
```

---

## 배포 확인 체크리스트

배포 후 확인할 사항:
- [ ] 웹페이지가 정상적으로 열리는가?
- [ ] 멤버 필터가 작동하는가?
- [ ] 포카 타입 드롭다운이 작동하는가?
- [ ] 검색 기능이 작동하는가?
- [ ] 차트가 표시되는가?
- [ ] 모바일에서도 정상인가?
- [ ] "상품 보러가기" 링크가 작동하는가?

---

## 배포 후 할 일

### 1. Google Analytics 설정 (선택)
```bash
# GA 측정 ID 발급 후
# bts_photocard_market.html 파일 수정:
# - 14줄: G-XXXXXXXXXX → 실제 ID
# - 19줄: G-XXXXXXXXXX → 실제 ID
# 다시 배포
```

### 2. URL 공유
- 팀 슬랙/메일로 공유
- 베타 테스터 10명 모집
- 피드백 수집

### 3. 트래픽 모니터링
- Vercel: 대시보드에서 실시간 확인
- Google Analytics: 상세 분석

---

## 자동 업데이트 설정 (GitHub + Vercel)

GitHub에 push하면 자동 재배포:

```bash
# 데이터 업데이트
python3 bts_photocard_analyzer.py

# Git 커밋
git add bts_photocard_market.html
git commit -m "Update photocard data $(date +%Y-%m-%d)"
git push

# Vercel이 자동으로 새 배포 시작!
```

---

## 커스텀 도메인 연결 (선택)

Vercel에서 커스텀 도메인 무료 연결:
1. Vercel 프로젝트 > Settings > Domains
2. 도메인 입력 (예: `photocard.globalbunjang.com`)
3. DNS 레코드 추가 (Vercel이 안내)
4. HTTPS 자동 활성화

---

## 문제 해결

### "파일을 찾을 수 없음"
```bash
# 현재 위치 확인
pwd
# 결과: /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# 파일 확인
ls -la bts_photocard_market.html
```

### "GitHub push 권한 없음"
```bash
# Personal Access Token 생성 필요
# GitHub Settings > Developer settings > Personal access tokens
# repo 권한 선택 후 토큰 생성
# 비밀번호 대신 토큰 사용
```

### "Vercel 배포 실패"
- vercel.json 파일 확인
- HTML 파일 이름 확인
- 로그 확인 (Vercel 대시보드)

---

## 추천 배포 순서

**지금 당장 테스트하려면:**
→ **방법 2: Netlify Drop** (2분)

**장기적으로 운영하려면:**
→ **방법 1: GitHub + Vercel** (5분, 자동 배포 가능)

**회사 도메인 사용하려면:**
→ **방법 1 + 커스텀 도메인**

---

## 최종 결과

배포 완료 후:
- ✅ 웹사이트 URL 획득
- ✅ HTTPS 자동 적용
- ✅ 글로벌 CDN (빠른 속도)
- ✅ 무료 호스팅
- ✅ 트래픽 분석 가능

---

**배포 후 URL을 공유해주세요!** 🎉
