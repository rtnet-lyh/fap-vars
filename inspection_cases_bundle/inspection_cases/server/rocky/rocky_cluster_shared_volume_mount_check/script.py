# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


DEFAULT_SHARED_VOLUME_MOUNT_PATHS = '/mnt/shared'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_paths(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _build_findmnt_command(self, mount_path):
        return 'findmnt ' + shlex.quote(mount_path)

    def _parse_options(self, raw_options):
        return [
            option.strip()
            for option in str(raw_options or '').split(',')
            if option.strip()
        ]

    def _parse_findmnt_output(self, mount_path, stdout):
        lines = [
            line.rstrip()
            for line in (stdout or '').splitlines()
            if line.strip()
        ]
        data_lines = [
            line
            for line in lines
            if not line.lstrip().upper().startswith('TARGET ')
        ]

        for line in data_lines:
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue

            target, source, filesystem_type, raw_options = parts
            if target != mount_path:
                continue

            options = self._parse_options(raw_options)
            if 'ro' in options:
                access_mode = 'ro'
            elif 'rw' in options:
                access_mode = 'rw'
            else:
                access_mode = 'unknown'

            return {
                'target': target,
                'source': source,
                'mount_path': mount_path,
                'filesystem_type': filesystem_type,
                'options': options,
                'access_mode': access_mode,
                'line': line,
                'raw_lines': lines,
            }

        return {
            'target': '',
            'source': '',
            'mount_path': mount_path,
            'filesystem_type': '',
            'options': [],
            'access_mode': 'unknown',
            'line': '',
            'raw_lines': lines,
        }

    def _build_metrics(self, path_results):
        return {
            'target_mount_count': len(path_results),
            'mounted_count': sum(1 for item in path_results if item.get('mount_found')),
            'rw_mount_count': sum(1 for item in path_results if item.get('access_mode') == 'rw'),
            'ro_mount_count': sum(1 for item in path_results if item.get('access_mode') == 'ro'),
            'missing_mount_count': sum(1 for item in path_results if item.get('status') == 'missing'),
            'parse_error_count': sum(1 for item in path_results if item.get('status') == 'parse_error'),
            'path_results': path_results,
        }

    def _format_path_results(self, path_results):
        return ', '.join(
            f"{item.get('mount_path')}={item.get('status')}"
            for item in path_results
        )

    def run(self):
        mount_paths = self._split_paths(
            self.get_threshold_var(
                'shared_volume_mount_paths',
                default=DEFAULT_SHARED_VOLUME_MOUNT_PATHS,
                value_type='str',
            )
        )
        if not mount_paths:
            return self.fail(
                '임계치 미정의',
                message='shared_volume_mount_paths 가 정의되어 있지 않습니다.',
            )

        path_results = []
        thresholds = {
            'shared_volume_mount_paths': '|'.join(mount_paths),
        }

        for mount_path in mount_paths:
            command = self._build_findmnt_command(mount_path)
            rc, out, err = self._ssh(command)

            if self._is_connection_error(rc, err):
                return self.fail(
                    '호스트 연결 실패',
                    message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                    stderr=(err or '').strip(),
                )

            if rc not in (0, 1):
                return self.fail(
                    '점검 명령 실행 실패',
                    message='공유 볼륨 findmnt 상태 점검 명령 실행에 실패했습니다.',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            parsed = self._parse_findmnt_output(mount_path, out)
            parsed['command'] = command
            parsed['rc'] = rc
            parsed['mount_found'] = rc == 0 and bool(parsed.get('line'))

            if not parsed['mount_found']:
                parsed['status'] = 'missing'
            elif parsed['access_mode'] == 'ro':
                parsed['status'] = 'read_only'
            elif parsed['access_mode'] == 'rw':
                parsed['status'] = 'ok'
            else:
                parsed['status'] = 'parse_error'

            path_results.append(parsed)

        metrics = self._build_metrics(path_results)
        threshold_summary = 'shared_volume_mount_paths=' + thresholds['shared_volume_mount_paths']
        failures = [
            item
            for item in path_results
            if item.get('status') != 'ok'
        ]

        if failures:
            result = self.fail(
                '공유 볼륨 마운트 상태 비정상',
                message=(
                    '공유 볼륨 마운트 상태가 기준에 맞지 않습니다. '
                    '경로별 상태: ' + self._format_path_results(path_results) +
                    '. 임계치: ' + threshold_summary
                ),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = (
                'findmnt 결과에서 마운트 경로가 없거나, ro 옵션으로 마운트되었거나, rw/ro 옵션 판별에 실패한 경로가 있습니다. '
                '경로별 상태: ' + self._format_path_results(path_results)
            )
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='모든 공유 볼륨이 rw 옵션으로 마운트되어 있습니다. 경로별 상태: ' + self._format_path_results(path_results),
            message=(
                '공유 볼륨 상태 점검이 정상 수행되었습니다. '
                '모든 대상 경로가 findmnt 결과에서 rw 옵션으로 확인되었습니다. '
                '임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
