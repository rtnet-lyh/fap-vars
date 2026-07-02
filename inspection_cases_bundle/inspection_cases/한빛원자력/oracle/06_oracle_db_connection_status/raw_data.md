# 영역
CONNECTION

# 세부 점검 항목
DB 접속 상태

# 점검 내용
Windows 환경에서 Oracle 클라이언트 명령으로 실제 접속 가능 여부를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SELECT ''DB is accessible'' FROM dual;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
DB is accessible
```

# 설명
- 서비스 기동 여부와 별개로, 실제 SQL 클라이언트 접속이 성공해야 정상입니다.
- 테스트 질의가 실패하면 인증, 인스턴스 상태, 네트워크 문제를 우선 의심합니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`
- 참고: 접속 계정 또는 인증 방식이 다르면 SQL 클라이언트 호출부도 함께 수정

# 임계치
- `success_keyword`: `DB is accessible`
- `failure_keywords`: `ORA-,ERROR,FATAL,Access denied,connection failed`

# 판단기준
- **정상**: 클라이언트 접속과 테스트 질의가 모두 성공합니다.
- **불량**: 인증 오류, 인스턴스 비정상, 통신 문제 등으로 접속이 실패합니다.
