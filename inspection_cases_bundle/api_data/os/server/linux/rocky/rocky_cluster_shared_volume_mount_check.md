# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-CLUSTER-SHARED-VOLUME-01

# is_required

권고

# inspection_name

공유 볼륨 상태 점검

# inspection_content

공유 볼륨 Read/Write 상태 및 마운트 정상 유무 점검(File System State On, HSM Server Not Responding)

# inspection_command

```bash
findmnt <마운트경로>
```

# inspection_output

```text
TARGET         SOURCE FSTYPE OPTIONS
/run/user/1000 tmpfs  tmpfs  rw,nosuid,nodev,relatime,seclabel,size=1572692k,nr_inodes=393173,mode=700,uid=1000,gid=1000,inode64
```

# description

- 본 항목은 클러스터 공유 볼륨이 지정된 마운트 경로에 정상 마운트되어 있고, 파일시스템이 읽기/쓰기 가능한 `rw` 옵션으로 동작하는지 확인한다.
- `findmnt <마운트경로>` 결과가 출력되면 해당 경로에 파일시스템이 마운트된 상태로 본다. 출력이 없으면 공유 볼륨이 마운트되지 않았거나 마운트 경로 임계치가 실제 경로와 다를 수 있으므로 클러스터 리소스 상태와 `/etc/fstab`, systemd mount unit, 스토리지 경로를 함께 확인한다.
- `findmnt` 출력의 `OPTIONS` 컬럼에 `rw`가 포함되어 있으면 읽기/쓰기 상태로 판단한다. `ro`가 포함되어 있으면 파일시스템 오류, 스토리지 경로 장애, 클러스터 보호 동작 등으로 읽기 전용 전환된 상태일 수 있으므로 즉시 원인 확인이 필요하다.
- `File System State On` 상태는 공유 파일시스템이 클러스터 리소스 관점에서 활성 상태임을 의미한다. 반대로 `HSM Server Not Responding` 같은 응답 불가 메시지가 함께 확인되면 공유 볼륨 접근성, 클러스터 서비스, 스토리지 연결 상태를 점검한다.
- 여러 공유 볼륨을 점검할 경우 임계치에 마운트 경로를 `|`로 구분하여 등록하고, 각 경로별 `findmnt <마운트경로>` 결과의 존재 여부와 `OPTIONS` 컬럼의 `rw`/`ro` 옵션을 확인한다.

- **성공**: 점검 대상 마운트 경로가 `findmnt` 결과에 존재하고, `OPTIONS` 컬럼에 `rw`가 포함되어 있는 경우
- **실패**: 점검 대상 마운트 경로가 `ro` 옵션으로 마운트되어 있는 경우
- **실패**: 점검 대상 마운트 경로가 `mount` 결과에 없거나, 출력은 있으나 `rw`/`ro` 옵션을 판별할 수 없는 경우
- **참고**: `shared_volume_mount_paths`는 기본값 `/mnt/shared`를 사용하며, 여러 경로는 `/mnt/shared|/mnt/share2`처럼 `|`로 구분한다.

# thresholds

[
    {id: null, key: "shared_volume_mount_paths", value: "/run/user/1000", sortOrder: 0}
]

# inspection_script

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
