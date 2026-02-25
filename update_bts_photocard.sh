#!/bin/bash
# BTS 포토카드 데이터 + HTML 매일 업데이트 스크립트
# cron 예: 0 10 * * * /Users/mosa/Documents/BGZT/Auto/SlangCrawling/update_bts_photocard.sh

cd "$(dirname "$0")"

# .env에서 REDASH_API_KEY 로드 (프로젝트 루트 또는 fandom_dict)
if [ -f .env ]; then
  set -a && source .env && set +a
elif [ -f fandom_dict/.env ]; then
  set -a && source fandom_dict/.env && set +a
fi

if [ -z "$REDASH_API_KEY" ]; then
  echo "[ERROR] REDASH_API_KEY가 설정되지 않았습니다."
  echo "  .env 파일에 REDASH_API_KEY=your_key 추가"
  exit 1
fi

echo "$(date '+%Y-%m-%d %H:%M') BTS 포토카드 업데이트 시작"
python3 fetch_redash_data.py || exit 1
python3 bts_photocard_analyzer.py --all-locales || exit 1

# index.html 동기화 (한국어 버전 배포용)
cp bts_photocard_market.html index.html
# en/index.html (영어 버전 /en/ 접근용)
cp en/bts_photocard_market.html en/index.html 2>/dev/null || true
echo "$(date '+%Y-%m-%d %H:%M') 완료"
exit 0
