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


SV-LIN-RKY-012

# is_required

권고

# inspection_name

Path 이중화 점검

# inspection_content

Multipath 이중화 정상 유무 점검(CONNECTED 등 상태 확인)

# inspection_command

```bash
multipath -ll
```

# inspection_output

```text
mpatha (36005076810810548b8000000000000aa) dm-2 IBM,2145
size=100G features='1 queue_if_no_path' hwhandler='0' wp=rw
|-+- policy='round-robin 0' prio=1 status=active
| `- 2:0:0:1 sdb 8:16 active ready running
`-+- policy='round-robin 0' prio=1 status=enabled
  `- 3:0:0:1 sdc 8:32 active ready running
```

# description

- `multipath -ll` 명령은 스토리지 장치에 대해 구성된 다중 경로(Multipath) 상태를 확인할 때 사용한다.
- 예시의 `sdb`, `sdc` 같은 장치는 실제 스토리지에 연결된 물리 경로를 나타내며, 괄호의 `8:16`, `8:32` 값은 Linux 블록 디바이스 번호다.
- `status=active`는 현재 실제 I/O를 처리하는 활성 경로 그룹을 의미하고, `status=enabled`는 대기 중이지만 장애 시 활성 경로로 전환될 수 있는 사용 가능한 경로 그룹을 의미한다.
- 각 경로 라인의 `active ready running`은 해당 경로가 인식되어 정상적으로 I/O를 처리할 수 있는 상태임을 의미한다.
- `policy='round-robin 0'`는 일반적인 경로 전환 정책 예시이며, 운영 환경에서 사용 중인 경로 정책이 일관되게 적용되어 있는지 함께 확인한다.
- `failed`, `faulty`, `offline` 같은 상태가 보이면 경로 장애 가능성이 있으므로 HBA, 케이블, SAN 스위치, 스토리지 포트 상태를 함께 점검한다.

- **양호**: `multipath -ll` 결과에서 경로 그룹 상태가 `active` 또는 `enabled`이고, 각 물리 경로가 `running` 상태로 확인되는 경우
- **경고**: `multipath -ll` 명령은 실행되지만 멀티패스 장치가 없거나, 경로 상태를 충분히 확인할 수 없어 실제 구성 여부를 추가 확인해야 하는 경우
- **실패**: `multipath -ll` 결과에 `failed`, `faulty`, `offline` 등 비정상 경로 상태가 하나 이상 확인되는 경우
- **참고**: SAN 다중 경로를 사용하지 않는 서버는 로컬 디스크 전용 구성일 수 있으므로 스토리지 연결 구조를 먼저 확인한다

# thresholds


[]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


MULTIPATH_COMMAND = 'multipath -ll'
BECOME_USER_MARKER = '__BECOME_USER__:'
ABNORMAL_MARKERS = ('failed', 'faulty', 'offline')
GROUP_STATUS_PATTERN = re.compile(r'status=(\w+)', re.IGNORECASE)
PATH_LINE_PATTERN = re.compile(r'(\d+:\d+:\d+:\d+)\s+(\S+)\s+\d+:\d+\s+(.+)$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _is_become_enabled(self):
        become_raw = self.get_application_credential_value('become', default=False)
        return str(become_raw).strip().lower() == 'true'

    def _mask_command_history(self, *secrets):
        if not self._command_history:
            return
        masked_cmd = self._command_history[-1].get('cmd', '')
        for secret in secrets:
            if secret:
                masked_cmd = masked_cmd.replace(secret, '*****')
        self._command_history[-1]['cmd'] = masked_cmd

    def _build_command(self):
        become_method = str(self.get_application_credential_value('become_method', default='') or '').strip().lower()
        become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
        become_password = str(self.get_application_credential_value('become_password', default='') or '')

        if not self._is_become_enabled():
            return MULTIPATH_COMMAND

        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method in ('su', 'su -'):
            become_script = "current_user=$(whoami); echo {marker}${{current_user}}; exec {command}".format(
                marker=shlex.quote(BECOME_USER_MARKER),
                command=MULTIPATH_COMMAND,
            )
            return "bash -lc " + shlex.quote(
                "printf '%s\\n' {password} | su - {user} -c {command}".format(
                    password=shlex.quote(become_password),
                    user=shlex.quote(become_user),
                    command=shlex.quote("bash -lc " + shlex.quote(become_script)),
                )
            )

        raise ValueError(f'unsupported become_method: {become_method}')

    def _is_command_not_found(self, rc, out, err):
        if rc == 127:
            return True
        command_error = self._detect_command_error(out, err)
        return bool(command_error)

    def _parse_path_line(self, line):
        match = PATH_LINE_PATTERN.search(line.strip())
        if not match:
            return None

        trailing = match.group(3).strip()
        status_tokens = trailing.split()
        lowered_tokens = [token.lower() for token in status_tokens]
        return {
            'host_channel': match.group(1),
            'device_name': match.group(2),
            'status_tokens': lowered_tokens,
            'running': 'running' in lowered_tokens,
            'abnormal_markers': [
                marker
                for marker in ABNORMAL_MARKERS
                if marker in lowered_tokens
            ],
            'line': line.strip(),
        }

    def _parse_output(self, stdout):
        lines = [
            line.rstrip()
            for line in (stdout or '').splitlines()
            if line.strip()
        ]
        group_statuses = []
        path_entries = []
        abnormal_lines = []

        for line in lines:
            lowered = line.lower()
            for status in GROUP_STATUS_PATTERN.findall(line):
                group_statuses.append(status.lower())

            path_entry = self._parse_path_line(line)
            if path_entry:
                path_entries.append(path_entry)

            if any(re.search(r'\b' + re.escape(marker) + r'\b', lowered) for marker in ABNORMAL_MARKERS):
                abnormal_lines.append(line.strip())

        return {
            'lines': lines,
            'group_statuses': group_statuses,
            'path_entries': path_entries,
            'abnormal_lines': abnormal_lines,
        }

    def run(self):
        try:
            command = self._build_command()
        except ValueError as exc:
            return self.fail(
                '권한 상승 설정 오류',
                message=str(exc),
            )

        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        rc, out, err = self._ssh(command)
        self._mask_command_history(become_password)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_command_not_found(rc, out, err):
            return self.not_applicable(
                'multipath 명령을 사용할 수 없거나 멀티패스 환경이 아니어서 Path 이중화 점검은 대상미해당입니다.',
                raw_output=((out or '').strip() or (err or '').strip()),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='multipath -ll 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = (out or '').splitlines()
        if not lines:
            return self.fail(
                'Multipath 정보 없음',
                message='multipath -ll 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        actual_become_user = ''
        if self._is_become_enabled():
            become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
            become_marker_line = next((line.strip() for line in lines if line.strip().startswith(BECOME_USER_MARKER)), '')
            if not become_marker_line:
                return self.fail(
                    '권한 상승 사용자 확인 실패',
                    message='권한 상승 후 사용자 확인 결과를 찾지 못했습니다.',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            actual_become_user = become_marker_line.split(BECOME_USER_MARKER, 1)[1].strip()
            if actual_become_user != become_user:
                return self.fail(
                    '권한 상승 사용자 불일치',
                    message=f'권한 상승 사용자가 기대값과 다릅니다: expected={become_user}, actual={actual_become_user}',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            lines = [line for line in lines if not line.strip().startswith(BECOME_USER_MARKER)]

        parsed = self._parse_output('\n'.join(lines))
        metrics = {
            'become_user': actual_become_user,
            'multipath_device_detected': bool(parsed['group_statuses'] or parsed['path_entries']),
            'path_group_count': len(parsed['group_statuses']),
            'path_entry_count': len(parsed['path_entries']),
            'running_path_count': sum(1 for entry in parsed['path_entries'] if entry.get('running')),
            'abnormal_path_count': len(parsed['abnormal_lines']),
            'group_statuses': parsed['group_statuses'],
            'path_entries': parsed['path_entries'],
            'abnormal_lines': parsed['abnormal_lines'],
        }

        if not metrics['multipath_device_detected']:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='multipath -ll 결과에서 멀티패스 장치 또는 경로 상태를 확인하지 못했습니다.',
                message='Path 이중화 구성이 없거나 상태 확인이 충분하지 않습니다.',
            )

        if parsed['abnormal_lines']:
            result = self.fail(
                'Multipath 경로 상태 비정상',
                message='multipath 경로 상태에 failed/faulty/offline 항목이 확인되었습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = '비정상 경로 상태가 검출되었습니다: ' + '; '.join(parsed['abnormal_lines'])
            return result

        if not all(status in ('active', 'enabled') for status in parsed['group_statuses']) or not all(
            entry.get('running') for entry in parsed['path_entries']
        ):
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='경로 그룹 또는 물리 경로 상태를 추가 확인해야 합니다.',
                message='Path 이중화 상태 추가 확인 필요',
            )

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='모든 경로 그룹이 active/enabled 상태이고 물리 경로가 running 상태입니다.',
            message='Path 이중화 점검 정상',
        )


CHECK_CLASS = Check
