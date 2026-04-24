# -*- coding: utf-8 -*-
# Rocky/Linux UI starter template
# 1. SAMPLE_COMMAND를 점검 목적에 맞게 먼저 수정한다.
# 2. run() 안에서는 self._ssh(...)로 명령을 실행한다.
# 3. 마지막에는 self.ok(...) 또는 self.fail(...) 중 하나를 반환한다.

from .common._base import BaseCheck


# Step 1. 가장 먼저 이 명령을 바꾼다.
SAMPLE_COMMAND = 'hostname && whoami'


class Check(BaseCheck):
    # Step 2. Rocky/Linux 기본 연결 방식은 ssh다.
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        # Step 3. threshold가 필요하면 아래 패턴을 주석 해제해서 사용한다.
        # max_usage_percent = self.get_threshold_var(
        #     'max_usage_percent',
        #     default=80,
        #     value_type='int',
        # )

        # Step 4. 명령 실행
        rc, out, err = self._ssh(SAMPLE_COMMAND)

        # Step 5-a. 연결 자체가 실패했는지 먼저 확인한다.
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        # Step 5-b. 연결은 되었지만 명령 실행이 실패한 경우다.
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='예시 명령 실행에 실패했습니다. SAMPLE_COMMAND를 점검 환경에 맞게 수정하세요.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        # Step 5-c. stdout을 사람이 쓰기 좋은 metrics 형태로 정리한다.
        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '출력 파싱 실패',
                message='예시 출력에서 hostname과 로그인 사용자를 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = lines[0]
        login_user = lines[-1]

        # Step 6. 정상 결과는 metrics / thresholds / reasons / message를 채워 반환한다.
        return self.ok(
            metrics={
                'hostname': hostname,
                'login_user': login_user,
            },
            thresholds={},
            reasons='SSH starter template이 기본 명령 실행과 출력 파싱 흐름을 보여줍니다.',
            message=(
                'Rocky/Linux starter 예시입니다. '
                f'hostname={hostname}, login_user={login_user}'
            ),
        )


CHECK_CLASS = Check
