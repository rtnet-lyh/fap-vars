# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

jeus

# application

rocky

# inspection_code

WAS-JEUS-ROCKY-REPLAY-014

# is_required

필수

# inspection_name

DB연결 상태 점검

# inspection_content

DB에 연결된 객체 저장공간인 DB Connection Pool 확인(각 컨테이너별 Enable상태 확인)

# inspection_command

```bash

```

# inspection_output

```text
2024-09-12 10:00:23,123 ERROR [JDBC] Connection timeout: Unable to get a connection from the poolager 3000ms.
2024-09-12 10:05:12,789 WARN [JDBC] Connection closed by database due to inactivity.
2024-09-12 10:22:45,456 INFO [JDBC] Connection established to database.
```

# description

- Connection Timeout: 커넥션 풀에서 설정된 시간 안에 DB 연결을 가져오지 못하면 Connection Timeout 오류가 발생하므로, 커넥션 풀 크기를 늘리거나 데이터베이스 성능을 최적화해 문제를 해결하는 것이 필요. 
- Connection Closed by Database: 비활성 연결이 자주 끊어지는 경우, 데이터베이스나 커넥션 풀 설정에서 idle timeout을 적절히 조정해 비활성 시간을 줄이는 것이 권고.
- Connection Established: 데이터베이스에 성공적으로 연결된 경우 추가적인 조치가 필요하지 않으나, 연결 시간이 과도하게 길어지면 데이터베이스 성능을 점검 필요.
※ 로그 파일을 통해서 DB 커넥션 풀에 대한 로그를 확인함으로써 DB연결 상태를 점검할 수 있으며, 각 컨테이너별 Enable 상태를 명령어로 직접 확인하는 것은 불가능함.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

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
            default='connection',
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
        if not lines:
            return self.ok(
                metrics={},
                thresholds={},
                reasons='DB Connection 로그 출력 없음',
                message='DB Connection 로그 출력 없음',                
            )
        
        abnormal_words = self.get_threshold_var(
            key='abnormal_words',
            default='TIMEOUT,CLOSED',
            value_type='str',
        )
        abnormal_words = re.split('[,|]+', abnormal_words)
        abnormal_words = set(abnormal_words)
        abnormal_lines = [line for line in lines if any(word in line.upper() for word in abnormal_words)]
        metrics = {
            'connection_log_count': len(lines), 
            'abnormal_line_count': len(abnormal_lines), 
            'abnormal_lines': abnormal_lines[:20], 
            'sample_lines': lines[:20]
        }
        thresholds = {'abnormal_patterns': '|'.join(abnormal_words)}

        if abnormal_lines:
            return self.warn(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons='DB Connection 로그에서 이상 징후가 발견되었습니다.', 
                message='DB Connection 상태 경고: abnormal_line_count=%s' % len(abnormal_lines)
            )

        return self.ok(
            metrics=metrics, 
            thresholds=thresholds, 
            reasons='DB Connection 로그에서 이상 징후가 발견되지 않았습니다.', 
            message='DB Connection 상태 정상: connection_log_count=%s' % len(lines)
        )


CHECK_CLASS = Check
