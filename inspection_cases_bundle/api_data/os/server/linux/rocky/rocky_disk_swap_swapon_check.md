# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-SWAP-01

# is_required

필수

# inspection_name

Disk Swap 사용률

# inspection_content

사용 가능한 가상 메모리 크기 확인(하드디스크를 메모리처럼 사용하여 
부족한 메모리의 용량을 증대, 가상 메모리가 사용한 크기와 사용 가능
한 크기를 확인)

# inspection_command

```bash
swapon -s
```

# inspection_output

```text
Filename                                Type            Size    Used    Priority
/dev/sda3                               partition       1048572 0       -1
/dev/sdb3                               partition       1048572 128     -2
/var/swap/swapfile1                     file            2097148 4096    -3
/var/swap/swapfile2                     file            2097148 0       -4
```

# description

본 항목은 swapon -s 명령 결과를 기준으로 시스템의 스왑 사용 현황을 점검한다.
스왑 사용량은 물리 메모리 부족 여부를 간접적으로 판단할 수 있는 지표이다.
스왑 사용률이 낮거나 사용되지 않으면 일반적으로 메모리 상태가 양호한 것으로 본다.
반대로 스왑 사용률이 높으면 메모리 압박 또는 성능 저하 가능성이 있으므로 주의가 필요하다. 사용률을 기준으로 양호, 불량을 판단한다.

각 메모리의 사용률이 50% 초과

# thresholds

[
    {id: null, key: "max_swap_usage_percent", value: "50", sortOrder: 0}
,
{id: null, key: "min_swap_size_gb", value: "2", sortOrder: 1}
]

# inspection_script

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
