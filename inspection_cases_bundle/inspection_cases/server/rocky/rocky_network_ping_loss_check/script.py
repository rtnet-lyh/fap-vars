# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


DEFAULT_PING_COUNT = 10
DEFAULT_PING_TARGET = '8.8.8.8'
DEFAULT_MAX_PING_LOSS_PERCENT = 0.0
PING_SUMMARY_PATTERN = re.compile(
    r'(?P<sent>\d+)\s+packets transmitted,\s+'
    r'(?P<received>\d+)(?:\s+packets)? received,.*?'
    r'(?P<loss>\d+(?:\.\d+)?)%\s+packet loss',
    re.IGNORECASE,
)
PING_HEADER_PATTERN = re.compile(
    r'^PING\s+(?P<label>\S+)\s+\((?P<resolved>[^\)]+)\)',
    re.IGNORECASE,
)
PING_REPLY_PATTERN = re.compile(
    r'^\d+\s+bytes from\s+(?P<source>[^:]+):.*?\btime=(?P<time_ms>\d+(?:\.\d+)?)\s*ms\b',
    re.IGNORECASE,
)
PING_RTT_PATTERN = re.compile(
    r'^rtt min/avg/max/(?:mdev|stddev)\s*=\s*'
    r'(?P<min>\d+(?:\.\d+)?)/'
    r'(?P<avg>\d+(?:\.\d+)?)/'
    r'(?P<max>\d+(?:\.\d+)?)/'
    r'(?P<mdev>\d+(?:\.\d+)?)\s*ms$',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _build_ping_command(self, ping_count, ping_target):
        return f'ping -c {ping_count} {shlex.quote(ping_target)}'

    def _parse_ping_output(self, stdout):
        lines = [
            line.strip()
            for line in (stdout or '').splitlines()
            if line.strip()
        ]
        if not lines:
            raise ValueError('ping 출력이 비어 있습니다.')

        summary_match = None
        resolved_target = ''
        header_target = ''
        reply_sources = []
        reply_times_ms = []
        rtt = {}

        for line in lines:
            header_match = PING_HEADER_PATTERN.match(line)
            if header_match and not resolved_target:
                header_target = header_match.group('label').strip()
                resolved_target = header_match.group('resolved').strip()
                continue

            reply_match = PING_REPLY_PATTERN.match(line)
            if reply_match:
                reply_sources.append(reply_match.group('source').strip())
                reply_times_ms.append(float(reply_match.group('time_ms')))
                continue

            current_summary_match = PING_SUMMARY_PATTERN.search(line)
            if current_summary_match:
                summary_match = current_summary_match
                continue

            rtt_match = PING_RTT_PATTERN.match(line)
            if rtt_match:
                rtt = {
                    'rtt_min_ms': float(rtt_match.group('min')),
                    'rtt_avg_ms': float(rtt_match.group('avg')),
                    'rtt_max_ms': float(rtt_match.group('max')),
                    'rtt_mdev_ms': float(rtt_match.group('mdev')),
                }

        if summary_match is None:
            raise ValueError('ping 출력에서 packet loss 요약 라인을 찾지 못했습니다.')

        sent_count = int(summary_match.group('sent'))
        received_count = int(summary_match.group('received'))
        loss_percent = float(summary_match.group('loss'))

        return {
            'sent_count': sent_count,
            'received_count': received_count,
            'loss_percent': loss_percent,
            'response_received': received_count > 0,
            'reply_count': len(reply_sources),
            'reply_sources': reply_sources,
            'reply_times_ms': reply_times_ms,
            'configured_target_from_header': header_target,
            'resolved_target': resolved_target,
            **rtt,
        }

    def run(self):
        ping_count = self.get_threshold_var(
            'ping_count',
            default=DEFAULT_PING_COUNT,
            value_type='int',
        )
        ping_target = str(
            self.get_threshold_var(
                'ping_target',
                default=DEFAULT_PING_TARGET,
                value_type='str',
            ) or ''
        ).strip()
        max_ping_loss_percent = self.get_threshold_var(
            'max_ping_loss_percent',
            default=DEFAULT_MAX_PING_LOSS_PERCENT,
            value_type='float',
        )

        if ping_count <= 0:
            return self.fail(
                '임계치 설정 오류',
                message='ping_count 는 1 이상의 정수여야 합니다.',
            )

        if not ping_target:
            return self.fail(
                '임계치 설정 오류',
                message='ping_target 이 비어 있습니다.',
            )

        command = self._build_ping_command(ping_count, ping_target)
        rc, out, err = self._ssh(command)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='ping 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            parsed = self._parse_ping_output(out)
        except ValueError as exc:
            return self.fail(
                'Ping Loss 파싱 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        metrics = {
            'command': command,
            'target': ping_target,
            **parsed,
        }
        thresholds = {
            'ping_count': ping_count,
            'ping_target': ping_target,
            'max_ping_loss_percent': max_ping_loss_percent,
        }

        loss_percent = parsed['loss_percent']
        received_count = parsed['received_count']
        sent_count = parsed['sent_count']

        if loss_percent > max_ping_loss_percent or received_count == 0:
            reasons = (
                'Ping 손실률이 임계치를 초과했거나 응답이 수신되지 않았습니다. '
                f'target={ping_target}, sent={sent_count}, received={received_count}, '
                f'loss={loss_percent}%, max={max_ping_loss_percent}%'
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=reasons,
                message='Ping Loss 추가 확인 필요',
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                'Ping 응답이 정상 수신되었고 손실률이 임계치 이하입니다. '
                f'target={ping_target}, sent={sent_count}, received={received_count}, '
                f'loss={loss_percent}%'
            ),
            message='Ping Loss 점검 정상',
        )


CHECK_CLASS = Check
