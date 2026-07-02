# -*- coding: utf-8 -*-

import csv
import io

from items.common._base import BaseCheck


TYPEPERF_COMMAND = (
    'typeperf "\\Processor(_Total)\\% User Time" '
    '"\\Processor(_Total)\\% Privileged Time" '
    '"\\Processor(_Total)\\% Idle Time" '
    '"\\Processor(_Total)\\% Interrupt Time" -sc 3 -si 1'
)

COUNTER_COLUMNS = {
    '% user time': 'user_percent',
    '% privileged time': 'privileged_percent',
    '% idle time': 'idle_percent',
    '% interrupt time': 'interrupt_percent',
}

REQUIRED_COUNTERS = (
    'user_percent',
    'privileged_percent',
    'idle_percent',
    'interrupt_percent',
)


def _parse_percent(value):
    return round(float(str(value).strip()), 2)


def _split_keywords(value):
    if isinstance(value, (list, tuple)):
        raw_keywords = value
    else:
        raw_keywords = str(value or '').split(',')
    return [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]


def _format_keywords(keywords):
    return ', '.join(keywords) if keywords else '없음'


def _average(rows, key):
    return round(sum(row[key] for row in rows) / len(rows), 2)


def _extract_host_name(header_value):
    text = str(header_value or '').strip()
    if not text:
        return ''
    return text.lstrip('\\').split('\\', 1)[0]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def parse_output(self, output):
        text = (output or '').strip()
        metrics = {
            'sample_count': 0,
            'host_name': '',
            'matched_failure_keywords': [],
            '_raw_output': text,
        }

        if not text:
            metrics['_parse_error'] = 'typeperf 결과가 비어 있습니다.'
            return metrics

        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error as exc:
            metrics['_parse_error'] = 'typeperf CSV 결과를 해석하지 못했습니다: {0}'.format(exc)
            return metrics

        if len(rows) < 2:
            metrics['_parse_error'] = 'typeperf CSV에 측정 샘플이 없습니다.'
            return metrics

        header = rows[0]
        if len(header) < 5:
            metrics['_parse_error'] = 'typeperf CSV 헤더 컬럼 수가 부족합니다.'
            return metrics

        metrics['host_name'] = _extract_host_name(header[1])

        column_indexes = {}
        for index, column_name in enumerate(header):
            normalized = str(column_name or '').lower()
            for counter_name, metric_key in COUNTER_COLUMNS.items():
                if counter_name in normalized:
                    column_indexes[metric_key] = index

        missing_columns = [
            metric_key for metric_key in REQUIRED_COUNTERS
            if metric_key not in column_indexes
        ]
        if missing_columns:
            metrics['_parse_error'] = '필수 CPU 카운터 컬럼을 찾지 못했습니다.'
            metrics['_missing_columns'] = missing_columns
            return metrics

        samples = []
        max_index = max(column_indexes.values())
        for row in rows[1:]:
            if len(row) <= max_index:
                continue

            try:
                sample = {
                    'timestamp': str(row[0]).strip(),
                    'user_percent': _parse_percent(row[column_indexes['user_percent']]),
                    'privileged_percent': _parse_percent(row[column_indexes['privileged_percent']]),
                    'idle_percent': _parse_percent(row[column_indexes['idle_percent']]),
                    'interrupt_percent': _parse_percent(row[column_indexes['interrupt_percent']]),
                }
            except ValueError:
                continue

            sample['usr_sys_percent'] = round(
                sample['user_percent'] + sample['privileged_percent'],
                2,
            )
            samples.append(sample)

        if not samples:
            metrics['_parse_error'] = 'typeperf CSV에서 유효한 CPU 측정값을 찾지 못했습니다.'
            return metrics

        peak_usr_sys_sample = max(samples, key=lambda row: row['usr_sys_percent'])
        peak_interrupt_sample = max(samples, key=lambda row: row['interrupt_percent'])

        metrics.update({
            'sample_count': len(samples),
            'avg_user_percent': _average(samples, 'user_percent'),
            'avg_privileged_percent': _average(samples, 'privileged_percent'),
            'avg_usr_sys_percent': _average(samples, 'usr_sys_percent'),
            'avg_idle_percent': _average(samples, 'idle_percent'),
            'avg_interrupt_percent': _average(samples, 'interrupt_percent'),
            'max_usr_sys_percent': peak_usr_sys_sample['usr_sys_percent'],
            'max_usr_sys_timestamp': peak_usr_sys_sample['timestamp'],
            'max_interrupt_percent': peak_interrupt_sample['interrupt_percent'],
            'max_interrupt_timestamp': peak_interrupt_sample['timestamp'],
        })
        return metrics

    def evaluate(
        self,
        metrics,
        max_usr_sys_percent,
        min_idle_percent,
        max_interrupt_percent,
        failure_keywords,
    ):
        if metrics.get('_parse_error'):
            return 'fail'

        raw_output = metrics.get('_raw_output', '')
        matched_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in raw_output.lower()
        ]
        if matched_keywords:
            return 'fail'

        if metrics['avg_usr_sys_percent'] >= max_usr_sys_percent:
            return 'fail'
        if metrics['avg_idle_percent'] < min_idle_percent:
            return 'fail'
        if metrics['avg_interrupt_percent'] >= max_interrupt_percent:
            return 'fail'
        return 'ok'

    def build_result(
        self,
        metrics,
        max_usr_sys_percent,
        min_idle_percent,
        max_interrupt_percent,
        failure_keywords,
        status,
    ):
        clean_metrics = {
            key: value for key, value in metrics.items()
            if not key.startswith('_')
        }
        raw_output = metrics.get('_raw_output', '')
        matched_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in raw_output.lower()
        ]
        clean_metrics['matched_failure_keywords'] = matched_keywords

        criteria = '\n'.join([
            '사용자+시스템 CPU 평균: {0:.2f}% 미만'.format(max_usr_sys_percent),
            'CPU Idle 평균: {0:.2f}% 이상'.format(min_idle_percent),
            'Interrupt Time 평균: {0:.2f}% 미만'.format(max_interrupt_percent),
            '실패 키워드: {0}'.format(_format_keywords(failure_keywords)),
        ])

        if metrics.get('_parse_error'):
            message = '\n'.join([
                'Windows CPU 사용률 점검 결과: 실패',
                metrics['_parse_error'],
            ])
            results = '\n'.join([
                '파싱 상태: 실패',
                '분석 가능한 샘플 수: {0}'.format(clean_metrics.get('sample_count', 0)),
                '호스트: {0}'.format(clean_metrics.get('host_name') or 'unknown'),
            ])
            if metrics.get('_missing_columns'):
                results = '\n'.join([
                    results,
                    '누락 컬럼: {0}'.format(', '.join(metrics['_missing_columns'])),
                ])
            return {
                'message': message,
                'results': results,
                'criteria': criteria,
                'metrics': clean_metrics,
            }

        failure_reasons = []
        if matched_keywords:
            failure_reasons.append(
                '실패 키워드 감지: {0}'.format(_format_keywords(matched_keywords))
            )
        if clean_metrics['avg_usr_sys_percent'] >= max_usr_sys_percent:
            failure_reasons.append(
                '사용자+시스템 CPU 평균 기준 미충족'
            )
        if clean_metrics['avg_idle_percent'] < min_idle_percent:
            failure_reasons.append(
                'CPU Idle 평균 기준 미충족'
            )
        if clean_metrics['avg_interrupt_percent'] >= max_interrupt_percent:
            failure_reasons.append(
                'Interrupt Time 평균 기준 미충족'
            )

        if status == 'ok':
            message = '\n'.join([
                'Windows CPU 사용률 점검 결과: 정상',
                '평균 CPU 사용률, Idle 비율, Interrupt 비율이 모두 기준 범위 내입니다.',
            ])
        else:
            message = '\n'.join([
                'Windows CPU 사용률 점검 결과: 기준 미충족',
                '\n'.join(failure_reasons),
            ])

        results = '\n'.join([
            '호스트: {0}'.format(clean_metrics.get('host_name') or 'unknown'),
            '샘플 수: {0}'.format(clean_metrics['sample_count']),
            '평균 User Time: {0:.2f}%'.format(clean_metrics['avg_user_percent']),
            '평균 Privileged Time: {0:.2f}%'.format(clean_metrics['avg_privileged_percent']),
            '평균 사용자+시스템 CPU: {0:.2f}%'.format(clean_metrics['avg_usr_sys_percent']),
            '평균 Idle Time: {0:.2f}%'.format(clean_metrics['avg_idle_percent']),
            '평균 Interrupt Time: {0:.2f}%'.format(clean_metrics['avg_interrupt_percent']),
            '최대 사용자+시스템 CPU: {0:.2f}% ({1})'.format(
                clean_metrics['max_usr_sys_percent'],
                clean_metrics['max_usr_sys_timestamp'] or 'timestamp 없음',
            ),
            '최대 Interrupt Time: {0:.2f}% ({1})'.format(
                clean_metrics['max_interrupt_percent'],
                clean_metrics['max_interrupt_timestamp'] or 'timestamp 없음',
            ),
            '감지된 실패 키워드: {0}'.format(_format_keywords(matched_keywords)),
        ])

        return {
            'message': message,
            'results': results,
            'criteria': criteria,
            'metrics': clean_metrics,
        }

    def run(self):
        max_usr_sys_percent = self.get_threshold_var(
            'max_usr_sys_percent',
            default=80.0,
            value_type='float',
        )
        min_idle_percent = self.get_threshold_var(
            'min_idle_percent',
            default=20.0,
            value_type='float',
        )
        max_interrupt_percent = self.get_threshold_var(
            'max_interrupt_percent',
            default=5.0,
            value_type='float',
        )
        failure_keywords = _split_keywords(
            self.get_threshold_var('failure_keywords', default='', value_type='str')
        )

        _rc, out, _err = self._run_ps(TYPEPERF_COMMAND)
        metrics = self.parse_output(out)
        status = self.evaluate(
            metrics,
            max_usr_sys_percent,
            min_idle_percent,
            max_interrupt_percent,
            failure_keywords,
        )
        result = self.build_result(
            metrics,
            max_usr_sys_percent,
            min_idle_percent,
            max_interrupt_percent,
            failure_keywords,
            status,
        )
        return self.result(
            status,
            message=result['message'],
            results=result['results'],
            criteria=result['criteria'],
            metrics=result['metrics'],
        )


CHECK_CLASS = Check
