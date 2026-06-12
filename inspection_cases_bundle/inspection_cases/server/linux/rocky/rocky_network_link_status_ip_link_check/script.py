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
