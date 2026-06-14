# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-CPU-CORE-01

# is_required

필수

# inspection_name

CPU 코어별 상태 점검

# inspection_content

물리적 코어의 정상(online/offline) 유무 점검

# inspection_command

```bash
lscpu
```

# inspection_output

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

# description

- 이 점검은 서버에 있는 CPU 코어들이 정상적으로 사용 가능한 상태인지 확인하는 작업이다.
- 리눅스에서는 CPU 코어가 online 상태이면 운영체제가 해당 코어를 사용할 수 있고, offline 상태이면 사용할 수 없다.
- 따라서 일부 코어가 offline 되어 있으면, 서버 성능이 평소보다 낮아지거나 특정 작업이 느려질 수 있다.
- 점검 시에는 전체 CPU 개수와 현재 online 상태인 CPU 목록, offline 상태인 CPU 목록을 확인한다.
- 즉, 이 점검은 서버의 CPU 코어가 빠짐없이 정상 동작 중인지 확인하는 기본 상태 점검이다.

- **양호**: `CPU(s)`에 표시된 전체 CPU 개수와 `On-line CPU(s) list`에 포함된 CPU 개수가 일치하고, offline CPU가 확인되지 않는 상태
- **실패**: 전체 CPU 중 일부가 offline 상태로 확인되어 운영체제가 해당 CPU 코어를 사용할 수 없는 상태
- **확인 필요**: `lscpu` 명령 실행에 실패하거나 전체 CPU 개수, online CPU 목록, offline CPU 목록을 파싱할 수 없는 상태

# thresholds

[
    {id: null, key: "fail_keywords", value: "offline", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_cpu_list(self, text):
        cpus = set()
        for token in str(text or '').split(','):
            token = token.strip()
            if not token:
                continue
            if '-' in token:
                start, end = token.split('-', 1)
                try:
                    start_no = int(start.strip())
                    end_no = int(end.strip())
                except ValueError:
                    continue
                if start_no <= end_no:
                    cpus.update(range(start_no, end_no + 1))
                else:
                    cpus.update(range(end_no, start_no + 1))
                continue
            try:
                cpus.add(int(token))
            except ValueError:
                continue
        return sorted(cpus)

    def _parse_fail_keywords(self, raw_value):
        return [
            keyword.strip().lower()
            for keyword in re.split(r'[,|\n]+', str(raw_value or ''))
            if keyword.strip()
        ]

    def _format_cpu_list(self, cpus):
        if not cpus:
            return '없음'
        return ','.join(str(cpu) for cpu in cpus)

    def _parse_lscpu(self, text):
        total_match = re.search(r'(?m)^\s*CPU\(s\):\s*([0-9]+)\s*$', text or '')
        online_match = re.search(r'(?m)^\s*On-line CPU\(s\) list:\s*(.+?)\s*$', text or '')
        offline_match = re.search(r'(?m)^\s*Off-line CPU\(s\) list:\s*(.+?)\s*$', text or '')

        total_cpu_count = int(total_match.group(1)) if total_match else 0
        online_cpus = self._parse_cpu_list(online_match.group(1) if online_match else '')
        offline_cpus = self._parse_cpu_list(offline_match.group(1) if offline_match else '')

        if total_cpu_count > 0 and online_cpus:
            expected_cpus = set(range(total_cpu_count))
            derived_offline = sorted(expected_cpus - set(online_cpus))
            if derived_offline:
                offline_cpus = sorted(set(offline_cpus) | set(derived_offline))

        return {
            'cpu_count': total_cpu_count,
            'online_cpus': online_cpus,
            'offline_cpus': offline_cpus,
        }

    def run(self):
        fail_keywords_raw = self.get_threshold_var('fail_keywords', default='offline')
        fail_keywords = self._parse_fail_keywords(fail_keywords_raw)
        rc, out, err = self._ssh("lscpu")

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='lscpu 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'CPU 정보 없음',
                message='lscpu 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = self._parse_lscpu(text)
        if parsed['cpu_count'] <= 0 or not parsed['online_cpus']:
            return self.fail(
                'CPU 정보 파싱 실패',
                message='lscpu 결과에서 CPU(s) 또는 On-line CPU(s) list를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        output_lower = text.lower()
        matched_fail_keywords = [
            keyword
            for keyword in fail_keywords
            if keyword and keyword in output_lower
        ]

        if parsed['offline_cpus']:
            return self.fail(
                'CPU 코어 상태 비정상',
                message=(
                    'offline CPU가 존재합니다. '
                    f"점검 근거: lscpu 결과 총 CPU {parsed['cpu_count']}개 중 "
                    f"online {len(parsed['online_cpus'])}개, "
                    f"offline {len(parsed['offline_cpus'])}개"
                    f"({self._format_cpu_list(parsed['offline_cpus'])})입니다. "
                    f'판단기준: offline CPU가 0개이고 '
                    f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                    '감지되지 않아야 합니다.'
                ),
                stdout=text,
            )

        if matched_fail_keywords:
            return self.fail(
                'CPU 코어 상태 비정상',
                message=(
                    f"실패 키워드가 감지되었습니다: {', '.join(matched_fail_keywords)}. "
                    f"점검 근거: lscpu 결과 총 CPU {parsed['cpu_count']}개 중 "
                    f"online {len(parsed['online_cpus'])}개, "
                    f"offline {len(parsed['offline_cpus'])}개이며 "
                    f"출력에서 실패 키워드 {', '.join(matched_fail_keywords)}가 감지되었습니다. "
                    f'판단기준: offline CPU가 0개이고 '
                    f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                    '감지되지 않아야 합니다.'
                ),
                stdout=text,
            )

        return self.ok(
            metrics={
                'cpu_count': parsed['cpu_count'],
                'online_cpu_count': len(parsed['online_cpus']),
                'offline_cpu_count': len(parsed['offline_cpus']),
                'online_cpus': parsed['online_cpus'],
                'offline_cpus': parsed['offline_cpus'],
                'matched_fail_keywords': matched_fail_keywords,
            },
            thresholds={
                'fail_keywords': fail_keywords_raw,
            },
            reasons=(
                f"총 CPU {parsed['cpu_count']}개 중 online {len(parsed['online_cpus'])}개, "
                'offline 0개이며 실패 키워드가 감지되지 않았습니다.'
            ),
            message=(
                'lscpu 기준 CPU 코어 상태 점검이 정상 수행되었습니다. '
                f"점검 근거: 총 CPU {parsed['cpu_count']}개 중 "
                f"online {len(parsed['online_cpus'])}개, "
                'offline 0개이며 실패 키워드가 감지되지 않았습니다. '
                f'판단기준: offline CPU가 0개이고 '
                f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                '감지되지 않아야 합니다.'
            ),
            raw_output=text,
        )


CHECK_CLASS = Check
