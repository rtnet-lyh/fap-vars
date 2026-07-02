# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


NETWORK_GATEWAY_PING_COMMAND = "powershell.exe -NoProfile -Command \"$gw = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1 -ExpandProperty NextHop); if (-not $gw) { 'NO_DEFAULT_GATEWAY'; exit 0 }; ping -n 5 $gw\"\n"


def _parse_int(value):
    return int(str(value).strip())



def _prepare_windows_command(command):
    text = (command or '').strip()
    prefixes = (
        'powershell.exe -NoProfile -Command ',
        'powershell -Command ',
    )
    for prefix in prefixes:
        if text.startswith(prefix):
            payload = text[len(prefix):].strip()
            if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in ('"', "'"):
                payload = payload[1:-1]
            payload = payload.replace('\\"', '"')
            payload = payload.replace("\\'", "'")
            return payload
    return text

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'



    def parse_output(self, legacy_result):
        metrics = dict(legacy_result.get("metrics") or {})
        metrics["_legacy_result"] = legacy_result
        return metrics

    def evaluate(self, metrics):
        legacy_result = metrics.get("_legacy_result", {})
        status = str(legacy_result.get("status", "fail")).strip().lower()
        if status in ("ok", "warn", "fail", "excluded"):
            return status
        return "fail"

    def build_result(self, metrics, status):
        legacy_result = metrics.get("_legacy_result", {})
        final_metrics = dict(metrics)
        final_metrics.pop("_legacy_result", None)

        thresholds = legacy_result.get("thresholds", {})
        results_text = legacy_result.get("results")
        if not results_text:
            results_text = legacy_result.get("reasons", "")
        if not results_text:
            message_text = str(legacy_result.get("message") or "").strip()
            if "현재 상태:" in message_text:
                results_text = message_text.split("현재 상태:", 1)[1].strip()
            else:
                results_text = message_text
        if not results_text and final_metrics:
            parts = []
            for key, value in final_metrics.items():
                if value in (None, "", [], {}):
                    continue
                parts.append(f"{key}={value}")
            results_text = ", ".join(parts)

        criteria_text = legacy_result.get("criteria")
        if not criteria_text:
            if isinstance(thresholds, dict) and thresholds:
                criteria_text = ", ".join(
                    f"{key}={value}" for key, value in thresholds.items()
                )
            else:
                criteria_text = ""

        return {
            "message": legacy_result.get("message"),
            "results": results_text,
            "criteria": criteria_text,
            "error": legacy_result.get("error"),
            "raw_output": legacy_result.get("raw_output"),
            "stdout": legacy_result.get("stdout"),
            "stderr": legacy_result.get("stderr"),
            "metrics": final_metrics,
        }


    def run(self):
        legacy_result = self.execute_check()
        metrics = self.parse_output(legacy_result)
        status = self.evaluate(metrics)
        result = self.build_result(metrics, status)

        thresholds = result["criteria"] if isinstance(result["criteria"], dict) else {"criteria": result["criteria"]}

        if status == "ok":
            return self.ok(
                metrics=result["metrics"],
                thresholds=thresholds,
                reasons=result["results"],
                message=result["message"],
                results=result["results"],
                criteria=result["criteria"],
            )
        if status == "warn":
            return self.warn(
                metrics=result["metrics"],
                thresholds=thresholds,
                reasons=result["results"],
                message=result["message"],
                results=result["results"],
                criteria=result["criteria"],
            )
        if status == "excluded":
            return self.not_applicable(
                message=result["message"],
                raw_output=result.get("raw_output") or result["results"],
            )
        return self.fail(
            error=result.get("error") or result["message"],
            message=result["message"],
            metrics=result["metrics"],
            thresholds=thresholds,
            reasons=result["results"],
            raw_output=result.get("raw_output"),
            stdout=result.get("stdout"),
            stderr=result.get("stderr"),
            results=result["results"],
            criteria=result["criteria"],
        )


    def execute_check(self):
        max_loss_percent = self.get_threshold_var('max_loss_percent', default=0, value_type='int')
        max_average_time_ms = self.get_threshold_var('max_average_time_ms', default=50, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(NETWORK_GATEWAY_PING_COMMAND))

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 기본 게이트웨이 Ping 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
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

        target_match = re.search(r'Ping(?:ing)?\s+([0-9.]+)\b', text, re.IGNORECASE)
        packet_match = re.search(
            r'(?:보냄|Sent)\s*=\s*(\d+),\s*'
            r'(?:받음|Received)\s*=\s*(\d+),\s*'
            r'(?:손실|Lost)\s*=\s*(\d+)\s*'
            r'\((\d+)%\s*(?:손실|loss)\)',
            text,
            re.IGNORECASE,
        )
        rtt_match = re.search(
            r'(?:최소|Minimum)\s*=\s*(\d+)ms,\s*'
            r'(?:최대|Maximum)\s*=\s*(\d+)ms,\s*'
            r'(?:평균|Average)\s*=\s*(\d+)ms',
            text,
            re.IGNORECASE,
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
                '최대 손실률': max_loss_percent,
                '최대 평균 응답 시간 ms': max_average_time_ms,
                '실패 키워드': failure_keywords,
            },
            reasons=(
                f'Windows 기본 게이트웨이 Ping 점검이 정상입니다. 현재 상태: '
                f'gateway={target_match.group(1) if target_match else "unknown"}, '
                f'sent={sent}, received={received}, lost={lost} ({loss_percent}% 손실, 기준 {max_loss_percent}% 이하), '
                f'avg={avg_rtt if avg_rtt != "" else "N/A"}ms (기준 {max_average_time_ms}ms 이하).'
            ),
            message='기본 라우터로의 Ping 결과에서 패킷 손실이 없고 응답 시간이 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
