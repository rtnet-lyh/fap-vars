# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

juniper_junos

# application

ex4300

# inspection_code

NETWORK-JUNIPER-JUNOS-EX4300-1-3-INTERFACE

# is_required

필수

# inspection_name

네트워크 인터페이스 사용률

# inspection_content

인터페이스 사용현황을 확인하여 네트워크 병목여부 확인

# inspection_command

```bash
show interfaces {{ interface_name }} statistics
```

# inspection_output

```text
falcon@Center_Server_J4300_A> show interfaces ge-0/0/0 statistics
Physical interface: ge-0/0/0, Enabled, Physical link is Up
  Interface index: 646, SNMP ifIndex: 512
  Description: ## ATMS_▒▒▒▒DB-1_172.18.8.87_97 ##
  Link-level type: Ethernet, MTU: 1514, LAN-PHY mode, Speed: 1000mbps, Duplex: Full-Duplex, BPDU Error: None,
  Loop Detect PDU Error: None, Ethernet-Switching Error: None, MAC-REWRITE Error: None, Loopback: Disabled,
  Source filtering: Disabled, Flow control: Enabled, Auto-negotiation: Enabled, Remote fault: Online, Media type: Fiber
  Device flags   : Present Running
  Interface flags: SNMP-Traps Internal: 0x0
  Link flags     : None
  CoS queues     : 12 supported, 12 maximum usable queues
  Current address: f4:bf:a8:ed:ad:e3, Hardware address: f4:bf:a8:ed:ad:e3
  Last flapped   : 2026-05-18 16:43:53 KST (1w2d 21:07 ago)
  Statistics last cleared: Never
  Input rate     : 2136 bps (3 pps)
  Output rate    : 3592 bps (6 pps)
  Input errors: 0, Output errors: 0
  Active alarms  : None
  Active defects : None
  PCS statistics                      Seconds
    Bit errors                             0
    Errored blocks                         0
  Ethernet FEC statistics              Errors
    FEC Corrected Errors                    0
    FEC Uncorrected Errors                  0
    FEC Corrected Errors Rate               0
    FEC Uncorrected Errors Rate             0
  Interface transmit statistics: Disabled

  Logical interface ge-0/0/0.0 (Index 555) (SNMP ifIndex 513)
    Flags: Up SNMP-Traps 0x0 Encapsulation: Ethernet-Bridge
    Input packets : 1395327
    Output packets: 4395788
    Protocol eth-switch, MTU: 1514
      Flags: Is-Primary
```

# description

- 명령어: 특정 인터페이스 상태 및 통계 정보를 확인하는 명령어.
- 인터페이스 사용률은 Input rate, Output rate값을 인터페이스 Speed 값과 비교하여 계산한다.- 
- 수신 사용률(%): Input rate / speed * 100
- 송신 사용률(%): Output rate / speed * 100
- Speed: 1000mbps = 1000000000 bps
- ex) 출력기준
수신 사용률(%) = 2136 / 1000000000 * 100 = 약 0.0002136%
송신 사용률(%) = 3592 / 1000000000 * 100 = 약 0.0003592%

- **양호**: 수신 또는 송신 사용률이 `max_interface_usage_percent`이하인 상태
- **경고**: 수신 또는 송신 사용률이 `max_interface_usage_percent`초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[
    {id: null, key: "max_interface_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show interfaces statistics'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _run_command(self, command):
        results = self._run_paramiko_commands([{"command": command, "timeout": 10}], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None  

    def _speed_to_bps(self, value, unit):
        number = float(value)
        normalized = str(unit or '').strip().lower()
        if normalized.startswith('g'):
            return number * 1000 * 1000 * 1000
        if normalized.startswith('m'):
            return number * 1000 * 1000
        if normalized.startswith('k'):
            return number * 1000
        return number

    def _parse_interface_usage(self, text):
        blocks = re.split(r'(?=Physical interface:)', text)
        blocks = [b.strip() for b in blocks if b.strip().startswith("Physical interface:")]
        force_1g_output = "Speed: 1000mbps"
        result = {}
        for block in blocks:
            is_forced = False
            match_interface = re.search(r'Physical interface:\s+(?P<interface>\S+),\s+.*Enabled.*Up', block)
            match_speed = re.search(r'Speed:\s+(?P<speed>\d+)(?P<unit>\w+)', block)
            if not match_speed:            
                match_speed = re.search(r'Speed:\s+(?P<speed>\d+)(?P<unit>\w+)', force_1g_output)
                is_forced = True
            match_input_bps = re.search(r'Input rate\s+:\s+(?P<input_bps>\d+)\s+bps', block)
            match_output_bps = re.search(r'Output rate\s+:\s+(?P<output_bps>\d+)\s+bps', block)
            if match_interface and match_speed and match_input_bps and match_output_bps:
                interface = match_interface.group("interface")
                speed = match_speed.group("speed")
                unit = match_speed.group("unit")
                input_bps = int(match_input_bps.group("input_bps"))
                output_bps = int(match_output_bps.group("output_bps"))
                speed_bps = self._speed_to_bps(speed, unit)
                result[interface] = {
                    "speed": speed + unit,                                                    
                    "input_bps": input_bps,
                    "input_percent": round((input_bps / speed_bps) * 100, 4) if speed_bps else 0.0,
                    "output_bps": output_bps,
                    "output_percent": round((output_bps / speed_bps) * 100, 4) if speed_bps else 0.0,
                    "is_forced": "대역폭 확인불가 - 1G로 간주" if is_forced else "대역폭 확인 성공",
                }

        return result

    def run(self):
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_interface_usage_percent': max_usage}
        
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        metrics = self._parse_interface_usage(stdout)
        if not metrics:
            return self.fail('인터페이스 사용률 파싱 실패', message='인터페이스 속도 또는 입출력 rate 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)

        max_interface, max_data = max(
            metrics.items(),
            key=lambda item: max(
                item[1]["input_percent"],
                item[1]["output_percent"],
            )
        )

        real_max_usage = max(
            max_data["input_percent"],
            max_data["output_percent"],
        )

        if real_max_usage > max_usage:
            return self.fail('인터페이스 사용률 임계치 초과', message=f'인터페이스({max_interface}) 사용률 최대값 {real_max_usage}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='인터페이스 입출력 사용률이 임계치 이하입니다.', message=f'인터페이스 사용률 점검 정상: 최대 {real_max_usage}%.')


CHECK_CLASS = Check
