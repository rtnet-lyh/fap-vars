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
    DEFAULT_WEB_LOG_FS_PATH = '/home/exTMS/tmax/webtob/log'
    DEFAULT_MAX_USE_PERCENT = 80
    DEFAULT_MIN_AVAIL_GB = 20.0
    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _split_csv(self, value):
        return [token.strip() for token in str(value or '').split(',') if token.strip()]

    def _threshold_raw_value(self, key):
        mapped = self.get_threshold_list_map()
        if key not in mapped:
            return None, False
        raw_value = mapped.get(key)
        has_value = raw_value is not None and (not isinstance(raw_value, str) or raw_value.strip() != '')
        return raw_value, has_value

    def _get_failure_keywords(self):
        raw_keywords = self.get_threshold_var(
            'failure_keywords',
            default=self.DEFAULT_FAILURE_KEYWORDS,
            value_type='str',
        )
        keywords = self._split_csv(raw_keywords)
        if not keywords:
            keywords = self._split_csv(self.DEFAULT_FAILURE_KEYWORDS)
        return keywords

    def _load_thresholds(self):
        web_log_fs_path = self.get_threshold_var(
            'web_log_fs_path',
            default=self.DEFAULT_WEB_LOG_FS_PATH,
            value_type='str',
        )
        max_use_percent = self.get_threshold_var(
            'max_use_percent',
            default=self.DEFAULT_MAX_USE_PERCENT,
            value_type='int',
        )
        min_avail_gb = self.get_threshold_var(
            'min_avail_gb',
            default=self.DEFAULT_MIN_AVAIL_GB,
            value_type='float',
        )
        failure_keywords = self._get_failure_keywords()

        raw_max, has_raw_max = self._threshold_raw_value('max_use_percent')
        if has_raw_max:
            try:
                max_use_percent = int(str(raw_max).strip())
            except Exception as exc:
                raise ValueError('max_use_percent must be an integer between 0 and 100') from exc

        raw_min, has_raw_min = self._threshold_raw_value('min_avail_gb')
        if has_raw_min:
            try:
                min_avail_gb = float(str(raw_min).strip())
            except Exception as exc:
                raise ValueError('min_avail_gb must be a number greater than or equal to 0') from exc

        if not str(web_log_fs_path or '').strip():
            raise ValueError('web_log_fs_path must not be empty')
        if int(max_use_percent) < 0 or int(max_use_percent) > 100:
            raise ValueError('max_use_percent must be an integer between 0 and 100')
        if float(min_avail_gb) < 0:
            raise ValueError('min_avail_gb must be a number greater than or equal to 0')

        return {
            'web_log_fs_path': str(web_log_fs_path).strip(),
            'max_use_percent': int(max_use_percent),
            'min_avail_gb': float(min_avail_gb),
            'failure_keywords': failure_keywords,
        }

    def _contains_failure_keyword(self, keywords, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None).lower()
        for keyword in keywords or []:
            if str(keyword).lower() in combined:
                return str(keyword)
        return ''

    def _run_df_command(self, command):
        results = self._run_paramiko_commands(
            [
                {
                    'command': command,
                    'timeout': self.DEFAULT_COMMAND_TIMEOUT,
                }
            ],
            profile=self.PARAMIKO_PROFILE,
        )
        if not results:
            return {
                'command': command,
                'rc': 1,
                'stdout': '',
                'stderr': 'paramiko command result is empty',
                'timed_out': False,
            }
        return results[0]

    def _base_metrics(self, command, result, thresholds, stdout='', stderr=''):
        return {
            'command': command,
            'command_rc': result.get('rc') if isinstance(result, dict) else None,
            'timed_out': bool(result.get('timed_out', False)) if isinstance(result, dict) else False,
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'web_log_fs_path': thresholds.get('web_log_fs_path', ''),
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
        }

    def _fail_result(self, error, message, result, metrics, thresholds, stdout='', stderr='', reasons=''):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def _to_gb(self, value):
        text = str(value or '').strip()
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([KMGTPE]?)(?:i?B?)?$', text, re.IGNORECASE)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).upper()
        if unit == '':
            if number == 0:
                return 0.0
            return number / (1024.0 * 1024.0 * 1024.0)
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
        return None

    def _find_use_index(self, tokens):
        for idx, token in enumerate(tokens or []):
            if re.match(r'^[0-9]+%$', str(token or '').strip()):
                return idx
        return None

    def _parse_df_tokens(self, tokens, previous_tokens=None):
        parse_tokens = list(tokens or [])
        previous_tokens = list(previous_tokens or [])
        use_index = self._find_use_index(parse_tokens)
        if use_index is None:
            return None

        if (use_index <= 3 or not parse_tokens[:use_index - 3]) and previous_tokens:
            parse_tokens = previous_tokens + parse_tokens
            use_index = self._find_use_index(parse_tokens)
            if use_index is None:
                return None

        if use_index < 3:
            return None

        filesystem_tokens = parse_tokens[:use_index - 3]
        if not filesystem_tokens:
            return None

        mounted_tokens = parse_tokens[use_index + 1:]
        if not mounted_tokens:
            return None

        use_text = str(parse_tokens[use_index]).rstrip('%')
        try:
            use_percent = int(use_text)
        except Exception:
            return None

        avail_raw = parse_tokens[use_index - 1]
        avail_gb = self._to_gb(avail_raw)
        if avail_gb is None:
            return None

        return {
            'filesystem': ' '.join(filesystem_tokens),
            'size_raw': parse_tokens[use_index - 3],
            'used_raw': parse_tokens[use_index - 2],
            'avail_raw': avail_raw,
            'avail_gb': round(float(avail_gb), 4),
            'use_percent': use_percent,
            'mounted_on': ' '.join(mounted_tokens),
        }

    def _parse_df_output(self, stdout):
        previous_tokens = []
        for line in str(stdout or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith('filesystem'):
                previous_tokens = []
                continue

            tokens = re.split(r'\s+', stripped)
            parsed = self._parse_df_tokens(tokens, previous_tokens=previous_tokens)
            if parsed:
                return parsed
            previous_tokens = tokens
        return None

    def run(self):
        command = ''
        stdout = ''
        stderr = ''
        result = {'rc': None, 'timed_out': False}

        try:
            thresholds = self._load_thresholds()
        except Exception as exc:
            thresholds = {
                'web_log_fs_path': self.get_threshold_var(
                    'web_log_fs_path',
                    default=self.DEFAULT_WEB_LOG_FS_PATH,
                    value_type='str',
                ),
                'max_use_percent': self.get_threshold_var(
                    'max_use_percent',
                    default=self.DEFAULT_MAX_USE_PERCENT,
                    value_type='int',
                ),
                'min_avail_gb': self.get_threshold_var(
                    'min_avail_gb',
                    default=self.DEFAULT_MIN_AVAIL_GB,
                    value_type='float',
                ),
                'failure_keywords': self._get_failure_keywords(),
            }
            metrics = self._base_metrics(command, result, thresholds, stdout=stdout, stderr=stderr)
            return self._fail_result(
                'threshold_error',
                'WEB log filesystem check failed because threshold values are invalid.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons=str(exc),
            )

        command = 'df -h {0}'.format(self._quote(thresholds['web_log_fs_path']))
        result = self._run_df_command(command)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        metrics = self._base_metrics(command, result, thresholds, stdout=stdout, stderr=stderr)

        if result.get('timed_out'):
            return self._fail_result(
                'command_timeout',
                'WEB log filesystem check failed because the df command timed out.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons='df command timeout',
            )

        rc = result.get('rc')
        if rc != 0:
            return self._fail_result(
                'command_error',
                'WEB log filesystem check failed because the df command returned a non-zero rc.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons='df command rc={0}'.format(rc),
            )

        failure_keyword = self._contains_failure_keyword(thresholds['failure_keywords'], stdout, stderr)
        if failure_keyword:
            metrics['failure_keyword'] = failure_keyword
            return self._fail_result(
                'command_error',
                'WEB log filesystem check failed because command output contains a failure keyword.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons='failure keyword: {0}'.format(failure_keyword),
            )

        if not stdout:
            return self._fail_result(
                'empty_output',
                'WEB log filesystem check failed because df output is empty.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons='empty stdout',
            )

        parsed = self._parse_df_output(stdout)
        if not parsed:
            return self._fail_result(
                'parse_error',
                'WEB log filesystem check failed because df output could not be parsed.',
                result,
                metrics,
                thresholds,
                stdout=stdout,
                stderr=stderr,
                reasons='df output parse failure',
            )

        metrics.update(parsed)
        usage_over_threshold = parsed['use_percent'] > thresholds['max_use_percent']
        avail_under_threshold = parsed['avail_gb'] < thresholds['min_avail_gb']
        metrics['usage_over_threshold'] = usage_over_threshold
        metrics['avail_under_threshold'] = avail_under_threshold

        if usage_over_threshold or avail_under_threshold:
            reasons = []
            if usage_over_threshold:
                reasons.append(
                    'use_percent {0}% is greater than max_use_percent {1}%'.format(
                        parsed['use_percent'],
                        thresholds['max_use_percent'],
                    )
                )
            if avail_under_threshold:
                reasons.append(
                    'avail_gb {0}GB is less than min_avail_gb {1}GB'.format(
                        parsed['avail_gb'],
                        thresholds['min_avail_gb'],
                    )
                )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=', '.join(reasons),
                message=(
                    'WEB log filesystem check warning. Path {path} has use_percent {use}% '
                    '(limit {limit}%) and available space {avail}GB (minimum {min_avail}GB).'
                ).format(
                    path=thresholds['web_log_fs_path'],
                    use=parsed['use_percent'],
                    limit=thresholds['max_use_percent'],
                    avail=parsed['avail_gb'],
                    min_avail=thresholds['min_avail_gb'],
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='filesystem usage and available space are within thresholds',
            message=(
                'WEB log filesystem check is normal. Path {path} has use_percent {use}% '
                '(limit {limit}%) and available space {avail}GB (minimum {min_avail}GB).'
            ).format(
                path=thresholds['web_log_fs_path'],
                use=parsed['use_percent'],
                limit=thresholds['max_use_percent'],
                avail=parsed['avail_gb'],
                min_avail=thresholds['min_avail_gb'],
            ),
        )


CHECK_CLASS = Check
