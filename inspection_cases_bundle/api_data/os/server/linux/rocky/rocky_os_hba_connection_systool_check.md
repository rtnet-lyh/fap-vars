# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-HBA-CONN-01

# is_required

권고

# inspection_name

HBA 연결상태 점검

# inspection_content

HBA 연결 정상 유무 점검(State Online, Current Speed)

# inspection_command

```bash
systool -c fc_host -a
```

# inspection_output

```text
Class Device = "host0"
Class Device path = "/sys/class/fc_host/host0"
port_name = "0x50014380186baf12"
node_name = "0x50014380186baf10"
port_state = "Online"
speed = "8 Gbit"
supported_speeds = "4 Gbit, 8 Gbit, 16 Gbit"
```

# description

- `systool -c fc_host -a` 명령은 Fibre Channel HBA 포트의 연결 상태를 조회할 때 사용한다.
- PDF의 `fc_portname`, `fc_node_name`, `fc_state`, `fc_speed`는 Linux `systool` 출력의 `port_name`, `node_name`, `port_state`, `speed`와 같은 의미로 해석한다.
- `port_state = "Online"`이면 HBA 포트가 정상적으로 링크 업 상태이며 스토리지 패브릭에 연결된 것으로 본다.
- `speed = "8 Gbit"` 같은 값은 현재 협상된 링크 속도를 의미한다. 기대 속도보다 낮거나 `unknown`으로 표시되면 SFP, 케이블, 스위치 포트, HBA 설정을 함께 점검한다.
- `supported_speeds`는 해당 포트가 지원하는 최대 속도 목록이다. 현재 속도와 지원 속도 차이가 크면 링크 협상이나 패브릭 설정 문제 가능성을 확인한다.
- `Offline`, `Linkdown`, `Unknown` 상태가 보이면 HBA 포트, 광 모듈, 케이블, SAN 스위치, 스토리지 연결 구성을 점검한다.

- **양호**: `systool -c fc_host -a` 결과에서 HBA 포트가 확인되고 `port_state`가 `Online`이며 현재 속도 값이 정상적으로 표시되는 경우
- **경고**: 포트 상태는 `Online`이지만 현재 속도 값이 비정상적으로 낮거나 `unknown`으로 표시되어 추가 확인이 필요한 경우
- **실패**: HBA 포트 상태가 `Offline`, `Linkdown`, `Unknown` 등 비정상 상태로 표시되는 경우
- **참고**: `fc_host` 클래스 자체가 없으면 FC HBA가 미구성 상태이거나 관련 패키지/드라이버가 없을 수 있으므로 서버 스토리지 연결 구조를 먼저 확인한다

# thresholds

[
    {id: null, key: "없음", value: "", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


HBA_COMMAND = 'systool -c fc_host -a'
PORT_STATE_PATTERN = re.compile(r'^port_state\s*=\s*"(.*)"$', re.IGNORECASE)
SPEED_PATTERN = re.compile(r'^speed\s*=\s*"(.*)"$', re.IGNORECASE)
SUPPORTED_SPEEDS_PATTERN = re.compile(r'^supported_speeds\s*=\s*"(.*)"$', re.IGNORECASE)
PORT_NAME_PATTERN = re.compile(r'^port_name\s*=\s*"(.*)"$', re.IGNORECASE)
NODE_NAME_PATTERN = re.compile(r'^node_name\s*=\s*"(.*)"$', re.IGNORECASE)
CLASS_DEVICE_PATTERN = re.compile(r'^Class Device\s*=\s*"(.*)"$', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _is_command_not_found(self, rc, out, err):
        if rc == 127:
            return True
        command_error = self._detect_command_error(out, err)
        return bool(command_error)

    def _normalize_state(self, value):
        return str(value or '').strip().lower().replace(' ', '')

    def _speed_needs_attention(self, speed_text):
        lowered = str(speed_text or '').strip().lower()
        if not lowered:
            return True
        if any(marker in lowered for marker in ('unknown', 'not negotiated', 'linkdown', 'offline')):
            return True
        return not bool(re.search(r'\d', lowered))

    def _parse_output(self, stdout):
        lines = [line.rstrip() for line in (stdout or '').splitlines() if line.strip()]
        ports = []
        current = None

        for raw_line in lines:
            line = raw_line.strip()

            class_match = CLASS_DEVICE_PATTERN.match(line)
            if class_match:
                if current:
                    ports.append(current)
                current = {
                    'class_device': class_match.group(1).strip(),
                    'port_name': '',
                    'node_name': '',
                    'port_state': '',
                    'speed': '',
                    'supported_speeds': '',
                }
                continue

            if current is None:
                continue

            for pattern, key in (
                (PORT_NAME_PATTERN, 'port_name'),
                (NODE_NAME_PATTERN, 'node_name'),
                (PORT_STATE_PATTERN, 'port_state'),
                (SPEED_PATTERN, 'speed'),
                (SUPPORTED_SPEEDS_PATTERN, 'supported_speeds'),
            ):
                match = pattern.match(line)
                if match:
                    current[key] = match.group(1).strip()
                    break

        if current:
            ports.append(current)

        return ports

    def run(self):
        rc, out, err = self._ssh(HBA_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_command_not_found(rc, out, err):
            return self.not_applicable(
                'systool 명령을 사용할 수 없거나 FC HBA 환경이 아니어서 HBA 연결상태 점검은 대상미해당입니다.',
                raw_output=((out or '').strip() or (err or '').strip()),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='systool -c fc_host -a 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        ports = self._parse_output(out)
        metrics = {
            'fc_host_detected': bool(ports),
            'port_count': len(ports),
            'online_port_count': 0,
            'attention_speed_port_count': 0,
            'ports': ports,
        }

        if not ports:
            return self.not_applicable(
                'fc_host 클래스가 확인되지 않아 FC HBA 미구성 또는 드라이버 미탑재 상태로 판단했습니다.',
                raw_output=(out or '').strip(),
            )

        failed_ports = []
        warning_ports = []
        for port in ports:
            normalized_state = self._normalize_state(port.get('port_state'))
            if normalized_state == 'online':
                metrics['online_port_count'] += 1
                if self._speed_needs_attention(port.get('speed')):
                    warning_ports.append(port.get('class_device') or '')
                    metrics['attention_speed_port_count'] += 1
                continue

            if normalized_state in ('offline', 'linkdown', 'linkdown.', 'unknown'):
                failed_ports.append(port.get('class_device') or '')
            else:
                warning_ports.append(port.get('class_device') or '')

        if failed_ports:
            result = self.fail(
                'HBA 포트 상태 비정상',
                message='비정상 HBA 포트 상태가 확인되었습니다: ' + ', '.join(failed_ports),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = 'port_state가 Offline/Linkdown/Unknown인 HBA 포트가 있습니다.'
            return result

        if warning_ports:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='HBA 포트는 Online이지만 속도 또는 상태 표기를 추가 확인해야 합니다: ' + ', '.join(warning_ports),
                message='HBA 연결 상태 추가 확인 필요',
            )

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='모든 HBA 포트가 Online 상태이며 현재 속도 값이 확인되었습니다.',
            message='HBA 연결상태 점검 정상',
        )


CHECK_CLASS = Check
