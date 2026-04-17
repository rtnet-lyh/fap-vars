# -*- coding: utf-8 -*-

import re

from .helpers import NetworkHelper, VMwareHelper, WebHelper


class BaseCheck:
    """점검 항목 공통 베이스 클래스.

    - 결과 포맷(`ok/warn/fail`)을 일관되게 생성한다.
    - 항목 코드/입력 payload 등 실행 컨텍스트는 `ctx`에서 참조한다.
    """

    ITEM_TYPE = 'python'
    # 기본은 호스트 접속 사용
    USE_HOST_CONNECTION = True
    # 기본 원격 연결 방식
    CONNECTION_METHOD = 'ssh'
    # SSH 명령 최대 대기 시간(초), None이면 runner 기본값 사용
    SSH_COMMAND_TIMEOUT_SEC = None
    # WinRM 사용 시 기본 쉘
    WINRM_SHELL = 'powershell'

    def __init__(self, ctx):
        # ctx에는 ssh 함수, 접속 정보, 임계치 등이 들어있다.
        self.ctx = ctx
        # raw_output 기본값 생성을 위해 명령 실행 이력을 누적한다.
        self._command_history = []
        self._threshold_list_map_cache = None
        self.network_helper = NetworkHelper(self)
        self.vmware_helper = VMwareHelper(self)
        self.web_helper = WebHelper(self)

    def run(self):
        raise NotImplementedError

    def _ssh(self, cmd):
        """현재 항목의 host 컨텍스트로 명령을 1회 실행한다."""
        rc, out, err = self.ctx['ssh'](
            cmd,
            self.ctx['host'],
            self.ctx['port'],
            self.ctx['user'],
            self.ctx['password'],
            self.ctx['ssh_options'],
        )
        self._record_command(cmd, rc, out, err)
        return rc, out, err

    # Network helper wrappers
    def _run_show(self, cmd):
        return self.network_helper.run_show(cmd)

    def _run_config(self, variant=None):
        return self.network_helper.run_config(variant=variant)

    def _section_vty(self, variant=None):
        return self.network_helper.section_vty(variant=variant)

    def _grep_lines(self, text, pattern):
        return self.network_helper.grep_lines(text, pattern)

    def _has(self, text, pattern):
        return self.network_helper.has(text, pattern)

    # Web helper wrappers
    def _source_dicts(self):
        return self.web_helper.source_dicts()

    def _get_source_value(self, *keys, **kwargs):
        return self.web_helper.get_source_value(*keys, **kwargs)

    def _get_list_value(self, *keys, **kwargs):
        return self.web_helper.get_list_value(*keys, **kwargs)

    def _resolve_base_url(self):
        return self.web_helper.resolve_base_url()

    def _build_url(self, path_or_url=None):
        return self.web_helper.build_url(path_or_url=path_or_url)

    def _new_cookie_jar(self):
        return self.web_helper.new_cookie_jar()

    def _request(self, path_or_url=None, method='GET', params=None, data=None, headers=None, follow_redirects=True, cookie_jar=None, timeout=5):
        return self.web_helper.request(
            path_or_url=path_or_url,
            method=method,
            params=params,
            data=data,
            headers=headers,
            follow_redirects=follow_redirects,
            cookie_jar=cookie_jar,
            timeout=timeout,
        )

    def _find_markers(self, text, markers):
        return self.web_helper.find_markers(text, markers)

    def _get_session_cookie_values(self, response=None, cookie_jar=None):
        return self.web_helper.get_session_cookie_values(response=response, cookie_jar=cookie_jar)

    def _extract_cookie_tokens(self, response=None, cookie_jar=None):
        return self.web_helper.extract_cookie_tokens(response=response, cookie_jar=cookie_jar)

    def _login(self, cookie_jar=None):
        return self.web_helper.login(cookie_jar=cookie_jar)

    def _make_multipart(self, fields, file_field, filename, content, content_type='application/octet-stream'):
        return self.web_helper.make_multipart(
            fields=fields,
            file_field=file_field,
            filename=filename,
            content=content,
            content_type=content_type,
        )

    # Windows/WinRM helper wrappers
    def _run_ps(self, command):
        return self._ssh(command)

    # 텍스트 결과를 정책 mode 기준으로 공통 판정한다.
    def _evaluate_policy_text(self, mode, text, rule, rc=None):
        if mode == 'pass_if_output':
            return bool(text)
        if mode == 'pass_if_no_output':
            return not bool(text)
        if mode == 'pass_if_regex':
            pattern = rule.get('pattern', '')
            return bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
        if mode == 'pass_if_not_regex':
            pattern = rule.get('pattern', '')
            return not bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
        if mode == 'pass_if_int_le':
            match = re.search(r'(-?\d+)', text)
            if not match:
                return False
            try:
                return int(match.group(1)) <= int(rule.get('threshold', 0))
            except Exception:
                return False
        if mode == 'pass_if_int_ge':
            match = re.search(r'(-?\d+)', text)
            if not match:
                return False
            try:
                return int(match.group(1)) >= int(rule.get('threshold', 0))
            except Exception:
                return False
        return rc == 0 if rc is not None else False

    def _extract_lines(self, text, pattern):
        return [ln.strip() for ln in (text or '').splitlines() if re.search(pattern, ln, re.IGNORECASE)]

    def _detect_command_error(self, *texts, extra_patterns=None):
        patterns = [
            'illegal option',
            'invalid option',
            'unknown option',
            'usage:',
            'command not found',
            'not found',
            'no such file',
            'cannot',
            '명령을 찾을 수 없습니다',
            '찾을 수 없습니다',
        ]
        if extra_patterns:
            patterns.extend([str(pattern).lower() for pattern in extra_patterns if pattern])

        for raw in texts:
            output = (raw or '').strip()
            if not output:
                continue
            output_lower = output.lower()
            for pattern in patterns:
                if pattern in output_lower:
                    return output.splitlines()[0].strip()
        return None

    def _to_mb(self, value):
        text = str(value or '').strip()
        if not text:
            return None
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([kmgt]?i?b?|)$', text, re.IGNORECASE)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).lower()
        if unit in ('', 'm', 'mb', 'mi', 'mib'):
            return number
        if unit in ('k', 'kb', 'ki', 'kib'):
            return number / 1024.0
        if unit in ('g', 'gb', 'gi', 'gib'):
            return number * 1024.0
        if unit in ('t', 'tb', 'ti', 'tib'):
            return number * 1024.0 * 1024.0
        if unit in ('b',):
            return number / (1024.0 * 1024.0)
        return None

    def _parse_mpstat_field(self, text, field_name):
        target = field_name.lower().lstrip('%')
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        header = None
        data = None

        for line in lines:
            lower = line.lower()
            if '%' + target in lower:
                header = re.split(r'\s+', line)
                continue
            if re.search(r'(^|\s)(average:)?\s*all(\s|$)', lower):
                data = re.split(r'\s+', line)

        if not header or not data:
            return None

        normalized = [token.lower() for token in header]
        column = '%' + target
        if column not in normalized:
            return None

        index = normalized.index(column)
        if index >= len(data):
            return None

        try:
            return round(float(data[index]), 2)
        except Exception:
            return None

    def _is_not_applicable(self, rc, err):
        text = (err or '').strip()
        if rc in (901, 902):
            return True
        if 'WINRM_UNAVAILABLE' in text or 'WINRM_EXEC_ERROR' in text:
            return True
        return False

    def _is_connection_error(self, rc, err):
        text = (err or '').strip().lower()
        if rc in (255, 901, 902):
            return True
        markers = (
            'no route to host',
            'network is unreachable',
            'connection refused',
            'connection timed out',
            'operation timed out',
            'could not resolve hostname',
            'host key verification failed',
            'permission denied',
            'connection reset by peer',
            'sshpass not installed',
            'winrm_unavailable',
            'winrm_exec_error',
        )
        return any(marker in text for marker in markers)

    def _record_command(self, cmd, rc, out, err):
        self._command_history.append({
            'cmd': cmd,
            'rc': rc,
            'stdout': out if out is not None else '',
            'stderr': err if err is not None else '',
        })

    def get_threshold_list_map(self):
        """item_payload.threshold_list를 {name: value1} 딕셔너리로 변환한다."""
        if self._threshold_list_map_cache is not None:
            return self._threshold_list_map_cache

        payload = self.ctx.get('item_payload') or {}
        threshold_list = payload.get('threshold_list') or []
        mapped = {}

        if isinstance(threshold_list, list):
            for item in threshold_list:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('name', '')).strip()
                if not name:
                    continue
                mapped[name] = item.get('value1')

        self._threshold_list_map_cache = mapped
        return mapped

    # application 계정이 필요한 항목은 아래 헬퍼로 조회한다.
    # 예)
    #   app_cred = self.get_application_credential()
    #   app_user = self.get_application_credential_value('username')
    #   app_password = self.get_application_credential_value('password')
    #
    # 기본 접속 계정/장비 계정이 필요한 항목은 connection 헬퍼를 사용한다.
    # 예)
    #   conn_type = self.get_connection_credential().get('credential_type_name')
    #   conn_user = self.get_connection_value('username')
    #   enable_password = self.get_connection_value('en_password')
    def get_application_credential(self):
        """현재 항목에 매핑된 application credential 원본을 반환한다."""
        cred = self.ctx.get('application_credential') or {}
        if isinstance(cred, dict):
            return cred
        return {}

    def get_connection_credential(self):
        """현재 항목에 매핑된 connection credential 원본을 반환한다."""
        cred = self.ctx.get('connection_credential') or {}
        if isinstance(cred, dict):
            return cred
        return {}

    def get_connection_credential_data(self):
        """현재 항목에 매핑된 connection credential data를 반환한다."""
        data = self.ctx.get('connection_credential_data') or {}
        if isinstance(data, dict):
            return data
        cred = self.get_connection_credential()
        data = cred.get('data') or {}
        if isinstance(data, dict):
            return data
        return {}

    def get_connection_value(self, key, default=None):
        """connection credential data에서 key 값을 조회한다."""
        data = self.get_connection_credential_data()
        return data.get(key, default)

    def get_application_credential_data(self):
        """현재 항목에 매핑된 application credential data를 반환한다."""
        data = self.ctx.get('application_credential_data') or {}
        if isinstance(data, dict):
            return data
        cred = self.get_application_credential()
        data = cred.get('data') or {}
        if isinstance(data, dict):
            return data
        return {}

    def get_application_credential_value(self, key, default=None):
        """application credential data에서 key 값을 조회한다."""
        data = self.get_application_credential_data()
        return data.get(key, default)

    def _cast_threshold_var(self, raw_value, default, value_type=None):
        """원시 value1 값을 지정 타입으로 변환한다."""
        if value_type is None:
            if isinstance(default, bool):
                value_type = 'bool'
            elif isinstance(default, int):
                value_type = 'int'
            elif isinstance(default, float):
                value_type = 'float'
            else:
                value_type = 'str'

        if isinstance(value_type, type):
            if value_type is bool:
                value_type = 'bool'
            elif value_type is int:
                value_type = 'int'
            elif value_type is float:
                value_type = 'float'
            else:
                value_type = 'str'

        value_type = str(value_type).lower()

        if value_type == 'int':
            return int(str(raw_value).strip())
        if value_type == 'float':
            return float(str(raw_value).strip())
        if value_type == 'bool':
            text = str(raw_value).strip().lower()
            return text in ('1', 'true', 'y', 'yes', 'on')
        if value_type == 'raw':
            return raw_value
        return str(raw_value)

    def get_threshold_var(self, key, default=None, value_type=None, return_source=False):
        """threshold_list에서 key(name) 기준으로 값을 조회한다.

        - key가 없거나 변환 실패 시 default 반환
        - value_type 미지정 시 default 타입으로 자동 추론
        """
        mapped = self.get_threshold_list_map()
        raw_value = mapped.get(key)

        has_raw = (
            key in mapped and
            raw_value is not None and
            (not isinstance(raw_value, str) or raw_value.strip() != '')
        )

        if not has_raw:
            if return_source:
                return default, 'default'
            return default

        try:
            value = self._cast_threshold_var(raw_value, default, value_type=value_type)
            if return_source:
                return value, 'api'
            return value
        except Exception:
            if return_source:
                return default, 'default'
            return default

    def _describe_rc(self, rc):
        # 쉘/SSH에서 자주 쓰이는 종료 코드를 한글 설명으로 매핑한다.
        rc_map = {
            0: '정상 종료',
            1: '일반 오류 또는 결과 없음/미일치',
            2: '잘못된 사용/실행 오류',
            126: '권한 없음 또는 실행 불가',
            127: '명령어를 찾을 수 없음',
            130: '사용자 인터럽트(Ctrl+C)',
            255: 'SSH/원격 실행 오류',
        }
        if rc in rc_map:
            return rc_map[rc]
        if isinstance(rc, int) and rc < 0:
            return '프로세스 비정상 종료'
        return '비정상 종료'

    def _build_history_raw_output(self):
        if not self._command_history:
            return ""
        parts = []
        for idx, item in enumerate(self._command_history, 1):
            rc = item.get('rc')
            rc_desc = self._describe_rc(rc)
            stdout = (item.get('stdout') or "").rstrip()
            stderr = (item.get('stderr') or "").rstrip()

            section = [
                f"[점검 단계 {idx}]",
                f" - 실행 명령어: {item.get('cmd', '')}",
                f" - 명령 종료코드: rc={rc} ({rc_desc})",
            ]
            # stdout/stderr가 비어 있지 않을 때만 출력 내용을 기록한다.
            if stdout and stderr:
                section.extend([
                    f" - 출력 내용(stdout): {stdout}",
                    f" - 출력 내용(stderr): {stderr}",
                ])
            elif stdout:
                section.append(f" - 출력 내용: {stdout}")
            elif stderr:
                section.append(f" - 출력 내용: {stderr}")
            parts.append("\n".join(section).rstrip())
        return "\n\n".join(parts).strip()

    def _build_virtual_raw_output(self, raw_output=None, stdout=None, stderr=None):
        """명령 이력이 없을 때도 출력 형식을 통일한다.

        - 점검 스크립트에서 `_ssh`를 통하지 않았거나
        - 로컬 계산값만 있는 경우에 fallback으로 사용한다.
        """
        out = (stdout or "").rstrip()
        err = (stderr or "").rstrip()
        raw = (raw_output or "").rstrip()

        section = [
            "[점검 단계 1]",
            " - 실행 명령어: (명령 이력 없음)",
            " - 명령 종료코드: rc=unknown (명령 이력 없음)",
        ]
        if out and err:
            section.extend([
                f" - 출력 내용(stdout): {out}",
                f" - 출력 내용(stderr): {err}",
            ])
        elif out:
            section.append(f" - 출력 내용: {out}")
        elif err:
            section.append(f" - 출력 내용: {err}")
        elif raw:
            section.append(f" - 출력 내용: {raw}")

        return "\n".join(section).rstrip()

    def _resolve_raw_output(self, raw_output=None, stdout=None, stderr=None):
        # 미구현 항목은 사용자 요청에 따라 문자열을 그대로 저장한다.
        if raw_output == '점검 스크립트 없음':
            return raw_output

        # 1순위: 실제 명령 이력(점검 단계 포맷)
        history_text = self._build_history_raw_output()
        if history_text:
            return history_text

        # 2순위: 명령 이력이 없더라도 동일 포맷으로 fallback
        if raw_output not in (None, '') or stdout not in (None, '') or stderr not in (None, ''):
            return self._build_virtual_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)

        # 3순위: 남길 데이터가 없어도 포맷은 통일한다.
        return self._build_virtual_raw_output()

    def ok(self, metrics=None, thresholds=None, reasons=None, raw_output=None, message=None):
        # 정상 결과 포맷
        if isinstance(reasons, list):
            reasons = ", ".join(reasons)
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'ok',
            'metrics': metrics or {},
            'thresholds': thresholds or {},
            'reasons': reasons or "",
            'raw_output': self._resolve_raw_output(raw_output=raw_output),
            'message': message or "",
        }
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data

    def warn(self, metrics=None, thresholds=None, reasons=None, raw_output=None, message=None):
        # 경고 결과 포맷
        if isinstance(reasons, list):
            reasons = ", ".join(reasons)
        if not message:
            message = reasons or ""
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'warn',
            'metrics': metrics or {},
            'thresholds': thresholds or {},
            'reasons': reasons or "",
            'message': message,
            'raw_output': self._resolve_raw_output(raw_output=raw_output),
        }
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data

    def not_applicable(self, message='대상미해당', raw_output=None):
        """대상 제품/벤더/환경 미해당 시 표준 반환."""
        return self.warn(
            metrics={'applicable': False},
            reasons='대상미해당',
            message=message or '대상미해당',
            raw_output=raw_output,
        ) if not message else self.warn(
            metrics={'applicable': False},
            reasons=message,
            message=message,
            raw_output=raw_output,
        )

    def fail(self, error, message=None, stdout=None, stderr=None, raw_output=None):
        # 실패 결과 포맷
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'fail',
            'error': error,
        }
        if message is not None:
            data['message'] = message
        if stdout is not None:
            data['stdout'] = stdout
        if stderr is not None:
            data['stderr'] = stderr
        data['raw_output'] = self._resolve_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data


class ShellCheck(BaseCheck):
    """Shell 기반 점검 항목 베이스 클래스."""

    ITEM_TYPE = 'shell'
    SCRIPT_PATH = None
    SCRIPT_INLINE = None

    def script_command(self):
        # 쉘 스크립트 실행 커맨드 구성
        if self.SCRIPT_PATH:
            return f"bash {self.SCRIPT_PATH}"
        if self.SCRIPT_INLINE:
            # inline script via bash -lc
            return "bash -lc " + __import__('json').dumps(self.SCRIPT_INLINE)
        return None
