# 영역
로그

# 세부 점검항목
클러스터 로그

# 점검 내용
서버 클러스터 노드의 상태변경 발생 점검(Resource Status Change Unknown/Offline/Online, Cluster Error)

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'cluster\|resource status\|unknown\|offline\|online\|error'
```

# 출력 결과
```text
[    0.025423] Unknown kernel command line parameters "rhgb BOOT_IMAGE=(hd0,msdos1)/vmlinuz-5.14.0-70.13.1.el9_0.x86_64", will be passed to user space.
[    0.341199] pci_bus 0000:ff: Unknown NUMA node; performance will be reduced
[    0.346354] pci_bus 0000:7f: Unknown NUMA node; performance will be reduced
[    0.439458] ERST: Error Record Serialization Table (ERST) support is initialized.
[    2.166432] megaraid_sas 0000:01:00.0: current msix/online cpus      : (25/24)
[    2.215766] megaraid_sas 0000:01:00.0: Online Controller Reset(OCR)  : Enabled
```

# 설명
- 본 항목은 `dmesg` 커널 로그에서 클러스터, 리소스 상태 변경, Unknown/Offline/Online, Error 관련 문자열을 조회하여 클러스터 노드 또는 리소스 상태 변경 징후를 확인한다.
- 예시 출력의 `Unknown kernel command line parameters`는 커널이 인식하지 못한 부팅 파라미터 안내이며, 클러스터 리소스의 `Unknown` 상태를 의미하지 않는다.
- `Unknown NUMA node`는 PCI 장치의 NUMA 노드 정보 확인 메시지이고, `ERST: Error Record Serialization Table`은 ACPI 오류 기록 테이블 초기화 로그이다. 단독으로 클러스터 상태 변경이나 클러스터 장애로 판단하지 않는다.
- `current msix/online cpus`, `Online Controller Reset(OCR) : Enabled`는 컨트롤러 또는 CPU 온라인 상태/기능 관련 메시지이며, 클러스터 리소스 `Online` 전환 이벤트와 구분해서 해석한다.
- 사용자 확인용 명령은 검색 범위가 넓어 정상 부팅 로그도 함께 출력될 수 있다. 최종 판정은 `cluster_log_fail_keywords`에 포함된 클러스터 상태 이상 키워드가 검출되고, `cluster_log_execpt_keywords` 예외 키워드에 해당하지 않는 로그가 남는지를 기준으로 한다.
- 장애 키워드가 검출되면 같은 시간대의 클러스터 매니저 로그, `/var/log/messages`, `journalctl`, 스토리지/HBA/RAID 컨트롤러 로그를 함께 확인하여 클러스터 리소스 상태 변경과 실제 장치 링크 장애의 연관성을 판단한다.

# 임계치
cluster_log_fail_keywords: resource status unknown|resource status offline|resource status online|cluster error|cluster failed|failover failed|quorum lost|node down|node offline|fencing failed|stonith failed|split brain
cluster_log_execpt_keywords: unknown kernel command line|unknown numa node|error record serialization table|online controller reset|online cpus|sata link down

# 판단기준
- **양호**: `dmesg` 조회 결과에서 `cluster_log_fail_keywords`에 정의된 클러스터 장애 또는 상태 변경 키워드가 검출되지 않거나, 검출 로그가 예외 키워드에 해당하여 제외되는 경우
- **실패**: `cluster_log_fail_keywords`에 포함된 키워드가 하나 이상 확인되고 `cluster_log_execpt_keywords` 예외 키워드에 해당하지 않는 경우
- **참고**: `resource status online`은 정상 상태 자체가 아니라 클러스터 리소스 상태 변경 로그를 식별하기 위한 키워드로 사용하며, 일반 커널의 `online cpus`, `Online Controller Reset` 같은 로그는 예외 키워드로 제외한다.
