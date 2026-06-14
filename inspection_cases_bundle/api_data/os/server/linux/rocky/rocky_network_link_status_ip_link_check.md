# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-IP-LINK-01

# is_required

필수

# inspection_name

NW 링크 상태 연결속도 설정

# inspection_content

Network 연결상태 정상 유무 점검(NIC 별 STATE Up, Down, Unknown 상태 확인)

# inspection_command

```bash
ip link
```

# inspection_output

```text
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
258: br-b687e047b713: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 0a:a9:67:08:33:43 brd ff:ff:ff:ff:ff:ff
2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 74:9d:8f:0e:ad:f2 brd ff:ff:ff:ff:ff:ff
    altname enp2s0f0
3: eno2: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 74:9d:8f:0e:ad:f3 brd ff:ff:ff:ff:ff:ff
    altname enp2s0f1
4: enp129s0f0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 04:27:58:0a:fa:2b brd ff:ff:ff:ff:ff:ff
5: enp129s0f1: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 04:27:58:0a:fa:2c brd ff:ff:ff:ff:ff:ff
6: br-3e40457894eb: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 22:e6:03:db:9a:72 brd ff:ff:ff:ff:ff:ff
7: docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 06:51:8e:96:c4:5d brd ff:ff:ff:ff:ff:ff
8: br-6a04ef950573: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 36:03:8e:67:89:f5 brd ff:ff:ff:ff:ff:ff
524: veth32719e4@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 76:1d:6c:77:8b:c5 brd ff:ff:ff:ff:ff:ff link-netnsid 1
525: veth6291e48@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 92:74:f7:f8:cd:4e brd ff:ff:ff:ff:ff:ff link-netnsid 2
14: br-ed17885ef5c2: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether ca:ef:a5:bf:46:55 brd ff:ff:ff:ff:ff:ff
280: docker_gwbridge: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 6e:ca:bc:88:d8:29 brd ff:ff:ff:ff:ff:ff
282: veth93dbdec@if281: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker_gwbridge state UP mode DEFAULT group default 
    link/ether c2:9d:8b:c2:cb:b5 brd ff:ff:ff:ff:ff:ff link-netnsid 5
293: vethda7d78b@if292: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker_gwbridge state UP mode DEFAULT group default 
    link/ether 5e:0c:cd:47:0e:7d brd ff:ff:ff:ff:ff:ff link-netnsid 8
294: vethe9072c6@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker0 state UP mode DEFAULT group default 
    link/ether 26:3a:00:00:e5:90 brd ff:ff:ff:ff:ff:ff link-netnsid 9
416: br-c05f4f389f6a: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 22:a7:a5:36:a0:0c brd ff:ff:ff:ff:ff:ff
417: veth73eb6b0@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 86:8c:33:38:1d:df brd ff:ff:ff:ff:ff:ff link-netnsid 0
```

# description

- `ip link` 명령은 시스템에 인식된 네트워크 인터페이스와 링크 상태를 확인하는 기본 명령이다.
- `lo`는 루프백 인터페이스이며 `<LOOPBACK,UP,LOWER_UP>`로 표시되면 로컬 TCP/IP 스택이 정상 활성화된 상태로 본다.
- `ens33` 같은 물리 NIC가 `<BROADCAST,MULTICAST,UP,LOWER_UP>`로 표시되면 인터페이스가 활성 상태이고 링크도 정상 연결된 것으로 해석한다.
- `mtu 65536`은 루프백 인터페이스의 최대 전송 단위이고, `mtu 1500`은 일반적인 이더넷 인터페이스의 표준 MTU 값이다.
- 물리 NIC가 `DOWN` 또는 `NO-CARRIER` 상태이거나 기대한 인터페이스가 보이지 않으면 케이블, 스위치 포트, NIC 드라이버, OS 네트워크 설정을 점검한다.

- **양호**: 점검 대상 물리 NIC가 `UP`, `LOWER_UP` 상태로 확인되는 경우
- **주의**: 인터페이스 상태가 `UNKNOWN`이거나 기대한 NIC 이름과 실제 NIC 이름이 달라 추가 확인이 필요한 경우
- **경고**: 점검 대상 물리 NIC가 `DOWN`, `NO-CARRIER` 또는 비활성 상태로 확인되는 경우

# thresholds

[
    {id: null, key: "exclude_interface_name_patterns", value: "^lo$|^br-.*|^docker.*|^veth.*", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


IP_LINK_COMMAND = 'ip link'
DEFAULT_EXCLUDE_INTERFACE_NAME_PATTERNS = '^lo$|^br-.*|^docker.*|^veth.*'
INTERFACE_HEADER_PATTERN = re.compile(
    r'^\d+:\s+(?P<name>[^:]+):\s+<(?P<flags>[^>]*)>.*\bstate\s+(?P<state>[A-Z_]+)\b',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_patterns(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _normalize_name(self, name):
        return str(name or '').strip().split('@', 1)[0]

    def _matches_any_pattern(self, name, patterns):
        return any(
            re.search(pattern, name)
            for pattern in patterns
        )

    def _parse_interfaces(self, stdout):
        interfaces = []

        for raw_line in (stdout or '').splitlines():
            match = INTERFACE_HEADER_PATTERN.match(raw_line.strip())
            if not match:
                continue

            raw_name = match.group('name').strip()
            flags = [
                flag.strip().upper()
                for flag in match.group('flags').split(',')
                if flag.strip()
            ]
            state = match.group('state').strip().upper()
            interfaces.append({
                'name': self._normalize_name(raw_name),
                'raw_name': raw_name,
                'flags': flags,
                'state': state,
            })

        if not interfaces:
            raise ValueError('ip link 출력에서 인터페이스 헤더를 찾지 못했습니다.')

        return interfaces

    def _classify_interface(self, interface):
        flags = set(interface.get('flags') or [])
        state = str(interface.get('state') or '').upper()

        if state == 'UP' and 'LOWER_UP' in flags and 'NO-CARRIER' not in flags:
            return 'ok', 'up_lower_up'

        if state == 'UNKNOWN':
            return 'warn', 'unknown_state'

        if state in ('DOWN', 'DORMANT', 'LOWERLAYERDOWN', 'NOTPRESENT') or 'NO-CARRIER' in flags:
            return 'warn', 'link_down_or_no_carrier'

        if state == 'UP':
            return 'warn', 'up_without_lower_up'

        return 'warn', 'unexpected_state'

    def _build_metrics(self, interfaces, excluded_interfaces, target_interfaces, missing_expected_patterns):
        return {
            'interface_count': len(interfaces),
            'excluded_interface_count': len(excluded_interfaces),
            'target_interface_count': len(target_interfaces),
            'ok_interface_count': sum(1 for item in target_interfaces if item.get('evaluation') == 'ok'),
            'warn_interface_count': sum(1 for item in target_interfaces if item.get('evaluation') == 'warn'),
            'excluded_interfaces': excluded_interfaces,
            'interfaces': target_interfaces,
            'missing_expected_interface_name_patterns': missing_expected_patterns,
        }

    def _format_interfaces(self, interfaces):
        return ', '.join(
            f"{item.get('name')}={item.get('state')}"
            for item in interfaces
        ) or '없음'

    def _format_patterns(self, patterns):
        return '|'.join(patterns) if patterns else '없음'

    def _format_thresholds(self, exclude_patterns, expected_patterns):
        return (
            f'exclude_interface_name_patterns={self._format_patterns(exclude_patterns)}, '
            f'expected_interface_name_patterns={self._format_patterns(expected_patterns)}'
        )

    def run(self):
        exclude_patterns = self._split_patterns(
            self.get_threshold_var(
                'exclude_interface_name_patterns',
                default=DEFAULT_EXCLUDE_INTERFACE_NAME_PATTERNS,
                value_type='str',
            )
        )
        expected_patterns = self._split_patterns(
            self.get_threshold_var(
                'expected_interface_name_patterns',
                default='',
                value_type='str',
            )
        )
        rc, out, err = self._ssh(IP_LINK_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='ip link 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            interfaces = self._parse_interfaces(out)
        except ValueError as exc:
            return self.fail(
                '네트워크 링크 상태 파싱 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        excluded_interfaces = []
        target_interfaces = []

        for interface in interfaces:
            normalized_name = interface.get('name') or ''
            if self._matches_any_pattern(normalized_name, exclude_patterns):
                excluded_interface = dict(interface)
                excluded_interface['excluded'] = True
                excluded_interfaces.append(excluded_interface)
                continue

            evaluation, evaluation_reason = self._classify_interface(interface)
            target_interface = dict(interface)
            target_interface['excluded'] = False
            target_interface['evaluation'] = evaluation
            target_interface['evaluation_reason'] = evaluation_reason
            target_interfaces.append(target_interface)

        if not target_interfaces:
            return self.fail(
                '점검 대상 NIC 없음',
                message=(
                    '제외 패턴 적용 후 점검할 네트워크 인터페이스가 없습니다. '
                    f'임계치 정보: {self._format_thresholds(exclude_patterns, expected_patterns)}. '
                    f'판단근거: 전체 인터페이스 {len(interfaces)}개 중 '
                    f'제외된 인터페이스 {len(excluded_interfaces)}개, 점검 대상 0개입니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        missing_expected_patterns = [
            pattern
            for pattern in expected_patterns
            if not any(
                re.search(pattern, interface.get('name') or '')
                for interface in target_interfaces
            )
        ]
        thresholds = {
            'exclude_interface_name_patterns': '|'.join(exclude_patterns),
            'expected_interface_name_patterns': '|'.join(expected_patterns),
        }
        metrics = self._build_metrics(
            interfaces,
            excluded_interfaces,
            target_interfaces,
            missing_expected_patterns,
        )
        warning_interfaces = [
            interface
            for interface in target_interfaces
            if interface.get('evaluation') == 'warn'
        ]

        reasons = []
        if warning_interfaces:
            reasons.append(
                '추가 확인이 필요한 NIC 상태: ' + self._format_interfaces(warning_interfaces)
            )
        if missing_expected_patterns:
            reasons.append(
                '기대한 NIC 이름 패턴이 확인되지 않았습니다: ' + ', '.join(missing_expected_patterns)
            )

        if reasons:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='; '.join(reasons),
                message=(
                    'NW 링크 상태 추가 확인 필요. '
                    f'임계치 정보: {self._format_thresholds(exclude_patterns, expected_patterns)}. '
                    '판단기준: 제외 패턴 적용 후 점검 대상 NIC는 '
                    'state=UP, LOWER_UP 플래그 보유, NO-CARRIER 미포함이어야 하며 '
                    '기대 NIC 패턴이 모두 확인되어야 합니다. '
                    f'판단근거: warning_interfaces={self._format_interfaces(warning_interfaces)}, '
                    f'missing_expected_patterns={self._format_patterns(missing_expected_patterns)}, '
                    f'target_interface_count={len(target_interfaces)}.'
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'점검 대상 NIC {len(target_interfaces)}개가 모두 UP, LOWER_UP 상태이며 '
                '기대 NIC 패턴 누락이 없습니다.'
            ),
            message=(
                'ip link 기준 NW 링크 상태 점검이 정상 수행되었습니다. '
                f'임계치 정보: {self._format_thresholds(exclude_patterns, expected_patterns)}. '
                '판단기준: 제외 패턴 적용 후 점검 대상 NIC는 '
                'state=UP, LOWER_UP 플래그 보유, NO-CARRIER 미포함이어야 하며 '
                '기대 NIC 패턴이 모두 확인되어야 합니다. '
                f'판단근거: target_interface_count={len(target_interfaces)}, '
                f'ok_interface_count={metrics["ok_interface_count"]}, '
                f'warn_interface_count={metrics["warn_interface_count"]}.'
            ),
        )


CHECK_CLASS = Check
