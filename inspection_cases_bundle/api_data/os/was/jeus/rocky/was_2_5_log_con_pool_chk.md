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

WAS-JEUS-ROCKY-REPLAY-009

# is_required

필수

# inspection_name

커넥션풀 누수 발생 여부 점검

# inspection_content

JDBC Connection Leak 발생여부 점검(문제 AP소스를 찾아 근본적인 원인 해결을 위해 Resourcenotclosed, Waittime outexception 등의 메모리 누수 로그 확인, DBConnectionPool 자원의 원활한 이용을 위한 사전 점검)

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- Connection Leak 메시지: 커넥션 누수가 발생한 상황에 대한 설명을 제공함. 예를 들어, "Connection was not closed for over 300 seconds"라는 메시지는 커넥션이 일정 시간 이상 반환되지 않았음을 나타냄.

- **양호**: 로그에 'connection leak' 발생하지 않은 상태
- **경고**: 로그에 'connection leak' 발생한 상태
- **확인 필요**: 출력 및 해당 로그 파일(jdbc.log)이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'grep -i "{bad_word}" "$(ls -t {admin_log_path}/*.log | head -1)"'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, bad_word: str, admin_log_path: str):
        command = COMMAND.format(bad_word=bad_word,admin_log_path=admin_log_path)
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
        bad_word = self.get_threshold_var(key='bad_word', default='connection leak', value_type='str')
        admin_log_path = self.get_threshold_var(key='admin_log_path', default='/home/exTMS/tmax/jeus/log/adminServer', value_type='str')
        expected_matching_line_count = self.get_threshold_var(key='expected_matching_line_count', default=0, value_type='int')

        stdout, _stderr, error = self._run_jeus_command(bad_word, admin_log_path)
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'finding_label': bad_word, 'matching_line_count': len(lines), 'sample_lines': lines[:20]}
        thresholds = {'expected_matching_line_count': expected_matching_line_count}
        
        if lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되었습니다.' % bad_word, message='JEUS 로그 패턴 경고: %s count=%s' % (bad_word, len(lines)))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되지 않았습니다.' % bad_word, message='JEUS 로그 패턴 정상: %s 미검출' % bad_word)


CHECK_CLASS = Check
