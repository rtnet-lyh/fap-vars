# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


MDADM_COMMAND = 'cat /proc/mdstat; echo "-----"; for md in /dev/md*; do [ -e "$md" ] && mdadm --detail "$md"; done; true'
ABNORMAL_STATE_MARKERS = ('degraded', 'recover', 'resync', 'failed', 'inactive', 'removed')
BECOME_USER_MARKER = '__BECOME_USER__:'


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
            return MDADM_COMMAND

        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method in ('su', 'su -'):
            become_script = "current_user=$(whoami); echo {marker}${{current_user}}; {command}".format(
                marker=BECOME_USER_MARKER,
                command=MDADM_COMMAND,
            )
            return "bash -lc " + shlex.quote(
                "printf '%s\\n' {password} | su - {user} -c {command}".format(
                    password=shlex.quote(become_password),
                    user=shlex.quote(become_user),
                    command=shlex.quote("bash -lc " + shlex.quote(become_script)),
                )
            )

        raise ValueError(f'unsupported become_method: {become_method}')

    def _parse_int_field(self, text, field_name):
        match = re.search(r'^\s*' + re.escape(field_name) + r'\s*:\s*(\d+)\s*$', text, re.MULTILINE)
        if not match:
            return None
        return int(match.group(1))

    def _parse_detail_blocks(self, detail_text):
        blocks = []
        current_name = None
        current_lines = []

        for raw_line in (detail_text or '').splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith('/dev/md') and stripped.endswith(':'):
                if current_name:
                    blocks.append((current_name, '\n'.join(current_lines).strip()))
                current_name = stripped[:-1]
                current_lines = []
                continue

            if current_name:
                current_lines.append(line)

        if current_name:
            blocks.append((current_name, '\n'.join(current_lines).strip()))

        return blocks

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

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='mdadm 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = (out or '').splitlines()
        actual_become_user = ''
        output_lines = lines

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

            output_lines = [line for line in lines if not line.strip().startswith(BECOME_USER_MARKER)]

        output = '\n'.join(output_lines).strip()
        if not output:
            return self.fail(
                'RAID 정보 없음',
                message='mdadm 상태 점검 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        if '-----' not in output:
            return self.fail(
                'RAID 정보 파싱 실패',
                message='출력에서 mdstat/detail 구분자를 찾지 못했습니다.',
                stdout=output,
                stderr=(err or '').strip(),
            )

        mdstat_text, detail_text = output.split('-----', 1)
        mdstat_text = mdstat_text.strip()
        detail_text = detail_text.strip()

        mdstat_matches = re.findall(r'^(md\d+)\s*:\s*(.+)$', mdstat_text, re.MULTILINE)
        mdstat_map = {name: line.strip() for name, line in mdstat_matches}
        detail_blocks = self._parse_detail_blocks(detail_text)

        if not mdstat_map and not detail_blocks:
            return self.fail(
                'mdadm 소프트웨어 RAID 미구성',
                message='mdadm 소프트웨어 RAID가 구성되어 있지 않습니다.',
                stdout=output,
                stderr=(err or '').strip(),
            )

        if not detail_blocks:
            return self.fail(
                'RAID 상세 정보 없음',
                message='mdadm --detail 결과를 찾지 못했습니다.',
                stdout=output,
                stderr=(err or '').strip(),
            )

        array_summaries = []
        failed_arrays = []

        for device_name, block_text in detail_blocks:
            array_name = device_name.rsplit('/', 1)[-1]
            mdstat_line = mdstat_map.get(array_name, '')
            if not mdstat_line:
                failed_arrays.append(f'{device_name}(mdstat 미일치)')
                continue

            state_text = ''
            state_match = re.search(r'^\s*State\s*:\s*(.+)$', block_text, re.MULTILINE)
            if state_match:
                state_text = state_match.group(1).strip()

            raid_level_match = re.search(r'^\s*Raid Level\s*:\s*(.+)$', block_text, re.MULTILINE)
            raid_level = raid_level_match.group(1).strip() if raid_level_match else ''

            raid_devices = self._parse_int_field(block_text, 'Raid Devices')
            active_devices = self._parse_int_field(block_text, 'Active Devices')
            failed_devices = self._parse_int_field(block_text, 'Failed Devices')
            working_devices = self._parse_int_field(block_text, 'Working Devices')

            summary = {
                'device_name': device_name,
                'array_name': array_name,
                'raid_level': raid_level,
                'mdstat_status': mdstat_line,
                'state': state_text,
                'raid_devices': raid_devices,
                'active_devices': active_devices,
                'working_devices': working_devices,
                'failed_devices': failed_devices,
            }
            array_summaries.append(summary)

            normalized_state = state_text.lower()
            has_abnormal_state = any(marker in normalized_state for marker in ABNORMAL_STATE_MARKERS)
            is_active_mdstat = mdstat_line.startswith('active ')
            has_degraded_marker = 'degraded' in mdstat_line.lower() or '_' in mdstat_line
            has_device_mismatch = (
                raid_devices is None or active_devices is None or failed_devices is None or raid_devices != active_devices
            )
            has_failed_device = failed_devices is None or failed_devices > 0

            if not is_active_mdstat or has_degraded_marker or has_abnormal_state or has_device_mismatch or has_failed_device:
                failed_arrays.append(device_name)

        if failed_arrays:
            return self.fail(
                'RAID 이중화 상태 비정상',
                message='일부 RAID 배열 상태가 비정상입니다: ' + ', '.join(failed_arrays),
                stdout=output,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'become_user': actual_become_user,
                'raid_array_count': len(array_summaries),
                'raid_arrays': array_summaries,
            },
            thresholds={},
            reasons='모든 mdadm RAID 배열이 active/clean 상태이며 실패 디스크가 없습니다.',
            message='mdadm 기준 디스크 이중화 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
