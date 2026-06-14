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

U-REPLAY-DMESG-CLUSTER-01

# is_required

필수

# inspection_name

클러스터 로그

# inspection_content

서버 클러스터 노드의 상태변경 발생 점검(Resource Status Change Unknown/Offline/Online, Cluster Error)

# inspection_command

```bash
dmesg | grep -i 'cluster\|resource status\|unknown\|offline\|online\|error'
```

# inspection_output

```text
[    0.025423] Unknown kernel command line parameters "rhgb BOOT_IMAGE=(hd0,msdos1)/vmlinuz-5.14.0-70.13.1.el9_0.x86_64", will be passed to user space.
[    0.341199] pci_bus 0000:ff: Unknown NUMA node; performance will be reduced
[    0.346354] pci_bus 0000:7f: Unknown NUMA node; performance will be reduced
[    0.439458] ERST: Error Record Serialization Table (ERST) support is initialized.
[    2.166432] megaraid_sas 0000:01:00.0: current msix/online cpus      : (25/24)
[    2.215766] megaraid_sas 0000:01:00.0: Online Controller Reset(OCR)  : Enabled
```

# description

- 본 항목은 `dmesg` 커널 로그에서 클러스터, 리소스 상태 변경, Unknown/Offline/Online, Error 관련 문자열을 조회하여 클러스터 노드 또는 리소스 상태 변경 징후를 확인한다.
- 예시 출력의 `Unknown kernel command line parameters`는 커널이 인식하지 못한 부팅 파라미터 안내이며, 클러스터 리소스의 `Unknown` 상태를 의미하지 않는다.
- `Unknown NUMA node`는 PCI 장치의 NUMA 노드 정보 확인 메시지이고, `ERST: Error Record Serialization Table`은 ACPI 오류 기록 테이블 초기화 로그이다. 단독으로 클러스터 상태 변경이나 클러스터 장애로 판단하지 않는다.
- `current msix/online cpus`, `Online Controller Reset(OCR) : Enabled`는 컨트롤러 또는 CPU 온라인 상태/기능 관련 메시지이며, 클러스터 리소스 `Online` 전환 이벤트와 구분해서 해석한다.
- 사용자 확인용 명령은 검색 범위가 넓어 정상 부팅 로그도 함께 출력될 수 있다. 최종 판정은 `cluster_log_fail_keywords`에 포함된 클러스터 상태 이상 키워드가 검출되고, `cluster_log_execpt_keywords` 예외 키워드에 해당하지 않는 로그가 남는지를 기준으로 한다.
- 장애 키워드가 검출되면 같은 시간대의 클러스터 매니저 로그, `/var/log/messages`, `journalctl`, 스토리지/HBA/RAID 컨트롤러 로그를 함께 확인하여 클러스터 리소스 상태 변경과 실제 장치 링크 장애의 연관성을 판단한다.

- **양호**: `dmesg` 조회 결과에서 `cluster_log_fail_keywords`에 정의된 클러스터 장애 또는 상태 변경 키워드가 검출되지 않거나, 검출 로그가 예외 키워드에 해당하여 제외되는 경우
- **실패**: `cluster_log_fail_keywords`에 포함된 키워드가 하나 이상 확인되고 `cluster_log_execpt_keywords` 예외 키워드에 해당하지 않는 경우
- **참고**: `resource status online`은 정상 상태 자체가 아니라 클러스터 리소스 상태 변경 로그를 식별하기 위한 키워드로 사용하며, 일반 커널의 `online cpus`, `Online Controller Reset` 같은 로그는 예외 키워드로 제외한다.

# thresholds

[
    {id: null, key: "cluster_log_fail_keywords", value: "resource status unknown|resource status offline|resource status online|cluster error|cluster failed|failover failed|quorum lost|node down|node offline|fencing failed|stonith failed|split brain", sortOrder: 0}
,
{id: null, key: "cluster_log_execpt_keywords", value: "unknown kernel command line|unknown numa node|error record serialization table|online controller reset|online cpus|sata link down", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


DEFAULT_CLUSTER_LOG_FAIL_KEYWORDS = (
    'resource status unknown|resource status offline|resource status online|'
    'cluster error|cluster failed|failover failed|quorum lost|'
    'node down|node offline|fencing failed|stonith failed|split brain'
)
DEFAULT_CLUSTER_LOG_EXECPT_KEYWORDS = (
    'unknown kernel command line|unknown numa node|error record serialization table|'
    'online controller reset|online cpus|sata link down'
)


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
                'cluster_log_fail_keywords',
                default=DEFAULT_CLUSTER_LOG_FAIL_KEYWORDS,
                value_type='str',
            )
        )
        except_keywords = self._split_keywords(
            self.get_threshold_var(
                'cluster_log_execpt_keywords',
                default=DEFAULT_CLUSTER_LOG_EXECPT_KEYWORDS,
                value_type='str',
            )
        )
        if not fail_keywords:
            return self.fail(
                '임계치 미정의',
                message='cluster_log_fail_keywords 가 정의되어 있지 않습니다.',
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
                message='dmesg 클러스터 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        candidate_matches = self._find_matches(lines, fail_keywords)
        fail_matches, except_matches = self._filter_except_matches(candidate_matches, except_keywords)
        fail_keyword_counts = self._count_keywords(fail_matches, fail_keywords)
        candidate_keyword_counts = self._count_keywords(candidate_matches, fail_keywords)
        thresholds = {
            'cluster_log_fail_keywords': '|'.join(fail_keywords),
            'cluster_log_execpt_keywords': '|'.join(except_keywords),
        }
        metrics = {
            'grep_line_count': len(lines),
            'cluster_log_fail_candidate_count': len(candidate_matches),
            'cluster_log_fail_match_count': len(fail_matches),
            'cluster_log_except_match_count': len(except_matches),
            'cluster_log_fail_keyword_counts': fail_keyword_counts,
            'cluster_log_fail_candidate_keyword_counts': candidate_keyword_counts,
            'cluster_log_fail_matches': fail_matches,
            'cluster_log_except_matches': except_matches,
            'grep_lines': lines,
        }
        threshold_summary = (
            'cluster_log_fail_keywords=' + thresholds['cluster_log_fail_keywords'] +
            '; cluster_log_execpt_keywords=' + thresholds['cluster_log_execpt_keywords']
        )

        if fail_matches:
            result = self.fail(
                '클러스터 로그 장애 키워드 감지',
                message=(
                    '클러스터 로그 검색 결과에서 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
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
                '클러스터 로그 검색 결과에서 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            )
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                '클러스터 로그 검색 결과에서 장애 키워드가 검출되지 않았습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            ),
            message=(
                '클러스터 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건. '
                '임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
