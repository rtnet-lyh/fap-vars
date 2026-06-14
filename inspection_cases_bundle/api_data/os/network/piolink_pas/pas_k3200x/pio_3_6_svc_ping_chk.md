# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code

NETWORK-PIOLINK-PAS-K3200X-SERVICE-PING-01

# is_required

권고

# inspection_name

통신 테스트

# inspection_content

특정 장비와 통신상태를 확인함으로써 정상 통신 여부를 확인

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- 응답 성공률(Success rate)은 ICMP 패킷 성공률을 의미하며 100%에 가까울수록 정상 상태를 의미 
- 최소/평균/최대 응답 시간(min/avg/max)은 패킷 왕복 시간(RTT)을 의미함

- **양호**: packet loss 값이 `max_packet_loss_percent` 이하이며 평균 응답 시간(avg)이 `max_avg_response_time_ms` 이하인 경우 
- **경고**: packet loss 값이 `max_packet_loss_percent` 초과 또는 평균 응답 시간(avg)이 `max_avg_response_time_ms` 초과인 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "ip_address", value: "172.18.8.191", sortOrder: 0}
,
{id: null, key: "max_packet_loss_percent", value: "0", sortOrder: 1}
,
{id: null, key: "max_avg_response_time_ms", value: "100", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PING_RUN_TIMEOUT_SEC = 1.0
PACKET_LOSS_RE = re.compile(r'(\d+)\s+packets transmitted,\s*(\d+)\s+received,\s*([0-9.]+)%\s+packet loss', re.IGNORECASE)
AVG_RTT_RE = re.compile(r'(?:rtt|round-trip).*?=\s*[0-9.]+/([0-9.]+)/[0-9.]+', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_ping(self, command):
        results = self._run_paramiko_commands([
            {'command': command, 'timeout': PING_RUN_TIMEOUT_SEC, 'ignore_prompt': True},
            {'command': '\x03', 'timeout': 5, 'hide_command': True},
        ], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        if len(results) < 2:
            return None, self.fail('점검 명령 실행 실패', message='ping 종료를 위한 Ctrl-C 결과를 수신하지 못했습니다.')
        first, second = results[0], results[1]
        if first.get('rc') not in (0, 124):
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=(first.get('stdout') or '').strip(), stderr=(first.get('stderr') or '').strip())
        if second.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='ping 종료 후 프롬프트를 수신하지 못했습니다.', stdout=(second.get('stdout') or '').strip(), stderr=(second.get('stderr') or '').strip())
        return '\n'.join((item.get('stdout') or '').strip() for item in results if (item.get('stdout') or '').strip()), None

    def run(self):
        ip_address = str(self.get_threshold_var('ip_address', default='172.18.8.191', value_type='str')).strip()
        max_packet_loss_percent = self.get_threshold_var('max_packet_loss_percent', default=0.0, value_type='float')
        max_avg_response_time_ms = self.get_threshold_var('max_avg_response_time_ms', default=100.0, value_type='float')
        thresholds = {
            'ip_address': ip_address,
            'max_packet_loss_percent': max_packet_loss_percent,
            'max_avg_response_time_ms': max_avg_response_time_ms,
            'ping_run_timeout_sec': PING_RUN_TIMEOUT_SEC,
        }
        if not ip_address:
            return self.fail('임계치 미정의', message='ip_address threshold 값이 필요합니다.', thresholds=thresholds)

        command = f'ping {ip_address}'
        output, error = self._run_ping(command)
        if error:
            return error

        loss_match = PACKET_LOSS_RE.search(output or '')
        avg_match = AVG_RTT_RE.search(output or '')
        if not loss_match or not avg_match:
            return self.fail('ping 결과 파싱 실패', message='packet loss 또는 avg RTT 값을 해석하지 못했습니다.', stdout=output, thresholds=thresholds)

        transmitted = int(loss_match.group(1))
        received = int(loss_match.group(2))
        packet_loss = float(loss_match.group(3))
        avg_response_time_ms = float(avg_match.group(1))
        metrics = {
            'ip_address': ip_address,
            'packets_transmitted': transmitted,
            'packets_received': received,
            'packet_loss_percent': packet_loss,
            'avg_response_time_ms': avg_response_time_ms,
        }
        if packet_loss > max_packet_loss_percent or avg_response_time_ms > max_avg_response_time_ms:
            return self.fail(error='packet loss 또는 avg RTT가 임계치를 초과했습니다.', metrics=metrics, thresholds=thresholds, reasons='packet loss 또는 avg RTT가 임계치를 초과했습니다.', message=f'통신 테스트 경고: loss={packet_loss}%, avg={avg_response_time_ms}ms.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='packet loss와 avg RTT가 임계치 이하입니다.', message=f'통신 테스트 정상: loss={packet_loss}%, avg={avg_response_time_ms}ms.')


CHECK_CLASS = Check
