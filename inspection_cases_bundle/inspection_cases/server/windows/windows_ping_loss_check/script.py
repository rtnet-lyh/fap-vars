# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


NETWORK_GATEWAY_PING_COMMAND = (
    'ping -n 10 ((Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" | '
    'Sort-Object RouteMetric,InterfaceMetric | Select-Object -First 1).NextHop)'
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_loss_percent = self.get_threshold_var('max_loss_percent', default=0, value_type='int')
        max_average_time_ms = self.get_threshold_var('max_average_time_ms', default=50, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(NETWORK_GATEWAY_PING_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 기본 게이트웨이 Ping 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'Ping 결과 없음',
                message='기본 게이트웨이 Ping 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '게이트웨이 Ping 실패 키워드 감지',
                message='기본 게이트웨이 Ping 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        target_match = re.search(r'Ping\s+([0-9.]+)\s+\S+', text)
        packet_match = re.search(
            r'보냄\s*=\s*(\d+),\s*받음\s*=\s*(\d+),\s*손실\s*=\s*(\d+)\s*\((\d+)%\s*손실\)',
            text,
        )
        rtt_match = re.search(
            r'최소\s*=\s*(\d+)ms,\s*최대\s*=\s*(\d+)ms,\s*평균\s*=\s*(\d+)ms',
            text,
        )

        if not packet_match:
            return self.fail(
                'Ping 통계 파싱 실패',
                message='패킷 송수신 및 손실 통계를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        sent = _parse_int(packet_match.group(1))
        received = _parse_int(packet_match.group(2))
        lost = _parse_int(packet_match.group(3))
        loss_percent = _parse_int(packet_match.group(4))

        min_rtt = ''
        max_rtt = ''
        avg_rtt = ''
        if rtt_match:
            min_rtt = _parse_int(rtt_match.group(1))
            max_rtt = _parse_int(rtt_match.group(2))
            avg_rtt = _parse_int(rtt_match.group(3))

        if loss_percent > max_loss_percent:
            return self.fail(
                '기본 게이트웨이 Ping 손실 감지',
                message='기본 게이트웨이 Ping 손실률이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if avg_rtt != '' and avg_rtt > max_average_time_ms:
            return self.fail(
                '기본 게이트웨이 Ping 지연 초과',
                message='기본 게이트웨이 Ping 평균 응답 시간이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        reasons = '기본 라우터로의 Ping 결과에서 패킷 손실이 없고 응답 시간이 기준 범위 내입니다.'

        return self.ok(
            metrics={
                'target_gateway': target_match.group(1) if target_match else '',
                'sent_packets': sent,
                'received_packets': received,
                'lost_packets': lost,
                'loss_percent': loss_percent,
                'minimum_time_ms': min_rtt,
                'maximum_time_ms': max_rtt,
                'average_time_ms': avg_rtt,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_loss_percent': max_loss_percent,
                'max_average_time_ms': max_average_time_ms,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message='Windows 기본 게이트웨이 Ping 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
