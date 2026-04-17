# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


BASE_COMMAND = 'dmidecode -t memory'
BECOME_USER_MARKER = '__BECOME_USER__:'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _recognition_thresholds(self):
        return {
            'min_recognized_memory_device_count': 1,
            'min_recognized_total_memory_gb': '>0',
        }

    def _recognition_threshold_summary(self):
        return 'min_recognized_memory_device_count=1, min_recognized_total_memory_gb>0'

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
            return BASE_COMMAND

        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method in ('su', 'su -'):
            become_script = "current_user=$(whoami); echo {marker}${{current_user}}; exec {command}".format(
                marker=shlex.quote(BECOME_USER_MARKER),
                command=BASE_COMMAND,
            )
            return "bash -lc " + shlex.quote(
                "printf '%s\\n' {password} | su - {user} -c {command}".format(
                    password=shlex.quote(become_password),
                    user=shlex.quote(become_user),
                    command=shlex.quote("bash -lc " + shlex.quote(become_script)),
                )
            )

        raise ValueError(f'unsupported become_method: {become_method}')

    def _parse_size_gb(self, size_text):
        text = str(size_text or '').strip()
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*(kB|MB|GB|TB)$', text, re.IGNORECASE)
        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'KB':
            return value / (1024.0 * 1024.0)
        if unit == 'MB':
            return value / 1024.0
        if unit == 'GB':
            return value
        if unit == 'TB':
            return value * 1024.0
        return None

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
                message='dmidecode -t memory 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = (out or '').splitlines()
        if not lines:
            return self.fail(
                '메모리 정보 없음',
                message='dmidecode -t memory 결과가 비어 있습니다.',
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

        ecc_type = ''
        installed_devices = []
        unparsed_devices = []
        current_device = None

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()

            if stripped == 'Physical Memory Array':
                current_device = None
                continue

            if stripped.startswith('Error Correction Type:') and not ecc_type:
                ecc_type = stripped.split(':', 1)[1].strip()
                continue

            if stripped == 'Memory Device':
                if current_device:
                    installed_devices.append(current_device)
                current_device = {}
                continue

            if current_device is None:
                continue

            if stripped.startswith('Size:'):
                size_text = stripped.split(':', 1)[1].strip()
                current_device['size_text'] = size_text
                continue

            if stripped.startswith('Locator:'):
                current_device['locator'] = stripped.split(':', 1)[1].strip()
                continue

            if stripped.startswith('Bank Locator:'):
                current_device['bank_locator'] = stripped.split(':', 1)[1].strip()
                continue

            if stripped.startswith('Manufacturer:'):
                current_device['manufacturer'] = stripped.split(':', 1)[1].strip()
                continue

            if stripped.startswith('Part Number:'):
                current_device['part_number'] = stripped.split(':', 1)[1].strip()
                continue

            if stripped.startswith('Configured Memory Speed:'):
                current_device['configured_speed'] = stripped.split(':', 1)[1].strip()
                continue

        if current_device:
            installed_devices.append(current_device)

        recognized_modules = []
        total_memory_gb = 0.0

        for device in installed_devices:
            size_text = device.get('size_text', '')
            if not size_text or size_text == 'No Module Installed':
                continue

            size_gb = self._parse_size_gb(size_text)
            if size_gb is None:
                unparsed_devices.append({
                    'locator': device.get('locator', ''),
                    'size_text': size_text,
                })
                continue

            recognized_modules.append({
                'locator': device.get('locator', ''),
                'bank_locator': device.get('bank_locator', ''),
                'size_gb': round(size_gb, 2),
                'manufacturer': device.get('manufacturer', ''),
                'part_number': device.get('part_number', ''),
                'configured_speed': device.get('configured_speed', ''),
            })
            total_memory_gb += size_gb

        if unparsed_devices:
            return self.fail(
                '메모리 용량 파싱 실패',
                message=(
                    '일부 메모리 슬롯의 용량 정보를 해석할 수 없습니다. '
                    f'임계치 정보: {self._recognition_threshold_summary()}. '
                    '판단근거: 용량 파싱 실패 슬롯='
                    + ', '.join(
                        f"{device.get('locator') or 'unknown'}({device.get('size_text')})"
                        for device in unparsed_devices
                    )
                    + '.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if not recognized_modules or total_memory_gb <= 0:
            return self.fail(
                '장착 메모리 미인식',
                message=(
                    '장착된 메모리를 정상적으로 인식하지 못했습니다. '
                    f'임계치 정보: {self._recognition_threshold_summary()}. '
                    f'판단근거: recognized_memory_device_count={len(recognized_modules)}, '
                    f'recognized_total_memory_gb={round(total_memory_gb, 2)}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'become_user': actual_become_user,
                'recognized_memory_device_count': len(recognized_modules),
                'recognized_total_memory_gb': round(total_memory_gb, 2),
                'recognized_modules': recognized_modules,
                'error_correction_type': ecc_type,
            },
            thresholds=self._recognition_thresholds(),
            reasons=(
                f'장착 메모리 {len(recognized_modules)}개와 '
                f'총 용량 {round(total_memory_gb, 2)}GB가 인식되었습니다.'
            ),
            message=(
                'dmidecode 기준 메모리 인식 점검이 정상 수행되었습니다. '
                f'임계치 정보: {self._recognition_threshold_summary()}. '
                f'판단근거: recognized_memory_device_count={len(recognized_modules)}, '
                f'recognized_total_memory_gb={round(total_memory_gb, 2)}, '
                f'error_correction_type={ecc_type or "unknown"}.'
            ),
        )


CHECK_CLASS = Check
