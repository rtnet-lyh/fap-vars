# 영역
로그

# 세부 점검항목
CPU 로그

# 점검 내용
CPU 에러로그 점검(Uncorrectable ECC Error, Offline)

# 구분
필수

# 명령어
```bash
dmesg | grep -i 'ECC error\|CPU'
```

# 출력 결과
```text
[    0.029376] CPU topo: Max. logical packages:   2
[    0.029377] CPU topo: Max. logical dies:       2
[    0.029377] CPU topo: Max. dies per package:   1
[    0.029382] CPU topo: Max. threads per core:   1
[    0.029383] CPU topo: Num. cores per package:     4
[    0.029383] CPU topo: Num. threads per package:   4
[    0.029384] CPU topo: Allowing 8 present CPUs plus 0 hotplug CPUs
[    0.029442] Warning: Deprecated Hardware is detected: x86_64-v2:GenuineIntel:QEMU Virtual CPU version 2.5+ will not be maintained in a future major release and may be disabled
[    0.035838] setup_percpu: NR_CPUS:8192 nr_cpumask_bits:8 nr_cpu_ids:8 nr_node_ids:1
[    0.036587] percpu: Embedded 64 pages/cpu s225280 r8192 d28672 u262144
[    0.036591] pcpu-alloc: s225280 r8192 d28672 u262144 alloc=1*2097152
[    0.036594] pcpu-alloc: [0] 0 1 2 3 4 5 6 7
[    0.085686] SLUB: HWalign=64, Order=0-3, MinObjects=0, CPUs=8, Nodes=1
[    0.096354] rcu:     RCU restricting CPUs from NR_CPUS=8192 to nr_cpu_ids=8.
[    0.096359] rcu: Adjusting geometry for rcu_fanout_leaf=16, nr_cpu_ids=8
[    0.096368] RCU Tasks: Setting shift to 3 and lim to 1 rcu_task_cb_adjust=1 rcu_task_cpu_ids=8.
[    0.096370] RCU Tasks Rude: Setting shift to 3 and lim to 1 rcu_task_cb_adjust=1 rcu_task_cpu_ids=8.
[    0.096371] RCU Tasks Trace: Setting shift to 3 and lim to 1 rcu_task_cb_adjust=1 rcu_task_cpu_ids=8.
[    0.120565] MDS: Vulnerable: Clear CPU buffers attempted, no microcode
[    0.242015] smpboot: CPU0: Intel QEMU Virtual CPU version 2.5+ (family: 0xf, model: 0x6b, stepping: 0x1)
[    0.242229] Performance Events: unsupported Netburst CPU model 107 no PMU driver, software events only.
[    0.245393] smp: Bringing up secondary CPUs ...
[    0.245523] .... node  #0, CPUs:      #1 #2 #3 #4 #5 #6 #7
[    0.334286] smp: Brought up 1 node, 8 CPUs
[    0.344234] cpuidle: using governor menu
[    0.347542] cryptd: max_cpu_qlen set to 1000
[    0.352276] ACPI: _OSC evaluation for CPUs failed, trying _PDC
[    0.404711] hpet: 3 channels of 0 reserved for per-cpu timers
[    1.348470] intel_pstate: CPU model not supported
```

# 설명
- (ECC 오류 메시지) ECC error 메시지가 발견되면, 메모리 모듈 점검 및 교체 필요
- (CPU 에러 메시지) CPU error 또는 관련 에러 메시지를 확인하여 CPU 및 하드웨어 점검 필요
- (CPU 오프라인 상태) offline 메시지가 발견되면, 시스템 점검 및 CPU 재활성화 필요

# 임계치
error_keywords: ecc error|cpu error|offline

# 판단기준
- **양호**: `dmesg | grep -i 'ECC error\|CPU'` 결과에서 임계치에 정의된 `ecc error`, `cpu error`, `offline` 키워드가 존재하지 않는 상태
- **경고**: `dmesg | grep -i 'ECC error\|CPU'` 결과에서 임계치에 정의된 `ecc error`, `cpu error`, `offline` 키워드 중 하나 이상이 확인되는 상태
- **참고**: CPU 정보, 토폴로지, 마이크로코드, 성능 관련 일반 메시지는 참고 정보로 보고, 실제 판정은 임계치에 정의된 오류 키워드 존재 여부를 기준으로 판단함

# 비고
- 커널 로그 조회를 위해 root 또는 sudo 권한이 필요할 수 있음
