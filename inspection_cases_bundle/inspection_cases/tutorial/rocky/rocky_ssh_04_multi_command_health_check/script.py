# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


NPROC_COMMAND = 'nproc'
FREE_COMMAND = 'free -m'
UPTIME_COMMAND = 'uptime'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _run_command(self, command, failure_message):
        rc, out, err = self._ssh(command)
        if self._is_connection_error(rc, err):
            return None, self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return None, self.fail(
                '점검 명령 실행 실패',
                message=failure_message,
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
        return (out or '').strip(), None

    def run(self):
        min_cpu_core_count = self.get_threshold_var('min_cpu_core_count', default=1, value_type='int')
        min_available_memory_mb = self.get_threshold_var(
            'min_available_memory_mb',
            default=256,
            value_type='int',
        )

        nproc_out, error = self._run_command(NPROC_COMMAND, 'nproc 명령 실행에 실패했습니다.')
        if error:
            return error

        free_out, error = self._run_command(FREE_COMMAND, 'free -m 명령 실행에 실패했습니다.')
        if error:
            return error

        uptime_out, error = self._run_command(UPTIME_COMMAND, 'uptime 명령 실행에 실패했습니다.')
        if error:
            return error

        try:
            cpu_core_count = int(nproc_out.splitlines()[-1].strip())
        except (IndexError, ValueError):
            return self.fail(
                '출력 파싱 실패',
                message='nproc 결과를 정수로 해석하지 못했습니다.',
                stdout=nproc_out,
            )

        mem_line = next((line for line in free_out.splitlines() if line.strip().startswith('Mem:')), '')
        mem_parts = mem_line.split()
        if len(mem_parts) < 7:
            return self.fail(
                '출력 파싱 실패',
                message='free -m 결과의 Mem 라인을 해석하지 못했습니다.',
                stdout=free_out,
            )

        try:
            total_memory_mb = int(mem_parts[1])
            used_memory_mb = int(mem_parts[2])
            available_memory_mb = int(mem_parts[6])
        except ValueError:
            return self.fail(
                '출력 파싱 실패',
                message='free -m 결과를 정수로 변환하지 못했습니다.',
                stdout=free_out,
            )

        load_match = re.search(r'load average: (.+)$', uptime_out)
        load_average = load_match.group(1).strip() if load_match else ''

        if cpu_core_count < min_cpu_core_count:
            return self.fail(
                'CPU 코어 수 기준 미달',
                message=(
                    f'확인된 CPU 코어 수가 기준 미만입니다: '
                    f'{cpu_core_count}개 (기준 {min_cpu_core_count}개 이상)'
                ),
                stdout=nproc_out,
            )

        if available_memory_mb < min_available_memory_mb:
            return self.fail(
                '가용 메모리 기준 미달',
                message=(
                    f'가용 메모리가 기준 미만입니다: '
                    f'{available_memory_mb}MB (기준 {min_available_memory_mb}MB 이상)'
                ),
                stdout=free_out,
            )

        return self.ok(
            metrics={
                'cpu_core_count': cpu_core_count,
                'total_memory_mb': total_memory_mb,
                'used_memory_mb': used_memory_mb,
                'available_memory_mb': available_memory_mb,
                'uptime_text': uptime_out,
                'load_average': load_average,
            },
            thresholds={
                'min_cpu_core_count': min_cpu_core_count,
                'min_available_memory_mb': min_available_memory_mb,
            },
            reasons='CPU, 메모리, uptime 정보를 여러 명령으로 정상 수집했습니다.',
            message=(
                '_ssh 다중 명령 예제가 정상 수행되었습니다. '
                f'cores={cpu_core_count}, available_memory_mb={available_memory_mb}'
            ),
        )


CHECK_CLASS = Check
