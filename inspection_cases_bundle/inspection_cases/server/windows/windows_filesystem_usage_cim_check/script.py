# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DISK_USAGE_COMMAND = (
    "Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and $_.Capacity } | "
    "Select-Object @{N='Filesystem';E={if($_.DriveLetter){$_.DriveLetter}else{$_.Name.TrimEnd('\\')}}},"
    "@{N='Size(GB)';E={[math]::Round($_.Capacity/1GB,2)}},"
    "@{N='Used(GB)';E={[math]::Round(($_.Capacity-$_.FreeSpace)/1GB,2)}},"
    "@{N='Avail(GB)';E={[math]::Round($_.FreeSpace/1GB,2)}},"
    "@{N='Use%';E={[math]::Round((($_.Capacity-$_.FreeSpace)/$_.Capacity)*100,2)}},"
    "@{N='Mounted on';E={$_.Name.TrimEnd('\\')}} | Format-Table -Auto"
)


def _parse_float(value):
    return round(float(str(value).strip()), 2)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_usage_percent = self.get_threshold_var('max_usage_percent', default=80.0, value_type='float')
        min_available_percent = self.get_threshold_var('min_available_percent', default=20.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(DISK_USAGE_COMMAND)

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
                message='Windows 디스크 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '디스크 사용량 정보 없음',
                message='디스크 사용률 결과가 비어 있습니다.',
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
                '디스크 점검 실패 키워드 감지',
                message='디스크 사용률 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if len(lines) < 3:
            return self.fail(
                '디스크 사용량 정보 없음',
                message='디스크 사용률 결과를 해석할 수 없습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = []
        for line in lines[2:]:
            if line.lstrip().startswith('---'):
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            try:
                size_gb = _parse_float(parts[1])
                used_gb = _parse_float(parts[2])
                avail_gb = _parse_float(parts[3])
                usage_percent = _parse_float(parts[4])
            except ValueError:
                continue

            available_percent = round((avail_gb / size_gb) * 100, 2) if size_gb > 0 else 0.0
            parsed.append({
                'filesystem': parts[0],
                'size_gb': size_gb,
                'used_gb': used_gb,
                'avail_gb': avail_gb,
                'usage_percent': usage_percent,
                'available_percent': available_percent,
                'mount_point': parts[5],
            })

        if not parsed:
            return self.fail(
                '디스크 사용량 파싱 실패',
                message='사용률(Use%)이 포함된 볼륨 정보를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        max_usage_entry = max(parsed, key=lambda entry: entry['usage_percent'])
        min_available_entry = min(parsed, key=lambda entry: entry['available_percent'])
        over_usage_mounts = [
            f"{entry['mount_point']}({entry['usage_percent']}%)"
            for entry in parsed
            if entry['usage_percent'] >= max_usage_percent
        ]
        low_available_mounts = [
            f"{entry['mount_point']}({entry['available_percent']}%)"
            for entry in parsed
            if entry['available_percent'] < min_available_percent
        ]

        if over_usage_mounts:
            return self.fail(
                '디스크 사용률 임계치 초과',
                message='일부 볼륨 사용률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if low_available_mounts:
            return self.fail(
                '디스크 가용 공간 비율 임계치 미달',
                message='일부 볼륨의 남은 디스크 공간 비율이 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filesystem_count': len(parsed),
                'max_usage_percent': max_usage_entry['usage_percent'],
                'max_usage_filesystem': max_usage_entry['filesystem'],
                'max_usage_mount_point': max_usage_entry['mount_point'],
                'min_available_percent': min_available_entry['available_percent'],
                'min_available_filesystem': min_available_entry['filesystem'],
                'min_available_mount_point': min_available_entry['mount_point'],
                'over_usage_mounts': over_usage_mounts,
                'low_available_mounts': low_available_mounts,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_usage_percent': max_usage_percent,
                'min_available_percent': min_available_percent,
                'failure_keywords': failure_keywords,
            },
            reasons='모든 볼륨 사용률과 가용 공간 비율이 기준 범위 내입니다.',
            message='Windows 디스크 사용률 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
