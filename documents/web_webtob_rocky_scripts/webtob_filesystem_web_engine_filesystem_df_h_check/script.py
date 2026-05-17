# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_COMMAND_TIMEOUT = 10

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
                default=(
                    'command not found,not found,No such file,'
                    'No such file or directory,Permission denied,cannot,'
                    'Connection refused,No route to host,timed out,'
                    'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
                ),
                value_type='str',
            )
        )

    def _contains_failure_keyword(self, *texts):
        failure_keywords = self._get_failure_keywords()
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in failure_keywords:
            if keyword.lower() in lowered:
                return keyword
        return ''

    def _run_command(self, command, timeout=None):
        command_timeout = self.DEFAULT_COMMAND_TIMEOUT if timeout is None else timeout
        results = self._run_paramiko_commands(
            [
                {
                    'command': command,
                    'timeout': command_timeout,
                }
            ],
            profile=self.PARAMIKO_PROFILE,
        )
        if not results:
            return {
                'command': command,
                'display_command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'raw_output': '',
                'timed_out': False,
            }
        return results[0]

    def _load_thresholds(self):
        web_engine_fs_path = self.get_threshold_var(
            'web_engine_fs_path',
            default='/home/exTMS/tmax/webtob',
            value_type='str',
        )
        max_use_percent = self.get_threshold_var(
            'max_use_percent',
            default=80,
            value_type='int',
        )
        min_avail_gb = self.get_threshold_var(
            'min_avail_gb',
            default=20.0,
            value_type='float',
        )
        failure_keywords = self._get_failure_keywords()
        return {
            'web_engine_fs_path': web_engine_fs_path,
            'max_use_percent': max_use_percent,
            'min_avail_gb': min_avail_gb,
            'failure_keywords': failure_keywords,
        }

    def _base_metrics(self, result, command, stdout=None, stderr=None):
        out = result.get('stdout') if stdout is None else stdout
        err = result.get('stderr') if stderr is None else stderr
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(out),
            'stderr_line_count': self._line_count(err),
        }

    def _empty_df_metrics(self, result, command, thresholds, stdout=None, stderr=None):
        metrics = self._base_metrics(result, command, stdout=stdout, stderr=stderr)
        metrics.update({
            'web_engine_fs_path': thresholds.get('web_engine_fs_path'),
            'filesystem': '',
            'size_raw': '',
            'used_raw': '',
            'avail_raw': '',
            'avail_gb': None,
            'use_percent': None,
            'mounted_on': '',
            'max_use_percent': thresholds.get('max_use_percent'),
            'min_avail_gb': thresholds.get('min_avail_gb'),
            'usage_over_threshold': None,
            'avail_under_threshold': None,
        })
        return metrics

    def _size_to_gb(self, raw_value):
        text = str(raw_value or '').strip()
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([KMGTPE]?)i?B?$', text, re.IGNORECASE)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'K':
            return number / (1024.0 * 1024.0)
        if unit == 'M':
            return number / 1024.0
        if unit == 'G':
            return number
        if unit == 'T':
            return number * 1024.0
        if unit == 'P':
            return number * 1024.0 * 1024.0
        if unit == 'E':
            return number * 1024.0 * 1024.0 * 1024.0
        return number

    def _use_percent_index(self, tokens):
        for idx, token in enumerate(tokens):
            if re.match(r'^\d+%$', str(token or '').strip()):
                return idx
        return -1

    def _parse_df_tokens(self, tokens):
        use_index = self._use_percent_index(tokens)
        if use_index < 4:
            return None
        if len(tokens) <= use_index + 1:
            return None

        filesystem = tokens[0]
        size_raw = tokens[use_index - 3]
        used_raw = tokens[use_index - 2]
        avail_raw = tokens[use_index - 1]
        mounted_on = ' '.join(tokens[use_index + 1:]).strip()
        if not filesystem or not mounted_on:
            return None

        try:
            use_percent = int(str(tokens[use_index]).rstrip('%'))
        except Exception:
            return None

        avail_gb = self._size_to_gb(avail_raw)
        if avail_gb is None:
            return None

        return {
            'filesystem': filesystem,
            'size_raw': size_raw,
            'used_raw': used_raw,
            'avail_raw': avail_raw,
            'avail_gb': round(float(avail_gb), 4),
            'use_percent': use_percent,
            'mounted_on': mounted_on,
        }

    def _parse_df_output(self, stdout):
        pending_tokens = []
        for raw_line in str(stdout or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if 'Filesystem' in line and 'Use%' in line:
                pending_tokens = []
                continue

            tokens = re.split(r'\s+', line)
            use_index = self._use_percent_index(tokens)

            if use_index < 0:
                pending_tokens = tokens
                continue

            parse_tokens = tokens
            if pending_tokens and (use_index <= 3 or not tokens[0].strip()):
                parse_tokens = pending_tokens + tokens
            parsed = self._parse_df_tokens(parse_tokens)
            if parsed:
                return parsed

            if pending_tokens:
                parsed = self._parse_df_tokens(pending_tokens + tokens)
                if parsed:
                    return parsed
            pending_tokens = []
        return None

    def _command_failure_reason(self, result, stdout, stderr):
        if result.get('timed_out'):
            return '명령 실행 중 timeout이 발생했습니다.'

        rc = result.get('rc')
        if rc != 0:
            return 'df 명령 종료코드가 rc=%s입니다.' % rc

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            return '출력에서 실패 키워드가 확인되었습니다: %s' % failure_keyword

        return ''

    def _fail_df_check(self, error, result, command, thresholds, reason, stdout, stderr):
        message = (
            'WEB 엔진 파일시스템 점검에 실패했습니다. '
            'df 명령 실행 오류, 출력 없음 또는 파싱 실패로 파일시스템 상태를 판단하지 못했습니다.'
        )
        metrics = self._empty_df_metrics(result, command, thresholds, stdout=stdout, stderr=stderr)
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reason,
        )

    def run(self):
        thresholds = self._load_thresholds()
        web_engine_fs_path = thresholds['web_engine_fs_path']
        max_use_percent = thresholds['max_use_percent']
        min_avail_gb = thresholds['min_avail_gb']

        command = 'df -h %s' % self._quote(web_engine_fs_path)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()

        failure_reason = self._command_failure_reason(result, stdout, stderr)
        if failure_reason:
            return self._fail_df_check(
                '점검 명령 실행 실패',
                result,
                command,
                thresholds,
                failure_reason,
                stdout,
                stderr,
            )

        if not stdout:
            return self._fail_df_check(
                '점검 출력 없음',
                result,
                command,
                thresholds,
                'df 명령 출력이 비어 있습니다.',
                stdout,
                stderr,
            )

        parsed = self._parse_df_output(stdout)
        if not parsed:
            return self._fail_df_check(
                'df 출력 파싱 실패',
                result,
                command,
                thresholds,
                'df -h 출력에서 파일시스템, 용량, 사용률, 마운트 경로를 파싱하지 못했습니다.',
                stdout,
                stderr,
            )

        usage_over_threshold = parsed['use_percent'] > max_use_percent
        avail_under_threshold = parsed['avail_gb'] < min_avail_gb

        metrics = self._base_metrics(result, command, stdout=stdout, stderr=stderr)
        metrics.update({
            'web_engine_fs_path': web_engine_fs_path,
            'filesystem': parsed['filesystem'],
            'size_raw': parsed['size_raw'],
            'used_raw': parsed['used_raw'],
            'avail_raw': parsed['avail_raw'],
            'avail_gb': parsed['avail_gb'],
            'use_percent': parsed['use_percent'],
            'mounted_on': parsed['mounted_on'],
            'max_use_percent': max_use_percent,
            'min_avail_gb': min_avail_gb,
            'usage_over_threshold': usage_over_threshold,
            'avail_under_threshold': avail_under_threshold,
        })

        if usage_over_threshold or avail_under_threshold:
            reasons = []
            if usage_over_threshold:
                reasons.append(
                    '파일시스템 사용률 %s%%가 기준 %s%%를 초과했습니다.' % (
                        parsed['use_percent'],
                        max_use_percent,
                    )
                )
            if avail_under_threshold:
                reasons.append(
                    '파일시스템 여유 공간 %.1fGB가 기준 %.1fGB 미만입니다.' % (
                        parsed['avail_gb'],
                        min_avail_gb,
                    )
                )
            message = (
                'WEB 엔진 파일시스템 점검 결과 경고입니다. '
                '%s 경로의 사용률은 %s%%로 기준 %s%%를 초과했거나, '
                '여유 공간이 %.1fGB로 기준 %.1fGB 미만입니다.'
            ) % (
                web_engine_fs_path,
                parsed['use_percent'],
                max_use_percent,
                parsed['avail_gb'],
                min_avail_gb,
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=reasons,
                message=message,
            )

        message = (
            'WEB 엔진 파일시스템 점검 결과 정상입니다. '
            '%s 경로의 사용률은 %s%%로 기준 %s%% 이하이고, '
            '여유 공간은 %.1fGB로 기준 %.1fGB 이상입니다.'
        ) % (
            web_engine_fs_path,
            parsed['use_percent'],
            max_use_percent,
            parsed['avail_gb'],
            min_avail_gb,
        )
        reasons = [
            '파일시스템 사용률과 여유 공간이 모두 기준을 만족합니다.'
        ]
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
            message=message,
        )


CHECK_CLASS = Check
