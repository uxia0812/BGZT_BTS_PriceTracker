# BTS 포토카드 데이터 매일 업데이트 스케줄

리대시 쿼리가 매일 오전 10시에 돌아간다면, 아래 설정으로 로컬에서도 같은 시간에 데이터를 가져와 HTML을 갱신할 수 있습니다.

## 사전 준비

1. **.env 파일 생성**

```bash
cd /Users/mosa/Documents/BGZT/Auto/SlangCrawling
cp .env.example .env
# .env 편집: REDASH_API_KEY=실제_API_키
```

2. **실행 권한 확인**

```bash
chmod +x update_bts_photocard.sh
```

## 방법 1: cron (macOS/Linux)

```bash
crontab -e
```

아래 줄 추가 (경로를 본인 프로젝트 경로로 수정):

```
0 10 * * * /Users/mosa/Documents/BGZT/Auto/SlangCrawling/update_bts_photocard.sh >> /Users/mosa/Documents/BGZT/Auto/SlangCrawling/logs/update.log 2>&1
```

`logs` 폴더가 없으면 `mkdir -p logs`로 생성 후 설정하세요.

## 방법 2: launchd (macOS 권장)

launchd는 cron보다 macOS에서 안정적으로 동작합니다.

1. **plist 파일 생성**

`~/Library/LaunchAgents/com.bgzt.bts-photocard-update.plist` 파일을 만들고 아래 내용 저장 (경로를 본인 프로젝트로 수정):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.bgzt.bts-photocard-update</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/mosa/Documents/BGZT/Auto/SlangCrawling/update_bts_photocard.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/mosa/Documents/BGZT/Auto/SlangCrawling</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>10</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/mosa/Documents/BGZT/Auto/SlangCrawling/logs/launchd.out</string>
  <key>StandardErrorPath</key>
  <string>/Users/mosa/Documents/BGZT/Auto/SlangCrawling/logs/launchd.err</string>
</dict>
</plist>
```

2. **실행 및 등록**

```bash
mkdir -p /Users/mosa/Documents/BGZT/Auto/SlangCrawling/logs
launchctl load ~/Library/LaunchAgents/com.bgzt.bts-photocard-update.plist
```

3. **등록 해제**

```bash
launchctl unload ~/Library/LaunchAgents/com.bgzt.bts-photocard-update.plist
```

## 수동 실행

```bash
./update_bts_photocard.sh
```
