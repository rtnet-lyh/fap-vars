# 영역
CONNECTION

# 세부 점검항목
WinRM 연결 확인

# 점검 내용
WinRM PowerShell 실행 및 응답 확인

# 구분
필수

# 명령어
```powershell
Write-Output 'USER=Administrator'; Write-Output 'HOST=WIN-DEMO'
```

# 출력 결과
```text
USER=Administrator
HOST=WIN-DEMO
```

# 설명
- WinRM PowerShell 실행 경로가 정상인지 확인한다.
- 명령 실행 결과에서 사용자와 호스트 값이 반환되면 기본 연결 및 PowerShell 실행이 가능한 상태로 본다.

# 임계치
없음

# 판단기준
- **양호**: WinRM PowerShell 명령이 정상 실행되고 USER/HOST 값이 확인되는 경우
- **경고**: WinRM 실행 환경을 사용할 수 없거나 명령 실행에 실패한 경우
