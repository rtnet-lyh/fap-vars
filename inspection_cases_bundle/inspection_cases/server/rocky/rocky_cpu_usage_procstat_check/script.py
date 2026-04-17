# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CPU_USAGE_COMMAND = (
    "bash -lc '"
    "read cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; "
    "total1=$((user + nice + system + idle + iowait + irq + softirq + steal)); "
    "idle1=$((idle + iowait)); "
    "sleep 1; "
    "read cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; "
    "total2=$((user + nice + system + idle + iowait + irq + softirq + steal)); "
    "idle2=$((idle + iowait)); "
    "total_diff=$((total2 - total1)); "
    "idle_diff=$((idle2 - idle1)); "
    "cpu_usage=$(awk \"BEGIN {printf \\\"%.2f\\\", (1 - $idle_diff / $total_diff) * 100}\"); "
    "echo \"CPU Usage: ${cpu_usage}%\""
    "'"
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        max_cpu_usage_percent = self.get_threshold_var('max_cpu_usage_percent', default=80.0, value_type='float')
        rc, out, err = self._ssh(CPU_USAGE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='CPU 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        match = re.search(r'CPU Usage:\s*([0-9]+(?:\.[0-9]+)?)%', out or '')
        if not match:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='CPU 사용률 출력 형식을 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        cpu_usage_percent = round(float(match.group(1)), 2)
        if cpu_usage_percent > max_cpu_usage_percent:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=(
                    'CPU 사용률이 기준치를 초과했습니다. '
                    f'임계치 정보: max_cpu_usage_percent={max_cpu_usage_percent}%. '
                    f'판단근거: 측정 CPU 사용률 {cpu_usage_percent}%가 '
                    f'임계치 {max_cpu_usage_percent}%보다 큽니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'cpu_usage_percent': cpu_usage_percent,
            },
            thresholds={
                'max_cpu_usage_percent': max_cpu_usage_percent,
            },
            reasons=(
                f'측정 CPU 사용률 {cpu_usage_percent}%가 '
                f'임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
            message=(
                'CPU 사용률 점검이 정상 수행되었습니다. '
                f'임계치 정보: max_cpu_usage_percent={max_cpu_usage_percent}%. '
                f'판단근거: 측정 CPU 사용률 {cpu_usage_percent}%가 '
                f'임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
        )


CHECK_CLASS = Check
