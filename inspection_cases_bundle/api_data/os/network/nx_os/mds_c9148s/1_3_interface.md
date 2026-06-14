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

NETWORK-NXOS-MDS-C9148S-INTERFACE-USAGE-01

# is_required

필수

# inspection_name

네트워크 인터페이스 사용률

# inspection_content

인터페이스 송신/수신 부하 상태를 확인하여 대역폭 사용률 점검(80% 미만 권고).

# inspection_command

```bash
show interface
```

# inspection_output

```text
fc1/10 is up
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:0a:00:3a:9c:16:48:10
    Admin port mode is auto, trunk mode is on
    snmp link state traps are enabled
    Port mode is F, FCID is 0xa90e00
    Port vsan is 10
    Speed is 8 Gbps
    Rate mode is dedicated
    Transmit B2B Credit is 12
    Receive B2B Credit is 64
    Receive data field Size is 2112
    Beacon is turned off
    admin fec state is down
    oper fec state is down
    5 minutes input rate 18940800 bits/sec,2367600 bytes/sec, 2254 frames/sec
    5 minutes output rate 64165888 bits/sec,8020736 bytes/sec, 4478 frames/sec
      6141735865596 frames input,10778094664129100 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      1996989242795 frames output,2432660549947668 bytes
        0 discards,0 errors
      0 input OLS,0  LRR,1 NOS,0 loop inits
      2 output OLS,2 LRR, 1 NOS, 2 loop inits
      64 receive B2B credit remaining
      12 transmit B2B credit remaining
      12 low priority transmit B2B credit remaining
    Interface last changed at Sat Jan 15 01:00:44 2022

    Last clearing of "show interface" counters  :never

fc1/11 is down (Link failure or not-connected)
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:0b:00:3a:9c:16:48:10
    Admin port mode is auto, trunk mode is on
    snmp link state traps are enabled
    Port vsan is 10
    Receive data field Size is 2112
    Beacon is turned off
    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec
    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec
      1 frames input,176 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      27402085 frames output,1096083536 bytes
        0 discards,0 errors
      0 input OLS,0  LRR,0 NOS,15071036 loop inits
      1370105 output OLS,0 LRR, 685057 NOS, 685059 loop inits
    Last clearing of "show interface" counters  :never
```

# description

- 명령어: 인터페이스 상태, 속도, 송수신 트래픽, 오류 등을 확인하는 명령어.
- 상태가 UP인 인터페이스만 점검 ex)fc1/10 is up
- 5 minutes input rate: 최근 5분 평균 수신 트래픽 사용량, 5 minutes output rate: 최근 5분 평균 송신 트래픽 사용량
- 수신 사용률(%): 5 minutes input rate / speed * 100
- 송신 사용률(%): 5 minutes output rate / speed * 100
- ex) 출력기준
수신 사용률(%) = 18940800 / 8000000000 * 100 = 약 0.24%
송신 사용률(%) = 64165888 / 8000000000 * 100 = 약 0.80%

[참고]
- 범정부 문서 기준 'txload','rxload'를 점검해야하지만, SAN장비에서는 결과 값이 달라서 rate 값으로 점검.

- **양호**: 상태가 UP인 인터페이스의 수신 또는 송신 사용률이 `max_interface_usage_percent`이하인 상태
- **경고**: 상태가 UP인 인터페이스의 수신 또는 송신 사용률이 `max_interface_usage_percent`초과인 상태
- **확인 필요**: 명령어 실패 및 '5 minutes input rate' 파싱 불가

# thresholds

[
    {id: null, key: "max_interface_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interface'
IFACE_RE = re.compile(r'^(\S+/\S+)\s+is\s+(\S+)')
RATE_RE = re.compile(r'5 minutes (input|output) rate (\d+) bits/sec')
SPEED_RE = re.compile(r'Speed is ([0-9.]+) Gbps')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _parse(self, text):
        rows = []
        current = None
        for line in (text or '').splitlines():
            iface = IFACE_RE.match(line.strip())
            if iface:
                if current:
                    rows.append(current)
                current = {'interface': iface.group(1)} if iface.group(2) == 'up' else None
                continue
            if not current:
                continue
            speed = SPEED_RE.search(line)
            rate = RATE_RE.search(line)
            if speed:
                current['speed_bps'] = float(speed.group(1)) * 1000000000
            if rate:
                current[rate.group(1) + '_bps'] = int(rate.group(2))
        if current:
            rows.append(current)

        parsed = []
        for row in rows:
            if not all(key in row for key in ('speed_bps', 'input_bps', 'output_bps')):
                continue
            row['input_usage_percent'] = round(row['input_bps'] / row['speed_bps'] * 100, 2)
            row['output_usage_percent'] = round(row['output_bps'] / row['speed_bps'] * 100, 2)
            parsed.append(row)
        return parsed

    def run(self):
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_interface_usage_percent': max_usage}
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        text = (out or '').strip()
        interfaces = self._parse(text)
        if not interfaces:
            return self.fail('인터페이스 사용률 파싱 실패', message='UP 인터페이스의 speed/input/output rate를 해석하지 못했습니다.', stdout=text, thresholds=thresholds)

        for row in interfaces:
            row['max_usage_percent'] = max(row['input_usage_percent'], row['output_usage_percent'])
        over = [row for row in interfaces if row['max_usage_percent'] > max_usage]
        max_row = max(interfaces, key=lambda row: row['max_usage_percent'])
        metrics = {
            'up_interface_count': len(interfaces),
            'max_interface_usage_percent': max_row['max_usage_percent'],
            'max_interface': max_row,
            'over_threshold_interfaces': over,
            'interfaces': interfaces,
        }
        if over:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(over)}개 인터페이스 사용률이 임계치를 초과했습니다.', message=f'인터페이스 사용률 기준 초과: max={max_row["max_usage_percent"]}%.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'UP 인터페이스 최대 사용률 {max_row["max_usage_percent"]}%가 임계치 이하입니다.', message=f'인터페이스 사용률 점검이 정상 수행되었습니다. max={max_row["max_usage_percent"]}%.')


CHECK_CLASS = Check
