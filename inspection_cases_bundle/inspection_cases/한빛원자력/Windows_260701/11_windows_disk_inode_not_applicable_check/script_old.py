# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


DISK_INODE_COMMAND = "powershell -Command \"Get-Volume | Where-Object DriveLetter | ForEach-Object { fsutil dirty query ($_.DriveLetter + ':') }\""


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
        max_iuse_percent = self.get_threshold_var('max_iuse_percent', default=80.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(DISK_INODE_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                message='Windows 볼륨의 inode 사용률은 직접 제공되지 않아 점검에서 제외합니다.',
                raw_output=(out or err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows inode 근사 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()

        if not text:
            return self.not_applicable(
                message='Windows inode 사용률 점검 결과가 비어 있어 제외합니다.',
                raw_output='',
            )

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail(
                'inode 점검 실패 키워드 감지',
                message='inode 점검 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        dirty_volumes = [line for line in lines if 'is dirty' in line.lower()]

        volume_count = len(lines)
        dirty_volume_count = len(dirty_volumes)
        current_iuse_percent = 100.0 if dirty_volumes else 0.0

        if dirty_volumes:
            return self.fail(
                '볼륨 Dirty 상태 감지',
                message='Dirty 상태의 볼륨이 확인되었습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics={
                'volume_count': volume_count,
                'dirty_volume_count': dirty_volume_count,
                'dirty_volumes': dirty_volumes,
                'current_iuse_percent': current_iuse_percent,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '최대 inode 사용률': max_iuse_percent,
                '실패 키워드': failure_keywords,
            },
            reasons=f'Windows 볼륨 dirty 상태 점검이 정상입니다. 현재 상태: 전체 볼륨 {volume_count}개, Dirty 볼륨 {dirty_volume_count}개 (기준 inode 근사 사용률 {max_iuse_percent:.2f}% 이하).',
            message='모든 볼륨이 NOT Dirty 상태입니다.',
        )


CHECK_CLASS = Check