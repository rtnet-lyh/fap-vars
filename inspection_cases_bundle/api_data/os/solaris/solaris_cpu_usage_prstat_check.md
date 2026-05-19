# type_name

일상점검(상태점검)

# area_name

서버

# category_name

CPU

# application_type

UNIX

# application

solaris

# inspection_code

SVR-1-1

# is_required

필수

# inspection_name

CPU 사용률

# inspection_content

Solaris 서버의 시스템 전체 CPU 사용률과 상위 프로세스 CPU 사용률을 함께 점검합니다.

# inspection_command

```bash
prstat 1
```

# inspection_output

```text
PID USERNAME SIZE  RSS   STATE PRI NICE TIME      CPU   STIME %MEM %CPU COMMAND
12345 user1  1024M 512M  R     10  0    00:00:01 90.0  11:00 2.0  0.0  myprocess
12346 user2  2048M 1024M S     20  0    00:00:02 0.0   12:00 3.0  0.1  anotherprocess
```

# description

- `%CPU`는 개별 프로세스 기준 0~5%, 시스템 전체 기준 70% 이하를 권장.
  - 사용률이 과도하면 해당 프로세스 성능 검토가 필요.
  - `mpstat` 명령어도 보조적으로 사용 가능.

# thresholds

[
    {id: null, key: "max_cpu_usage_percent", value: "70", sortOrder: 0}
,
{id: null, key: "max_process_cpu_percent", value: "5", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PRSTAT_CPU_COMMAND = 'prstat 1 1'
MPSTAT_CPU_COMMAND = 'mpstat 1 1'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_number(self, value):
        try:
            return float(str(value).strip().rstrip('%'))
        except (TypeError, ValueError):
            return None

    def _parse_prstat_top_process(self, text):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        header = None

        for line in lines:
            tokens = re.split(r'\s+', line)
            lowered = [token.lower() for token in tokens]
            if 'pid' in lowered and ('cpu' in lowered or '%cpu' in lowered):
                header = lowered
                break

        if not header:
            return None

        cpu_index = header.index('%cpu') if '%cpu' in header else header.index('cpu')
        pid_index = header.index('pid') if 'pid' in header else 0
        user_index = header.index('username') if 'username' in header else None
        process_index = None
        for column_name in ('process/nlwp', 'command', 'process'):
            if column_name in header:
                process_index = header.index(column_name)
                break

        process_entries = []
        for line in lines:
            if not re.match(r'^\d+\s+', line):
                continue
            tokens = re.split(r'\s+', line)
            if len(tokens) <= cpu_index:
                continue

            cpu_percent = self._parse_number(tokens[cpu_index])
            if cpu_percent is None:
                continue

            process_entries.append({
                'pid': tokens[pid_index] if len(tokens) > pid_index else '',
                'username': tokens[user_index] if user_index is not None and len(tokens) > user_index else '',
                'process_name': tokens[process_index] if process_index is not None and len(tokens) > process_index else tokens[-1],
                'cpu_percent': round(cpu_percent, 2),
            })

        if not process_entries:
            return None

        top_process = max(process_entries, key=lambda entry: entry['cpu_percent'])
        return {
            'top_process': top_process,
            'process_entries': process_entries,
        }

    def _parse_mpstat_cpu(self, text):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        header = None
        data_rows = []

        for line in lines:
            tokens = re.split(r'\s+', line)
            lowered = [token.lower() for token in tokens]
            if 'cpu' in lowered and 'idl' in lowered:
                header = lowered
                continue

            if not header or len(tokens) < len(header):
                continue

            cpu_id = tokens[0]
            if not re.match(r'^\d+$', cpu_id):
                continue

            data_rows.append(tokens)

        if not header or not data_rows:
            return None

        usr_index = header.index('usr') if 'usr' in header else None
        sys_index = header.index('sys') if 'sys' in header else None
        wt_index = header.index('wt') if 'wt' in header else None
        idl_index = header.index('idl')

        parsed_rows = []
        for row in data_rows:
            idle_percent = self._parse_number(row[idl_index]) if len(row) > idl_index else None
            user_percent = self._parse_number(row[usr_index]) if usr_index is not None and len(row) > usr_index else None
            system_percent = self._parse_number(row[sys_index]) if sys_index is not None and len(row) > sys_index else None
            wait_percent = self._parse_number(row[wt_index]) if wt_index is not None and len(row) > wt_index else None

            if idle_percent is None:
                continue

            parsed_rows.append({
                'cpu_id': row[0],
                'user_percent': round(user_percent or 0.0, 2),
                'system_percent': round(system_percent or 0.0, 2),
                'wait_percent': round(wait_percent or 0.0, 2),
                'idle_percent': round(idle_percent, 2),
                'cpu_usage_percent': round(100.0 - idle_percent, 2),
            })

        if not parsed_rows:
            return None

        count = float(len(parsed_rows))
        avg_user = round(sum(row['user_percent'] for row in parsed_rows) / count, 2)
        avg_system = round(sum(row['system_percent'] for row in parsed_rows) / count, 2)
        avg_wait = round(sum(row['wait_percent'] for row in parsed_rows) / count, 2)
        avg_idle = round(sum(row['idle_percent'] for row in parsed_rows) / count, 2)

        return {
            'cpu_row_count': len(parsed_rows),
            'user_percent': avg_user,
            'system_percent': avg_system,
            'wait_percent': avg_wait,
            'idle_percent': avg_idle,
            'cpu_usage_percent': round(100.0 - avg_idle, 2),
        }

    def run(self):
        max_cpu_usage_percent = self.get_threshold_var('max_cpu_usage_percent', default=70.0, value_type='float')
        max_process_cpu_percent = self.get_threshold_var('max_process_cpu_percent', default=5.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        prstat_rc, prstat_out, prstat_err = self._ssh(PRSTAT_CPU_COMMAND)

        if self._is_connection_error(prstat_rc, prstat_err):
            return self.fail(
                '호스트 연결 실패',
                message=(prstat_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(prstat_err or '').strip(),
            )

        if prstat_rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris CPU 사용률 점검 명령 실행에 실패했습니다. 현재 상태: prstat 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(prstat_out or '').strip(),
                stderr=(prstat_err or '').strip(),
            )

        prstat_command_error = self._detect_command_error(
            prstat_out,
            prstat_err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if prstat_command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris CPU 사용률 점검에 실패했습니다. '
                    f'현재 상태: prstat 출력에서 실행 오류가 확인되었습니다: {prstat_command_error}'
                ),
                stdout=(prstat_out or '').strip(),
                stderr=(prstat_err or '').strip(),
            )

        mpstat_rc, mpstat_out, mpstat_err = self._ssh(MPSTAT_CPU_COMMAND)

        if self._is_connection_error(mpstat_rc, mpstat_err):
            return self.fail(
                '호스트 연결 실패',
                message=(mpstat_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(mpstat_err or '').strip(),
            )

        if mpstat_rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris CPU 사용률 점검에 실패했습니다. '
                    '현재 상태: 시스템 전체 CPU 사용률 확인용 mpstat 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=(mpstat_out or '').strip(),
                stderr=(mpstat_err or '').strip(),
            )

        mpstat_command_error = self._detect_command_error(
            mpstat_out,
            mpstat_err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if mpstat_command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris CPU 사용률 점검에 실패했습니다. '
                    f'현재 상태: mpstat 출력에서 실행 오류가 확인되었습니다: {mpstat_command_error}'
                ),
                stdout=(mpstat_out or '').strip(),
                stderr=(mpstat_err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        combined_output = '\n'.join(part for part in ((prstat_out or '').strip(), (mpstat_out or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'CPU 사용률 실패 키워드 감지',
                message=(
                    'Solaris CPU 사용률 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=combined_output,
                stderr='\n'.join(part for part in ((prstat_err or '').strip(), (mpstat_err or '').strip()) if part),
            )

        prstat_parsed = self._parse_prstat_top_process(prstat_out)
        if not prstat_parsed:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='Solaris CPU 사용률 점검에 실패했습니다. 현재 상태: prstat 출력에서 상위 프로세스 CPU 정보를 해석하지 못했습니다.',
                stdout=(prstat_out or '').strip(),
                stderr=(prstat_err or '').strip(),
            )

        mpstat_parsed = self._parse_mpstat_cpu(mpstat_out)
        if not mpstat_parsed:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='Solaris CPU 사용률 점검에 실패했습니다. 현재 상태: mpstat 출력에서 시스템 전체 CPU 사용률을 해석하지 못했습니다.',
                stdout=(mpstat_out or '').strip(),
                stderr=(mpstat_err or '').strip(),
            )

        top_process = prstat_parsed['top_process']
        system_cpu_usage_percent = mpstat_parsed['cpu_usage_percent']
        top_process_cpu_percent = top_process['cpu_percent']

        metrics = {
            'system_cpu_usage_percent': system_cpu_usage_percent,
            'idle_percent': mpstat_parsed['idle_percent'],
            'user_percent': mpstat_parsed['user_percent'],
            'system_percent': mpstat_parsed['system_percent'],
            'wait_percent': mpstat_parsed['wait_percent'],
            'cpu_row_count': mpstat_parsed['cpu_row_count'],
            'sampled_process_count': len(prstat_parsed['process_entries']),
            'top_process_pid': top_process['pid'],
            'top_process_name': top_process['process_name'],
            'top_process_user': top_process['username'],
            'top_process_cpu_percent': top_process_cpu_percent,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'max_cpu_usage_percent': max_cpu_usage_percent,
            'max_process_cpu_percent': max_process_cpu_percent,
            'failure_keywords': failure_keywords,
        }

        if system_cpu_usage_percent > max_cpu_usage_percent:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=(
                    'Solaris CPU 사용률이 기준치를 초과했습니다. '
                    f'현재 상태: 시스템 CPU 사용률 {system_cpu_usage_percent:.2f}% '
                    f'(기준 {max_cpu_usage_percent:.2f}% 이하), '
                    f'Idle {mpstat_parsed["idle_percent"]:.2f}%, '
                    f'최고 프로세스 {top_process["process_name"]} {top_process_cpu_percent:.2f}%CPU '
                    f'(기준 {max_process_cpu_percent:.2f}% 이하).'
                ),
                stdout=combined_output,
                stderr='\n'.join(part for part in ((prstat_err or '').strip(), (mpstat_err or '').strip()) if part),
            )

        if top_process_cpu_percent > max_process_cpu_percent:
            return self.fail(
                '상위 프로세스 CPU 사용률 임계치 초과',
                message=(
                    'Solaris CPU 사용률이 기준치를 초과했습니다. '
                    f'현재 상태: 최고 프로세스 {top_process["process_name"]}({top_process["pid"]}) '
                    f'{top_process_cpu_percent:.2f}%CPU '
                    f'(기준 {max_process_cpu_percent:.2f}% 이하), '
                    f'시스템 CPU 사용률 {system_cpu_usage_percent:.2f}% '
                    f'(기준 {max_cpu_usage_percent:.2f}% 이하).'
                ),
                stdout=combined_output,
                stderr='\n'.join(part for part in ((prstat_err or '').strip(), (mpstat_err or '').strip()) if part),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'시스템 CPU 사용률 {system_cpu_usage_percent:.2f}%와 최고 프로세스 '
                f'{top_process["process_name"]} {top_process_cpu_percent:.2f}%CPU가 모두 기준 이내입니다.'
            ),
            message=(
                'Solaris CPU 사용률이 정상입니다. '
                f'현재 상태: 시스템 CPU 사용률 {system_cpu_usage_percent:.2f}% '
                f'(기준 {max_cpu_usage_percent:.2f}% 이하), '
                f'Idle {mpstat_parsed["idle_percent"]:.2f}%, '
                f'최고 프로세스 {top_process["process_name"]} {top_process_cpu_percent:.2f}%CPU '
                f'(기준 {max_process_cpu_percent:.2f}% 이하), '
                f'샘플 프로세스 {len(prstat_parsed["process_entries"])}건.'
            ),
        )


CHECK_CLASS = Check
