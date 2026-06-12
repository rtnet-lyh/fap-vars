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

U-REPLAY-DMESG-IO-02

# is_required

필수

# inspection_name

I/O 에러로그

# inspection_content

입출력 작동 이상 유무 점검(통신 지연으로 인한 Timeout 발생 및 I/O Error, Transport Failed, Media Error)

# inspection_command

```bash
dmesg | grep -Fi <동적 생성된 -e fail_keyword 목록>
```

기본 임계치 기준 생성 예시:

```bash
dmesg | grep -Fi -e 'i/o error' -e timeout -e 'transport failed' -e 'media error'
```

# inspection_output

```text
[    2.215770] megaraid_sas 0000:01:00.0: FW provided TM TaskAbort/Reset timeout        : 0 secs/0 secs
```

# description

- 본 항목은 `dmesg` 커널 로그에서 디스크, HBA, RAID 컨트롤러, 스토리지 경로와 관련된 I/O 오류 및 timeout 징후를 확인한다.
- 점검 스크립트는 `io_error_fail_keywords` 값을 `|` 기준으로 분리한 뒤 각 키워드를 `grep -Fi -e '<keyword>'` 인자로 붙여 명령어를 동적으로 생성한다.
- 예시의 `megaraid_sas` `TaskAbort/Reset timeout` 메시지는 RAID 컨트롤러 또는 연결된 디스크 장치 처리 과정에서 명령 중단, 리셋, 응답 지연이 발생했을 가능성을 의미한다.
- fail 키워드가 포함된 후보 로그 중 `io_error_except_keywords`에 해당하는 라인은 제외하고, 제외 후 남은 로그가 하나 이상이면 I/O 장애 징후로 판정한다.
- 장애 로그가 확인되면 같은 시간대의 `/var/log/messages`, RAID 관리 도구 출력, 디스크 SMART 상태, HBA 또는 스토리지 이벤트 로그를 함께 확인하여 단발성 메시지인지 반복 장애인지 판단한다.

- **양호**: fail 키워드가 포함된 후보 로그가 없거나, 후보 로그가 모두 `io_error_except_keywords`에 의해 제외되는 경우
- **실패**: fail 키워드가 포함된 로그 중 `io_error_except_keywords`로 제외되지 않은 로그가 하나 이상 확인되는 경우
- **참고**: `grep` 결과가 없어서 명령 반환 코드가 1인 경우는 오류 로그 미검출로 보고, 명령 실행 오류와 구분한다.
- **참고**: `timeout`은 I/O 외 다른 커널 메시지에도 포함될 수 있으므로 except 임계치로 비 I/O성 timeout 로그를 분리한다.

# thresholds

[
    {id: null, key: "io_error_fail_keywords", value: "i/o error|timeout|transport failed|media error", sortOrder: 0}
,
{id: null, key: "io_error_except_keywords", value: "hung_task_timeout_secs|rcu:|watchdog", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


DEFAULT_IO_ERROR_FAIL_KEYWORDS = 'i/o error|timeout|transport failed|media error'
DEFAULT_IO_ERROR_EXCEPT_KEYWORDS = 'hung_task_timeout_secs|rcu:|watchdog'


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
                'io_error_fail_keywords',
                default=DEFAULT_IO_ERROR_FAIL_KEYWORDS,
                value_type='str',
            )
        )
        except_keywords = self._split_keywords(
            self.get_threshold_var(
                'io_error_except_keywords',
                default=DEFAULT_IO_ERROR_EXCEPT_KEYWORDS,
                value_type='str',
            )
        )
        if not fail_keywords:
            return self.fail(
                '임계치 미정의',
                message='io_error_fail_keywords 가 정의되어 있지 않습니다.',
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
                message='dmesg I/O 에러로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        candidate_matches = self._find_matches(lines, fail_keywords)
        fail_matches, except_matches = self._filter_except_matches(candidate_matches, except_keywords)
        fail_keyword_counts = self._count_keywords(fail_matches, fail_keywords)
        candidate_keyword_counts = self._count_keywords(candidate_matches, fail_keywords)
        thresholds = {
            'io_error_fail_keywords': '|'.join(fail_keywords),
            'io_error_except_keywords': '|'.join(except_keywords),
        }
        metrics = {
            'grep_line_count': len(lines),
            'io_error_fail_candidate_count': len(candidate_matches),
            'io_error_fail_match_count': len(fail_matches),
            'io_error_except_match_count': len(except_matches),
            'io_error_fail_keyword_counts': fail_keyword_counts,
            'io_error_fail_candidate_keyword_counts': candidate_keyword_counts,
            'io_error_fail_matches': fail_matches,
            'io_error_except_matches': except_matches,
            'grep_lines': lines,
        }
        threshold_summary = (
            'io_error_fail_keywords=' + thresholds['io_error_fail_keywords'] +
            '; io_error_except_keywords=' + thresholds['io_error_except_keywords']
        )

        if fail_matches:
            result = self.fail(
                'I/O 에러로그 감지',
                message=(
                    'I/O 오류 또는 timeout 관련 dmesg 로그가 확인되었습니다. '
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
                'I/O 오류 또는 timeout 관련 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            )
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                'I/O 오류 또는 timeout 관련 키워드가 검출되지 않았습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            ),
            message=(
                'I/O 에러로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건. '
                '임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
