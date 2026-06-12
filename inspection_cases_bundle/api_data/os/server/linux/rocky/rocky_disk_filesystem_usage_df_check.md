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

U-REPLAY-DF-EX-01

# is_required

권고

# inspection_name

파일시스템 사용량

# inspection_content

파일시스템 사용량 점검

# inspection_command

```bash
df
```

# inspection_output

```text
Filesystem          1K-blocks      Used Available Use% Mounted on
devtmpfs              7831328         0   7831328   0% /dev
tmpfs                 7863464         8   7863456   1% /dev/shm
tmpfs                 3145388    338060   2807328  11% /run
/dev/mapper/rl-root  73364480  26892896  46471584  37% /
/dev/sda1             1038336    396548    641788  39% /boot
/dev/mapper/rl-home 793069212 174973520 618095692  23% /home
tmpfs                 1572692        36   1572656   1% /run/user/1000
```

# description

- `df` 명령을 실행해서 파일시스템별 사용률 정보를 가져온다.
- 임계치 `max_usage_percent`와 제외 목록 `exclude_mount_points`를 읽고, 제외 목록은 `|` 기준으로 분리한다.
- 각 행에서 파일시스템, 마운트포인트, 사용률을 파싱한 뒤 제외 대상은 점검 목록에서 뺀다.
- 제외 후 남은 파일시스템 중 사용률이 임계치를 넘는 항목이 하나라도 있으면 실패한다.
- 모두 임계치 이하이면 최대 사용률 파일시스템, 제외 항목, 전체 개수를 metrics로 남기고 정상 처리한다.

- **양호**: `exclude_mount_points`에 포함된 마운트포인트를 제외한 모든 파일시스템의 `Use%` 값이 `max_usage_percent` 이하인 상태
- **실패**: 제외 후 점검 대상 파일시스템 중 하나 이상에서 `Use%` 값이 `max_usage_percent`를 초과한 상태
- **점검 제외**: `exclude_mount_points`에 지정된 마운트포인트는 용도나 정책상 별도 관리 대상으로 보고 파일시스템 사용량 판정에서 제외
- **확인 필요**: `df` 명령 실행에 실패하거나 출력 형식이 달라 파일시스템, 마운트포인트, 사용률을 파싱할 수 없는 상태

# thresholds

[
    {id: null, key: "max_usage_percent", value: "80", sortOrder: 0}
,
{id: null, key: "exclude_mount_points", value: "/", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DF_COMMAND = 'df'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        max_usage_percent = self.get_threshold_var('max_usage_percent', default=80, value_type='int')
        exclude_mount_points_raw = self.get_threshold_var('exclude_mount_points', default='', value_type='str')
        excluded_targets = {
            token.strip()
            for token in str(exclude_mount_points_raw or '').split('|')
            if token.strip()
        }
        rc, out, err = self._ssh(DF_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='df 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '디스크 사용량 정보 없음',
                message='df 결과를 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = []
        excluded_entries = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6 or not parts[4].endswith('%'):
                continue
            try:
                usage_percent = int(parts[4].rstrip('%'))
            except ValueError:
                continue

            entry = {
                'filesystem': parts[0],
                'size_1k_blocks': parts[1],
                'used_1k_blocks': parts[2],
                'available_1k_blocks': parts[3],
                'usage_percent': usage_percent,
                'mount_point': parts[5],
            }

            if entry['filesystem'] in excluded_targets or entry['mount_point'] in excluded_targets:
                excluded_entries.append(entry)
                continue
            parsed.append(entry)

        if not parsed:
            return self.fail(
                '디스크 사용량 파싱 실패',
                message='제외 대상을 반영한 뒤 점검할 파일시스템이 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        max_usage_entry = max(parsed, key=lambda entry: entry['usage_percent'])
        over_threshold_mounts = [
            f"{entry['mount_point']}({entry['usage_percent']}%)"
            for entry in parsed
            if entry['usage_percent'] > max_usage_percent
        ]

        if over_threshold_mounts:
            return self.fail(
                '디스크 사용률 임계치 초과',
                message=(
                    '일부 파일시스템 사용률이 기준을 초과했습니다: '
                    + ', '.join(over_threshold_mounts) + '. '
                    f'임계치 정보: max_usage_percent={max_usage_percent}%, '
                    f'exclude_mount_points={"|".join(sorted(excluded_targets)) or "없음"}. '
                    f'판단근거: 최대 사용률은 '
                    f'{max_usage_entry["mount_point"]}={max_usage_entry["usage_percent"]}%이고, '
                    f'임계치 초과 항목={", ".join(over_threshold_mounts)}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filesystem_count': len(parsed),
                'max_usage_percent': max_usage_entry['usage_percent'],
                'max_usage_filesystem': max_usage_entry['filesystem'],
                'max_usage_mount_point': max_usage_entry['mount_point'],
                'excluded_targets': sorted(excluded_targets),
                'excluded_filesystems': excluded_entries,
                'over_threshold_mounts': over_threshold_mounts,
            },
            thresholds={
                'max_usage_percent': max_usage_percent,
                'exclude_mount_points': '|'.join(sorted(excluded_targets)),
            },
            reasons=(
                f'제외 대상 외 최대 파일시스템 사용률 {max_usage_entry["usage_percent"]}%가 '
                f'임계치 {max_usage_percent}% 이하입니다.'
            ),
            message=(
                'df 기준 디스크 사용률 점검이 정상 수행되었습니다. '
                f'임계치 정보: max_usage_percent={max_usage_percent}%, '
                f'exclude_mount_points={"|".join(sorted(excluded_targets)) or "없음"}. '
                f'판단근거: 제외 대상 {len(excluded_entries)}개를 제외한 '
                f'점검 파일시스템 {len(parsed)}개 중 최대 사용률은 '
                f'{max_usage_entry["mount_point"]}={max_usage_entry["usage_percent"]}%입니다.'
            ),
        )


CHECK_CLASS = Check
