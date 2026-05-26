# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


SGA_COMMAND = """echo "=====Physical Memory====="
PHYS_MEM=$(prtconf | awk '/Memory size:/ {printf "%.0f\\n", $3/1024}')
echo "${PHYS_MEM} GB"
echo ""
echo "=====Oracle SGA Parameter====="
echo "
show parameter sga
exit;
" | sqlplus -S / as sysdba"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _size_to_gb(self, value):
        match = re.match(r'^(\d+(?:\.\d+)?)([KMGT])$', str(value or '').strip(), flags=re.I)
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2).upper()
        factors = {'K': 1.0 / (1024 * 1024), 'M': 1.0 / 1024, 'G': 1.0, 'T': 1024.0}
        return amount * factors[unit]

    def _parse_sga(self, text):
        memory_match = re.search(r'(?m)^\s*(\d+(?:\.\d+)?)\s+GB\s*$', str(text or ''))
        values = {}
        for line in str(text or '').splitlines():
            parts = line.split()
            if parts and parts[0] in ('sga_target', 'sga_max_size') and len(parts) >= 3:
                values[parts[0]] = parts[-1]
        if not memory_match or 'sga_target' not in values or 'sga_max_size' not in values:
            return None
        physical_memory_gb = float(memory_match.group(1))
        sga_target_gb = self._size_to_gb(values['sga_target'])
        sga_max_gb = self._size_to_gb(values['sga_max_size'])
        if not physical_memory_gb or sga_target_gb is None or sga_max_gb is None:
            return None
        return {
            'physical_memory_gb': physical_memory_gb,
            'sga_target': values['sga_target'],
            'sga_target_gb': round(sga_target_gb, 3),
            'sga_target_usage_ratio': round(sga_target_gb / physical_memory_gb * 100, 2),
            'sga_max_size': values['sga_max_size'],
            'sga_max_size_gb': round(sga_max_gb, 3),
            'sga_max_usage_ratio': round(sga_max_gb / physical_memory_gb * 100, 2),
        }

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        sga_target_limit = self.get_threshold_var('sga_target_usage_ratio', default=70, value_type='float')
        sga_max_limit = self.get_threshold_var('sga_max_usage_ratio', default=70, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': SGA_COMMAND, 'timeout': 30}],
            )[0]
        except ValueError as exc:
            return self.fail('Oracle 계정 전환 설정 오류', message=str(exc))

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        switch = getattr(self, '_solaris_last_account_switch_verification', {}) or {}
        if self._is_connection_error(result.get('rc'), stderr):
            return self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if not switch.get('ok'):
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=stderr)
        if result.get('rc') != 0:
            return self.fail('SGA 파라미터 명령 실행 실패', message='물리 메모리와 SGA 파라미터 출력을 수집하지 못했습니다.', stdout=stdout, stderr=stderr)

        metrics = self._parse_sga(stdout)
        if not metrics:
            return self.fail('SGA 파라미터 출력 파싱 실패', message='물리 메모리, sga_target, sga_max_size 값을 해석하지 못했습니다.', stdout=stdout, stderr=stderr)
        metrics.update({
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
        })
        thresholds = {
            'oracle_account': oracle_account,
            'sga_target_usage_ratio': sga_target_limit,
            'sga_max_usage_ratio': sga_max_limit,
        }
        if metrics['sga_target_usage_ratio'] > sga_target_limit or metrics['sga_max_usage_ratio'] > sga_max_limit:
            return self.fail(
                'SGA 물리 메모리 비율 임계치 초과',
                metrics=metrics,
                thresholds=thresholds,
                message='SGA 물리 메모리 사용 비율이 기준을 초과했습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='sga_target와 sga_max_size 물리 메모리 비율이 기준 이하입니다.',
            message='Oracle SGA 파라미터 점검 정상',
        )


CHECK_CLASS = Check
