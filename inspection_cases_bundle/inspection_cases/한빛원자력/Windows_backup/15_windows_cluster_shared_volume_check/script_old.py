# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CLUSTER_MOUNT_COMMAND = "powershell.exe -NoProfile -Command \"$cmd = Get-Command Get-ClusterSharedVolume -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-ClusterSharedVolume unavailable'; exit 0 }; $csvs = Get-ClusterSharedVolume; if (-not $csvs) { 'NOT_APPLICABLE=No cluster shared volume'; exit 0 }; foreach ($csv in $csvs) { 'Name=' + $csv.Name; 'State=' + $csv.State; 'Path=' + $csv.SharedVolumeInfo.FriendlyVolumeName; '' }\"\n"


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
        expected_mount_path = self.get_threshold_var('expected_mount_path', default='C:\\mnt\\shared\\', value_type='str')
        expected_mode = self.get_threshold_var('expected_mode', default='rw', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(CLUSTER_MOUNT_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        stderr_text = (err or '').strip()

        if self._is_not_applicable(rc, err) or text.startswith('NOT_APPLICABLE='):
            return self.not_applicable(message='클러스터 공유 볼륨이 없거나 관련 cmdlet이 없어 점검에서 제외합니다.', raw_output=text or stderr_text)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 클러스터 공유 볼륨 점검 명령 실행에 실패했습니다.', stdout=text, stderr=stderr_text)

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('공유 볼륨 실패 키워드 감지', message='공유 볼륨 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=stderr_text)

        entries = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            entries.append(current)

        if not entries:
            return self.fail('공유 볼륨 마운트 파싱 실패', message='공유 볼륨 마운트 정보를 해석하지 못했습니다.', stdout=text, stderr=stderr_text)

        first = entries[0]
        mount_path = first.get('Path', '')
        state = first.get('State', '')
        csv_count = len(entries)

        if expected_mount_path and expected_mount_path.lower() not in mount_path.lower():
            return self.warn(
                metrics={
                    'csv_count': csv_count,
                    'mount_path': mount_path,
                    'state': state,
                    'entries': entries,
                    'matched_failure_keywords': matched_failure_keywords,
                },
                thresholds={
                    '기대 마운트 경로': expected_mount_path,
                    '기대 마운트 모드': expected_mode,
                    '실패 키워드': failure_keywords,
                },
                reasons=(
                    f'공유 볼륨 경로가 기대 경로와 다릅니다. '
                    f'현재 상태: 볼륨 {csv_count}개, 첫 경로 {mount_path}, 상태 {state}, '
                    f'기대 경로 {expected_mount_path}.'
                ),
                message='공유 볼륨 경로가 기대 경로와 다릅니다.',
            )

        if state.lower() not in ('online', 'ok'):
            return self.fail('공유 볼륨 상태 이상', message='공유 볼륨 상태가 Online이 아닙니다.', stdout=text, stderr=stderr_text)

        return self.ok(
            metrics={
                'csv_count': csv_count,
                'mount_path': mount_path,
                'state': state,
                'entries': entries,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '기대 마운트 경로': expected_mount_path,
                '기대 마운트 모드': expected_mode,
                '실패 키워드': failure_keywords,
            },
            reasons=(
                f'공유 볼륨이 정상 상태입니다. '
                f'현재 상태: 볼륨 {csv_count}개, 첫 경로 {mount_path}, 상태 {state}.'
            ),
            message='Windows 클러스터 공유 볼륨 상태가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check