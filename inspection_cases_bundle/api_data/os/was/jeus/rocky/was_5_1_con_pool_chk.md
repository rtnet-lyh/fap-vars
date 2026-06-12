# type_name

일상점검

# area_name

상태점검

# category_name

was

# application_type

jeus

# application

rocky

# inspection_code

WAS-JEUS-ROCKY-REPLAY-013

# is_required

필수

# inspection_name

DB연결 객체저장공간 설정값 초과 여부 점검

# inspection_content

DB에 연결된 객체 저장공간인 DB Connection Pool 확인(기 설정된 Max 값과 현재 사용량을 체크하여 임계치 조정 등의 활동을 위한 점검)

# inspection_command

```bash

```

# inspection_output

```text
2024-09-12 10:15:23,123 ERROR [JDBC] Connection pool exhausted for datasource 'myPool'. Maximum connections reached (30).
2024-09-12 10:17:45,456 ERROR [JDBC] Connection pool exhausted for datasource 'myPool'. Maximum connections reached (30).
```

# description

- Error Message: "Connection pool exhausted" 메시지가 자주 발생하면, Max Connections 설정이 부족할 수 있으며, 이 값을 늘리거나 연결 관리 방식을 최적화하는 것이 필요. 
※ 기 설정된 환경 값과 현재 사용량은 명령어를 통해서 알 수 없음.

- **양호**: "Connection pool exhausted" 메시지 개수가 `max_message_count`를 넘지 않은 상태
- **경고**: "Connection pool exhausted" 메시지 개수가 `max_message_count`를 넘지 않은 상태(Max Connections 설정 확인 필요)
- **확인 필요**: 출력 및 jdbc.log 파일이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "max_message_count: 최대 \"Connection pool exhausted\" 메시지 개수", value: "", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck

COMMAND = 'grep -i "{search_keyword}" "$(ls -t {jeus_log_path}/*.log | head -1)"'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, search_keyword, jeus_log_path):    
        command = COMMAND.format(search_keyword=search_keyword, jeus_log_path=jeus_log_path)    

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()

        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        return stdout, stderr, None

    def run(self):
        search_keyword = self.get_threshold_var(
            key='search_keyword', 
            default='connection pool exhausted',
            value_type='str',
        )
        
        jeus_log_path = self.get_threshold_var(
            key='jeus_log_path', 
            default='/home/exTMS/tmax/jeus/log/extms1',
            value_type='str',
        )

        stdout, _stderr, error = self._run_jeus_command(search_keyword, jeus_log_path)
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        threshold = self.get_threshold_var('max_message_count', default=0, value_type='int')
        metrics = {'message_count': len(lines), 'sample_lines': lines[:20]}
        thresholds = {'max_message_count': threshold}
        if len(lines) > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{search_keyword} 메시지 수가 기준을 초과했습니다.', message='%s 메시지 경고: count=%s, 기준=%s' % (search_keyword, len(lines), threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'{search_keyword} 메시지 수가 기준 이하입니다.', message='%s 메시지 정상: count=%s, 기준=%s' % (search_keyword, len(lines), threshold))


CHECK_CLASS = Check
