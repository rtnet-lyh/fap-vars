# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_COMMAND_TIMEOUT = 15
    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    REQUIRED_FIELDS = (
        ('MaxConnections', 'actual_max_connections', 'threshold_max_connections', 'max_connections_ok', 'max_connections'),
        (
            'MaxRequestPerConnection',
            'actual_max_request_per_connection',
            'threshold_max_request_per_connection',
            'max_request_per_connection_ok',
            'max_request_per_connection',
        ),
        ('MaxWorkerThreads', 'actual_max_worker_threads', 'threshold_max_worker_threads', 'max_worker_threads_ok', 'max_worker_threads'),
    )

    def _split_csv(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split(',')
            if token.strip()
        ]

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _get_failure_keywords(self):
        return self._split_csv(
            self.get_threshold_var(
                'failure_keywords',
                default=self.DEFAULT_FAILURE_KEYWORDS,
                value_type='str',
            )
        )

    def _get_positive_int_threshold(self, key, default):
        resolved_value = self.get_threshold_var(
            key,
            default=default,
            value_type='int',
        )

        raw_map = self.get_threshold_list_map()
        raw_value = raw_map.get(key)
        has_raw_value = (
            key in raw_map and
            raw_value is not None and
            (not isinstance(raw_value, str) or raw_value.strip() != '')
        )

        if has_raw_value:
            try:
                resolved_value = int(str(raw_value).strip())
            except Exception:
                return resolved_value, '%s 값은 정수여야 합니다: %s' % (key, raw_value)

        try:
            number = int(resolved_value)
        except Exception:
            return resolved_value, '%s 값은 정수여야 합니다: %s' % (key, resolved_value)

        if number <= 0:
            return number, '%s 값은 0보다 큰 정수여야 합니다: %s' % (key, number)

        return number, ''

    def _load_thresholds(self):
        thresholds = {
            'webtob_ctl_command': self.get_threshold_var(
                'webtob_ctl_command',
                default='webtob_ctl',
                value_type='str',
            ),
            'failure_keywords': self._get_failure_keywords(),
        }
        errors = []

        for key, default in (
            ('max_connections', 1000),
            ('max_request_per_connection', 50),
            ('max_worker_threads', 200),
        ):
            value, error = self._get_positive_int_threshold(key, default)
            thresholds[key] = value
            if error:
                errors.append(error)

        if not str(thresholds.get('webtob_ctl_command') or '').strip():
            errors.append('webtob_ctl_command 값이 비어 있습니다.')

        return thresholds, errors

    def _contains_failure_keyword(self, failure_keywords, stdout, stderr):
        combined = '\n'.join(str(text or '') for text in (stdout, stderr) if text is not None)
        lowered = combined.lower()
        for keyword in failure_keywords:
            if keyword and keyword.lower() in lowered:
                return keyword
        return ''

    def _run_command(self, command, timeout):
        results = self._run_paramiko_commands(
            [
                {
                    'command': command,
                    'timeout': timeout,
                }
            ],
            profile=self.PARAMIKO_PROFILE,
        )

        if not results:
            return {
                'command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'timed_out': False,
            }

        return results[0]

    def _empty_metrics(self, command, result=None, stdout='', stderr='', thresholds=None):
        result = result or {}
        thresholds = thresholds or {}
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'actual_status': '',
            'status_line': '',
            'actual_max_connections': None,
            'actual_max_request_per_connection': None,
            'actual_max_worker_threads': None,
            'threshold_max_connections': thresholds.get('max_connections'),
            'threshold_max_request_per_connection': thresholds.get('max_request_per_connection'),
            'threshold_max_worker_threads': thresholds.get('max_worker_threads'),
            'max_connections_ok': None,
            'max_request_per_connection_ok': None,
            'max_worker_threads_ok': None,
            'under_threshold_count': 0,
            'under_threshold_fields': [],
            'first_under_threshold_field': '',
        }

    def _field_pattern(self, field_name):
        return re.compile(r'^\s*' + re.escape(field_name) + r'\s*:\s*(.*?)\s*$', re.IGNORECASE)

    def _extract_status_values(self, stdout):
        status_line = ''
        actual_status = ''
        values = {}
        errors = []

        status_pattern = self._field_pattern('Status')
        field_patterns = [
            (field_name, actual_key, self._field_pattern(field_name))
            for field_name, actual_key, _threshold_key, _ok_key, _threshold_name in self.REQUIRED_FIELDS
        ]

        for line in str(stdout or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            status_match = status_pattern.match(stripped)
            if status_match and not status_line:
                status_line = stripped
                actual_status = status_match.group(1).strip()
                continue

            for field_name, actual_key, pattern in field_patterns:
                match = pattern.match(stripped)
                if not match:
                    continue
                raw_number = match.group(1).strip()
                if not re.match(r'^[+-]?\d+$', raw_number):
                    errors.append('%s 값 숫자 변환 실패: %s' % (field_name, raw_number))
                    continue
                values[actual_key] = int(raw_number)

        for field_name, actual_key, _threshold_key, _ok_key, _threshold_name in self.REQUIRED_FIELDS:
            if actual_key not in values:
                errors.append('%s 필드를 파싱하지 못했습니다.' % field_name)

        return actual_status, status_line, values, errors

    def _merge_metrics(self, base_metrics, actual_status, status_line, values, thresholds):
        metrics = dict(base_metrics)
        metrics['actual_status'] = actual_status or ''
        metrics['status_line'] = status_line or ''

        for _field_name, actual_key, threshold_key, ok_key, threshold_name in self.REQUIRED_FIELDS:
            actual = values.get(actual_key)
            threshold = thresholds.get(threshold_name)
            metrics[actual_key] = actual
            metrics[threshold_key] = threshold
            metrics[ok_key] = None if actual is None or threshold is None else actual >= threshold

        under_threshold_fields = []
        for field_name, actual_key, _threshold_key, _ok_key, threshold_name in self.REQUIRED_FIELDS:
            actual = values.get(actual_key)
            threshold = thresholds.get(threshold_name)
            if actual is None or threshold is None:
                continue
            if actual < threshold:
                under_threshold_fields.append({
                    'field': field_name,
                    'actual': actual,
                    'threshold': threshold,
                    'reason': 'actual < threshold',
                })

        metrics['under_threshold_count'] = len(under_threshold_fields)
        metrics['under_threshold_fields'] = under_threshold_fields
        metrics['first_under_threshold_field'] = under_threshold_fields[0]['field'] if under_threshold_fields else ''
        return metrics

    def _failure_result(self, title, message, result, stdout, stderr, metrics, thresholds, reasons):
        return self.fail(
            title,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def run(self):
        thresholds, threshold_errors = self._load_thresholds()
        webtob_ctl_command = thresholds.get('webtob_ctl_command')
        command = '%s status' % self._quote(webtob_ctl_command)

        if threshold_errors:
            metrics = self._empty_metrics(command, thresholds=thresholds)
            return self.fail(
                '임계치 오류',
                message='사용자 요청량 처리 수 점검에 실패했습니다. threshold 값 오류로 점검을 수행할 수 없습니다.',
                stdout='',
                stderr='',
                metrics=metrics,
                thresholds=thresholds,
                reasons=threshold_errors,
            )

        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        metrics = self._empty_metrics(command, result=result, stdout=stdout, stderr=stderr, thresholds=thresholds)

        if result.get('timed_out'):
            return self._failure_result(
                '점검 명령 timeout',
                '사용자 요청량 처리 수 점검에 실패했습니다. webtob_ctl status 명령 실행 중 timeout이 발생했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['명령 실행 중 timeout이 발생했습니다.'],
            )

        if result.get('rc') != 0:
            return self._failure_result(
                '점검 명령 실행 실패',
                '사용자 요청량 처리 수 점검에 실패했습니다. webtob_ctl status 명령 실행 오류로 요청량 처리 설정값을 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['명령 종료코드가 rc=%s입니다.' % result.get('rc')],
            )

        failure_keyword = self._contains_failure_keyword(thresholds.get('failure_keywords'), stdout, stderr)
        if failure_keyword:
            return self._failure_result(
                '점검 명령 실행 실패',
                '사용자 요청량 처리 수 점검에 실패했습니다. webtob_ctl status 출력에서 실행 실패 키워드가 확인되었습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['출력에서 실패 키워드가 확인되었습니다: %s' % failure_keyword],
            )

        if not stdout:
            return self._failure_result(
                '점검 출력 없음',
                '사용자 요청량 처리 수 점검에 실패했습니다. webtob_ctl status 명령 출력이 없어 요청량 처리 설정값을 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['명령 출력이 비어 있습니다.'],
            )

        actual_status, status_line, values, extract_errors = self._extract_status_values(stdout)
        metrics = self._merge_metrics(metrics, actual_status, status_line, values, thresholds)

        if extract_errors:
            return self._failure_result(
                '필수 필드 파싱 실패',
                '사용자 요청량 처리 수 점검에 실패했습니다. webtob_ctl status 명령 실행 오류, 출력 없음 또는 필수 필드 파싱 실패로 요청량 처리 설정값을 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                extract_errors,
            )

        under_threshold_fields = metrics.get('under_threshold_fields') or []
        if under_threshold_fields:
            first = under_threshold_fields[0]
            details = ', '.join(
                '%s=%s(권장 최소 기준 %s)' % (item.get('field'), item.get('actual'), item.get('threshold'))
                for item in under_threshold_fields
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=[
                    '%s 값이 권장 최소 기준보다 낮습니다.' % item.get('field')
                    for item in under_threshold_fields
                ],
                message=(
                    '사용자 요청량 처리 수 점검 결과 경고입니다. '
                    '%s 값이 권장 최소 기준보다 낮아 사용자 요청 처리 용량 점검이 필요합니다. '
                    '기준 미달 항목: %s'
                ) % (first.get('field'), details),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='MaxConnections, MaxRequestPerConnection, MaxWorkerThreads 값이 모두 권장 최소 기준 이상입니다.',
            message=(
                '사용자 요청량 처리 수 점검 결과 정상입니다. '
                'MaxConnections=%s, MaxRequestPerConnection=%s, MaxWorkerThreads=%s 값이 모두 권장 최소 기준 이상입니다.'
            ) % (
                metrics.get('actual_max_connections'),
                metrics.get('actual_max_request_per_connection'),
                metrics.get('actual_max_worker_threads'),
            ),
        )


CHECK_CLASS = Check
