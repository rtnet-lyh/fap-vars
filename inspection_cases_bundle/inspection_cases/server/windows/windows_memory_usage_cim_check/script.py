# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


MEMORY_USAGE_COMMAND = (
    '$os=Get-CimInstance Win32_OperatingSystem;'
    '$pf=Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue;'
    '$mt=[double]$os.TotalVisibleMemorySize*1KB;'
    '$mf=[double]$os.FreePhysicalMemory*1KB;'
    '$mu=$mt-$mf;'
    '$pt=([double](($pf|Measure-Object -Property AllocatedBaseSize -Sum).Sum))*1MB;'
    '$pu=([double](($pf|Measure-Object -Property CurrentUsage -Sum).Sum))*1MB;'
    'if(-not $pt){$pt=0};'
    'if(-not $pu){$pu=0};'
    '$pfree=[Math]::Max($pt-$pu,0);'
    "'MEM total={0:N2}GiB used={1:N2}GiB free={2:N2}GiB usage={3:N2}% | SWAP total={4:N2}GiB used={5:N2}GiB free={6:N2}GiB' -f "
    '($mt/1GB),($mu/1GB),($mf/1GB),(($mu/$mt)*100),($pt/1GB),($pu/1GB),($pfree/1GB)'
)


def _parse_float(value):
    return round(float(value), 2)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_memory_usage_percent = self.get_threshold_var('max_memory_usage_percent', default=80.0, value_type='float')
        min_memory_free_percent = self.get_threshold_var('min_memory_free_percent', default=20.0, value_type='float')
        max_swap_usage_percent = self.get_threshold_var('max_swap_usage_percent', default=50.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(MEMORY_USAGE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 메모리 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '메모리 사용률 정보 없음',
                message='메모리 사용률 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '메모리 점검 실패 키워드 감지',
                message='메모리 사용률 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        match = re.search(
            r'MEM total=([0-9]+(?:\.[0-9]+)?)GiB '
            r'used=([0-9]+(?:\.[0-9]+)?)GiB '
            r'free=([0-9]+(?:\.[0-9]+)?)GiB '
            r'usage=([0-9]+(?:\.[0-9]+)?)% \| '
            r'SWAP total=([0-9]+(?:\.[0-9]+)?)GiB '
            r'used=([0-9]+(?:\.[0-9]+)?)GiB '
            r'free=([0-9]+(?:\.[0-9]+)?)GiB',
            text,
        )
        if not match:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='메모리 사용률 출력 형식을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        memory_total_gib = _parse_float(match.group(1))
        memory_used_gib = _parse_float(match.group(2))
        memory_free_gib = _parse_float(match.group(3))
        memory_usage_percent = _parse_float(match.group(4))
        swap_total_gib = _parse_float(match.group(5))
        swap_used_gib = _parse_float(match.group(6))
        swap_free_gib = _parse_float(match.group(7))

        memory_free_percent = round((memory_free_gib / memory_total_gib) * 100, 2) if memory_total_gib > 0 else 0.0
        swap_usage_percent = round((swap_used_gib / swap_total_gib) * 100, 2) if swap_total_gib > 0 else 0.0

        if memory_usage_percent >= max_memory_usage_percent:
            return self.fail(
                '메모리 사용률 임계치 초과',
                message='물리 메모리 사용률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if memory_free_percent <= min_memory_free_percent:
            return self.fail(
                '가용 메모리 비율 임계치 미달',
                message='사용 가능한 물리 메모리 비율이 기준치 이하입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if swap_usage_percent >= max_swap_usage_percent:
            return self.fail(
                '스왑 사용률 임계치 초과',
                message='스왑 사용률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'memory_total_gib': memory_total_gib,
                'memory_used_gib': memory_used_gib,
                'memory_free_gib': memory_free_gib,
                'memory_usage_percent': memory_usage_percent,
                'memory_free_percent': memory_free_percent,
                'swap_total_gib': swap_total_gib,
                'swap_used_gib': swap_used_gib,
                'swap_free_gib': swap_free_gib,
                'swap_usage_percent': swap_usage_percent,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_memory_usage_percent': max_memory_usage_percent,
                'min_memory_free_percent': min_memory_free_percent,
                'max_swap_usage_percent': max_swap_usage_percent,
                'failure_keywords': failure_keywords,
            },
            reasons='물리 메모리 사용률, 가용 메모리 비율, 스왑 사용률이 모두 기준 범위 내입니다.',
            message='Windows 메모리 사용률 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
