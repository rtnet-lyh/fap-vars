# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


FCINFO_HBA_PORT_COMMAND = 'fcinfo hba-port'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _normalize(self, value):
        return str(value or '').strip().lower()

    def _extract_speed_gbps(self, value):
        text = str(value or '').strip()
        match = re.search(r'(\d+(?:\.\d+)?)\s*gb', text, re.IGNORECASE)
        if not match:
            return None
        number = float(match.group(1))
        if number.is_integer():
            return int(number)
        return number

    def _parse_ports(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        ports = []
        current = None

        for line in lines:
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if key == 'HBA Port WWN':
                if current:
                    ports.append(current)
                current = {
                    'hba_port_wwn': value,
                    'os_device_name': '',
                    'manufacturer': '',
                    'model': '',
                    'driver_name': '',
                    'state': '',
                    'supported_speeds': '',
                    'current_speed': '',
                    'current_speed_gbps': None,
                    'node_wwn': '',
                }
                continue

            if current is None:
                continue

            if key == 'OS Device Name':
                current['os_device_name'] = value
            elif key == 'Manufacturer':
                current['manufacturer'] = value
            elif key == 'Model':
                current['model'] = value
            elif key == 'Driver Name':
                current['driver_name'] = value
            elif key == 'State':
                current['state'] = value
            elif key == 'Supported Speeds':
                current['supported_speeds'] = value
            elif key == 'Current Speed':
                current['current_speed'] = value
                current['current_speed_gbps'] = self._extract_speed_gbps(value)
            elif key == 'Node WWN':
                current['node_wwn'] = value

        if current:
            ports.append(current)

        return ports

    def run(self):
        expected_state_value = self.get_threshold_var('expected_state_value', default='online', value_type='str')
        min_current_speed_gbps = self.get_threshold_var('min_current_speed_gbps', default=8, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(FCINFO_HBA_PORT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris HBA 연결 상태 점검에 실패했습니다. 현재 상태: fcinfo 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=[
                'permission denied',
                'not supported',
                'no such file or directory',
                'cannot find',
                'not found',
                'unknown userland error',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris HBA 연결 상태 점검에 실패했습니다. '
                    f'현재 상태: fcinfo 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in (out or '').lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'HBA 실패 키워드 감지',
                message=(
                    'Solaris HBA 연결 상태 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        ports = self._parse_ports(out)
        if not ports:
            return self.fail(
                'HBA 연결 상태 파싱 실패',
                message='Solaris HBA 연결 상태 점검에 실패했습니다. 현재 상태: fcinfo 출력에서 HBA 포트 정보를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        expected_state_norm = self._normalize(expected_state_value)
        offline_ports = []
        speed_issue_ports = []
        speed_parse_issue_ports = []
        online_port_count = 0
        compliant_speed_port_count = 0
        observed_speeds = []

        for port in ports:
            state_norm = self._normalize(port.get('state'))
            if state_norm == expected_state_norm:
                online_port_count += 1
            else:
                offline_ports.append(port.get('os_device_name') or port.get('hba_port_wwn'))

            speed_value = port.get('current_speed_gbps')
            if speed_value is None:
                speed_parse_issue_ports.append(port.get('os_device_name') or port.get('hba_port_wwn'))
            else:
                observed_speeds.append(speed_value)
                if speed_value >= min_current_speed_gbps:
                    compliant_speed_port_count += 1
                else:
                    speed_issue_ports.append(port.get('os_device_name') or port.get('hba_port_wwn'))

        metrics = {
            'port_count': len(ports),
            'online_port_count': online_port_count,
            'compliant_speed_port_count': compliant_speed_port_count,
            'minimum_speed_gbps_observed': min(observed_speeds) if observed_speeds else None,
            'ports': ports,
            'offline_ports': offline_ports,
            'speed_issue_ports': speed_issue_ports,
            'speed_parse_issue_ports': speed_parse_issue_ports,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'expected_state_value': expected_state_value,
            'min_current_speed_gbps': min_current_speed_gbps,
            'failure_keywords': failure_keywords,
        }

        if speed_parse_issue_ports:
            return self.fail(
                'HBA 속도 파싱 실패',
                message=(
                    'Solaris HBA 연결 상태 점검에 실패했습니다. '
                    f'현재 상태: Current Speed 값을 해석하지 못한 포트가 있습니다: {speed_parse_issue_ports}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if offline_ports or speed_issue_ports:
            problem_parts = []
            if offline_ports:
                problem_parts.append(f'State 비정상={offline_ports}')
            if speed_issue_ports:
                problem_parts.append(f'속도 기준 미달={speed_issue_ports}')
            return self.fail(
                'HBA 연결 상태 비정상',
                message=(
                    'Solaris HBA 연결 상태 점검에 실패했습니다. '
                    '현재 상태: ' + ', '.join(problem_parts) + '. '
                    f'기준 State={expected_state_value}, Current Speed {min_current_speed_gbps}Gb 이상.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        port_names = ', '.join(port.get('os_device_name') or port.get('hba_port_wwn') for port in ports)
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'모든 HBA 포트가 State={expected_state_value}이며 Current Speed가 {min_current_speed_gbps}Gb 이상입니다.'
            ),
            message=(
                'Solaris HBA 연결 상태가 정상입니다. '
                f'현재 상태: 포트 {port_names}, 총 포트 {len(ports)}개, '
                f'online 포트 {online_port_count}개, '
                f'Current Speed 기준 {min_current_speed_gbps}Gb 이상 충족 {compliant_speed_port_count}개, '
                f'최저 확인 속도 {min(observed_speeds) if observed_speeds else "확인 불가"}Gb.'
            ),
        )


CHECK_CLASS = Check
