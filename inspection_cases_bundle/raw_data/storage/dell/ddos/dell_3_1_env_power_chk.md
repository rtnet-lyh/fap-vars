# 영역
SAN 스위치

# 세부 점검항목
전원공급 장치 점검

# 점검 내용
SAN 스위치 SFP 정보 및 상태 확인

# 구분
권고

# 명령어
```bash
enclosure show powersupply
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# enclosure show powersupply
This command may take up to a minute to complete. Please wait...
Enclosure   Description      Status
---------   --------------   ------
1           Power module 0   OK
1           Power module 1   OK
2           Power module A   OK
2           Power module B   OK
---------   --------------   ------

```

# 설명
- enclosure show powersupply 명령어를 통해 스토리지 전원 공급 장치 (Power Supply Module) 상태를 확인할 수 있음
- 각 Enclosure에 장착된 전원 모듈의 정상 동작 여부 및 장애 상태를 점검
- Status 항목을 통해 각 Power Module 상태를 확인하며, 일반적으로 ok 상태일 경우 정상으로 판단

# 임계치


# 판단기준
- **양호**: 명령어 출력값에서 모든 Power module 상태가 'ok'로 표시되는 경우 
- **경고**: 명령어 출력값에서 모든 Power module 상태가 'ok'로 표시되지 않는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
