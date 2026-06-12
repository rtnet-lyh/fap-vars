# type_name

일상점검

# area_name

상태점검

# category_name

dbms

# application_type

oracle

# application

solaris

# inspection_code

DBMS-ORACLE-SOLARIS-REPLAY-014

# is_required

권고

# inspection_name

공유메모리(SGA) 파라미터 점검

# inspection_content

DB에 접속하는 모든 사용자가 공유해서 사용하는 메모리로 물리 메모리 대비 적절한 값으로 설정되어 있는지 점검

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- sga_target: 오라클 DB가 동적으로 사용할 메모리의 목표값을 나타냄. 시스템이 실제로 얼마나 많은 메모리를 SGA에 할당할 것인지를 결정하는 값임. 시스템의 물리 메모리와 비교하여, 이 값이 너무 낮으면 DB 성능에 영향을 미칠 수 있고, 너무 높으면 시스템의 다른 프로세스에 영향을 줄 수 있음. 따라서 물리 메모리와의 균형을 잘 맞추는 것이 중요함. 
- sga_max_size: SGA가 사용할 수 있는 최대 메모리 크기를 설정한 값임. sga_target 값은 이 sga_max_size 범위 내에서만 조정될 수 있음. SGA가 커질 수 있는 최대 크기를 제한하는 값이기 때문에, 시스템의 물리 메모리보다 너무 큰 값으로 설정되면 메모리 부족 문제(예: 스와핑)가 발생할 수 있음.

SGA Target Usage Ratio(%) = sga_target / OS 물리 메모리 = 물리 메모리 대비 Oracle SGA(sga_target) 비율
SGA Max Usage Ratio(%) = sga_max_size / OS 물리 메모리 = 물리 메모리 대비 Oracle SGA 최대 사용 가능 크기(sga_max_size) 비율
※ 비율이 임계치 이상일 경우 sga_max_size 및 sga_target 설정값 점검 필요

- **양호**: SGA Target Usage Ratio(%), SGA Max Usage Ratio(%)가 `sga_target_usage_ratio`, `sga_max_usage_ratio` 값을 넘지 않는 상태
- **경고**: SGA Target Usage Ratio(%), SGA Max Usage Ratio(%)가 `sga_target_usage_ratio`, `sga_max_usage_ratio` 값을 넘는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "sga_target_usage_ratio", value: "70", sortOrder: 1}
,
{id: null, key: "sga_max_usage_ratio", value: "70", sortOrder: 2}
]

# inspection_script

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
