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
