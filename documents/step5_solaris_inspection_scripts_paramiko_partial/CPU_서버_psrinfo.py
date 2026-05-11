# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PSRINFO_COMMAND = 'psrinfo'
ONLINE_KEYWORD = 'on-line'
OFFLINE_KEYWORD = 'off-line'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False
    PARAMIKO_AUTH_METHOD = 'auto'
    PARAMIKO_TIMEOUT_SEC = 10
    PARAMIKO_BANNER_TIMEOUT_SEC = 10
    PARAMIKO_AUTH_TIMEOUT_SEC = 30
    PARAMIKO_READ_TIMEOUT_SEC = 0.5
    PARAMIKO_PROBE_PROMPT = True
    PARAMIKO_CONTINUE_ON_TIMEOUT = False

    def _find_check_result(self, results):
        for item in reversed(results or []):
            if item.get('command') == PSRINFO_COMMAND:
                return item
        return None

    def run(self):
        try:
            results = self._run_solaris_commands([
                {'command': PSRINFO_COMMAND, 'timeout': 10},
            ])
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
                error='psrinfo 명령 결과 없음',
                message='psrinfo 명령 실행 결과를 찾지 못했습니다.',
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
        out = result.get('stdout', '')
        err = result.get('stderr', '')
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return self.fail(
                error='psrinfo 명령 실행 실패',
                message='Solaris CPU 코어 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                error='psrinfo 명령 실행 실패',
                message=f'psrinfo 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        cpu_lines = out.splitlines()
        online_cpus = []
        offline_cpus = []

        for line in cpu_lines:
            if ONLINE_KEYWORD.lower() in line.lower():
                online_cpus.append(line)
            if OFFLINE_KEYWORD.lower() in line.lower():
                offline_cpus.append(line)

        metrics = {
            'online_cpus': online_cpus,
            'offline_cpus': offline_cpus,
        }

        if offline_cpus:
            return self.fail(
                error=f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                message=f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                reasons=f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                metrics=metrics,
            )
        if online_cpus:
            return self.ok(
                message=f'offline_cpu가 존재하지 않습니다. online_cpu가 {len(online_cpus)}개 존재합니다.',
                reasons=f'offline_cpu가 존재하지 않습니다. online_cpu가 {len(online_cpus)}개 존재합니다.',
                metrics=metrics,
            )
        return self.fail(
            error='on/offline cpu 정보 수집에 실패하였습니다.',
            message='on/offline cpu 정보 수집에 실패하였습니다.',
            reasons='on/offline cpu 정보 수집에 실패하였습니다.',
            metrics=metrics,
        )


CHECK_CLASS = Check
