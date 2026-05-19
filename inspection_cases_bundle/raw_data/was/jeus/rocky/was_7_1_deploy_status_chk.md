# 영역
소스 배포 상태

# 세부 점검항목
Deploy 상태 점검

# 점검 내용
각 컨테이너별 Application Deploy 상태 확인(비정상시 특정서비스 불가)

# 구분
권고

# 명령어
```bash
jeusadmin -u jeus -p jeus -f listApplications
```

# 출력 결과(정상 출력)
```text
Application Name    | Deployment Status | Running Instances
-----------------------------------------------------------
myApp               | deployed          | 2 (server1, server2)
otherApp            | not deployed      | 0
```

# 출력 결과(접속 불가 출력)
```text
[exTMS@sd_tipswebwas:/home/exTMS]$ jeusadmin -u jeus -p jeus -f listApplications
Attempting to connect to 127.0.0.1:9736.
The connection failed: fail to connect to 127.0.0.1:9736(/JeusMBeanServer), the node is not ready.
```

# 설명
- Deployment Status: 애플리케이션 목록과 Deploy 상태 여부를 확인할 수 있음

# 임계치


# 판단기준 - 수동 확인 필요
- **양호**: `Deployment Status`값이 "deployed"인 상태
- **경고**: `Deployment Status`값이 "not deployed" 상태
- **확인 필요**: 출력이 없거나 jeusadmin 명령어 실행불가(권한/미설치/미기동 등)로 점검 불가한 상태