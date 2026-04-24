# 영역
CPU

# 세부 점검항목
CPU 코어별 상태 점검

# 점검 내용
물리적 코어의 정상(online/offline) 유무 점검

# 구분
필수

# 명령어
```bash
lscpu
```

# 출력 결과
```text
Architecture:            x86_64
  CPU op-mode(s):        32-bit, 64-bit
  Address sizes:         46 bits physical, 48 bits virtual
  Byte Order:            Little Endian
CPU(s):                  24
  On-line CPU(s) list:   0-23
Vendor ID:               GenuineIntel
  Model name:            Intel(R) Xeon(R) CPU E5-2620 v3 @ 2.40GHz
    CPU family:          6
    Model:               63
    Thread(s) per core:  2
    Core(s) per socket:  6
    Socket(s):           2
    Stepping:            2
    CPU(s) scaling MHz:  100%
    CPU max MHz:         2400.0000
    CPU min MHz:         1200.0000
    BogoMIPS:            4789.25
    Flags:               fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_
                         tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid
                         dca sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb invpcid_single pti intel_ppin ssbd ibrs ibpb st
                         ibp tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid cqm xsaveopt cqm_llc cqm_occup_llc dtherm arat pln pts m
                         d_clear flush_l1d
Virtualization features:
  Virtualization:        VT-x
Caches (sum of all):
  L1d:                   384 KiB (12 instances)
  L1i:                   384 KiB (12 instances)
  L2:                    3 MiB (12 instances)
  L3:                    30 MiB (2 instances)
NUMA:
  NUMA node(s):          2
  NUMA node0 CPU(s):     0-5,12-17
  NUMA node1 CPU(s):     6-11,18-23
Vulnerabilities:
  Itlb multihit:         KVM: Mitigation: VMX disabled
  L1tf:                  Mitigation; PTE Inversion; VMX conditional cache flushes, SMT vulnerable
  Mds:                   Mitigation; Clear CPU buffers; SMT vulnerable
  Meltdown:              Mitigation; PTI
  Spec store bypass:     Mitigation; Speculative Store Bypass disabled via prctl
  Spectre v1:            Mitigation; usercopy/swapgs barriers and __user pointer sanitization
  Spectre v2:            Mitigation; Retpolines, IBPB conditional, IBRS_FW, STIBP conditional, RSB filling
  Srbds:                 Not affected
  Tsx async abort:       Not affected
```

# 설명
- 이 점검은 서버에 있는 CPU 코어들이 정상적으로 사용 가능한 상태인지 확인하는 작업이다.
- 리눅스에서는 CPU 코어가 online 상태이면 운영체제가 해당 코어를 사용할 수 있고, offline 상태이면 사용할 수 없다.
- 따라서 일부 코어가 offline 되어 있으면, 서버 성능이 평소보다 낮아지거나 특정 작업이 느려질 수 있다.
- 점검 시에는 전체 CPU 개수와 현재 online 상태인 CPU 목록, offline 상태인 CPU 목록을 확인한다.
- 즉, 이 점검은 서버의 CPU 코어가 빠짐없이 정상 동작 중인지 확인하는 기본 상태 점검이다.

# 임계치
없음

# 판단기준
- **양호**: `CPU(s)`에 표시된 전체 CPU 개수와 `On-line CPU(s) list`에 포함된 CPU 개수가 일치하고, offline CPU가 확인되지 않는 상태
- **실패**: 전체 CPU 중 일부가 offline 상태로 확인되어 운영체제가 해당 CPU 코어를 사용할 수 없는 상태
- **확인 필요**: `lscpu` 명령 실행에 실패하거나 전체 CPU 개수, online CPU 목록, offline CPU 목록을 파싱할 수 없는 상태
