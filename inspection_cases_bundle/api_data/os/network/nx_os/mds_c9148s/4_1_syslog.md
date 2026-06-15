# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

nx_os

# application

mds_c9148s

# inspection_code


NW-NX-MDS9148-012

# is_required

필수

# inspection_name

시스템 로그

# inspection_content

HW 상태와 관련된 ERROR 로그(Fail, Error, Warning, Stop, Down) 발생 여부 점검

# inspection_command

```bash
show logging | include fail|error|warning|stop|down
```

# inspection_output

```text
CITS-SAN1# show logging | include fail|error|warning|stop|down
3(errors)               4(warnings)     5(notifications)
2026 Mar 27 09:46:04 CITS-SAN1 %PORT-5-IF_DOWN_LINK_FAILURE: %$VSAN 10%$ Interface fc1/5 is down (Link failure loss of signal)
2026 Apr 15 15:47:57 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from console - login
2026 May 19 17:00:17 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from 172.18.8.191 - sshd[21938]
2026 May 20 17:44:48 CITS-SAN1 %AUTHPRIV-3-SYSTEM_MSG: pam_aaa:Authentication failed from 172.18.8.191 - sshd[13859]
```

# description

- 명령어: 장비에 기록된 시스템 로그를 확인하는 명령어.
- include 옵션으로 특정 문자 파싱: fail|error|warning|stop|down

[참고]
- 변수로 파싱할 문자를 선언하는 방향도 있음.

- **양호**: 결과 값 미 출력
- **경고**: 결과 값 출력
- **확인 필요**: 명령어 실패

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show logging | include {include_keyword}'
PROMPT_RE = re.compile(r'^[A-Za-z0-9_.:/-]+[>#]\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _lines(self, text):
        lines = []
        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or PROMPT_RE.match(stripped) or stripped.endswith('# ' + COMMAND):
                continue
            lines.append(stripped)
        return lines

    def run(self):
        include_keyword = self.get_threshold_var(key='include_keyword', default='fail|error|warning|stop|down', value_type='str')
        command = COMMAND.format(include_keyword=include_keyword)
        rc, out, err = self._ssh(command)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        lines = self._lines(out)
        metrics = {'matched_log_count': len(lines), 'matched_logs': lines}
        if lines:
            return self.warn(metrics=metrics, thresholds={'include_keyword': include_keyword}, reasons='fail/error/warning/stop/down 관련 로그가 출력되었습니다.', message=f'시스템 로그 키워드 출력 {len(lines)}건.')
        return self.ok(metrics=metrics, thresholds={'include_keyword': include_keyword}, reasons='fail/error/warning/stop/down 관련 로그가 출력되지 않았습니다.', message='시스템 로그 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
