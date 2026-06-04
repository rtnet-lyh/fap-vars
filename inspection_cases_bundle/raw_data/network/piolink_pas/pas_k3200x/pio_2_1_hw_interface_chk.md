# 영역
HW 상태

# 세부 점검항목
인터페이스/모듈 상태

# 점검 내용
각 인터페이스/Module Down/up 상태 점검 및 CRC error 증가 여부 확인

# 구분
필수

# 명령어
```bash
show port
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show port

================================================================================
PORT Configuration
 ------------------------------------------------------------------------------
  Port  Link  Status  Speed MaxSpeed Duplex Auto Nego MDI/MDIX Flow  Cable  Jumbo-Frame Description
  1     down  disable 10000 10000    --     disable   --       off   fiber  disable
  2     down  disable 10000 10000    --     disable   --       off   fiber  disable
  3     down  disable 10000 10000    --     disable   --       off   fiber  disable
  4     down  disable 10000 10000    --     disable   --       off   fiber  disable
  5     down  disable 1000  1000     --     enable    --       off   fiber  disable
  6     down  disable 1000  1000     --     enable    --       off   fiber  disable
  7     down  disable 1000  1000     --     enable    --       off   fiber  disable
  8     down  disable 1000  1000     --     enable    --       off   fiber  disable
  9     down  disable 1000  1000     --     enable    --       off   fiber  disable
  10    down  disable 1000  1000     --     enable    --       off   fiber  disable
  11    down  disable 1000  1000     --     enable    --       off   fiber  disable
  12    up    enable  1000  1000     --     disable   --       off   fiber  disable     ## Falcon_auto_8.191 ##
  13    up    enable  1000  1000     --     enable    --       off   fiber  disable     ## Center_Switch_A ##
  14    up    enable  1000  1000     --     enable    --       off   fiber  disable     ## Center_PAS-K3200X_B ##
  15    up    enable  1000  1000     --     enable    --       off   fiber  disable     ## Center_PAS-K3200X_B ##
  16    up    enable  1000  1000     --     enable    --       off   fiber  disable     ## Center_FW_A ##
  17    down  disable 0     1000     half   enable    auto     off   copper disable
  18    up    enable  1000  1000     full   enable    auto     off   copper disable     ## ATMS_Server_2_eth0 ##
  19    down  disable 0     1000     half   enable    auto     off   copper disable
  20    down  disable 0     1000     half   enable    auto     off   copper disable
  21    down  disable 0     1000     half   enable    auto     off   copper disable
  22    down  disable 0     1000     half   enable    auto     off   copper disable
  23    down  disable 0     1000     half   enable    auto     off   copper disable
  24    down  disable 0     1000     half   enable    auto     off   copper disable
  agg1  --    enable  --             --     --        --       --    --     disable
================================================================================
```

# 설명
- Link: 물리적인 링크 상태(= 실제 케이블/상대 장비 연결 상태)
- Status: 관리자(Admin) 설정 상태로, 포트를 사용 가능하게 설정했는지 여부

# 임계치

# 판단기준
- **양호**: Link값이 'up'이고, Status값이 'enable'인 상태
- **경고**: Link값이 'down'이거나 Status값이 'disable'인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
