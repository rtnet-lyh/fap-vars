# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


SAR_CPU_COMMAND = 'sar -u 1 3'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_number(self, value):
        try:
            return float(str(value).strip().rstrip('%'))
        except (TypeError, ValueError):
            return None

    def _parse_sar_cpu(self, text):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        header = None
        header_index = None

        for idx, line in enumerate(lines):
            tokens = re.split(r'\s+', line)
            normalized = [token.lower() for token in tokens]
            if '%idle' in normalized:
                header = normalized
                header_index = idx
                break

        if not header or header_index is None:
            return None

        idle_index = header.index('%idle')
        usr_index = header.index('%usr') if '%usr' in header else None
        sys_index = header.index('%sys') if '%sys' in header else None
        wio_index = header.index('%wio') if '%wio' in header else None

        samples = []
        average = None
        for line in lines[header_index + 1:]:
            tokens = re.split(r'\s+', line)
            if len(tokens) <= idle_index:
                continue

            idle_percent = self._parse_number(tokens[idle_index])
            if idle_percent is None:
                continue

            label = tokens[0]
            entry = {
                'label': label,
                'usr_percent': self._parse_number(tokens[usr_index]) if usr_index is not None and len(tokens) > usr_index else None,
                'sys_percent': self._parse_number(tokens[sys_index]) if sys_index is not None and len(tokens) > sys_index else None,
                'wio_percent': self._parse_number(tokens[wio_index]) if wio_index is not None and len(tokens) > wio_index else None,
                'idle_percent': round(idle_percent, 2),
                'cpu_usage_percent': round(100.0 - idle_percent, 2),
            }

            if label.lower().startswith('average'):
                average = entry
            else:
                samples.append(entry)

        selected = samples[-1] if samples else average
        if not selected:
            return None

        return {
            'selected': selected,
            'average': average,
            'samples': samples,
        }

    def run(self):
        max_cpu_usage_percent = self.get_threshold_var('CPU_MAX_PCT', default=70.0, value_type='float')
        rc, out, err = self._ssh(SAR_CPU_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='sar -u 1 3 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(out, err)
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'sar 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = self._parse_sar_cpu(out)
        if not parsed:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='sar 출력에서 %idle 컬럼과 CPU 사용률 샘플을 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        selected = parsed['selected']
        average = parsed['average'] or {}
        cpu_usage_percent = selected['cpu_usage_percent']
        selected_label = selected['label']
        threshold_summary = f'CPU_MAX_PCT={max_cpu_usage_percent}%'

        metrics = {
            'cpu_usage_percent': cpu_usage_percent,
            'selected_sample': selected_label,
            'selected_idle_percent': selected['idle_percent'],
            'sample_count': len(parsed['samples']),
            'average_cpu_usage_percent': average.get('cpu_usage_percent'),
            'average_idle_percent': average.get('idle_percent'),
        }
        thresholds = {
            'CPU_MAX_PCT': max_cpu_usage_percent,
        }

        if cpu_usage_percent > max_cpu_usage_percent:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=(
                    'CPU 사용률이 기준치를 초과했습니다. '
                    f'임계치 정보: {threshold_summary}. '
                    f'판단근거: 선택 샘플({selected_label})의 CPU 사용률 '
                    f'{cpu_usage_percent}%가 임계치 {max_cpu_usage_percent}%보다 큽니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'선택 샘플({selected_label})의 CPU 사용률 {cpu_usage_percent}%가 '
                f'임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
            message=(
                'sar 기준 HP-UX CPU 사용률 점검이 정상 수행되었습니다. '
                f'임계치 정보: {threshold_summary}. '
                f'판단근거: 선택 샘플({selected_label})의 CPU 사용률 '
                f'{cpu_usage_percent}%가 임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
        )


CHECK_CLASS = Check
