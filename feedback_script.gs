/**
 * BTS 포토카드 피드백 수집 - Google Apps Script
 *
 * 설정 방법:
 * 1. Google Sheets에서 새 스프레드시트 생성
 * 2. 확장 프로그램 > Apps Script 클릭
 * 3. 이 코드를 붙여넣기
 * 4. 배포 > 새 배포 > 유형: 웹 앱
 * 5. 실행 권한: 나, 액세스 권한: 모든 사용자 (익명 포함)
 * 6. 배포 후 받은 웹 앱 URL을 bts_photocard_analyzer.py에 설정
 */

function doPost(e) {
  try {
    // JSON 데이터 파싱
    const data = JSON.parse(e.postData.contents);

    // 스프레드시트 가져오기 (현재 스크립트가 연결된 시트)
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // 헤더가 없으면 추가
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        'Timestamp',
        'Locale',
        'Usefulness',
        'Suggestions',
        'URL',
        'User Agent',
        'IP Address'
      ]);

      // 헤더 스타일 설정
      const headerRange = sheet.getRange(1, 1, 1, 7);
      headerRange.setFontWeight('bold');
      headerRange.setBackground('#4285f4');
      headerRange.setFontColor('#ffffff');
    }

    // 데이터 행 추가
    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.locale || 'unknown',
      data.usefulness || '',
      data.suggestions || '',
      data.url || '',
      e.parameter.userAgent || '',
      e.parameter.remoteAddress || ''
    ]);

    // 최신 행에 스타일 적용
    const lastRow = sheet.getLastRow();
    const dataRange = sheet.getRange(lastRow, 1, 1, 7);

    // usefulness에 따라 색상 구분
    if (data.usefulness === 'yes') {
      dataRange.getCell(1, 3).setBackground('#d4edda'); // 초록
    } else if (data.usefulness === 'no') {
      dataRange.getCell(1, 3).setBackground('#f8d7da'); // 빨강
    } else if (data.usefulness === 'maybe') {
      dataRange.getCell(1, 3).setBackground('#fff3cd'); // 노랑
    }

    // 자동 열 너비 조정
    sheet.autoResizeColumns(1, 7);

    // 성공 응답
    return ContentService.createTextOutput(JSON.stringify({
      status: 'success',
      message: 'Feedback received'
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    // 에러 응답
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// GET 요청 처리 (테스트용)
function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: 'ok',
    message: 'BTS Photocard Feedback Collector is running',
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}
