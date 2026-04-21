# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PING_COMMAND = 'ping 8.8.8.8'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_ping_output(self, text):
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

        if not transmitted_match:
            return None

        parsed = {
            'packets_transmitted': int(transmitted_match.group(1)),
            'packets_received': int(transmitted_match.group(2)),
            'packet_loss_percent': float(transmitted_match.group(3)),
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

    def run(self):
        max_packet_loss_percent = self.get_threshold_var('max_packet_loss_percent', default=0, value_type='float')
        max_avg_rtt_ms = self.get_threshold_var('max_avg_rtt_ms', default=100, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(PING_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: ping 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
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
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: ping 출력에서 실행 오류가 확인되었습니다: {command_error}'
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
                '네트워크 실패 키워드 감지',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = self._parse_ping_output(out)
        if not parsed:
            return self.fail(
                'ping 파싱 실패',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: ping 출력에서 손실률 또는 RTT 정보를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        metrics = {
            'packets_transmitted': parsed['packets_transmitted'],
            'packets_received': parsed['packets_received'],
            'packet_loss_percent': parsed['packet_loss_percent'],
            'rtt_min_ms': parsed['rtt_min_ms'],
            'rtt_avg_ms': parsed['rtt_avg_ms'],
            'rtt_max_ms': parsed['rtt_max_ms'],
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
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if parsed['rtt_avg_ms'] is None:
            return self.fail(
                'RTT 정보 없음',
                message='Solaris Network 통신 상태 점검에 실패했습니다. 현재 상태: round-trip RTT 정보를 확인하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if parsed['rtt_avg_ms'] > max_avg_rtt_ms:
            return self.fail(
                '평균 RTT 기준 초과',
                message=(
                    'Solaris Network 통신 상태 점검에 실패했습니다. '
                    f'현재 상태: 평균 RTT {parsed["rtt_avg_ms"]:.2f}ms '
                    f'(기준 {max_avg_rtt_ms:.2f}ms 이하), '
                    f'RTT min/avg/max {parsed["rtt_min_ms"]:.1f}/{parsed["rtt_avg_ms"]:.1f}/{parsed["rtt_max_ms"]:.1f}ms입니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'패킷 손실률이 {max_packet_loss_percent:.2f}% 이하이고 '
                f'평균 RTT가 {max_avg_rtt_ms:.2f}ms 이하입니다.'
            ),
            message=(
                'Solaris Network 통신 상태가 정상입니다. '
                f'현재 상태: 패킷 손실률 {parsed["packet_loss_percent"]:.2f}% '
                f'(기준 {max_packet_loss_percent:.2f}% 이하), '
                f'전송 {parsed["packets_transmitted"]}건, 수신 {parsed["packets_received"]}건, '
                f'RTT min/avg/max {parsed["rtt_min_ms"]:.1f}/{parsed["rtt_avg_ms"]:.1f}/{parsed["rtt_max_ms"]:.1f}ms, '
                f'평균 RTT 기준 {max_avg_rtt_ms:.2f}ms 이하 충족.'
            ),
        )


CHECK_CLASS = Check
