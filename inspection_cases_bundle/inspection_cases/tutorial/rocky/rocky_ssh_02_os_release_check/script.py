# -*- coding: utf-8 -*-

from .common._base import BaseCheck


OS_RELEASE_COMMAND = 'cat /etc/os-release'


def _parse_os_release(text):
    parsed = {}
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line or '=' not in line:
            continue
        key, value = line.split('=', 1)
        parsed[key.strip()] = value.strip().strip('"')
    return parsed


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(OS_RELEASE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='cat /etc/os-release 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = _parse_os_release(out)
        distro_name = parsed.get('NAME', '')
        distro_id = parsed.get('ID', '')
        version_id = parsed.get('VERSION_ID', '')
        pretty_name = parsed.get('PRETTY_NAME', '')

        if not distro_name or not distro_id:
            return self.fail(
                '출력 파싱 실패',
                message='/etc/os-release 결과에서 NAME 또는 ID를 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'name': distro_name,
                'id': distro_id,
                'version_id': version_id,
                'pretty_name': pretty_name,
                'line_count': len([line for line in (out or '').splitlines() if line.strip()]),
            },
            thresholds={},
            reasons='/etc/os-release 핵심 필드를 정상 파싱했습니다.',
            message=f'OS 정보 예제가 정상 수행되었습니다. name={distro_name}, version_id={version_id or "unknown"}',
        )


CHECK_CLASS = Check
