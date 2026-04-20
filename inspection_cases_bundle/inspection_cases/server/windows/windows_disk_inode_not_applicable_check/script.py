# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


DISK_INODE_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and $_.DriveLetter -and $_.FileSystem -eq 'NTFS' } | "
    "ForEach-Object { $t=(fsutil fsinfo ntfsinfo $_.DriveLetter 2>$null | Out-String); "
    "$m=[regex]::Match($t,'Mft Valid Data Length\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; "
    "$fr=[regex]::Match($t,'Bytes Per FileRecord Segment\\s*:\\s*([0-9]+)').Groups[1].Value; "
    "$bpc=[regex]::Match($t,'Bytes Per Cluster\\s*:\\s*([0-9]+)').Groups[1].Value; "
    "$zs=[regex]::Match($t,'Mft Zone Start\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; "
    "$ze=[regex]::Match($t,'Mft Zone End\\s*:\\s*0x([0-9A-Fa-f]+)').Groups[1].Value; "
    "$used=$(if($m -and $fr){[int64](([convert]::ToInt64($m,16))/[int64]$fr)}else{$null}); "
    "$total=$(if($zs -and $ze -and $bpc -and $fr){[int64]((([convert]::ToInt64($ze,16)-[convert]::ToInt64($zs,16))*[int64]$bpc)/[int64]$fr)}else{$null}); "
    "[pscustomobject]@{Filesystem=$_.FileSystem; 'Inodes(approx)'=$total; 'IUsed(approx)'=$used; 'IFree(approx)'=$(if($total -ne $null -and $used -ne $null){$total-$used}else{$null}); "
    "'IUse%(approx)'=$(if($total -gt 0 -and $used -ne $null){[math]::Round(($used/$total)*100,2)}else{$null}); 'Mounted on'=$_.Name.TrimEnd('\\')} } | ConvertTo-Json -Depth 3"
)


def _parse_float(value):
    return round(float(str(value).strip()), 2)


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_iuse_percent = self.get_threshold_var('max_iuse_percent', default=80.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(DISK_INODE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows inode 근사 사용률 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows inode 근사 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'inode 근사 사용률 정보 없음',
                message='inode 근사 사용률 결과가 비어 있습니다.',
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
                'inode 점검 실패 키워드 감지',
                message='inode 근사 사용률 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'inode 근사 사용률 파싱 실패',
                message='inode 근사 사용률 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            parsed.append({
                'filesystem': str(entry.get('Filesystem', '')).strip(),
                'mount_point': str(entry.get('Mounted on', '')).strip(),
                'inode_total': entry.get('Inodes(approx)', ''),
                'inode_used': entry.get('IUsed(approx)', ''),
                'inode_free': entry.get('IFree(approx)', ''),
                'inode_use_percent': entry.get('IUse%(approx)', ''),
            })

        if not parsed:
            return self.fail(
                'inode 근사 사용률 파싱 실패',
                message='inode 근사 사용률 행을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        measurable_entries = [
            entry for entry in parsed
            if entry['inode_total'] and entry['inode_used'] and entry['inode_free'] and entry['inode_use_percent']
        ]
        if not measurable_entries:
            return self.fail(
                'NTFS inode 근사 사용률 계산 불가',
                message='Windows inode 근사 사용률 점검에 실패했습니다. 현재 상태: IUsed(approx) 또는 IUse%(approx) 값을 확인할 수 없습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        over_threshold_mounts = []
        parsed_metrics = []
        for entry in measurable_entries:
            inode_total = int(entry['inode_total'])
            inode_used = int(entry['inode_used'])
            inode_free = int(entry['inode_free'])
            inode_use_percent = _parse_float(entry['inode_use_percent'])

            parsed_metrics.append({
                'filesystem': entry['filesystem'],
                'mount_point': entry['mount_point'],
                'inode_total': inode_total,
                'inode_used': inode_used,
                'inode_free': inode_free,
                'inode_use_percent': inode_use_percent,
            })

            if inode_use_percent > max_iuse_percent:
                over_threshold_mounts.append(f"{entry['mount_point']}({inode_use_percent}%)")

        max_iuse_entry = max(parsed_metrics, key=lambda entry: entry['inode_use_percent'])

        if over_threshold_mounts:
            return self.fail(
                'inode 사용률 임계치 초과',
                message='일부 파일시스템 inode 근사 사용률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filesystem_count': len(parsed_metrics),
                'max_iuse_percent': max_iuse_entry['inode_use_percent'],
                'max_iuse_filesystem': max_iuse_entry['filesystem'],
                'max_iuse_mount_point': max_iuse_entry['mount_point'],
                'inode_totals': [entry['inode_total'] for entry in parsed_metrics],
                'inode_used_values': [entry['inode_used'] for entry in parsed_metrics],
                'inode_free_values': [entry['inode_free'] for entry in parsed_metrics],
                'over_threshold_mounts': over_threshold_mounts,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_iuse_percent': max_iuse_percent,
                'failure_keywords': failure_keywords,
            },
            reasons='모든 파일시스템 inode 근사 사용률이 기준 범위 내입니다.',
            message=(
                f'Windows inode 근사 사용률 점검이 정상입니다. 현재 상태: '
                f'파일시스템 {len(parsed_metrics)}개, 최고 inode 사용률 '
                f'{max_iuse_entry["mount_point"]} {max_iuse_entry["inode_use_percent"]:.2f}% '
                f'(기준 {max_iuse_percent:.2f}% 이하).'
            ),
        )


CHECK_CLASS = Check
