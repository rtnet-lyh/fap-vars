# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DF_ROOT_COMMAND = 'df -h /'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        max_root_usage_percent = self.get_threshold_var(
            'max_root_usage_percent',
            default=85,
            value_type='int',
        )
        rc, out, err = self._ssh(DF_ROOT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='df -h / 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '출력 파싱 실패',
                message='df -h / 결과를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parts = lines[1].split()
        if len(parts) < 6 or not parts[4].endswith('%'):
            return self.fail(
                '출력 파싱 실패',
                message='루트 파일시스템 사용률 칼럼을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            usage_percent = int(parts[4].rstrip('%'))
        except ValueError:
            return self.fail(
                '출력 파싱 실패',
                message='루트 파일시스템 사용률 퍼센트를 정수로 변환하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        filesystem = parts[0]
        size = parts[1]
        used = parts[2]
        available = parts[3]
        mount_point = parts[-1]

        if usage_percent >= max_root_usage_percent:
            return self.fail(
                '루트 파일시스템 사용률 임계치 초과',
                message=(
                    f'루트 파일시스템 사용률이 기준 이상입니다: '
                    f'{mount_point}={usage_percent}% (기준 {max_root_usage_percent}% 미만)'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'filesystem': filesystem,
                'size': size,
                'used': used,
                'available': available,
                'mount_point': mount_point,
                'usage_percent': usage_percent,
            },
            thresholds={
                'max_root_usage_percent': max_root_usage_percent,
            },
            reasons='루트 파일시스템 사용률이 기준 범위 내입니다.',
            message=f'df -h / 예제가 정상 수행되었습니다. {mount_point} usage={usage_percent}%',
        )


CHECK_CLASS = Check
