# BTS 포토카드 시세 분석 웹사이트

![Project Status](https://img.shields.io/badge/status-ready%20for%20deployment-brightgreen)
![Data Source](https://img.shields.io/badge/data-Bunjang-purple)
![License](https://img.shields.io/badge/license-Internal-blue)

## 프로젝트 개요

글로벌번장의 **50,000개 실거래 데이터**를 분석하여 BTS 포토카드의 시세를 시각화한 웹사이트입니다. 사용자들이 포토카드의 적정 가격을 쉽게 파악할 수 있도록 중앙값 기반의 시세 정보와 시계열 그래프를 제공합니다.

## 주요 기능

### 1. 포토카드 분류 시스템
- **299개 포토카드 종류** 자동 분류
- 멤버별 구분 (RM, 진, 슈가, 제이홉, 지민, 뷔, 정국, 단체)
- 앨범/시즌별 구분 (PROOF, MAP OF THE SOUL, BE, LOVE YOURSELF 등)
- 특수 타입 구분 (럭드포, 위버스포, 공포, 시그포 등)

### 2. 시세 분석
- **중앙값 기반 시세** (이상치 제거 알고리즘 적용)
- 최저가/최고가/평균가 표시
- 거래량 기반 신뢰도 (최소 3건 이상)
- 시계열 그래프 (최근 30개 거래 추이)

### 3. 사용자 경험
- **파스텔톤 디자인** (핑크/블루 그라디언트)
- **모바일 반응형** (Mobile First)
- **멤버별 필터링** (원클릭)
- **카드형 레이아웃** (직관적 정보 구조)
- **Chart.js 그래프** (부드러운 애니메이션)

## 기술 스택

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Chart Library**: Chart.js 4.x
- **Data Analysis**: Python 3.9+
- **Data Source**: Redash API (글로벌번장 DB)
- **Deployment**: Vercel / Netlify (권장)

## 디렉토리 구조

```
fandom_dict/
├── bts_photocard_analyzer.py      # 데이터 분석 및 HTML 생성 스크립트
├── bts_photocard_market.html      # 최종 웹페이지 (배포용)
├── vercel.json                     # Vercel 배포 설정
├── DEPLOYMENT.md                   # 상세 배포 가이드
├── README.md                       # 프로젝트 개요 (이 파일)
└── ../bts_photocard_data.json     # Redash API 원본 데이터 (72MB)
```

## 빠른 시작

### 1. 로컬에서 확인

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling/fandom_dict

# 간단한 HTTP 서버 실행
python3 -m http.server 8000

# 브라우저에서 열기
open http://localhost:8000/bts_photocard_market.html
```

### 2. 데이터 업데이트

```bash
# 1) Redash에서 최신 데이터 페치 (필수)
# .env에 REDASH_API_KEY 설정 또는:
REDASH_API_KEY=your_key python3 fetch_redash_data.py

# 2) HTML 생성 (페치 후)
python3 bts_photocard_analyzer.py

# 한 번에: 페치 + HTML 생성
REDASH_API_KEY=your_key python3 fetch_redash_data.py --analyze
```

**매일 오전 10시 자동 업데이트**: `SCHEDULE.md` 참고

### 3. 배포 (Vercel 권장)

```bash
# Vercel CLI 설치
npm install -g vercel

# 배포 (프로젝트 디렉토리에서)
vercel --prod
```

자세한 배포 방법은 `DEPLOYMENT.md`를 참고하세요.

## 분석 결과

### 데이터 통계
- **총 상품 수**: 50,000개
- **분석된 포토카드**: 299종류
- **평균 시세**: 자동 계산
- **거래량 TOP 3**:
  1. 가장 많이 거래된 포카
  2. 두 번째로 많이 거래된 포카
  3. 세 번째로 많이 거래된 포카

### 인사이트
- 최근 2년 데이터 기반 분석
- 이상치 제거를 통한 신뢰도 높은 시세
- 시계열 분석으로 트렌드 파악 가능

## 스크린샷

### 데스크톱 뷰
```
┌─────────────────────────────────────────┐
│   BTS 포토카드 시세 분석                │
│   글로벌번장 실거래 데이터 기반          │
│                                          │
│  [299종]  [50,000건]  [평균 시세]       │
│                                          │
│  [전체] [RM] [진] [슈가] [제이홉]...     │
├─────────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │ 포카1│  │ 포카2│  │ 포카3│          │
│  │ 그래프│  │ 그래프│  │ 그래프│          │
│  └──────┘  └──────┘  └──────┘          │
└─────────────────────────────────────────┘
```

### 모바일 뷰
```
┌──────────────┐
│ BTS 시세 분석│
│              │
│  [필터 버튼] │
├──────────────┤
│  ┌────────┐  │
│  │  포카1  │  │
│  │  그래프 │  │
│  └────────┘  │
│  ┌────────┐  │
│  │  포카2  │  │
│  │  그래프 │  │
│  └────────┘  │
└──────────────┘
```

## 비즈니스 임팩트

### 목표
1. **검색 품질 개선**: 인기 포토카드 데이터 수집
2. **사용자 신뢰도 향상**: 투명한 시세 정보 제공
3. **트래픽 증가**: 외부 유입 → 글로벌번장 전환
4. **킬러피처**: 경쟁사 대비 차별화 (StockX, GOAT 벤치마킹)

### KPI
- **페이지뷰**: 1주일 내 1,000 PV 목표
- **평균 체류시간**: 3분 이상
- **이탈률**: 40% 이하
- **멤버별 인기도**: 클릭 분석
- **전환율**: 시세 확인 → 글로벌번장 방문

## 다음 단계

### Phase 1: 베타 테스트 (1-2주)
- [ ] Google Analytics 연결
- [ ] Vercel 배포
- [ ] 내부 테스트 (10명)
- [ ] 초기 피드백 수집

### Phase 2: 기능 개선 (2-4주)
- [ ] 검색 기능 추가
- [ ] 가격 알림 기능
- [ ] 이미지 API 연동 (실제 포카 이미지)
- [ ] 상품 페이지 링크 연결

### Phase 3: 확장 (1-3개월)
- [ ] 다른 그룹 추가 (SEVENTEEN, BLACKPINK 등)
- [ ] 실시간 데이터 업데이트
- [ ] 사용자 위시리스트 기능
- [ ] 가격 예측 ML 모델

## 기술적 특징

### 데이터 처리
- **멤버 인식**: 7가지 패턴 매칭
- **앨범 분류**: 15개 주요 앨범 자동 인식
- **특수 타입**: 10가지 포카 타입 분류
- **이상치 제거**: IQR 방법 (Q1-1.5IQR, Q3+1.5IQR)

### 성능 최적화
- **파일 크기**: 451KB (최적화 가능)
- **로딩 속도**: Chart.js CDN 사용
- **반응형**: CSS Grid + Flexbox
- **SEO**: 메타 태그 최적화

## 문의 및 기여

### 버그 리포트
이슈가 발견되면 다음 정보와 함께 제보해주세요:
- 브라우저 및 버전
- 디바이스 타입 (Desktop/Mobile)
- 재현 방법
- 스크린샷

### 기여 방법
1. Fork this repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 라이선스

이 프로젝트는 글로벌번장 내부용입니다. 외부 배포 시 법무팀 검토가 필요합니다.

## 크레딧

- **데이터 소스**: 글로벌번장 (Redash API)
- **차트 라이브러리**: Chart.js
- **디자인 영감**: Airbnb, Notion

---

**만든 날짜**: 2026-02-25
**마지막 업데이트**: 2026-02-25
**버전**: 1.0.0
