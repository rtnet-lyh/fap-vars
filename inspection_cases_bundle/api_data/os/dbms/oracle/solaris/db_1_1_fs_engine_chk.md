# type_name

일상점검

# area_name

상태점검

# category_name

dbms

# application_type

oracle

# application

solaris

# inspection_code

DBMS-ORACLE-SOLARIS-REPLAY-001

# is_required

필수

# inspection_name

DB엔진 파일시스템

# inspection_content

DB 엔진이 설치된 파일시스템의 물리적인 저장 공간 사용률 점검(Full 시 서비스 불가)

# inspection_command

```bash
df -k $ORACLE_HOME
```

# inspection_output

```text

```

# description

- %Use : 파일 시스템의 사용률 확인

- **양호**: (Used/Total)*100 값이 `max_used_percent`를 초과하지 않는 상태
- **경고**: (Used/Total)*100 값이 `max_used_percent`를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "max_used_percent", value: "80", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck


DF_COMMAND = 'df -k $ORACLE_HOME'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ORACLE_ACCOUNT = 'oratips'
    DEFAULT_MAX_USED_PERCENT = 80
    COMMAND_TIMEOUT = 10

    def _parse_row(self, filesystem, parts):
        if len(parts) < 5:
            return None

        try:
            total_kb = int(parts[0])
            used_kb = int(parts[1])
            available_kb = int(parts[2])
            used_percent = int(parts[3].rstrip('%'))
        except ValueError:
            return None

        if not re.match(r'^\d+%$', parts[3]):
            return None

        mounted_on = ' '.join(parts[4:]).strip()
        if not mounted_on:
            return None

        return {
            'filesystem': filesystem,
            'total_kb': total_kb,
            'used_kb': used_kb,
            'available_kb': available_kb,
            'used_percent': used_percent,
            'mounted_on': mounted_on,
        }

    def _parse_df(self, stdout):
        lines = [line.rstrip() for line in str(stdout or '').splitlines() if line.strip()]
        header_index = None
        for index, line in enumerate(lines):
            lowered = [part.lower() for part in re.split(r'\s+', line.strip())]
            if 'filesystem' in lowered and 'capacity' in lowered and 'mounted' in lowered:
                header_index = index
                break

        if header_index is None:
            return {
                'header_found': False,
                'row': None,
            }

        pending_filesystem = None
        for line in lines[header_index + 1:]:
            parts = re.split(r'\s+', line.strip())

            if pending_filesystem:
                row = self._parse_row(pending_filesystem, parts)
                if row:
                    return {
                        'header_found': True,
                        'row': row,
                    }
                pending_filesystem = None

            if len(parts) >= 6:
                row = self._parse_row(parts[0], parts[1:])
                if row:
                    return {
                        'header_found': True,
                        'row': row,
                    }

            if len(parts) == 1 and not parts[0].startswith(('#', '$')):
                pending_filesystem = parts[0]

        return {
            'header_found': True,
            'row': None,
        }

    def run(self):
        oracle_account = str(
            self.get_threshold_var(
                'oracle_account',
                default=self.DEFAULT_ORACLE_ACCOUNT,
                value_type='str',
            ) or ''
        ).strip() or self.DEFAULT_ORACLE_ACCOUNT
        max_used_percent = self.get_threshold_var(
            'max_used_percent',
            default=self.DEFAULT_MAX_USED_PERCENT,
            value_type='int',
        )

        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': DF_COMMAND, 'timeout': self.COMMAND_TIMEOUT}],
            )[0]
        except ValueError as exc:
            return self.fail(
                'Oracle 계정 전환 설정 오류',
                message=str(exc),
            )

        rc = result.get('rc')
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        switch_verification = getattr(self, '_solaris_last_account_switch_verification', {}) or {}

        if self._is_connection_error(rc, stderr):
            return self.fail(
                '호스트 연결 실패',
                message=(stderr or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                stderr=stderr,
            )

        if not switch_verification.get('ok'):
            return self.fail(
                'Oracle 계정 전환 실패',
                message=switch_verification.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.',
                stdout=(switch_verification.get('stdout') or '').strip(),
                stderr=stderr,
            )

        if rc != 0:
            return self.fail(
                'df 명령 실행 실패',
                message='Oracle DB 엔진 파일시스템 사용률을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        parsed = self._parse_df(stdout)
        if not parsed['header_found']:
            return self.fail(
                'df 출력 헤더 파싱 실패',
                message='df -k 출력에서 Filesystem/Capacity/Mounted 헤더를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        row = parsed['row']
        if not row:
            return self.fail(
                'df 출력 행 파싱 실패',
                message='df -k 출력에서 Oracle Home 파일시스템 사용률 행을 해석하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch_verification.get('actual_user') or '',
            'filesystem': row['filesystem'],
            'total_kb': row['total_kb'],
            'used_kb': row['used_kb'],
            'available_kb': row['available_kb'],
            'used_percent': row['used_percent'],
            'mounted_on': row['mounted_on'],
        }
        thresholds = {
            'oracle_account': oracle_account,
            'max_used_percent': max_used_percent,
        }

        if row['used_percent'] > max_used_percent:
            return self.fail(
                'DB 엔진 파일시스템 사용률 임계치 초과',
                metrics=metrics,
                thresholds=thresholds,
                reasons='파일시스템 사용률 %s%%가 기준 %s%%를 초과했습니다.' % (
                    row['used_percent'],
                    max_used_percent,
                ),
                message='DB 엔진 파일시스템 사용률 초과: %s 사용률 %s%%, 기준 %s%%' % (
                    DF_COMMAND,
                    row['used_percent'],
                    max_used_percent,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='파일시스템 사용률이 기준 이하입니다.',
            message='DB 엔진 파일시스템 사용률 정상: %s 사용률 %s%%, 기준 %s%%' % (
                DF_COMMAND,
                row['used_percent'],
                max_used_percent,
            ),
        )


CHECK_CLASS = Check
