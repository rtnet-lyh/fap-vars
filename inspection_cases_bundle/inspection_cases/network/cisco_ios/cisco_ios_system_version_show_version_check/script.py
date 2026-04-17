# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh("show version")

        if self._is_connection_error(rc, err):
            return self.fail(
                '장비 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='show version 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if not lines:
            return self.fail(
                '장비 정보 없음',
                message='show version 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        ios_line = next((line for line in lines if 'Cisco IOS Software' in line), '')
        if not ios_line:
            return self.fail(
                'Cisco IOS 식별 실패',
                message='show version 결과에서 Cisco IOS Software 문자열을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = ''
        uptime_line = next((line for line in lines if ' uptime is ' in line), '')
        if uptime_line:
            hostname = uptime_line.split(' uptime is ', 1)[0].strip()

        version_match = re.search(r'Version\s+([^,]+)', ios_line)
        ios_version = version_match.group(1).strip() if version_match else ''

        model = ''
        model_line = next((line for line in lines if line.lower().startswith('cisco ')), '')
        if model_line:
            model = model_line.split()[1]

        system_image = ''
        image_line = next((line for line in lines if line.startswith('System image file is ')), '')
        if image_line:
            system_image = image_line.split('"', 2)[1] if '"' in image_line else image_line

        return self.ok(
            metrics={
                'connection': 'ssh',
                'platform': 'cisco_ios',
                'hostname': hostname,
                'ios_version': ios_version,
                'model': model,
                'system_image': system_image,
            },
            reasons='Cisco IOS 장비 정보가 정상 확인되었습니다.',
            message='Cisco IOS show version 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
