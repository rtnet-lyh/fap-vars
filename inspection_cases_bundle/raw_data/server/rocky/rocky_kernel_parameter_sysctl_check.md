# 영역
커널

# 세부 점검항목
Kernel Parameter CHeck

# 점검 내용
커널 파라미터 설정값의 기본 설정이 적용되어 있는지를 확인하여 서비스 및 OS 장애를 예방하기 위하여 점검

# 구분
권고

# 명령어
```bash
sysctl -a
```

# 출력 결과
```text
vm.lowmem_reserve_ratio = 256	256	32	0	0
net.ipv4.ip_forward = 1
vm.swappiness = 60
kernel.panic = 0
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.forwarding = 1
```

# 설명
- `sysctl -a` 명령은 현재 커널, 메모리, 파일시스템, 네트워크 관련 런타임 파라미터 값을 조회하기 위한 명령이다.
- 본 항목은 사전에 정의된 임계치 항목의 sysctl 키가 실제 시스템에 존재하는지와, 해당 값이 기준값과 일치하는지를 점검하기 위한 항목이다.
- 예를 들어 `vm.lowmem_reserve_ratio`, `net.ipv4.ip_forward` 와 같은 항목은 시스템 정책 또는 서비스 요구사항에 따라 기준값을 별도로 정의하여 관리한다.
- 점검 시 단순히 명령 실행 여부만 보는 것이 아니라, 임계치에 정의된 키가 출력 결과에 존재하고 기대값과 동일한지 확인해야 한다.
- 기준값과 다른 경우 시스템 동작 방식, 네트워크 포워딩, 메모리 보호 정책 등에 영향을 줄 수 있으므로 설정 검토를 권고한다.

# 임계치
아래의 임계치값 외에 임계치 값을 추가하면 자동반영되야함
vm.lowmem_reserve_ratio
net.ipv4.ip_forward

# 판단기준
- **양호**: 임계치에 정의된 모든 sysctl 키가 `sysctl -a` 출력에 존재하며, 각 설정값이 사전 정의된 기준값과 일치하는 상태
- **주의**: 임계치에 정의된 sysctl 키는 모두 존재하나, 일부 값이 기준값과 상이하여 운영 정책 검토가 필요한 상태
- **경고**: 임계치에 정의된 sysctl 키 중 하나 이상이 출력 결과에 존재하지 않거나, 필수 설정값이 누락된 상태
- **참고**: 다중 값 항목(예: `vm.lowmem_reserve_ratio = 256 256 32 0 0`)은 전체 값 문자열 단위로 기준값과 비교해야 함

# 비고
- become_method를 사용하여 root 권한 획득필요