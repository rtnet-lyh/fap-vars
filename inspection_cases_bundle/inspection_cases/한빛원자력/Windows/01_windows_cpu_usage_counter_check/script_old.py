# -*- coding: utf-8 -*-

import csv
import io

from items.common._base import BaseCheck


TYPEPERF_COMMAND = "powershell.exe -NoProfile -Command \"$paths = @('\\Processor(_Total)\\% User Time', '\\Processor(_Total)\\% Privileged Time','\\Processor(_Total)\\% Idle Time', '\\Processor(_Total)\\% Interrupt Time'); $data = Get-Counter -Counter $paths -SampleInterval 1 -MaxSamples 3; $data.CounterSamples | Group-Object Path | ForEach-Object { $avg = ($_.Group | Measure-Object -Property CookedValue -Average).Average; $counter = [regex]::Match($_.Name, '% .*time$', 'IgnoreCase').Value.ToLower(); switch ($counter) { '% user time' { $name = 'User' } '% privileged time' { $name = 'Privileged' } '% idle time' { $name = 'Idle' } '% interrupt time' { $name = 'Interrupt' } default { $name = $_.Name } }; '{0}={1:N2}' -f $name, $avg }\"\n"


def _parse_percent(value):
    return round(float(value), 2)



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
        max_usr_sys_percent = self.get_threshold_var('max_usr_sys_percent', default=80.0, value_type='float')
        min_idle_percent = self.get_threshold_var('min_idle_percent', default=20.0, value_type='float')
        max_interrupt_percent = self.get_threshold_var('max_interrupt_percent', default=5.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(TYPEPERF_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows CPU 사용률 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows CPU 사용률 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('CPU 사용률 정보 없음', message='CPU 사용률 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('CPU 점검 실패 키워드 감지', message='CPU 사용률 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        values = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            try:
                values[key.strip().lower()] = round(float(value.strip()), 2)
            except ValueError:
                continue

        if not {'user', 'privileged', 'idle', 'interrupt'}.issubset(values):
            return self.fail('CPU 통계 파싱 실패', message='CPU 사용률 key=value 결과를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        avg_user_percent = values['user']
        avg_privileged_percent = values['privileged']
        avg_idle_percent = values['idle']
        avg_interrupt_percent = values['interrupt']
        avg_usr_sys_percent = round(avg_user_percent + avg_privileged_percent, 2)

        if avg_usr_sys_percent >= max_usr_sys_percent:
            return self.fail('CPU 사용률 임계치 초과', message='사용자+시스템 CPU 사용률 평균이 기준치를 초과했습니다.', stdout=text, stderr=(err or '').strip())
        if avg_idle_percent < min_idle_percent:
            return self.fail('CPU 유휴율 임계치 미달', message='CPU idle 비율 평균이 기준치 미만입니다.', stdout=text, stderr=(err or '').strip())
        if avg_interrupt_percent >= max_interrupt_percent:
            return self.fail('CPU 인터럽트 처리 비율 임계치 초과', message='Interrupt Time 평균이 기준치를 초과했습니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'sample_count': 1,
                'host_name': '',
                'avg_user_percent': avg_user_percent,
                'avg_privileged_percent': avg_privileged_percent,
                'avg_usr_sys_percent': avg_usr_sys_percent,
                'avg_idle_percent': avg_idle_percent,
                'avg_interrupt_percent': avg_interrupt_percent,
                'max_usr_sys_percent': avg_usr_sys_percent,
                'max_usr_sys_timestamp': '',
                'max_interrupt_percent': avg_interrupt_percent,
                'max_interrupt_timestamp': '',
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '최대 사용자 시스템 사용률': max_usr_sys_percent,
                '최소 유휴율': min_idle_percent,
                '최대 인터럽트 사용률': max_interrupt_percent,
                '실패 키워드': failure_keywords,
            },
            reasons=(
                f'User {avg_user_percent:.2f}%, Privileged {avg_privileged_percent:.2f}%, '
                f'User+System {avg_usr_sys_percent:.2f}% (기준 {max_usr_sys_percent:.2f}% 이하), '
                f'Idle {avg_idle_percent:.2f}% (기준 {min_idle_percent:.2f}% 이상), '
                f'Interrupt {avg_interrupt_percent:.2f}% (기준 {max_interrupt_percent:.2f}% 이하).'
            ),
            message='Windows CPU 사용률, 유휴율, 인터럽트 처리 시간이 모두 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
