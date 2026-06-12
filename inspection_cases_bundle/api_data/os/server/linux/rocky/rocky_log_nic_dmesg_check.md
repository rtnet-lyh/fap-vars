# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-DMESG-NIC-01

# is_required

필수

# inspection_name

NIC 로그

# inspection_content

NIC 정상 유무 점검(Ipmp Fail over 및 Status Up/Down, Link Down)

# inspection_command

```bash
dmesg | grep -i 'nic\|link\|ipmp\|failover\|status\|up\|down'
```

# inspection_output

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

# description

- 본 항목은 `dmesg` 커널 로그에서 NIC, link, IPMP, failover, status, up, down 관련 문자열을 조회하여 NIC 링크 상태와 장애 징후를 확인한다.
- 예시 출력의 `microcode updated`, `Supporting XSAVE`, `setup node`, `Brought up`, `supports`, `supported` 등은 부팅 초기 하드웨어 및 커널 초기화 로그이다. 검색어 `up` 또는 `status`가 일반 단어 일부에 포함되어 조회될 수 있으므로 이 출력만으로 NIC 장애로 판단하지 않는다.
- `NET: Registered PF_NETLINK/PF_ROUTE protocol family`, `audit: initializing netlink subsys`는 네트워크 관련 커널 서브시스템 초기화 로그이며, 단독으로 장애를 의미하지 않는다.
- 실제 장애 판단은 fail 키워드가 포함된 후보 로그 중 execpt 키워드에 해당하지 않는 라인이 남는지 기준으로 한다. 예를 들어 `link down`이 NIC 장치명과 함께 반복되거나, IPMP/Failover 상태 이상 로그가 함께 확인되면 NIC, 케이블, 스위치 포트, bonding/team 구성 상태를 점검한다.
- `dmesg | grep -i 'nic\|link\|ipmp\|failover\|status\|up\|down'` 명령은 검색 범위가 넓어 정상 부팅 로그도 함께 출력될 수 있다. 운영자는 최종 판정 시 장치명, 인터페이스명, 장애 키워드, 제외 키워드를 함께 확인한다.

- **양호**: fail 키워드가 포함된 후보 로그가 없거나, 후보 로그가 모두 `nic_port_execpt_keywords`에 의해 제외되는 경우
- **실패**: fail 키워드가 포함된 로그 중 `nic_port_execpt_keywords`로 제외되지 않은 로그가 하나 이상 확인되는 경우
- **참고**: HBA 로그 점검과 동일하게 fail 후보와 제외 키워드를 분리하여 판단한다. 검색 결과에 정상 초기화 로그가 포함될 수 있으므로 단순 출력 존재 여부가 아니라 최종 fail 매칭 건수를 기준으로 판정한다.

# thresholds

[
    {id: null, key: "nic_port_fail_keywords", value: "offline due to error|port offline|link down|loop detected|loop failure|loop down", sortOrder: 0}
,
{id: null, key: "nic_port_execpt_keywords", value: "sata link down", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


DEFAULT_NIC_PORT_FAIL_KEYWORDS = (
    'offline due to error|port offline|link down|loop detected|loop failure|loop down'
)
DEFAULT_NIC_PORT_EXECPT_KEYWORDS = 'sata link down'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _build_dmesg_fail_command(self, keywords):
        grep_args = ' '.join(
            '-e ' + shlex.quote(keyword)
            for keyword in keywords
        )
        return 'dmesg | grep -Fi ' + grep_args

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

    def _filter_except_matches(self, matches, except_keywords):
        fail_matches = []
        except_matches = []

        for match in matches:
            line = match.get('line') or ''
            lowered = line.lower()
            matched_except_keywords = [
                keyword
                for keyword in except_keywords
                if keyword.lower() in lowered
            ]
            if matched_except_keywords:
                excluded_match = dict(match)
                excluded_match['matched_except_keywords'] = matched_except_keywords
                except_matches.append(excluded_match)
                continue

            fail_matches.append(match)

        return fail_matches, except_matches

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
        fail_keywords = self._split_keywords(
            self.get_threshold_var(
                'nic_port_fail_keywords',
                default=DEFAULT_NIC_PORT_FAIL_KEYWORDS,
                value_type='str',
            )
        )
        except_keywords = self._split_keywords(
            self.get_threshold_var(
                'nic_port_execpt_keywords',
                default=DEFAULT_NIC_PORT_EXECPT_KEYWORDS,
                value_type='str',
            )
        )
        if not fail_keywords:
            return self.fail(
                '임계치 미정의',
                message='nic_port_fail_keywords 가 정의되어 있지 않습니다.',
            )

        command = self._build_dmesg_fail_command(fail_keywords)
        rc, out, err = self._ssh(command)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg NIC 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        candidate_matches = self._find_matches(lines, fail_keywords)
        fail_matches, except_matches = self._filter_except_matches(candidate_matches, except_keywords)
        fail_keyword_counts = self._count_keywords(fail_matches, fail_keywords)
        candidate_keyword_counts = self._count_keywords(candidate_matches, fail_keywords)
        thresholds = {
            'nic_port_fail_keywords': '|'.join(fail_keywords),
            'nic_port_execpt_keywords': '|'.join(except_keywords),
        }
        metrics = {
            'grep_line_count': len(lines),
            'nic_port_fail_candidate_count': len(candidate_matches),
            'nic_port_fail_match_count': len(fail_matches),
            'nic_port_except_match_count': len(except_matches),
            'nic_port_fail_keyword_counts': fail_keyword_counts,
            'nic_port_fail_candidate_keyword_counts': candidate_keyword_counts,
            'nic_port_fail_matches': fail_matches,
            'nic_port_except_matches': except_matches,
            'grep_lines': lines,
        }
        threshold_summary = (
            'nic_port_fail_keywords=' + thresholds['nic_port_fail_keywords'] +
            '; nic_port_execpt_keywords=' + thresholds['nic_port_execpt_keywords']
        )

        if fail_matches:
            result = self.fail(
                'NIC 포트 장애 로그 감지',
                message=(
                    'NIC 포트 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                    f'. 제외 로그 {len(except_matches)}건. '
                    '임계치: ' + threshold_summary
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = (
                'NIC 포트 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            )
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                'NIC 포트 장애 키워드가 검출되지 않았습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            ),
            message=(
                'NIC 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건. '
                '임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
