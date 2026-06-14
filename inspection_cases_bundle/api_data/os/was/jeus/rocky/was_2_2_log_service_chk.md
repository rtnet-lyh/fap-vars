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

WAS-JEUS-ROCKY-REPLAY-006

# is_required

필수

# inspection_name

서비스 로그 이상 유무 점검

# inspection_content

각 서비스 컨테이너 로그 점검(비정상 SQL 존재 여부, Trasaction commit 확인 등 서비스 로그 점검)

# inspection_command

```bash

```

# inspection_output

```text
[exTMS@tips_was1:/home/exTMS/tmax/jeus/log/adminServer]$ tail -f /home/exTMS/tmax/jeus/log/adminServer/JeusServer.log
[2026.05.14 13:10:28:479][2] [adminServer-777] [SERVER-0208] Operation: DOWNLOAD_CONFIG [extms2]
[2026.05.14 13:10:28:480][2] [adminServer-777] [SERVER-0228] The files on the managed server are up-to-date, so the configuration files will not be sent..
[2026.05.14 13:10:30:079][2] [adminServer-15] [SCF-0121] SCF Connection from extms2 has been allowed. Handler is SocketStream@3b0d6807(172.18.9.62:10000(SCF) -> 172.18.9.63:10010(SCF)).
[2026.05.14 13:10:30:079][2] [adminServer-15] [SCF-0310] State of member [extms2] changed. STOPPED -> ALIVE
[2026.05.14 13:10:30:186][2] [adminServer-1044] [Domain-0037] Sending a resynchronization request to extms2[172.18.9.63:10010(SCF)]
[2026.05.14 13:10:30:290][2] [adminServer-777] [SERVER-0208] Operation: DOWNLOAD_CONFIG [extms2]
[2026.05.14 13:10:30:291][2] [adminServer-777] [SERVER-0228] The files on the managed server are up-to-date, so the configuration files will not be sent..
[2026.05.14 13:10:42:608][2] [adminServer-399] [Deploy-0376] The state of the application [exTMS] in the server [extms2] is DISTRIBUTED. Final state is DISTRIBUTED
[2026.05.14 13:10:42:620][2] [adminServer-68] [Deploy-0376] The state of the application [exTMS] in the server [extms2] is RUNNING. Final state is RUNNING
[2026.05.14 13:10:42:696][2] [adminServer-768] [Domain-0022] Domain Administration Server succeeded to start server extms2.
```

# description

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

# COMMAND = 'tail -n 50 /home/exTMS/tmax/jeus/log/adminServer/JeusServer.log'
COMMAND = 'tail -100 $(find -L {admin_log_path} -iname "{log_file}" | xargs ls -t | head -1)'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        admin_log_path = self.get_threshold_var(
            key='admin_log_path',
            default='/home/exTMS/tmax/jeus/log',
            value_type='str',
        )

        log_file = self.get_threshold_var(
            key='log_file',
            default='JeusServer.log',
            value_type='str',
        )

        command = COMMAND.format(admin_log_path=admin_log_path, log_file=log_file)

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
        stdout, _stderr, error = self._run_jeus_command()
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return self.fail('로그 출력 없음', message='로그 출력이 비어 있습니다.', stdout=stdout)
        
        warning_words = self.get_threshold_var(
            key='warning_words', 
            default='ERROR,WARN,FATAL,CRITICAL,EXCEPTION', 
            value_type='str'
        )
        warning_words = re.split(r'[,|]+', warning_words)
        
        warning_lines = [line for line in lines if any(word in line.upper() for word in warning_words)]
        metrics = {'inspected_line_count': len(lines), 'warning_line_count': len(warning_lines), 'warning_lines': warning_lines[:20], 'sample_lines': lines[:20]}
        thresholds = {'warning_patterns': '|'.join(warning_words)}

        if warning_lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='로그에서 ERROR/WARN 계열 라인이 발견되었습니다.', message='JEUS 로그 점검 경고: warning_line_count=%s' % len(warning_lines))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='로그에서 ERROR/WARN 계열 라인이 발견되지 않았습니다.', message='JEUS 로그 점검 정상: inspected_line_count=%s' % len(lines))


CHECK_CLASS = Check
