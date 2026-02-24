# BTS 포토카드 시세 분석 웹사이트 배포 가이드

## 프로젝트 개요
글로벌번장의 실거래 데이터를 기반으로 BTS 포토카드 시세를 분석하고 시각화한 웹사이트입니다.

## 주요 기능
- **299개 포토카드 종류** 분석 (50,000개 상품 데이터 기반)
- **멤버별 필터링** (RM, 진, 슈가, 제이홉, 지민, 뷔, 정국, 단체)
- **시세 중앙값 계산** (이상치 제거 알고리즘 적용)
- **시계열 그래프** (최근 30개 거래 추이)
- **모바일 반응형 디자인** (파스텔톤 UI)

## 데이터 분석 통계
- 총 거래 수: 50,000+ 건
- 포토카드 종류: 299개
- 평균 시세: 자동 계산
- 최소 거래 수: 3건 이상만 포함

## 배포 방법

### 1. Vercel로 배포 (권장)

가장 빠르고 간단한 방법입니다.

```bash
# Vercel CLI 설치
npm install -g vercel

# 배포 (프로젝트 디렉토리에서 실행)
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict
vercel

# 프로덕션 배포
vercel --prod
```

**장점:**
- 무료
- 자동 HTTPS
- 글로벌 CDN
- 실시간 트래픽 분석 제공
- 커스텀 도메인 연결 가능

### 2. Netlify로 배포

```bash
# Netlify CLI 설치
npm install -g netlify-cli

# 배포
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict
netlify deploy

# 프로덕션 배포
netlify deploy --prod
```

### 3. GitHub Pages로 배포

```bash
# Git 저장소 생성
git init
git add bts_photocard_market.html
git commit -m "Initial commit: BTS photocard market analysis"

# GitHub에 푸시
git remote add origin https://github.com/YOUR_USERNAME/bts-photocard-market.git
git branch -M main
git push -u origin main

# GitHub Settings > Pages에서 main 브랜치 선택
```

## Google Analytics 설정

1. [Google Analytics](https://analytics.google.com/)에서 새 속성 생성
2. 측정 ID (G-XXXXXXXXXX) 복사
3. `bts_photocard_market.html` 파일 14, 19줄의 `G-XXXXXXXXXX`를 실제 ID로 교체:

```html
<!-- 14줄 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YOUR_ID"></script>

<!-- 19줄 -->
gtag('config', 'G-YOUR_ID');
```

## 트래픽 측정 지표

### 주요 KPI
- **페이지뷰 (PV)**: 총 방문 수
- **순 사용자 (UV)**: 고유 방문자 수
- **세션 지속 시간**: 평균 체류 시간
- **이탈률**: 한 페이지만 보고 나간 비율

### 이벤트 추적 (추가 구현 가능)
다음 이벤트를 추적하여 사용자 행동 분석:
- 멤버 필터 클릭
- 포토카드 카드 클릭
- 가격대별 필터링
- 검색 기능 사용

이벤트 추적 코드 예시:
```javascript
// 멤버 필터 클릭 추적
gtag('event', 'member_filter', {
  'member_name': member,
  'event_category': 'engagement'
});
```

## 데이터 업데이트

매일/매주 자동으로 데이터를 업데이트하려면:

```bash
# cron job 설정 (매일 새벽 2시)
0 2 * * * cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict && python3 bts_photocard_analyzer.py && vercel --prod
```

또는 GitHub Actions 사용:

```yaml
# .github/workflows/update.yml
name: Update Data
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 새벽 2시
  workflow_dispatch:  # 수동 실행 가능

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Run analysis
        run: python3 bts_photocard_analyzer.py
      - name: Deploy to Vercel
        run: vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
```

## 성능 최적화

현재 HTML 파일 크기가 큰 경우:
- 이미지 lazy loading 추가
- Chart.js를 CDN 대신 번들링
- 멤버별로 페이지 분리

## 모니터링

### Vercel Analytics
배포 후 자동으로 제공되는 지표:
- 실시간 방문자
- 지역별 분포
- 디바이스 타입
- 페이지 로딩 속도

### Google Analytics 대시보드
- 실시간 사용자 수
- 인기 멤버/포토카드
- 사용자 유입 경로
- 전환율 분석

## 예상 임팩트

### 비즈니스 목표
1. **사용자 인게이지먼트 증가**: 평균 체류 시간 3분+ 목표
2. **검색 품질 개선 데이터**: 어떤 포카가 인기인지 파악
3. **사용자 신뢰도 향상**: 투명한 시세 정보 제공
4. **트래픽 증가**: 글로벌번장 메인 사이트로 유입

### 측정 방법
- **1주차**: 초기 트래픽 측정 (베타 사용자)
- **2주차**: 인기 포토카드 TOP 10 분석
- **3주차**: 사용자 피드백 수집
- **4주차**: 전환율 측정 (시세 확인 → 글로벌번장 방문)

## 파일 구조

```
fandom_dict/
├── bts_photocard_analyzer.py      # 데이터 분석 스크립트
├── bts_photocard_market.html      # 웹페이지 (배포 파일)
├── vercel.json                     # Vercel 설정
├── DEPLOYMENT.md                   # 배포 가이드 (이 파일)
└── ../bts_photocard_data.json     # Redash에서 가져온 원본 데이터
```

## 문제 해결

### HTML 파일이 너무 큰 경우
현재 파일 크기를 확인:
```bash
ls -lh bts_photocard_market.html
```

해결 방법:
1. 차트 데이터를 외부 JSON 파일로 분리
2. 멤버별로 페이지 분리
3. 서버 사이드 렌더링 (Next.js 등)

### 데이터 업데이트가 안 되는 경우
Redash API 키 확인:
```bash
curl -H "Authorization: Key lKBmNOl2aew5VY9lduiOqG8esfVBcSMMrWTRqOKD" \
     "https://redash.bunjang.io/api/queries/23818/results.json"
```

## 다음 단계

### 단기 (1-2주)
- [ ] Google Analytics 설정 완료
- [ ] Vercel/Netlify 배포
- [ ] 베타 테스트 사용자 10명 모집
- [ ] 초기 트래픽 분석

### 중기 (1개월)
- [ ] 검색 기능 추가
- [ ] 가격 알림 기능
- [ ] 다른 그룹 확장 (SEVENTEEN, BLACKPINK 등)
- [ ] 사용자 피드백 수집

### 장기 (3개월)
- [ ] 글로벌번장 메인 사이트와 연동
- [ ] 실시간 시세 업데이트
- [ ] 포토카드 거래 추천 기능
- [ ] 커뮤니티 기능 추가

## 연락처
질문이나 피드백이 있으면 언제든지 연락주세요!
