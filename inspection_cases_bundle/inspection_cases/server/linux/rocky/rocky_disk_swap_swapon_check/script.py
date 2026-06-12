# -*- coding: utf-8 -*-

from .common._base import BaseCheck


SWAPON_COMMAND = 'swapon -s'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        max_swap_usage_percent = self.get_threshold_var('max_swap_usage_percent', default=50.0, value_type='float')
        min_swap_size_gb = self.get_threshold_var('min_swap_size_gb', default=0.0, value_type='float')
        rc, out, err = self._ssh(SWAPON_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='swapon -s 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                'swap 항목 미존재',
                message='활성화된 swap 항목을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        entries = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                size_kib = int(parts[2])
                used_kib = int(parts[3])
            except ValueError:
                continue
            entries.append({
                'filename': parts[0],
                'swap_type': parts[1],
                'size_kib': size_kib,
                'used_kib': used_kib,
                'priority': parts[4],
            })

        if not entries:
            return self.fail(
                'swap 항목 파싱 실패',
                message='활성화된 swap 항목을 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        total_size_kib = sum(entry['size_kib'] for entry in entries)
        total_used_kib = sum(entry['used_kib'] for entry in entries)
        total_size_mib = round(total_size_kib / 1024.0, 2)
        total_used_mib = round(total_used_kib / 1024.0, 2)
        total_size_gb = round(total_size_kib / (1024.0 * 1024.0), 2)

        for entry in entries:
            size_kib = entry['size_kib']
            used_kib = entry['used_kib']
            usage_percent = round((used_kib / size_kib) * 100, 2) if size_kib > 0 else 0.0
            entry['usage_percent'] = usage_percent
            entry['size_mib'] = round(size_kib / 1024.0, 2)
            entry['used_mib'] = round(used_kib / 1024.0, 2)

        max_usage_entry = max(entries, key=lambda entry: entry['usage_percent'])
        over_threshold_entries = [
            f"{entry['filename']}({entry['usage_percent']}%)"
            for entry in entries
            if entry['usage_percent'] > max_swap_usage_percent
        ]

        if min_swap_size_gb > 0 and total_size_gb < min_swap_size_gb:
            return self.fail(
                'swap 용량 부족',
                message=(
                    f'총 swap 용량이 최소 기준보다 작습니다: '
                    f'min={min_swap_size_gb}GB, current={total_size_gb}GB, '
                    f'max_usage={max_usage_entry["usage_percent"]}%'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if over_threshold_entries:
            return self.fail(
                'swap 사용률 임계치 초과',
                message=(
                    f'일부 swap 사용률이 기준치를 초과했습니다: '
                    f'total_swap={total_size_gb}GB, ' + ', '.join(over_threshold_entries)
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'swap_entry_count': len(entries),
                'total_swap_size_kib': total_size_kib,
                'total_swap_used_kib': total_used_kib,
                'total_swap_size_mib': total_size_mib,
                'total_swap_used_mib': total_used_mib,
                'total_swap_size_gb': total_size_gb,
                'max_swap_usage_percent': max_usage_entry['usage_percent'],
                'max_swap_usage_target': max_usage_entry['filename'],
                'over_threshold_entries': over_threshold_entries,
                'swap_entries': entries,
            },
            thresholds={
                'max_swap_usage_percent': max_swap_usage_percent,
                'min_swap_size_gb': min_swap_size_gb,
            },
            reasons='모든 swap 항목의 사용률이 임계치 이하입니다.',
            message=f'swapon -s 기준 swap 점검이 정상 수행되었습니다. total_swap={total_size_gb}GB',
        )


CHECK_CLASS = Check
