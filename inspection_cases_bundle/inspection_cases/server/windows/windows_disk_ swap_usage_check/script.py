# -*- coding: utf-8 -*-

from .common._base import BaseCheck


SWAP_MEMORY_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-CimInstance Win32_PageFileUsage | "
    "Select-Object @{N='Filename';E={$_.Name}},@{N='Type';E={'file'}},@{N='Size(MB)';E={$_.AllocatedBaseSize}},"
    "@{N='Used(MB)';E={$_.CurrentUsage}},@{N='Usage(%)';E={if($_.AllocatedBaseSize){[math]::Round(($_.CurrentUsage/$_.AllocatedBaseSize)*100,2)}else{0}}},"
    "@{N='Peak(MB)';E={$_.PeakUsage}}"
)


def _parse_float(value):
    return round(float(str(value).strip()), 2)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_swap_usage_percent = self.get_threshold_var('max_swap_usage_percent', default=50.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(SWAP_MEMORY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 스왑 메모리 사용률 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 스왑 메모리 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '스왑 메모리 정보 없음',
                message='스왑 메모리 사용률 결과가 비어 있습니다.',
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
                '스왑 메모리 점검 실패 키워드 감지',
                message='스왑 메모리 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        result_map = {}
        for line in text.splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            result_map[key.strip().lower()] = value.strip()

        required_keys = ['filename', 'type', 'size(mb)', 'used(mb)', 'usage(%)', 'peak(mb)']
        if any(not result_map.get(key) for key in required_keys):
            return self.fail(
                '스왑 메모리 파싱 실패',
                message='스왑 메모리 출력 형식을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            swap_size_mb = _parse_float(result_map['size(mb)'])
            swap_used_mb = _parse_float(result_map['used(mb)'])
            swap_usage_percent = _parse_float(result_map['usage(%)'])
            peak_usage_mb = _parse_float(result_map['peak(mb)'])
        except ValueError:
            return self.fail(
                '스왑 메모리 파싱 실패',
                message='스왑 메모리 수치 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        swap_free_mb = round(max(swap_size_mb - swap_used_mb, 0.0), 2)
        swap_size_gib = round(swap_size_mb / 1024, 2)
        swap_used_gib = round(swap_used_mb / 1024, 2)
        swap_free_gib = round(swap_free_mb / 1024, 2)
        peak_usage_gib = round(peak_usage_mb / 1024, 2)

        if swap_usage_percent >= max_swap_usage_percent:
            return self.fail(
                '스왑 메모리 사용률 임계치 초과',
                message='스왑 메모리 사용률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filename': result_map['filename'],
                'swap_type': result_map['type'],
                'swap_size_mb': swap_size_mb,
                'swap_used_mb': swap_used_mb,
                'swap_free_mb': swap_free_mb,
                'swap_usage_percent': swap_usage_percent,
                'peak_usage_mb': peak_usage_mb,
                'swap_size_gib': swap_size_gib,
                'swap_used_gib': swap_used_gib,
                'swap_free_gib': swap_free_gib,
                'peak_usage_gib': peak_usage_gib,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_swap_usage_percent': max_swap_usage_percent,
                'failure_keywords': failure_keywords,
            },
            reasons='스왑 메모리 사용률이 기준 범위 내입니다.',
            message=(
                f'Windows 스왑 메모리 사용률 점검이 정상입니다. 현재 상태: '
                f'파일={result_map["filename"]}, 총 {swap_size_gib:.2f}GiB, 사용 {swap_used_gib:.2f}GiB, '
                f'여유 {swap_free_gib:.2f}GiB, 사용률 {swap_usage_percent:.2f}% '
                f'(기준 {max_swap_usage_percent:.2f}% 미만), 피크 {peak_usage_gib:.2f}GiB.'
            ),
        )


CHECK_CLASS = Check
