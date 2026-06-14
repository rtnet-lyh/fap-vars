# type_name

일상점검

# area_name

dbms

# category_name

상태점검

# application_type

oracle

# application

solaris

# inspection_code

DBMS-ORACLE-SOLARIS-REPLAY-010

# is_required

필수

# inspection_name

리스너(DB 서비스 연결) 로그 파일 점검

# inspection_content

리스너를 통해 DB에 접근하는 클라이언트에 대한 로그 파일로 세션 접속(WAS와 DB간)에 문제가 있는지 점검

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- TNS-12514: TNS:listener does not currently know of service requested in connect descriptor: 요청된 서비스에 대한 정보가 리스너에 존재하지 않음을 나타내며, 로그에서 해당 메시지가 출력되면 서비스 설정을 확인해야 하고, 데이터베이스 서비스가 정상적으로 등록되어 있는지 점검한 후 필요 시 리스너를 재시작하는 것이 필요. 
- connection refused: 클라이언트가 리스너에 연결 요청을 했으나 연결이 거부되었음을 나타내며, 해당 메시지가 
출력된 경우 리스너가 실행 중인지 확인하고, 리스너가 정지된 경우에는 즉시 리스너를 시작해야 함. 
- timeout: 연결 시도 시간이 초과되었음을 나타내며, 이 메시지가 출력될 때는 연결 요청 후 일정 시간 내에 응답이 없었던 경우이므로 네트워크 상태를 점검하고 필요 시 리스너 및 클라이언트 설정을 조정해야 함. 
- TNS listener stopped: 리스너가 정지된 상태임을 나타내며, 이 메시지가 출력된 경우 리스너의 상태를 확인하고, 리스너가 중지된 경우 즉시 리스너를 시작해야 함. 
- warning: potential configuration issue detected: 구성 문제의 가능성을 나타내는 경고 메시지로, 해당 메시지를 통해 구성 파일을 검토해야 
하며, 구성 파일을 점검하고 필요한 수정 사항을 적용하는 것이 권고. 
- slow response from client: 클라이언트에서 느린 응답이 감지되었음을 나타내며, 이 메시지가 출력될 경우 클라이언트의 성능을 확인하고, 성능 문제를 해결하기 위해 네트워크 상태와 시스템 리소스를 점검해야 함. 
- delay: network latency detected: 네트워크 지연이 감지되었음을 나타내며, 이 메시지가 출력되면 네트워크의 응답 시간을 확인하고, 네트워크 지연 문제를 해결하기 위해 네트워크 구성 및 상태를 점검해야 함.

# thresholds

[
    {id: null, key: "oracle_account", value: "oracle", sortOrder: 0}
,
{id: null, key: "lsnr_log_dir", value: "/TTIPS_GRID/oracle/grid/gridbase/diag/tnslsnr/exTMStotalDB1/listener/trace", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import shlex
import re

from .common._base import BaseCheck


# LSNR_PATTERN = 'connection refused|timeout|TNS listener stopped|warning|slow|delay|TNS-12514|TNS-12541|TNS-12170'
LSNR_PATTERN = 'TNS-|ORA-|WARNING|FATAL|REFUSED|FAILED'
FIND_LISTENER_COMMAND = "find /TTIPS_GRID /TTIPS_HOME /oracle/app/oracle/diag/tnslsnr/citsdb1/listener/trace -type f -name 'listener.log' 2>/dev/null | xargs ls -t | head -1"

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')

        # log 경로를 찾기위한 쿼리 실행
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': FIND_LISTENER_COMMAND, 'timeout': 20}],
            )[0]
        except ValueError as exc:
            return self.fail('Oracle 계정 전환 설정 오류', message=str(exc))

        switch = getattr(self, '_solaris_last_account_switch_verification', {}) or {}
        if not switch.get('ok'):
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=switch.get('stderr'))

        stdout = result.get('stdout', '').splitlines()[-1]
        match = re.search(r"(/[\w./-]+)", stdout)
        listener_log = match.group(1) if match else False
        if not listener_log:
            return self.fail('listener_log 검색 실패', message='listener_log 검색 실패')        
        
        # command = f'egrep -i "{LSNR_PATTERN}" {listener_log} | tail -200'
        command = f'tail -2000 {listener_log} | egrep -i "{LSNR_PATTERN}"'

        result = self._run_paramiko_commands(                
            [{'command': command, 'timeout': 20}],
            become=True
        )[0]
        
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()        
        
        if result.get('rc') not in (0, 1):
            return self.fail('리스너 로그 grep 실행 실패', message='리스너 로그 파일 검색 명령을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'matched_log_count': len(lines),
            'matched_logs': lines,
        }
        thresholds = {'oracle_account': oracle_account}
        if lines:
            return self.fail(
                '리스너 로그 이상 감지',
                metrics=metrics,
                thresholds=thresholds,
                message='리스너 로그에서 접속 이상 패턴 %s건이 확인되었습니다.' % len(lines),
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='리스너 로그에서 접속 이상 패턴이 검출되지 않았습니다.',
            message='리스너 로그 파일 점검 정상',
        )


CHECK_CLASS = Check
