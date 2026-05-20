# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

COMMAND = "tail -50 $(ls -t {admin_log_path}/*.log | head -1)"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, admin_log_path):

        command = COMMAND.format(admin_log_path=admin_log_path)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        return stdout, stderr, None

    FINDING_LABEL = 'HTTP 400/500대 오류'

    def _parse_access_log(self, output: str, bad_status_bands: list[int]):
        results = []

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            match = re.search(r'"[^"]+"\s+(\d{3})\s+', line)
            if not match:
                continue

            status_code = int(match.group(1))
            status_band = status_code // 100

            is_bad = status_band in bad_status_bands

            results.append({
                "status_code": status_code,
                "status_band": f"{status_band}xx",
                "is_bad": is_bad,
                "line": line,
            })

        return results

    def run(self):
        admin_log_path = self.get_threshold_var(
            key='admin_log_path',
            default='/home/exTMS/tmax/jeus/log/adminServer/servlet',
            value_type='str',
        )

        bad_status_bands = self.get_threshold_var(
            key='bad_status_bands', 
            default='4,5', 
            value_type='str'
        )

        bad_status_bands = re.split(r'[,|]+', bad_status_bands)
        bad_status_bands = [int(band) for band in bad_status_bands]                

        stdout, _stderr, error = self._run_jeus_command(admin_log_path)

        ok_items = []
        fail_items = []
        metrics = {}
        thresholds = {}

        if error:
            return error
        
        results = self._parse_access_log(stdout, bad_status_bands)

        if results:
            metrics = {
                "results": results
            }

            ok_items = [item for item in results if not item["is_bad"]]
            bad_items = [item for item in results if item["is_bad"]]

        is_pass = True if not bad_items else False

        thresholds = {
            'bad_status_bands': bad_status_bands, 
            'admin_log_path': admin_log_path
        }

        if is_pass:
            return self.ok(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons=f"HTTP Staud Code에 {bad_status_bands}가 존재하지 않습니다.", 
                message=f"HTTP Staud Code에 {bad_status_bands}가 존재하지 않습니다.", 
            )
        else:    
            return self.warn(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons=f"HTTP Staud Code에 {bad_status_bands}가 존재합니다.", 
                message=f"HTTP Staud Code에 {bad_status_bands}가 존재합니다.", 
            )


CHECK_CLASS = Check
