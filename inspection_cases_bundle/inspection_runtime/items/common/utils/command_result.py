# -*- coding: utf-8 -*-
"""Command result, raw output, timeout/error normalization helpers.

The helpers in this module are side-effect-light ports of the legacy
``BaseCheck`` command/result helpers.  Public ``BaseCheck`` method names stay
as wrappers so item scripts keep their existing API and result schema.
"""

from .policy import (
    COMMAND_ERROR_PATTERNS,
    CONNECTION_ERROR_MARKERS,
    detect_command_error,
    evaluate_policy_text,
    extract_lines,
    is_connection_error,
    is_not_applicable,
)


def describe_rc(rc):
    """Return the legacy Korean description for common shell/SSH rc values."""
    rc_map = {
        0: '정상 종료',
        1: '일반 오류 또는 결과 없음/미일치',
        2: '잘못된 사용/실행 오류',
        126: '권한 없음 또는 실행 불가',
        127: '명령어를 찾을 수 없음',
        124: '명령 시간 초과',
        130: '사용자 인터럽트(Ctrl+C)',
        255: 'SSH/원격 실행 오류',
    }
    if rc in rc_map:
        return rc_map[rc]
    if isinstance(rc, int) and rc < 0:
        return '프로세스 비정상 종료'
    return '비정상 종료'


def build_command_history_raw_output(command_history):
    if not command_history:
        return ""
    parts = []
    for idx, item in enumerate(command_history, 1):
        rc = item.get('rc')
        rc_desc = describe_rc(rc)
        stdout = (item.get('stdout') or "").rstrip()
        stderr = (item.get('stderr') or "").rstrip()

        section = [
            f"[점검 단계 {idx}]",
            f" - 실행 명령어: {item.get('cmd', '')}",
            f" - 명령 종료코드: rc={rc} ({rc_desc})",
        ]
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


def build_virtual_raw_output(raw_output=None, stdout=None, stderr=None):
    """Build the legacy fallback raw_output when no command history exists."""
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


def build_terminal_history_raw_output(terminal_history):
    if not terminal_history:
        return ""

    parts = []
    for idx, item in enumerate(terminal_history, 1):
        kind = str(item.get('kind') or '').strip().lower()
        raw_text = str(item.get('text') or '')
        text = '<space>' if raw_text == ' ' else raw_text.rstrip()
        section = [f"[점검 단계 {idx}]"]

        if kind == 'send':
            send_label = '자동 응답' if item.get('auto') else '터미널 송신'
            section.append(f" - {send_label}: {text}")
        elif kind == 'recv':
            recv_label = '터미널 수신(timeout)' if item.get('timeout') else '터미널 수신'
            section.append(f" - {recv_label}: {text}")
        else:
            section.append(f" - 터미널 이벤트: {text}")

        parts.append("\n".join(section).rstrip())

    return "\n\n".join(parts).strip()


def resolve_raw_output(command_history, terminal_history, raw_output=None, stdout=None, stderr=None):
    if raw_output == '점검 스크립트 없음':
        return raw_output

    history_text = build_command_history_raw_output(command_history)
    terminal_text = build_terminal_history_raw_output(terminal_history)
    if history_text and terminal_text:
        return f'{history_text}\n\n{terminal_text}'.strip()
    if history_text:
        return history_text
    if terminal_text:
        return terminal_text

    if raw_output not in (None, '') or stdout not in (None, '') or stderr not in (None, ''):
        return build_virtual_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)

    return build_virtual_raw_output()



def strip_shell_output_text(text):
    """Strip shell stdout/stderr text with the legacy direct .strip() behavior."""
    return text.strip()


def select_shell_failure_raw_output(stdout, stderr):
    """Return the legacy shell failure raw_output preference: non-empty stdout, else stderr."""
    stripped_stdout = stdout.strip() if stdout and stdout.strip() else ''
    return stripped_stdout if stripped_stdout else stderr.strip()


def summarize_raw_output(raw_output, preview_limit=200):
    """Return (raw_len, raw_preview) for runner result logging without changing result data."""
    raw_len = len(raw_output) if isinstance(raw_output, str) else 0
    raw_preview = ''
    if isinstance(raw_output, str) and raw_output:
        raw_preview = raw_output.replace('\n', '\\n')[:preview_limit]
    return raw_len, raw_preview

def build_paramiko_result(
    command,
    rc,
    stdout='',
    stderr='',
    raw_output='',
    timed_out=False,
    prompt='',
    display_command='',
    hide_command=False,
):
    return {
        'command': command,
        'display_command': display_command or command,
        'hide_command': bool(hide_command),
        'rc': rc,
        'stdout': stdout or '',
        'stderr': stderr or '',
        'raw_output': raw_output or '',
        'timed_out': bool(timed_out),
        'prompt': prompt or '',
    }


def strip_paramiko_command_output(command, text, prompt, command_matches_line_func=None):
    body = str(text or '').rstrip()
    prompt_text = str(prompt or '').rstrip()
    if prompt_text and body.endswith(prompt_text):
        body = body[:-len(prompt_text)].rstrip()
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines = lines[1:]
    if command_matches_line_func is not None and lines and command_matches_line_func(command, lines[0]):
        lines = lines[1:]
    return '\n'.join(lines).strip()



def record_command(command_history, cmd, rc, out, err):
    command_history.append({
        'cmd': cmd,
        'rc': rc,
        'stdout': out if out is not None else '',
        'stderr': err if err is not None else '',
    })


def record_terminal_event(terminal_history, event):
    if not isinstance(event, dict):
        return
    copied = dict(event)
    copied['text'] = copied.get('text') if copied.get('text') is not None else ''
    terminal_history.append(copied)
