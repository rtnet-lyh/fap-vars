# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

cisco_ios

# application

c2960x

# inspection_code


NW-CIS-C2960X-005

# is_required

필수

# inspection_name

시스템 로그

# inspection_content

Cisco 장비의 시스템 로그 점검

# inspection_command

```bash
show logging
```

# inspection_output

```text
[OS: Cisco IOS] 추출된 결과입니다.
C2960X_Service#show logging
Syslog logging: enabled (0 messages dropped, 1 messages rate-limited, 0 flushes, 0 overruns, xml disabled, filtering disabled)

No Active Message Discriminator.



No Inactive Message Discriminator.


    Console logging: level debugging, 26183 messages logged, xml disabled,
                     filtering disabled
    Monitor logging: level debugging, 0 messages logged, xml disabled,
                     filtering disabled
    Buffer logging:  level debugging, 26184 messages logged, xml disabled,
                    filtering disabled
    Exception Logging: size (4096 bytes)
    Count and timestamp logging messages: disabled
    File logging: disabled
    Persistent logging: disabled

No active filter modules.

    Trap logging: level informational, 24380 message lines logged
        Logging to 211.241.21.110  (udp port 514, audit disabled,
              link up),
              24379 message lines logged,
              0 message lines rate-limited,
              0 message lines dropped-by-MD,
              xml disabled, sequence number disabled
              filtering disabled
        Logging to 211.241.21.35  (udp port 514, audit disabled,
              link up),
              24380 message lines logged,
              0 message lines rate-limited,
              0 message lines dropped-by-MD,
              xml disabled, sequence number disabled
              filtering disabled
        Logging Source-Interface:       VRF Name:

Log Buffer (16000 bytes):
abitEthernet0/5, changed state to down
May 29 2026 09:02:39.841: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 29 2026 09:02:40.840: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 29 2026 14:04:09.091: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(39052) -> 0.0.29.169(7593), 1 packet
May 29 2026 14:09:50.664: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(39052) -> 192.168.77.71(7593), 1 packet
May 29 2026 19:07:14.931: NTP Core (INFO): 211.241.21.15 961D 8D popcorn popcorn
May 30 2026 00:00:50.554: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:00:51.558: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:00:54.798: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 00:00:55.801: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 00:02:17.452: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:02:18.458: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:02:20.737: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 00:02:21.740: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 00:02:35.854: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:02:36.858: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 00:02:39.934: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 00:02:40.937: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 14:04:22.946: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(45982) -> 0.0.29.169(7593), 1 packet
May 30 2026 14:09:52.317: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(45982) -> 192.168.77.71(7593), 1 packet
May 30 2026 15:00:50.463: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:00:51.466: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:00:54.661: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 15:00:55.664: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 15:02:19.416: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:02:20.419: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:02:22.621: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 15:02:23.624: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 15:02:37.979: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:02:38.982: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 30 2026 15:02:42.219: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 30 2026 15:02:43.222: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 30 2026 19:49:22.630: NTP Core (INFO): 211.241.21.15 961D 8D popcorn popcorn
May 31 2026 06:00:50.567: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:00:51.570: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:00:54.807: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 06:00:55.810: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 31 2026 06:02:17.447: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:02:18.446: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:02:20.687: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 06:02:21.686: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 31 2026 06:02:36.077: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:02:37.062: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 06:02:40.425: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 06:02:41.428: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 31 2026 14:04:20.761: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(39436) -> 0.0.29.169(7593), 1 packet
May 31 2026 14:09:53.963: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(39436) -> 192.168.77.71(7593), 1 packet
May 31 2026 21:00:50.586: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:00:51.586: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:00:54.745: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 21:00:55.745: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 31 2026 21:02:17.487: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:02:18.486: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:02:20.723: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 21:02:21.727: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
May 31 2026 21:02:35.928: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:02:36.928: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
May 31 2026 21:02:40.245: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
May 31 2026 21:02:41.248: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:00:50.283: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:00:51.290: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:00:54.607: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:00:55.610: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:02:17.194: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:02:18.197: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:02:20.878: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:02:21.881: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:02:36.597: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:02:37.600: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  1 2026 12:02:40.676: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  1 2026 12:02:41.679: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:00:50.894: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:00:51.894: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:00:55.102: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:00:56.102: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:02:17.816: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:02:18.819: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:02:21.094: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:02:22.094: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:02:37.253: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:02:38.260: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 03:02:41.374: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 03:02:42.377: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 13:46:28.906: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(48688) -> 0.0.29.169(7593), 1 packet
Jun  2 2026 13:51:57.243: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(48688) -> 192.168.77.71(7593), 1 packet
Jun  2 2026 18:00:51.619: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:00:52.626: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:00:55.824: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 18:00:56.827: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 18:02:20.544: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:02:21.547: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:02:23.861: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 18:02:24.878: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 18:02:39.988: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:02:40.988: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  2 2026 18:02:44.228: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  2 2026 18:02:45.231: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:00:50.910: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:00:51.916: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:00:55.153: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:00:56.153: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:02:17.824: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:02:18.828: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:02:21.023: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:02:22.026: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:02:37.262: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:02:38.269: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  3 2026 09:02:41.582: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 09:02:42.582: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  3 2026 13:46:47.706: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(40716) -> 0.0.29.169(7593), 1 packet
Jun  3 2026 13:51:58.891: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(40716) -> 192.168.77.71(7593), 1 packet
Jun  4 2026 00:00:51.873: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:00:52.880: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:00:56.036: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 00:00:57.036: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 00:02:18.760: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:02:19.766: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:02:22.003: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 00:02:23.006: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 00:02:37.201: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:02:38.208: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 00:02:41.560: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 00:02:42.563: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 07:22:13.023: NTP Core (INFO): 211.241.21.15 961D 8D popcorn popcorn
Jun  4 2026 13:46:34.401: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(55558) -> 0.0.29.169(7593), 1 packet
Jun  4 2026 13:52:00.545: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(55558) -> 192.168.77.71(7593), 1 packet
Jun  4 2026 15:00:51.636: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:00:52.639: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:00:55.880: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 15:00:56.883: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 15:02:18.519: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:02:19.526: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:02:21.721: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 15:02:22.724: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 15:02:37.918: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:02:38.925: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  4 2026 15:02:42.116: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  4 2026 15:02:43.144: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:00:51.339: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:00:52.343: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:00:55.502: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:00:56.502: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:02:18.244: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:02:19.250: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:02:21.445: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:02:22.448: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:02:37.643: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:02:38.649: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to down
Jun  5 2026 06:02:41.886: %LINK-3-UPDOWN: Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 06:02:42.886: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/5, changed state to up
Jun  5 2026 13:24:20.688: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(46496) -> 0.0.29.169(7593), 1 packet
Jun  5 2026 13:30:02.170: %SEC-6-IPACCESSLOGP: list DenySSH permitted tcp 211.241.21.80(46496) -> 192.168.77.71(7593), 1 packet
```

# description

- `show logging` 명령을 통해 장비에 기록된 주요 이벤트, 경고, 에러 로그(syslog)를 확인합니다.

- **양호**: 장비 구동 및 서비스에 영향을 주는 에러 로그가 없음
- **경고**: 포트 Flapping, 모듈 다운, 리소스 부족 등 시스템 장애를 시사하는 로그 다수 발생
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds

[
    {id: null, key: "bad_log_keywords", value: "critical,error,fail,down,flapping,overrun,stop", sortOrder: 0}
,
{id: null, key: "max_bad_log_count", value: "0", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show logging'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _split_keywords(self, value):
        return [item for item in re.split(r'[\s,|]+', str(value or '')) if item]

    def run(self):
        keywords = self._split_keywords(self.get_threshold_var(
            'bad_log_keywords',
            default='critical,error,fail,down,flapping,overrun,stop',
            value_type='str',
        ))
        max_bad_count = self.get_threshold_var('max_bad_log_count', default=0, value_type='int')
        thresholds = {
            'bad_log_keywords': keywords,
            'max_bad_log_count': max_bad_count,
        }
        stdout, error = self._run_command()
        if error:
            return error
        if not stdout:
            return self.fail('시스템 로그 출력 없음', message='show logging 결과가 비어 있습니다.', thresholds=thresholds)

        pattern = re.compile('|'.join(re.escape(item) for item in keywords), re.IGNORECASE) if keywords else None
        bad_lines = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped or stripped == COMMAND:
                continue
            if pattern and pattern.search(stripped):
                bad_lines.append(stripped)

        metrics = {
            'bad_log_count': len(bad_lines),
            'bad_logs': bad_lines,
        }
        if len(bad_lines) > max_bad_count:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='시스템 로그에서 장애 관련 키워드가 탐지되었습니다.',
                message=f'시스템 로그 경고: 장애 관련 로그 {len(bad_lines)}건.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='장애 관련 시스템 로그가 기준 이하입니다.',
            message='시스템 로그 점검 정상.',
        )


CHECK_CLASS = Check
