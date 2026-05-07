# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


ROUTE_COMMAND = 'netstat -rn'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_paramiko_commands(self, command):
        if not self._is_become_enabled():
            return [command]

        return [
            {
                'command': self._build_become_command(),
                'timeout': 1,
                'ignore_prompt': True,
            },
            {
                'command': str(self.get_connection_value('become_password', default='') or ''),
                'hide_command': True,
            },
            command,
        ]

    def _run_check_command(self, command):
        try:
            results = self._run_paramiko_commands(self._build_paramiko_commands(command))
        except ValueError as exc:
            return 1, '', str(exc)

        for item in reversed(results):
            if item.get('command') == command:
                return item.get('rc'), item.get('stdout', ''), item.get('stderr', '')

        failed_result = next((item for item in results if item.get('rc') != 0), None)
        if failed_result:
            return failed_result.get('rc'), failed_result.get('stdout', ''), failed_result.get('stderr', '')
        return 1, '', 'paramiko command result not found'


    def _parse_ping_output(self, text):
        alive_match = re.search(r'([0-9]+(?:\.[0-9]+){3})\s+is\s+alive', text or '', re.IGNORECASE)
        no_answer_match = re.search(r'no\s+answer\s+from\s+([0-9]+(?:\.[0-9]+){3})', text or '', re.IGNORECASE)
        transmitted_match = re.search(
            r'(\d+)\s+packets\s+transmitted,\s*(\d+)\s+received,\s*([0-9.]+)%\s+packet\s+loss',
            text or '',
            re.IGNORECASE,
        )
        rtt_match = re.search(
            r'round-trip\s*\(ms\)\s*min/avg/max\s*=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)',
            text or '',
            re.IGNORECASE,
        )

        if alive_match:
            return {
                'packets_transmitted': 1,
                'packets_received': 1,
                'packet_loss_percent': 0.0,
                'rtt_min_ms': None,
                'rtt_avg_ms': None,
                'rtt_max_ms': None,
                'is_alive': True,
                'no_answer': False,
            }

        if no_answer_match:
            return {
                'packets_transmitted': 1,
                'packets_received': 0,
                'packet_loss_percent': 100.0,
                'rtt_min_ms': None,
                'rtt_avg_ms': None,
                'rtt_max_ms': None,
                'is_alive': False,
                'no_answer': True,
            }

        if not transmitted_match:
            return None

        parsed = {
            'packets_transmitted': int(transmitted_match.group(1)),
            'packets_received': int(transmitted_match.group(2)),
            'packet_loss_percent': float(transmitted_match.group(3)),
            'is_alive': False,
            'no_answer': False,
        }

        if rtt_match:
            parsed.update({
                'rtt_min_ms': float(rtt_match.group(1)),
                'rtt_avg_ms': float(rtt_match.group(2)),
                'rtt_max_ms': float(rtt_match.group(3)),
            })
        else:
            parsed.update({
                'rtt_min_ms': None,
                'rtt_avg_ms': None,
                'rtt_max_ms': None,
            })

        return parsed

    def _parse_default_gateway(self, text):
        for raw_line in (text or '').splitlines():
            parts = re.split(r'\s+', raw_line.strip())
            if len(parts) < 2:
                continue
            destination = parts[0].strip().lower()
            gateway = parts[1].strip()
            if destination not in ('default', '0.0.0.0'):
                continue
            if re.match(r'^[0-9]+(?:\.[0-9]+){3}$', gateway):
                return gateway
        return None

    def run(self):
        max_packet_loss_percent = self.get_threshold_var('max_packet_loss_percent', default=0, value_type='float')
        max_avg_rtt_ms = self.get_threshold_var('max_avg_rtt_ms', default=100, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        route_rc, route_out, route_err = self._run_check_command(ROUTE_COMMAND)

        if self._is_connection_error(route_rc, route_err):
            return self.fail(
                '호스트 연결 실패',
                message=(route_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(route_err or '').strip(),
            )

        if route_rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: netstat -rn 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(route_out or '').strip(),
                stderr=(route_err or '').strip(),
            )

        route_command_error = self._detect_command_error(
            route_out,
            route_err,
            extra_patterns=[
                'permission denied',
                'not supported',
                'unknown userland error',
                'no such file or directory',
                'cannot find',
                'not found',
                'name or service not known',
                'network is unreachable',
            ],
        )
        if route_command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: netstat -rn 출력에서 실행 오류가 확인되었습니다: {route_command_error}'
                ),
                stdout=(route_out or '').strip(),
                stderr=(route_err or '').strip(),
            )

        default_gateway = self._parse_default_gateway(route_out)
        if not default_gateway:
            return self.fail(
                '디폴트 라우트 없음',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: netstat -rn 출력에서 default route gateway를 찾지 못했습니다.',
                stdout=(route_out or '').strip(),
                stderr=(route_err or '').strip(),
            )

        ping_command = f'ping {default_gateway}'
        ping_rc, ping_out, ping_err = self._run_check_command(ping_command)

        if self._is_connection_error(ping_rc, ping_err):
            return self.fail(
                '호스트 연결 실패',
                message=(ping_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(ping_err or '').strip(),
            )

        if ping_rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: ping 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(ping_out or '').strip(),
                stderr=(ping_err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        combined_output = '\n'.join(part for part in ((route_out or '').strip(), (ping_out or '').strip(), (route_err or '').strip(), (ping_err or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '네트워크 실패 키워드 감지',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=combined_output,
                stderr='\n'.join(part for part in ((route_err or '').strip(), (ping_err or '').strip()) if part),
            )

        ping_command_error = self._detect_command_error(
            ping_out,
            ping_err,
            extra_patterns=[
                'permission denied',
                'not supported',
                'unknown userland error',
                'no such file or directory',
                'cannot find',
                'not found',
                'name or service not known',
                'network is unreachable',
            ],
        )
        if ping_command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: ping 출력에서 실행 오류가 확인되었습니다: {ping_command_error}'
                ),
                stdout=(ping_out or '').strip(),
                stderr=(ping_err or '').strip(),
            )

        parsed = self._parse_ping_output(ping_out)
        if not parsed:
            return self.fail(
                'ping 파싱 실패',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: ping 출력에서 손실률 또는 RTT 정보를 해석하지 못했습니다.',
                stdout=(ping_out or '').strip(),
                stderr=(ping_err or '').strip(),
            )

        metrics = {
            'default_gateway': default_gateway,
            'route_command': ROUTE_COMMAND,
            'ping_command': ping_command,
            'packets_transmitted': parsed['packets_transmitted'],
            'packets_received': parsed['packets_received'],
            'packet_loss_percent': parsed['packet_loss_percent'],
            'rtt_min_ms': parsed['rtt_min_ms'],
            'rtt_avg_ms': parsed['rtt_avg_ms'],
            'rtt_max_ms': parsed['rtt_max_ms'],
            'is_alive': parsed['is_alive'],
            'no_answer': parsed['no_answer'],
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'max_packet_loss_percent': max_packet_loss_percent,
            'max_avg_rtt_ms': max_avg_rtt_ms,
            'failure_keywords': failure_keywords,
        }

        if parsed['packet_loss_percent'] > max_packet_loss_percent:
            return self.fail(
                '패킷 손실률 기준 초과',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: 패킷 손실률 {parsed["packet_loss_percent"]:.2f}% '
                    f'(기준 {max_packet_loss_percent:.2f}% 이하), '
                    f'전송 {parsed["packets_transmitted"]}건, 수신 {parsed["packets_received"]}건입니다.'
                ),
                stdout=(ping_out or '').strip(),
                stderr=(ping_err or '').strip(),
            )

        if parsed['rtt_avg_ms'] is not None and parsed['rtt_avg_ms'] > max_avg_rtt_ms:
            return self.fail(
                '평균 RTT 기준 초과',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: 평균 RTT {parsed["rtt_avg_ms"]:.2f}ms '
                    f'(기준 {max_avg_rtt_ms:.2f}ms 이하), '
                    f'RTT min/avg/max {parsed["rtt_min_ms"]:.1f}/{parsed["rtt_avg_ms"]:.1f}/{parsed["rtt_max_ms"]:.1f}ms입니다.'
                ),
                stdout=(ping_out or '').strip(),
                stderr=(ping_err or '').strip(),
            )

        if parsed['rtt_avg_ms'] is None:
            rtt_message = 'RTT 정보 없음'
        else:
            rtt_message = f'RTT min/avg/max {parsed["rtt_min_ms"]:.1f}/{parsed["rtt_avg_ms"]:.1f}/{parsed["rtt_max_ms"]:.1f}ms'

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'default gateway {default_gateway} ping 응답이 정상이고 패킷 손실률이 {max_packet_loss_percent:.2f}% 이하입니다.'
            ),
            message=(
                'Solaris Network 통신 상태가 정상입니다. '
                f'현재 상태: default gateway {default_gateway} 대상으로 ping 성공, 패킷 손실률 {parsed["packet_loss_percent"]:.2f}% '
                f'(기준 {max_packet_loss_percent:.2f}% 이하), '
                f'전송 {parsed["packets_transmitted"]}건, 수신 {parsed["packets_received"]}건, '
                f'{rtt_message}.'
            ),
        )


CHECK_CLASS = Check
