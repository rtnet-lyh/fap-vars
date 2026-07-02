# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CPU_CORE_COMMAND = "wmic path Win32_Processor get DeviceID,Status,Availability,CpuStatus,NumberOfCores,NumberOfLogicalProcessors /value"


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
        min_socket_count = self.get_threshold_var('min_socket_count', default=1, value_type='int')
        min_total_core_count = self.get_threshold_var('min_total_core_count', default=4, value_type='int')
        min_total_logical_processor_count = self.get_threshold_var('min_total_logical_processor_count', default=8, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(CPU_CORE_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows CPU 코어 상태 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows CPU 코어 상태 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('CPU 코어 정보 없음', message='CPU 코어 상태 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('CPU 점검 실패 키워드 감지', message='CPU 코어 상태 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        processors = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    processors.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            processors.append(current)

        if not processors:
            return self.fail('CPU 코어 정보 파싱 실패', message='CPU 코어 상태 결과를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        parsed_processors = []
        for processor in processors:
            try:
                core_count = int(processor.get('NumberOfCores', '0') or '0')
                logical_processor_count = int(processor.get('NumberOfLogicalProcessors', '0') or '0')
            except ValueError:
                continue
            parsed_processors.append({
                'name': processor.get('DeviceID', ''),
                'socket_designation': processor.get('DeviceID', ''),
                'manufacturer': '',
                'max_clock_speed_mhz': 0,
                'number_of_cores': core_count,
                'number_of_logical_processors': logical_processor_count,
                'threads_per_core': round(logical_processor_count / core_count, 2) if core_count > 0 else 0.0,
                'status': processor.get('Status', ''),
                'availability': processor.get('Availability', ''),
                'cpu_status': processor.get('CpuStatus', ''),
            })

        if not parsed_processors:
            return self.fail('CPU 코어 정보 파싱 실패', message='CPU 코어 수 또는 논리 프로세서 수를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        socket_count = len(parsed_processors)
        total_core_count = sum(p['number_of_cores'] for p in parsed_processors)
        total_logical_processor_count = sum(p['number_of_logical_processors'] for p in parsed_processors)
        primary_processor = parsed_processors[0]

        metrics = {
            'socket_count': socket_count,
            'total_core_count': total_core_count,
            'total_logical_processor_count': total_logical_processor_count,
            'threads_per_core': primary_processor['threads_per_core'],
            'processor_name': primary_processor['name'],
            'socket_designation': primary_processor['socket_designation'],
            'manufacturer': primary_processor['manufacturer'],
            'max_clock_speed_mhz': 0,
            'processor_names': [p['name'] for p in parsed_processors],
            'socket_designations': [p['socket_designation'] for p in parsed_processors],
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            '최소 소켓 수': min_socket_count,
            '최소 전체 코어 수': min_total_core_count,
            '최소 전체 논리 프로세서 수': min_total_logical_processor_count,
            '실패 키워드': failure_keywords,
        }

        if socket_count < min_socket_count:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='물리 CPU 소켓 수가 기준치 미만입니다.', message=f'확인된 물리 CPU 소켓 수가 기준치 미만입니다. 기준치 {min_socket_count}개 이상 필요하지만 현재 {socket_count}개입니다.')
        if total_core_count < min_total_core_count:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='물리 CPU 코어 수가 기준치 미만입니다.', message=f'확인된 물리 CPU 코어 수가 기준치 미만입니다. 기준치 {min_total_core_count}개 이상 필요하지만 현재 {total_core_count}개입니다.')
        if total_logical_processor_count < min_total_logical_processor_count:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='논리 CPU 수가 기준치 미만입니다.', message=f'확인된 논리 CPU 수가 기준치 미만입니다. 기준치 {min_total_logical_processor_count}개 이상 필요하지만 현재 {total_logical_processor_count}개입니다.')

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'CPU="{primary_processor["name"]}", 소켓 {socket_count}개 (기준 {min_socket_count}개 이상), '
                f'물리 코어 {total_core_count}개 (기준 {min_total_core_count}개 이상), '
                f'논리 프로세서 {total_logical_processor_count}개 (기준 {min_total_logical_processor_count}개 이상).'
            ),
            message='물리 CPU 소켓 수, 물리 코어 수, 논리 프로세서 수가 모두 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
