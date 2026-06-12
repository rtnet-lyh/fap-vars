# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = "printf '\\n' | format"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _find_check_result(self, results):
        for item in reversed(results or []):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _parse_disk_names(self, output):
        disks = []
        for line in str(output or '').splitlines():
            match = re.match(r'^\s*\d+\.\s+(\S+)', line)
            if match:
                disks.append(match.group(1))
        return disks

    def run(self):
        min_disk_count = self.get_threshold_var('expected_disk_count', default=1, value_type=int)
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='Unknown,Drive not available',
                value_type=str,
            )
        )

        try:
            results = self._run_solaris_commands([
                {'command': CHECK_COMMAND, 'timeout': 20},
            ], become_required=True)
        except ValueError as exc:
            return self.fail('권한 상승 설정 오류', message=str(exc))

        result = self._find_check_result(results)

        if result is None:
            failed_result = next((item for item in results if item.get('rc') != 0), None)
            rc = failed_result.get('rc') if failed_result else 1
            err = failed_result.get('stderr') if failed_result else ''
            if self._is_connection_error(rc, err):
                return self.fail(
                    '호스트 연결 실패',
                    message=(err or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                    stderr=(err or '').strip(),
                )
            return self.fail(
                error='명령 결과 없음',
                message='명령 실행 결과를 찾지 못했습니다.',
                stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                stderr=(err or '').strip(),
                metrics={
                    'executed_commands': [
                        item.get('display_command') or item.get('command')
                        for item in results
                    ],
                },
            )

        rc = result.get('rc')
        output = result.get('stdout', '')
        err = result.get('stderr', '')
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return self.fail(
                error='format 명령 실행 실패',
                message='Solaris format 명령 실행에 실패했습니다.',
                stdout=(output or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            output,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                error='format 명령 실행 실패',
                message=f'format 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(output or '').strip(),
                stderr=(err or '').strip(),
            )

        disk_names = self._parse_disk_names(output)
        disk_count = len(disk_names)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in output.lower()
        ]

        metrics = {
            'disk_count': disk_count,
            'disk_names': disk_names,
            'matched_failure_keywords': matched_failure_keywords,
        }

        if matched_failure_keywords:
            return self.fail(
                error='Disk 인식 실패 키워드 감지',
                message=f'Disk 인식 출력에서 실패 키워드가 확인되었습니다: {", ".join(matched_failure_keywords)}',
                reasons=f'Disk 인식 출력에서 실패 키워드가 확인되었습니다: {", ".join(matched_failure_keywords)}',
                metrics=metrics,
            )

        if disk_count >= min_disk_count:
            return self.ok(
                message=f'Disk 인식 개수가 정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
                reasons=f'format 출력에서 디스크 {disk_count}개가 확인되었습니다.',
                metrics=metrics,
                thresholds={
                    'expected_disk_count': min_disk_count,
                    'failure_keywords': failure_keywords,
                },
            )

        return self.fail(
            error=f'Disk 인식 개수가 비정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
            message=f'Disk 인식 개수가 비정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
            reasons=f'format 출력에서 기준보다 적은 디스크 {disk_count}개만 확인되었습니다.',
            metrics=metrics,
            thresholds={
                'expected_disk_count': min_disk_count,
                'failure_keywords': failure_keywords,
            },
        )


CHECK_CLASS = Check
