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

U-REPLAY-INODE-01

# is_required

권고

# inspection_name

I-Node 사용률

# inspection_content

`df -i` 명령 결과를 이용하여 파일시스템별 I-Node 사용률 점검

# inspection_command

```bash
df -i
```

# inspection_output

```text
Filesystem    512-blocks      Free %Used    Iused %Iused Mounted on
/dev/hd4        10485760   6886888   35%    30040     4% /
/dev/hd2        20971520  12360784   42%    87134     6% /usr
/dev/hd9var     31457280  14136944   56%    13838     1% /var
/dev/hd3        31457280  19907296   37%     2341     1% /tmp
/dev/hd1        20971520  19179464    9%     5287     1% /home
/dev/hd10opt    20971520  19118752    9%    15867     1% /opt
/dev/nbu_lv     41943040  20571944   51%     7013     1% /netbackup
/dev/hd11admin    1048576   1046912    1%        7     1% /admin
/proc                  -         -    -         -     -  /proc
/dev/livedump    1048576   1047760    1%        4     1% /var/adm/ras/livedump
/dev/kras_lv   335544320 308189416    9%    41084     1% /kras_home
/dev/ora_lv    104857600  74727808   29%    16000     1% /oracle10
/dev/tmax_lv   377487360 246001464   35%  1764105     7% /tmax
/dev/klissido_lv   25165824  17412576   31%    50619     3% /klissido
/dev/app_lv     83886080  38536272   55%    34122     1% /app
/dev/irais_city_lv   20971520  16771752   21%     2074     1% /irais_city
/dev/landinfo_lv 1258291200 483399400   62%  3899073     7% /landinfo
/dev/lv_landtest  209715200 149812096   29%   756020     5% /land_test
```

# description

- `df -i` 명령은 파일시스템별 I-Node 사용량과 사용률을 확인하기 위한 명령이다.
- I-Node는 파일 및 디렉토리의 메타정보를 저장하는 자원으로, 용량이 충분하더라도 I-Node가 모두 소진되면 신규 파일 생성이 불가능하다.
- `%Iused` 값이 높을수록 해당 파일시스템에 생성된 파일 수가 많음을 의미하며, 소량 파일이 대량으로 생성되는 환경에서는 특히 주의가 필요하다.
- 특정 마운트 포인트의 I-Node 사용률이 임계치 이상이면 불필요한 파일, 로그, 임시파일 정리 여부를 점검하도록 권고한다.
- 파일시스템 용량 사용률과 별개로 I-Node 사용률도 함께 점검하여 파일 생성 장애를 예방해야 한다.

- **양호**: 파일시스템별 `%Iused` 값이 임계치 미만이며, 전반적으로 I-Node 사용률이 안정적인 상태
- **실패**: 일부 파일시스템의 `%Iused` 값이 임계치에 근접하여 지속적인 모니터링이 필요한 상태
- **경고**: 하나 이상의 파일시스템에서 `%Iused` 값이 임계치 이상으로 높아 파일 생성 장애 가능성이 있는 상태
- **참고**: `/proc` 등 가상 파일시스템은 실제 디스크 I-Node 점검 대상에서 제외할 수 있음

# thresholds

[
    {id: null, key: "max_inode_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DF_INODE_COMMAND = 'df -i'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        max_inode_usage_percent = self.get_threshold_var('max_inode_usage_percent', default=80, value_type='int')
        rc, out, err = self._ssh(DF_INODE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='df -i 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                'I-Node 사용률 정보 없음',
                message='df -i 결과를 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = []
        skipped_entries = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                skipped_entries.append({'raw_line': line, 'reason': 'column_count'})
                continue

            inode_usage_raw = parts[-2]
            if not inode_usage_raw.endswith('%'):
                skipped_entries.append({'raw_line': line, 'reason': 'inode_usage_not_percent'})
                continue

            try:
                inode_usage_percent = int(inode_usage_raw.rstrip('%'))
            except ValueError:
                skipped_entries.append({'raw_line': line, 'reason': 'inode_usage_parse_error'})
                continue

            parsed.append({
                'filesystem': parts[0],
                'inode_used_raw': parts[-3],
                'inode_usage_percent': inode_usage_percent,
                'mount_point': parts[-1],
                'raw_columns': parts[1:-1],
            })

        if not parsed:
            return self.fail(
                'I-Node 사용률 파싱 실패',
                message='점검 가능한 파일시스템의 %Iused 값을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        max_inode_entry = max(parsed, key=lambda entry: entry['inode_usage_percent'])
        over_threshold_mounts = [
            f"{entry['mount_point']}({entry['inode_usage_percent']}%)"
            for entry in parsed
            if entry['inode_usage_percent'] >= max_inode_usage_percent
        ]

        if over_threshold_mounts:
            return self.fail(
                'I-Node 사용률 임계치 초과',
                message=(
                    '일부 파일시스템의 I-Node 사용률이 기준 이상입니다: '
                    + ', '.join(over_threshold_mounts) + '. '
                    f'임계치 정보: max_inode_usage_percent={max_inode_usage_percent}% '
                    '(기준 이상이면 실패). '
                    f'판단근거: 최대 I-Node 사용률은 '
                    f'{max_inode_entry["mount_point"]}={max_inode_entry["inode_usage_percent"]}%이고, '
                    f'임계치 초과/도달 항목={", ".join(over_threshold_mounts)}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filesystem_count': len(parsed),
                'max_inode_usage_percent': max_inode_entry['inode_usage_percent'],
                'max_inode_usage_filesystem': max_inode_entry['filesystem'],
                'max_inode_usage_mount_point': max_inode_entry['mount_point'],
                'checked_filesystems': parsed,
                'skipped_entries': skipped_entries,
                'over_threshold_mounts': over_threshold_mounts,
            },
            thresholds={
                'max_inode_usage_percent': max_inode_usage_percent,
            },
            reasons=(
                f'최대 I-Node 사용률 {max_inode_entry["inode_usage_percent"]}%가 '
                f'임계치 {max_inode_usage_percent}% 미만입니다.'
            ),
            message=(
                'df -i 기준 I-Node 사용률 점검이 정상 수행되었습니다. '
                f'임계치 정보: max_inode_usage_percent={max_inode_usage_percent}% '
                '(기준 이상이면 실패). '
                f'판단근거: 최대 I-Node 사용률은 '
                f'{max_inode_entry["mount_point"]}={max_inode_entry["inode_usage_percent"]}%이고, '
                f'점검 파일시스템 수는 {len(parsed)}개입니다.'
            ),
        )


CHECK_CLASS = Check
