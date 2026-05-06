# -*- coding: utf-8 -*-

import re
import shlex
import time

from .common._base import BaseCheck, decode_paramiko_bytes, normalize_paramiko_text


SYSDEF_COMMAND = 'sysdef'
SOLARIS_PATH = '/usr/sbin:/usr/bin:/sbin:/bin:/usr/platform/`/usr/bin/uname -i`/sbin:$PATH'
BECOME_USER_MARKER = '__BECOME_USER__:'
COMMAND_RC_MARKER = '__FAP_CMD_RC__:'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True

    # runner.py에서 CONNECTION_METHOD='paramiko'이면 ctx['ssh']는 의도적으로 막혀 있다.
    # 따라서 이 script.py에서는 self._ssh() / self._run_paramiko_commands()를 쓰지 않고,
    # Paramiko client.invoke_shell()을 직접 열어 처리한다.
    CONNECTION_METHOD = 'paramiko'

    # Solaris 일반 shell에는 pager 처리가 필요 없으므로 linux profile 기준 옵션만 재사용한다.
    PARAMIKO_PROFILE = 'linux'

    # SSH 인증 단계 안정화:
    # auto 모드에서는 key 인증을 먼저 시도하면서 UNIX/Solaris에서 authentication timeout이 날 수 있으므로
    # password 인증만 사용하도록 고정한다.
    PARAMIKO_AUTH_METHOD = 'password'
    PARAMIKO_ALLOW_AGENT = False
    PARAMIKO_LOOK_FOR_KEYS = False

    # Solaris/UNIX 장비 인증 및 sysdef 출력 지연 대비
    PARAMIKO_TIMEOUT_SEC = 60
    PARAMIKO_BANNER_TIMEOUT_SEC = 60
    PARAMIKO_AUTH_TIMEOUT_SEC = 60
    PARAMIKO_READ_TIMEOUT_SEC = 1.0

    def _is_become_enabled(self):
        become_raw = self.get_application_credential_value('become', default=False)
        return str(become_raw).strip().lower() == 'true'

    def _build_shell_command(self, command):
        script = (
            'PATH={path}; export PATH; '
            '{command}; '
            'rc=$?; echo {rc_marker}${{rc}}'
        ).format(
            path=SOLARIS_PATH,
            command=command,
            rc_marker=COMMAND_RC_MARKER,
        )
        return '/bin/sh -c ' + shlex.quote(script)

    def _build_marked_shell_command(self, command):
        # 현재 버전에서는 whoami/id 검증과 marker 검증을 사용하지 않는다.
        # 호환성을 위해 함수는 남겨두지만 _run_invoke_shell_with_become()에서는 호출하지 않는다.
        script = (
            'PATH={path}; export PATH; '
            '{command}; '
            'rc=$?; echo {rc_marker}${{rc}}'
        ).format(
            path=SOLARIS_PATH,
            command=command,
            rc_marker=COMMAND_RC_MARKER,
        )
        return '/bin/sh -c ' + shlex.quote(script)

    def _build_su_command(self):
        become_method = str(
            self.get_application_credential_value('become_method', default='su -') or 'su -'
        ).strip().lower()
        become_user = str(
            self.get_application_credential_value('become_user', default='root') or 'root'
        ).strip() or 'root'

        normalized_become_method = ' '.join(become_method.split())

        if normalized_become_method == 'su':
            return 'su ' + shlex.quote(become_user)

        if normalized_become_method == 'su -':
            return 'su - ' + shlex.quote(become_user)

        raise ValueError(f'unsupported become_method: {become_method}')

    def _strip_become_marker(self, output):
        if not self._is_become_enabled():
            return output or '', ''

        expected_user = str(
            self.get_application_credential_value('become_user', default='root') or 'root'
        ).strip() or 'root'

        lines = (output or '').splitlines()
        marker_line = next(
            (line.strip() for line in lines if line.strip().startswith(BECOME_USER_MARKER)),
            '',
        )

        # 현재 버전은 whoami/id 검증을 하지 않고 marker도 출력하지 않는다.
        # 따라서 marker가 없어도 실패시키지 않고 출력 그대로 반환한다.
        if not marker_line:
            return (output or '').strip(), expected_user

        actual_user = marker_line.split(BECOME_USER_MARKER, 1)[1].strip()

        cleaned_lines = [
            line
            for line in lines
            if not line.strip().startswith(BECOME_USER_MARKER)
        ]
        return '\n'.join(cleaned_lines).strip(), actual_user

    def _sendline(self, channel, text):
        channel.send(str(text or '') + '\n')

    def _redact_text(self, text, *secrets):
        redacted = str(text or '')
        for secret in secrets:
            if secret:
                redacted = redacted.replace(str(secret), '*****')
        return redacted

    def _extract_prompt_from_text(self, text, command=None):
        lines = str(text or '').splitlines()
        command_text = str(command or '').strip()

        for line in reversed(lines):
            candidate = line.rstrip()
            if not candidate.strip():
                continue
            if command_text and (
                candidate.strip() == command_text
                or candidate.strip().endswith(command_text)
            ):
                continue
            return candidate

        return ''

    def _read_channel_until(
        self,
        channel,
        timeout_sec,
        prompt=None,
        patterns=None,
        command=None,
        settle_timeout_sec=None,
    ):
        compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in (patterns or [])
        ]

        buffer = ''
        deadline = time.monotonic() + float(timeout_sec)
        settle_timeout = (
            float(settle_timeout_sec)
            if settle_timeout_sec is not None
            else float(getattr(self, 'PARAMIKO_READ_TIMEOUT_SEC', 1.0))
        )
        if settle_timeout <= 0:
            settle_timeout = 0.2

        idle_deadline = None

        while True:
            now = time.monotonic()

            if now >= deadline:
                return {
                    'matched': False,
                    'timed_out': True,
                    'text': buffer,
                    'prompt': '',
                    'pattern': '',
                }

            try:
                ready = bool(channel.recv_ready())
            except Exception:
                ready = False

            if ready:
                data = channel.recv(4096)
                if not data:
                    return {
                        'matched': False,
                        'timed_out': False,
                        'text': buffer,
                        'prompt': '',
                        'pattern': '',
                        'closed': True,
                    }

                buffer += normalize_paramiko_text(decode_paramiko_bytes(data))
                idle_deadline = time.monotonic() + settle_timeout

                for pattern in compiled_patterns:
                    if pattern.search(buffer):
                        return {
                            'matched': True,
                            'timed_out': False,
                            'text': buffer,
                            'prompt': '',
                            'pattern': pattern.pattern,
                        }

                if prompt and str(buffer).rstrip().endswith(str(prompt).rstrip()):
                    return {
                        'matched': True,
                        'timed_out': False,
                        'text': buffer,
                        'prompt': str(prompt).rstrip(),
                        'pattern': '',
                    }

                continue

            # prompt를 모르는 경우에는 출력이 잠깐 멈췄을 때 마지막 non-empty line을 prompt로 추정한다.
            if not prompt and idle_deadline is not None and now >= idle_deadline and buffer.strip():
                learned_prompt = self._extract_prompt_from_text(buffer, command=command)
                if learned_prompt:
                    return {
                        'matched': True,
                        'timed_out': False,
                        'text': buffer,
                        'prompt': learned_prompt,
                        'pattern': '',
                    }

            time.sleep(0.05)

    def _open_invoke_shell(self):
        options = self._paramiko_options()
        timeout_sec = float(getattr(self, 'PARAMIKO_TIMEOUT_SEC', 60))
        read_timeout = float(getattr(self, 'PARAMIKO_READ_TIMEOUT_SEC', 1.0))

        client = self._open_paramiko_client(options)
        channel = client.invoke_shell(term='vt100', width=200, height=1000)

        # 로그인 직후 prompt를 안정적으로 얻기 위한 probe
        channel.send('\n')

        initial = self._read_channel_until(
            channel,
            timeout_sec=timeout_sec,
            prompt=None,
            patterns=None,
            settle_timeout_sec=read_timeout,
        )

        login_prompt = str(initial.get('prompt') or '').rstrip()
        if not initial.get('matched') or not login_prompt:
            try:
                channel.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass
            raise RuntimeError('login prompt was not received after invoke_shell')

        return client, channel, login_prompt

    def _strip_shell_command_output(self, command, raw_text, prompt):
        body = str(raw_text or '').rstrip()
        prompt_text = str(prompt or '').rstrip()

        if prompt_text and body.endswith(prompt_text):
            body = body[:-len(prompt_text)].rstrip()

        lines = body.splitlines()

        while lines and not lines[0].strip():
            lines = lines[1:]

        command_text = str(command or '').strip()
        if lines:
            first = lines[0].strip()
            if first == command_text or first.endswith(command_text):
                lines = lines[1:]

        return '\n'.join(lines).strip()

    def _extract_command_rc(self, output):
        rc = 0
        cleaned_lines = []

        for line in str(output or '').splitlines():
            stripped = line.strip()
            if stripped.startswith(COMMAND_RC_MARKER):
                raw_rc = stripped.split(COMMAND_RC_MARKER, 1)[1].strip()
                try:
                    rc = int(raw_rc)
                except Exception:
                    rc = 1
                continue
            cleaned_lines.append(line)

        return rc, '\n'.join(cleaned_lines).strip()

    def _su_failure_patterns(self):
        return [
            r'su:\s*sorry',
            r'sorry',
            r'authentication\s+fail',
            r'login\s+incorrect',
            r'incorrect\s+password',
            r'permission\s+denied',
        ]

    def _run_invoke_shell_without_become(self, command):
        client = None
        channel = None
        actual_command = self._build_shell_command(command)

        try:
            client, channel, login_prompt = self._open_invoke_shell()

            self._sendline(channel, actual_command)

            received = self._read_channel_until(
                channel,
                timeout_sec=self.PARAMIKO_TIMEOUT_SEC,
                prompt=login_prompt,
                command=actual_command,
                settle_timeout_sec=self.PARAMIKO_READ_TIMEOUT_SEC,
            )

            raw_output = received.get('text') or ''
            if not received.get('matched'):
                stderr = 'PARAMIKO_COMMAND_TIMEOUT: prompt was not received'
                output = self._strip_shell_command_output(actual_command, raw_output, login_prompt)
                self._record_command(command, 124, output, stderr)
                return 124, output, stderr

            output = self._strip_shell_command_output(
                actual_command,
                raw_output,
                received.get('prompt') or login_prompt,
            )
            rc, output = self._extract_command_rc(output)

            self._record_command(command, rc, output, '')
            return rc, output, ''

        except Exception as exc:
            stderr = 'PARAMIKO_CONNECTION_ERROR: ' + str(exc)
            self._record_command(command, 255, '', stderr)
            return 255, '', stderr

        finally:
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def _run_invoke_shell_with_become(self, command):
        client = None
        channel = None

        try:
            su_command = self._build_su_command()
        except ValueError as exc:
            return None, '', str(exc)

        become_user = str(
            self.get_application_credential_value('become_user', default='root') or 'root'
        ).strip() or 'root'
        become_password = str(
            self.get_application_credential_value('become_password', default='') or ''
        )

        # whoami/id 검증을 하지 않는다.
        # su 후 sorry 계열 실패 문구가 감지되지 않으면 바로 실제 점검 명령을 실행한다.
        actual_command = self._build_shell_command(command)

        try:
            client, channel, login_prompt = self._open_invoke_shell()

            # 1) su 실행
            self._sendline(channel, su_command)

            # Password 프롬프트를 명시적으로 검증하지 않는다.
            # UNIX/Solaris에서 prompt 문구가 다양하거나 감지가 늦는 경우가 있어,
            # 잠깐 출력만 읽고 실패 처리 없이 password 입력 단계로 넘어간다.
            password_prompt = self._read_channel_until(
                channel,
                timeout_sec=2,
                prompt=None,
                patterns=None,
                command=su_command,
                settle_timeout_sec=self.PARAMIKO_READ_TIMEOUT_SEC,
            )

            password_prompt_text = password_prompt.get('text') or ''
            if password_prompt_text:
                safe_text = self._redact_text(password_prompt_text, become_password)
                self._record_command(su_command, 0, safe_text, '')

            # 2) password 입력
            self._sendline(channel, become_password)

            # 3) su 실패 문구만 확인한다.
            # sorry / authentication fail / permission denied 등이 나오면 실패.
            # 그 외에는 root 여부를 별도 검증하지 않고 sysdef로 진행한다.
            after_password = self._read_channel_until(
                channel,
                timeout_sec=20,
                prompt=None,
                patterns=self._su_failure_patterns(),
                command='*******',
                settle_timeout_sec=self.PARAMIKO_READ_TIMEOUT_SEC,
            )

            after_password_text = after_password.get('text') or ''

            if after_password.get('pattern'):
                safe_text = self._redact_text(after_password_text, become_password)
                stderr = 'su authentication failed: ' + safe_text.strip()
                self._record_command(su_command, 1, safe_text, stderr)
                return 1, safe_text, stderr

            # prompt를 잡았으면 그 prompt를 기준으로 읽고,
            # 못 잡았더라도 prompt=None으로 두고 idle 기반 prompt 추정에 맡긴다.
            current_prompt = str(after_password.get('prompt') or '').rstrip()

            # 4) whoami/id 검증 없이 바로 실제 점검 명령 실행
            self._sendline(channel, actual_command)

            command_received = self._read_channel_until(
                channel,
                timeout_sec=self.PARAMIKO_TIMEOUT_SEC,
                prompt=current_prompt or None,
                command=actual_command,
                settle_timeout_sec=self.PARAMIKO_READ_TIMEOUT_SEC,
            )

            command_raw = command_received.get('text') or ''

            if not command_received.get('matched'):
                stderr = 'PARAMIKO_COMMAND_TIMEOUT: prompt was not received'
                output = self._strip_shell_command_output(
                    actual_command,
                    command_raw,
                    current_prompt,
                )
                self._record_command(command, 124, output, stderr)
                return 124, output, stderr

            output = self._strip_shell_command_output(
                actual_command,
                command_raw,
                command_received.get('prompt') or current_prompt,
            )
            rc, output = self._extract_command_rc(output)

            self._record_command(command, rc, output, '')
            return rc, output, ''

        except Exception as exc:
            stderr = 'PARAMIKO_CONNECTION_ERROR: ' + str(exc)
            self._record_command(command, 255, '', stderr)
            return 255, '', stderr

        finally:
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def _run_command(self, command):
        if self._is_become_enabled():
            return self._run_invoke_shell_with_become(command)

        return self._run_invoke_shell_without_become(command)

    def _parse_parameters(self, text):
        parameter_map = {}
        section_names = []
        current_section = ''

        for line in text.splitlines():
            stripped = line.strip()
            section_match = stripped.startswith('*') and stripped.endswith('*')
            if section_match:
                current_section = stripped.strip('*').strip()
                if current_section:
                    section_names.append(current_section)
                continue

            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if not key or not value or key.startswith('*'):
                continue

            parameter_map[key] = {
                'value': value,
                'section': current_section,
            }

        return {
            'parameter_map': parameter_map,
            'section_names': section_names,
        }

    def run(self):
        required_parameters_raw = self.get_threshold_var(
            'required_parameters',
            default='shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax',
            value_type='str',
        )
        failure_keywords_raw = self.get_threshold_var(
            'failure_keywords',
            default='',
            value_type='str',
        )

        rc, out, err = self._run_command(SYSDEF_COMMAND)

        if rc is None:
            return self.fail(
                '권한 상승 설정 오류',
                message=(err or '').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'Paramiko SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        try:
            text, actual_become_user = self._strip_become_marker(out)
        except ValueError as exc:
            return self.fail(
                '권한 상승 사용자 확인 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (text or '').strip()

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    '현재 상태: sysdef 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            text,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: sysdef 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        combined_output = '\n'.join(
            part for part in (text, (err or '').strip())
            if part
        )
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]

        if matched_failure_keywords:
            return self.fail(
                '커널 파라미터 실패 키워드 감지',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_parameters(text)
        parameter_map = parsed['parameter_map']
        section_names = parsed['section_names']

        if not parameter_map:
            return self.fail(
                '커널 파라미터 파싱 실패',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    '현재 상태: sysdef 출력에서 파라미터 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        required_sections = [
            'Tunable Parameters',
            'File System Parameters',
            'Memory Management Parameters',
            'IPC Parameters',
        ]
        missing_sections = [
            section for section in required_sections
            if section not in section_names
        ]

        if missing_sections:
            return self.fail(
                '커널 파라미터 섹션 누락',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: sysdef 출력에서 핵심 섹션 {missing_sections}를 확인하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        required_parameters = [
            token.strip()
            for token in required_parameters_raw.split(',')
            if token.strip()
        ]
        missing_parameters = [
            name for name in required_parameters
            if name not in parameter_map
        ]

        if missing_parameters:
            return self.fail(
                '커널 파라미터 누락',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: 핵심 파라미터 {missing_parameters}를 sysdef 출력에서 확인하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        summary = ', '.join(
            f'{name}={parameter_map[name]["value"]}'
            for name in required_parameters
        )

        return self.ok(
            metrics={
                'parameter_count': len(parameter_map),
                'section_count': len(section_names),
                'section_names': section_names,
                'required_parameter_count': len(required_parameters),
                'required_parameters': {
                    name: {
                        'value': parameter_map[name]['value'],
                        'section': parameter_map[name]['section'],
                    }
                    for name in required_parameters
                },
                'matched_failure_keywords': matched_failure_keywords,
                'become_user': actual_become_user,
            },
            thresholds={
                'required_parameters': required_parameters,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'핵심 커널 파라미터 {len(required_parameters)}개와 '
                f'주요 섹션 {len(required_sections)}개가 모두 조회되었습니다.'
            ),
            message=(
                'Solaris 커널 파라미터가 정상입니다. '
                f'현재 상태: 섹션 {len(section_names)}개, 파라미터 {len(parameter_map)}개, '
                f'핵심 파라미터 {len(required_parameters)}개가 모두 확인되었습니다. {summary}.'
            ),
        )


CHECK_CLASS = Check