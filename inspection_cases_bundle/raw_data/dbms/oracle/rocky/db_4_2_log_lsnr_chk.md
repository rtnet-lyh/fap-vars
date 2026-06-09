# 영역
로그 점검

# 세부 점검항목
리스너(DB 서비스 연결) 로그 파일 점검

# 점검 내용
리스너를 통해 DB에 접근하는 클라이언트에 대한 로그 파일로 세션 접속(WAS와 DB간)에 문제가 있는지 점검

# 구분
필수

# 명령어
```bash
grep -i -E 'connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170' /koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log || echo '에러로그없음'
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem> grep -i -E 'connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170' /koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log || echo '에러로그없음'
에러로그없음




---
```

# 설명
- `alert.log` 및 `listener.log`, `*.trc` 등의 파일 내용을 점검하여 DB와 리스너에서 발생한 오류나 경고를 파악합니다.

# 임계치
에러 로깅 빈도 및 치명적 에러 존재 여부

# 판단기준
- **양호**: 시스템 장애를 유발할 수 있는 치명적인 에러 로그가 없음
- **경고**: 서비스 지연이나 장애를 일으키는 에러 다수 발생
- **확인 필요**: 파일 경로 오류 등으로 로그 확인 불가
