# 영역
로그

# 세부 점검항목
NIC 로그

# 점검 내용
NIC 정상 유무 점검(Ipmp Fail over 및 Status Up/Down, Link Down)

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'nic\|link\|ipmp\|failover\|status\|up\|down'
```

# 출력 결과
```text
[    0.000000] microcode: microcode updated early to revision 0x49, date = 2021-08-11
[    0.000000] x86/fpu: Supporting XSAVE feature 0x001: 'x87 floating point registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x002: 'SSE registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x004: 'AVX registers'
[    0.000739] e820: update [mem 0x00000000-0x00000fff] usable ==> reserved
[    0.010605] Initmem setup node 0 [mem 0x0000000000001000-0x000000027fffffff]
[    0.010609] Initmem setup node 1 [mem 0x0000000280000000-0x000000047fffffff]
[    0.023419] setup_percpu: NR_CPUS:8192 nr_cpumask_bits:24 nr_cpu_ids:24 nr_node_ids:2
[    0.025302] Built 2 zonelists, mobility grouping on.  Total pages: 4027176
[    0.081062] ftrace: allocated 169 pages with 4 groups
[    0.092743] APIC: Switch to symmetric I/O mode setup
[    0.093641] x2apic: IRQ remapping doesn't support X2APIC mode
[    0.098886] LSM support for eBPF active
[    0.110954] smp: Bringing up secondary CPUs ...
[    0.225473] smp: Brought up 2 nodes, 24 CPUs
[    0.256204] NET: Registered PF_NETLINK/PF_ROUTE protocol family
[    0.256374] audit: initializing netlink subsys (disabled)
[    0.256383] ACPI FADT declares the system doesn't support PCIe ASPM, so disable it
[    0.291832] ACPI: PM: (supports S0 S4 S5)
[    0.291834] ACPI: Using IOAPIC for interrupt routing
[    0.315308] acpi PNP0A08:00: _OSC: OS supports [ExtendedConfig ASPM ClockPM Segments MSI EDR HPX-Type3]
[    0.315883] acpi PNP0A08:00: FADT indicates ASPM is unsupported, using BIOS configuration
[    0.316911] pci 0000:00:01.0: PME# supported from D0 D3hot D3cold
[    0.317177] pci 0000:00:02.0: PME# supported from D0 D3hot D3cold
[    0.317427] pci 0000:00:02.2: PME# supported from D0 D3hot D3cold
[    0.317675] pci 0000:00:03.0: PME# supported from D0 D3hot D3cold
[    0.317922] pci 0000:00:03.2: PME# supported from D0 D3hot D3cold
```

# 설명
- 본 항목은 `dmesg` 커널 로그에서 NIC, link, IPMP, failover, status, up, down 관련 문자열을 조회하여 NIC 링크 상태와 장애 징후를 확인한다.
- 예시 출력의 `microcode updated`, `Supporting XSAVE`, `setup node`, `Brought up`, `supports`, `supported` 등은 부팅 초기 하드웨어 및 커널 초기화 로그이다. 검색어 `up` 또는 `status`가 일반 단어 일부에 포함되어 조회될 수 있으므로 이 출력만으로 NIC 장애로 판단하지 않는다.
- `NET: Registered PF_NETLINK/PF_ROUTE protocol family`, `audit: initializing netlink subsys`는 네트워크 관련 커널 서브시스템 초기화 로그이며, 단독으로 장애를 의미하지 않는다.
- 실제 장애 판단은 fail 키워드가 포함된 후보 로그 중 execpt 키워드에 해당하지 않는 라인이 남는지 기준으로 한다. 예를 들어 `link down`이 NIC 장치명과 함께 반복되거나, IPMP/Failover 상태 이상 로그가 함께 확인되면 NIC, 케이블, 스위치 포트, bonding/team 구성 상태를 점검한다.
- `dmesg | grep -i 'nic\|link\|ipmp\|failover\|status\|up\|down'` 명령은 검색 범위가 넓어 정상 부팅 로그도 함께 출력될 수 있다. 운영자는 최종 판정 시 장치명, 인터페이스명, 장애 키워드, 제외 키워드를 함께 확인한다.

# 임계치
nic_port_fail_keywords: offline due to error|port offline|link down|loop detected|loop failure|loop down
nic_port_execpt_keywords: sata link down

# 판단기준
- **양호**: fail 키워드가 포함된 후보 로그가 없거나, 후보 로그가 모두 `nic_port_execpt_keywords`에 의해 제외되는 경우
- **실패**: fail 키워드가 포함된 로그 중 `nic_port_execpt_keywords`로 제외되지 않은 로그가 하나 이상 확인되는 경우
- **참고**: HBA 로그 점검과 동일하게 fail 후보와 제외 키워드를 분리하여 판단한다. 검색 결과에 정상 초기화 로그가 포함될 수 있으므로 단순 출력 존재 여부가 아니라 최종 fail 매칭 건수를 기준으로 판정한다.
