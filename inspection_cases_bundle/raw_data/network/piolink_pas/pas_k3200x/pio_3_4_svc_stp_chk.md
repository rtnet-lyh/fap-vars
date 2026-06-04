# 영역
서비스  

# 세부 점검항목
STP 상태 점검

# 점검 내용
STP 설정을 통해 Loop구조를 방지하고 원활한 통신상태를 확인

# 구분
권고

# 명령어
```bash
show stp
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show stp

================================================================================
  STP
 ------------------------------------------------------------------------------
    Status               : disable
    Priority             : 8
    Instance Name        :
    Path Cost            :
    Root Max Age         :
    Root Hello Time      :
    Root Forward Delay   :
    Root ID              :
    Root Port            :
    Bridge ID            :
    Bridge Max Age       : 20
    Bridge Hello Time    : 2
    Bridge Forward Delay : 15
    Bpdu-Guard           : disable

    Port
       Name  Status  Link  State Priority Path Cost Portfast Bpdu-Guard Bpdu-Filter Root-Guard
       1     disable down  -     8                  disable  disable    disable     disable
       2     disable down  -     8                  disable  disable    disable     disable
       3     disable down  -     8                  disable  disable    disable     disable
       4     disable down  -     8                  disable  disable    disable     disable
       5     disable down  -     8                  disable  disable    disable     disable
       6     disable down  -     8                  disable  disable    disable     disable
       7     disable down  -     8                  disable  disable    disable     disable
       8     disable down  -     8                  disable  disable    disable     disable
       9     disable down  -     8                  disable  disable    disable     disable
       10    disable down  -     8                  disable  disable    disable     disable
       11    disable down  -     8                  disable  disable    disable     disable
       12    enable  up    -     8                  disable  disable    disable     disable
       13    enable  up    -     8                  disable  disable    disable     disable
       14    enable  up    -     8                  disable  disable    disable     disable
       15    enable  up    -     8                  disable  disable    disable     disable
       16    enable  up    -     8                  disable  disable    disable     disable
       17    disable down  -     8                  disable  disable    disable     disable
       18    enable  up    -     8                  disable  disable    disable     disable
       19    disable down  -     8                  disable  disable    disable     disable
       20    disable down  -     8                  disable  disable    disable     disable
       21    disable down  -     8                  disable  disable    disable     disable
       22    disable down  -     8                  disable  disable    disable     disable
       23    disable down  -     8                  disable  disable    disable     disable
       24    disable down  -     8                  disable  disable    disable     disable
================================================================================
```

# 설명
- STP는 네트워크 Loop 구조를 방지하고 이중화 환경에서 안정적인 통신을 유지하기 위한 기능
- Status 항목을 통해 STP 활성 여부를 확인 가능
- Port별 Link 및 STP 상태를 확인 가능
- BPDU Guard, Root Guard 등의 Loop 방지 설정 상태를 확인 가능


# 임계치

# 판단기준
- **양호**: STP status 값이 'enable'이며 사용 Port의 Link 상태가 'up'인 상태
- **경고**: STP status 값이 'enable'이 아니거나 사용 Port의 Link 상태가 'down'인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
※참고: STP disable 이어도 운영 정책상 정상일 수 있음. 확인 필요. 
