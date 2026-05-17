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

    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _split_csv(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split(',')
            if token.strip()
        ]

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _get_failure_keywords(self):
        return self._split_csv(
            self.get_threshold_var(
                'failure_keywords',
                default=self.DEFAULT_FAILURE_KEYWORDS,
                value_type='str',
            )
        )

    def _load_thresholds(self):
        web_app_fs_path = self.get_threshold_var(
            'web_app_fs_path',
            default='/home/exTMS/tmax/webtob/docs',
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
            'web_app_fs_path': web_app_fs_path,
            'max_use_percent': max_use_percent,
            'min_avail_gb': min_avail_gb,
            'failure_keywords': failure_keywords,
        }

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
                'display_command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'timed_out': False,
            }
        return results[0]

    def _contains_failure_keyword(self, failure_keywords, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        combined_lower = combined.lower()
        for keyword in failure_keywords:
            if keyword and keyword.lower() in combined_lower:
                return keyword
        return ''

    def _base_metrics(self, command, result, thresholds, stdout='', stderr=''):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'web_app_fs_path': thresholds.get('web_app_fs_path'),
            'filesystem': None,
            'size_raw': None,
            'used_raw': None,
            'avail_raw': None,
            'avail_gb': None,
            'use_percent': None,
            'mounted_on': None,
            'max_use_percent': thresholds.get('max_use_percent'),
            'min_avail_gb': thresholds.get('min_avail_gb'),
            'usage_over_threshold': None,
            'avail_under_threshold': None,
        }

    def _fail_result(self, error, message, result, metrics, thresholds, stdout, stderr, reasons):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def _command_failure_reason(self, result, stdout, stderr, failure_keywords):
        if bool(result.get('timed_out', False)):
            return 'df 명령 실행 중 timeout이 발생했습니다.'

        rc = result.get('rc')
        if rc != 0:
            return 'df 명령 종료코드가 rc={0}입니다.'.format(rc)

        keyword = self._contains_failure_keyword(failure_keywords, stdout, stderr)
        if keyword:
            return 'df 명령 출력에서 실패 키워드가 확인되었습니다: {0}'.format(keyword)

        return ''

    def _to_gb(self, value):
        text = str(value or '').strip()
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)$', text)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).strip().lower()

        if unit in ('', 'g', 'gb', 'gi', 'gib'):
            return number
        if unit in ('k', 'kb', 'ki', 'kib'):
            return number / (1024.0 * 1024.0)
        if unit in ('m', 'mb', 'mi', 'mib'):
            return number / 1024.0
        if unit in ('t', 'tb', 'ti', 'tib'):
            return number * 1024.0
        if unit in ('p', 'pb', 'pi', 'pib'):
            return number * 1024.0 * 1024.0
        if unit in ('b',):
            return number / (1024.0 * 1024.0 * 1024.0)
        return None

    def _parse_df_tokens(self, tokens, previous_tokens=None):
        use_index = None
        for idx, token in enumerate(tokens):
            if re.match(r'^[0-9]+%$', token):
                use_index = idx
                break

        if use_index is None:
            return None

        parse_tokens = list(tokens)
        if (use_index <= 3 or not parse_tokens[:use_index - 3]) and previous_tokens:
            parse_tokens = list(previous_tokens) + parse_tokens
            for idx, token in enumerate(parse_tokens):
                if re.match(r'^[0-9]+%$', token):
                    use_index = idx
                    break

        if use_index < 3 or use_index + 1 >= len(parse_tokens):
            return None

        filesystem_tokens = parse_tokens[:use_index - 3]
        if not filesystem_tokens:
            return None

        size_raw = parse_tokens[use_index - 3]
        used_raw = parse_tokens[use_index - 2]
        avail_raw = parse_tokens[use_index - 1]
        use_raw = parse_tokens[use_index]
        mounted_on = ' '.join(parse_tokens[use_index + 1:]).strip()

        if not mounted_on:
            return None

        try:
            use_percent = int(use_raw.rstrip('%'))
        except Exception:
            return None

        avail_gb = self._to_gb(avail_raw)
        if avail_gb is None:
            return None

        return {
            'filesystem': ' '.join(filesystem_tokens).strip(),
            'size_raw': size_raw,
            'used_raw': used_raw,
            'avail_raw': avail_raw,
            'avail_gb': round(float(avail_gb), 3),
            'use_percent': use_percent,
            'mounted_on': mounted_on,
        }

    def _parse_df_output(self, stdout):
        lines = [line.rstrip() for line in str(stdout or '').splitlines() if line.strip()]
        previous_tokens = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith('filesystem'):
                previous_tokens = None
                continue

            tokens = re.split(r'\s+', stripped)
            parsed = self._parse_df_tokens(tokens, previous_tokens=previous_tokens)
            if parsed:
                return parsed

            previous_tokens = tokens

        return None

    def run(self):
        thresholds = self._load_thresholds()
        command = 'df -h {0}'.format(self._quote(thresholds['web_app_fs_path']))
        timeout = self.DEFAULT_COMMAND_TIMEOUT

        result = self._run_command(command, timeout=timeout)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()

        metrics = self._base_metrics(command, result, thresholds, stdout=stdout, stderr=stderr)

        fail_reason = self._command_failure_reason(
            result,
            stdout,
            stderr,
            thresholds['failure_keywords'],
        )
        if fail_reason:
            return self._fail_result(
                'df 명령 실행 실패',
                'WEB 어플리케이션 설치 파일시스템 점검에 실패했습니다. df 명령 실행 오류로 파일시스템 상태를 판단하지 못했습니다.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                fail_reason,
            )

        if not stdout:
            reason = 'df 명령 출력이 비어 있습니다.'
            return self._fail_result(
                '점검 출력 없음',
                'WEB 어플리케이션 설치 파일시스템 점검에 실패했습니다. df 명령 출력이 비어 있어 파일시스템 상태를 판단하지 못했습니다.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                reason,
            )

        parsed = self._parse_df_output(stdout)
        if not parsed:
            reason = 'df -h 출력에서 파일시스템, 용량, 여유 공간, 사용률, 마운트 경로를 파싱하지 못했습니다.'
            return self._fail_result(
                'df 출력 파싱 실패',
                'WEB 어플리케이션 설치 파일시스템 점검에 실패했습니다. df 명령 실행 오류, 출력 없음 또는 파싱 실패로 파일시스템 상태를 판단하지 못했습니다.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                reason,
            )

        usage_over_threshold = parsed['use_percent'] > thresholds['max_use_percent']
        avail_under_threshold = parsed['avail_gb'] < thresholds['min_avail_gb']

        metrics.update(parsed)
        metrics.update({
            'usage_over_threshold': usage_over_threshold,
            'avail_under_threshold': avail_under_threshold,
        })

        if usage_over_threshold or avail_under_threshold:
            reasons = []
            if usage_over_threshold:
                reasons.append(
                    '사용률 {0}%가 기준 {1}%를 초과했습니다.'.format(
                        parsed['use_percent'],
                        thresholds['max_use_percent'],
                    )
                )
            if avail_under_threshold:
                reasons.append(
                    '여유 공간 {0}GB가 기준 {1}GB 미만입니다.'.format(
                        parsed['avail_gb'],
                        thresholds['min_avail_gb'],
                    )
                )

            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=', '.join(reasons),
                message=(
                    'WEB 어플리케이션 설치 파일시스템 점검 결과 경고입니다. '
                    '{path} 경로의 사용률은 {use_percent}%로 기준 {max_use_percent}%를 초과했거나, '
                    '여유 공간이 {avail_gb}GB로 기준 {min_avail_gb}GB 미만입니다.'
                ).format(
                    path=thresholds['web_app_fs_path'],
                    use_percent=parsed['use_percent'],
                    max_use_percent=thresholds['max_use_percent'],
                    avail_gb=parsed['avail_gb'],
                    min_avail_gb=thresholds['min_avail_gb'],
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='파일시스템 사용률과 여유 공간이 모두 기준을 만족합니다.',
            message=(
                'WEB 어플리케이션 설치 파일시스템 점검 결과 정상입니다. '
                '{path} 경로의 사용률은 {use_percent}%로 기준 {max_use_percent}% 이하이고, '
                '여유 공간은 {avail_gb}GB로 기준 {min_avail_gb}GB 이상입니다.'
            ).format(
                path=thresholds['web_app_fs_path'],
                use_percent=parsed['use_percent'],
                max_use_percent=thresholds['max_use_percent'],
                avail_gb=parsed['avail_gb'],
                min_avail_gb=thresholds['min_avail_gb'],
            ),
        )


CHECK_CLASS = Check
