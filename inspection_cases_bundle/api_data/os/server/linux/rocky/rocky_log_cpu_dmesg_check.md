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


SV-LIN-RKY-004

# is_required

필수

# inspection_name

CPU 로그

# inspection_content

CPU 에러로그 점검(Uncorrectable ECC Error, Offline)

# inspection_command

```bash
dmesg | grep -i 'ECC error\|CPU'
```

# inspection_output

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

# description

- (ECC 오류 메시지) ECC error 메시지가 발견되면, 메모리 모듈 점검 및 교체 필요
- (CPU 에러 메시지) CPU error 또는 관련 에러 메시지를 확인하여 CPU 및 하드웨어 점검 필요
- (CPU 오프라인 상태) offline 메시지가 발견되면, 시스템 점검 및 CPU 재활성화 필요

- **양호**: `dmesg | grep -i 'ECC error\|CPU'` 결과에서 임계치에 정의된 `ecc error`, `cpu error`, `offline` 키워드가 존재하지 않는 상태
- **경고**: `dmesg | grep -i 'ECC error\|CPU'` 결과에서 임계치에 정의된 `ecc error`, `cpu error`, `offline` 키워드 중 하나 이상이 확인되는 상태
- **참고**: CPU 정보, 토폴로지, 마이크로코드, 성능 관련 일반 메시지는 참고 정보로 보고, 실제 판정은 임계치에 정의된 오류 키워드 존재 여부를 기준으로 판단함

# thresholds

[
    {id: null, key: "error_keywords", value: "ecc error|cpu error|offline", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_CPU_COMMAND = "dmesg | grep -i 'ECC error\\|CPU'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _find_matches(self, lines, keywords):
        matches = []

        for line in lines:
            lowered = line.lower()
            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower() in lowered
            ]
            if not matched_keywords:
                continue
            matches.append({
                'line': line,
                'matched_keywords': matched_keywords,
            })

        return matches

    def _count_keywords(self, matches, keywords):
        counts = {keyword: 0 for keyword in keywords}

        for match in matches:
            for keyword in match.get('matched_keywords', []):
                if keyword in counts:
                    counts[keyword] += 1

        return counts

    def _format_keyword_counts(self, counts):
        return ', '.join(
            f'{keyword}={count}건'
            for keyword, count in counts.items()
        )

    def run(self):
        error_keywords = self._split_keywords(
            self.get_threshold_var('error_keywords', default='ecc error|cpu error|offline', value_type='str')
        )
        if not error_keywords:
            return self.fail(
                '임계치 미정의',
                message='error_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_CPU_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg CPU 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        matches = self._find_matches(lines, error_keywords)
        keyword_counts = self._count_keywords(matches, error_keywords)
        threshold_summary = 'error_keywords=' + '|'.join(error_keywords)

        metrics = {
            'grep_line_count': len(lines),
            'error_match_count': len(matches),
            'error_keyword_counts': keyword_counts,
            'error_matches': matches,
            'grep_lines': lines,
        }
        thresholds = {
            'error_keywords': '|'.join(error_keywords),
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='CPU 오류 관련 키워드가 확인되었습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
                message=(
                    'CPU 오류 관련 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='CPU 오류 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                'CPU 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
