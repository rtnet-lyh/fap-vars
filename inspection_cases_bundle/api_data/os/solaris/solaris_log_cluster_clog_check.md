# type_name

일상점검(상태점검)

# area_name

서버

# category_name

CLUSTER

# application_type

UNIX

# application

solaris

# inspection_code

SVR-5-10

# is_required

필수

# inspection_name

클러스터 로그

# inspection_content

Solaris 클러스터 로그에서 노드 online/offline 변경과 클러스터 통신 오류를 점검합니다.

# inspection_command

```bash
clog | grep -i 'status change|offline|online|cluster error'
```

# inspection_output

```text
[2024-09-16T10:00:00] Resource Status Change: Node1 Offline
[2024-09-16T10:05:00] Cluster Error: Node2 communication failure
[2024-09-16T10:10:00] Resource Status Change: Node3 Online
```

# description

- 노드 online/offline 변경 및 클러스터 통신 오류를 확인.
  - 노드 오프라인이나 통신 실패 메시지가 있으면 클러스터 상태 점검 필요.

# thresholds

[
    {id: null, key: "bad_log_keywords", value: "offline,cluster error,communication failure,failed,failure", sortOrder: 0}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,module,cannot,command not found", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "clog | grep -i 'status change|offline|online|cluster error'"
LOG_PATTERNS = (
    'status change',
    'offline',
    'online',
    'cluster error',
    'communication failure',
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _find_bad_lines(self, lines, bad_keywords):
        bad_lines = []
        for line in lines:
            lowered = line.lower()
            if any(keyword.lower() in lowered for keyword in bad_keywords):
                bad_lines.append(line)
        return bad_lines

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return '클러스터 이상 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def _count_pattern_hits(self, lines):
        counts = {}
        lowered_lines = [line.lower() for line in lines]
        for pattern in LOG_PATTERNS:
            counts[pattern.replace(' ', '_')] = sum(
                1 for line in lowered_lines if pattern in line
            )
        return counts

    def run(self):
        bad_log_keywords = self._split_keywords(
            self.get_threshold_var(
                'bad_log_keywords',
                default='offline,cluster error,communication failure,failed,failure',
                value_type='str',
            )
        )
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found',
                value_type='str',
            )
        )

        rc, out, err = self._ssh(LOG_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(value for value in (text, stderr_text) if value)

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=failure_keywords + [
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 서버 클러스터 노드 상태변경 발생 점검에 실패했습니다. '
                    f'현재 상태: 명령 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 서버 클러스터 노드 상태변경 발생 점검에 실패했습니다. '
                    f'현재 상태: {LOG_COMMAND} 명령 종료코드가 rc={rc}로 반환되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '클러스터 로그 실패 키워드 감지',
                message=(
                    'Solaris 서버 클러스터 노드 상태변경 발생 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 서버 클러스터 노드 상태변경 발생 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        bad_lines = self._find_bad_lines(lines, bad_log_keywords)
        pattern_hit_count = self._count_pattern_hits(lines)

        metrics = {
            'command_rc': rc,
            'matched_log_count': len(lines),
            'abnormal_log_count': len(bad_lines),
            'matched_logs': lines,
            'abnormal_logs': bad_lines,
            'matched_failure_keywords': matched_failure_keywords,
            'stderr_line_count': len([line for line in stderr_text.splitlines() if line.strip()]),
            'status_change_count': pattern_hit_count['status_change'],
            'offline_count': pattern_hit_count['offline'],
            'online_count': pattern_hit_count['online'],
            'cluster_error_count': pattern_hit_count['cluster_error'],
            'communication_failure_count': pattern_hit_count['communication_failure'],
        }

        if bad_lines:
            return self.fail(
                '클러스터 상태변경 이상 로그 감지',
                message=(
                    'Solaris 서버 클러스터 노드 상태변경 발생 점검에 실패했습니다. '
                    f'현재 상태: 클러스터 로그 {len(lines)}건 중 비정상 로그 {len(bad_lines)}건이 확인되었습니다. '
                    f'offline {pattern_hit_count["offline"]}건, '
                    f'cluster error {pattern_hit_count["cluster_error"]}건, '
                    f'communication failure {pattern_hit_count["communication_failure"]}건, '
                    f'online {pattern_hit_count["online"]}건입니다. '
                    f'첫 비정상 로그: {bad_lines[0]}. 로그 요약: {self._build_log_summary(bad_lines)}.'
                ),
                metrics=metrics,
                thresholds={
                    'bad_log_keywords': bad_log_keywords,
                    'failure_keywords': failure_keywords,
                },
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds={
                'bad_log_keywords': bad_log_keywords,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                'offline, cluster error, communication failure 같은 비정상 클러스터 로그가 검출되지 않았고 '
                '실행 오류나 stderr도 없습니다.'
            ),
            message=(
                'Solaris 서버 클러스터 노드 상태변경 발생 점검이 정상입니다. '
                f'현재 상태: status change {pattern_hit_count["status_change"]}건, '
                f'online {pattern_hit_count["online"]}건, offline 0건, '
                f'cluster error 0건, communication failure 0건, stderr 0건으로 집계되었습니다.'
            ),
        )


CHECK_CLASS = Check
