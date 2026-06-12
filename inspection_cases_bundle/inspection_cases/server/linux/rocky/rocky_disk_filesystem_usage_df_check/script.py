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
