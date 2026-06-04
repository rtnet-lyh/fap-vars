# -*- coding: utf-8 -*-
# 다양한 예시는 아래의 경로에서 확인하실수 있습니다.
# 입문자: /fap/ansible/scripts/inspection/inspection_cases/tutorial
# 경험자: /fap/ansible/scripts/inspection/inspection_cases/{os}/{item}/script.py
    # 경험자 경로에있는 점검 스크립트는 아래 경로에 작성된 문서를 기반으로 작성되었습니다.
    # 문서 경로: /fap/ansible/scripts/inspection/raw_data/

# 점검 스크립트 유지보수 및 확장 시 사용 되는 runner, helper, base 경로 입니다.
# runner 경로: /fap/ansible/scripts/inspection/runner.py
# helper 경로: /fap/ansible/scripts/inspection/items/common/helpers/    
# base 경로: /fap/ansible/scripts/inspection/items/common/
# 점검 로그 경로: /fap/logs/ansible/{yyyymmdd}/job-{job_id}_exec-{execution_id}_host-{host_ip}.log

# 점검 시 호출되는 플레이북 경로 입니다.
# 플레이북 경로: /fap/ansible/projects/VARS/playbooks

# 점검항목별로 CLI를 기반으로 테스트하기위한 프로그램 경로 입니다.
# 테스트 프로그램 경로: /fap/ansible/scripts/inspection/replay_cli.py
# 테스트 프로그램 사용가이드 경로: /fap/ansible/scripts/inspection/REPLAY_CLI_GUIDE.md

"""BaseCheck 기반 기본 점검 샘플.

- `_` 접두 파일이라 러너가 로드하지 않는다.
- 실제 점검 파일은 `BaseCheck`만 상속한다.
- 공통 기능은 `BaseCheck` 래퍼나 helper를 사용한다.
"""

from ._base import BaseCheck


class Check(BaseCheck):
    """기본 점검 샘플 클래스.

    가장 단순한 점검 흐름 예시.
    """

    USE_HOST_CONNECTION = True

    def run(self):
        # 임계치 조회
        threshold = self.get_threshold_var('sample_threshold', default=1)

        # 원격 명령 실행
        rc, out, err = self._ssh('echo sample-check')

        # 연결 실패 우선 처리
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or '호스트 연결에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        # 명령 실패 처리
        if rc != 0:
            return self.fail(
                '명령 실행 실패',
                message='샘플 명령 실행에 실패했습니다.',
                stderr=(err or '').strip(),
            )

        # 성공 결과 반환
        return self.ok(
            metrics={
                'sample_threshold': threshold,
                'command_output': (out or '').strip(),
            },
            raw_output=(out or '').strip(),
        )


CHECK_CLASS = Check
