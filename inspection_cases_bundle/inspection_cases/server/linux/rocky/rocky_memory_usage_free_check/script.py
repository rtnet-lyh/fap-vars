# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


FREE_COMMAND = 'free'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        min_available_memory_percent = self.get_threshold_var('min_available_memory_percent', default=10.0, value_type='float')
        max_swap_usage_percent = self.get_threshold_var('max_swap_usage_percent', default=50.0, value_type='float')
        rc, out, err = self._ssh(FREE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='free 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 3:
            return self.fail(
                '메모리 정보 없음',
                message='free 결과를 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        mem_line = next((line for line in lines if line.strip().startswith('Mem:')), '')
        swap_line = next((line for line in lines if line.strip().startswith('Swap:')), '')
        if not mem_line or not swap_line:
            return self.fail(
                '메모리 정보 파싱 실패',
                message='Mem 또는 Swap 행을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        mem_parts = re.split(r'\s+', mem_line.strip())
        swap_parts = re.split(r'\s+', swap_line.strip())
        if len(mem_parts) < 7 or len(swap_parts) < 4:
            return self.fail(
                '메모리 정보 파싱 실패',
                message='free 출력 컬럼 수가 예상과 다릅니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            mem_total_kib = int(mem_parts[1])
            mem_used_kib = int(mem_parts[2])
            mem_free_kib = int(mem_parts[3])
            mem_shared_kib = int(mem_parts[4])
            mem_buff_cache_kib = int(mem_parts[5])
            mem_available_kib = int(mem_parts[6])
            swap_total_kib = int(swap_parts[1])
            swap_used_kib = int(swap_parts[2])
            swap_free_kib = int(swap_parts[3])
        except ValueError:
            return self.fail(
                '메모리 정보 파싱 실패',
                message='메모리 또는 swap 수치 값을 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if mem_total_kib <= 0:
            return self.fail(
                '메모리 총량 비정상',
                message='총 메모리 용량이 0 이하로 표시됩니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        available_memory_percent = round((mem_available_kib / mem_total_kib) * 100, 2)
        swap_usage_percent = round((swap_used_kib / swap_total_kib) * 100, 2, ) if swap_total_kib > 0 else 0.0
        threshold_summary = (
            f'min_available_memory_percent={min_available_memory_percent}%, '
            f'max_swap_usage_percent={max_swap_usage_percent}%'
        )

        if available_memory_percent < min_available_memory_percent:
            return self.fail(
                '사용 가능 메모리 부족',
                message=(
                    '사용 가능 메모리 비율이 최소 기준보다 작습니다. '
                    f'임계치 정보: {threshold_summary}. '
                    f'판단근거: available_memory_percent={available_memory_percent}%가 '
                    f'min_available_memory_percent={min_available_memory_percent}%보다 작습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if swap_usage_percent > max_swap_usage_percent:
            return self.fail(
                'swap 사용률 임계치 초과',
                message=(
                    'swap 사용률이 기준치를 초과했습니다. '
                    f'임계치 정보: {threshold_summary}. '
                    f'판단근거: swap_usage_percent={swap_usage_percent}%가 '
                    f'max_swap_usage_percent={max_swap_usage_percent}%보다 큽니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'mem_total_kib': mem_total_kib,
                'mem_used_kib': mem_used_kib,
                'mem_free_kib': mem_free_kib,
                'mem_shared_kib': mem_shared_kib,
                'mem_buff_cache_kib': mem_buff_cache_kib,
                'mem_available_kib': mem_available_kib,
                'available_memory_percent': available_memory_percent,
                'swap_total_kib': swap_total_kib,
                'swap_used_kib': swap_used_kib,
                'swap_free_kib': swap_free_kib,
                'swap_usage_percent': swap_usage_percent,
            },
            thresholds={
                'min_available_memory_percent': min_available_memory_percent,
                'max_swap_usage_percent': max_swap_usage_percent,
            },
            reasons=(
                f'available_memory_percent={available_memory_percent}%가 '
                f'최소 기준 {min_available_memory_percent}% 이상이고 '
                f'swap_usage_percent={swap_usage_percent}%가 '
                f'최대 기준 {max_swap_usage_percent}% 이하입니다.'
            ),
            message=(
                'free 기준 메모리 사용률 점검이 정상 수행되었습니다. '
                f'임계치 정보: {threshold_summary}. '
                f'판단근거: available_memory_percent={available_memory_percent}%, '
                f'swap_usage_percent={swap_usage_percent}%, '
                f'mem_available_kib={mem_available_kib}, swap_used_kib={swap_used_kib}.'
            ),
        )


CHECK_CLASS = Check
