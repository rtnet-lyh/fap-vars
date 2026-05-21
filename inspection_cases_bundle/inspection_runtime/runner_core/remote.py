# -*- coding: utf-8 -*-


POWERSHELL_UTF8_PREFIX = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
)

def strip_runtime_warnings(text, coerce_text_func=None):
    from items.common.utils.encoding import strip_runtime_warnings as _strip_runtime_warnings

    return _strip_runtime_warnings(text, coerce_text_func=coerce_text_func)


def create_winrm_session(host, port, user, password, transport, server_cert_validation, operation_timeout_sec, read_timeout_sec):
    import winrm
    endpoint = f"http://{host}:{port}/wsman"
    if int(port) == 5986:
        endpoint = f"https://{host}:{port}/wsman"
    return winrm.Session(
        target=endpoint,
        auth=(user or '', password or ''),
        transport=transport,
        server_cert_validation=server_cert_validation,
        operation_timeout_sec=operation_timeout_sec,
        read_timeout_sec=read_timeout_sec,
    )


def run_winrm_with_session(
    cmd,
    host,
    port,
    user,
    password,
    _ssh_options,
    winrm_options=None,
    session_factory=None,
    decode_stream_bytes_func=None,
    strip_runtime_warnings_func=None,
):
    """WinRM 기반 원격 명령 실행.

    반환 형식은 SSH 실행과 동일하게 (rc, stdout, stderr)로 맞춘다.
    """
    opts = winrm_options or {}
    transport = opts.get('transport', 'ntlm')
    server_cert_validation = opts.get('server_cert_validation', 'ignore')
    operation_timeout_sec = int(opts.get('operation_timeout_sec', 30))
    read_timeout_sec = int(opts.get('read_timeout_sec', 60))
    shell = (opts.get('shell') or 'powershell').lower()

    if session_factory is None:
        session_factory = create_winrm_session

    try:
        session = session_factory(
            host,
            int(port),
            user or '',
            password or '',
            transport,
            server_cert_validation,
            operation_timeout_sec,
            read_timeout_sec,
        )
    except Exception as exc:
        return 901, '', 'WINRM_UNAVAILABLE: ' + str(exc)

    if decode_stream_bytes_func is None:
        from items.common.utils.encoding import decode_bytes as decode_stream_bytes_func
    if strip_runtime_warnings_func is None:
        strip_runtime_warnings_func = lambda text: text

    try:
        if shell == 'cmd':
            resp = session.run_cmd(cmd)
        else:
            resp = session.run_ps(POWERSHELL_UTF8_PREFIX + cmd)
        out = strip_runtime_warnings_func(decode_stream_bytes_func(resp.std_out or b''))
        err = strip_runtime_warnings_func(decode_stream_bytes_func(resp.std_err or b''))
        return int(resp.status_code), out, err
    except Exception as exc:
        return 902, '', 'WINRM_EXEC_ERROR: ' + str(exc)


def run_ssh_with_helpers(
    cmd,
    host,
    port,
    user,
    password,
    ssh_options,
    timeout_sec=None,
    normalize_timeout_func=None,
    strip_runtime_warnings_func=None,
    default_timeout_sec=None,
    timeout_rc=None,
):
    import shutil
    import subprocess
    resolved_timeout_sec = normalize_timeout_func(timeout_sec, default_timeout_sec)
    # SSH 실행 기본 커맨드 구성
    base_cmd = ['ssh', '-p', str(port)]
    if ssh_options:
        base_cmd += ssh_options.split()
    target = f"{user}@{host}" if user else host
    base_cmd.append(target)
    base_cmd.append(cmd)
    if password:
        # 패스워드 인증이면 sshpass 사용 (없으면 실패 처리)
        sshpass = shutil.which('sshpass')
        if not sshpass:
            return (1, '', 'sshpass not installed for password auth')
        base_cmd = [sshpass, '-p', password] + base_cmd
    try:
        proc = subprocess.run(
            base_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=resolved_timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = strip_runtime_warnings_func(exc.stdout) or ''
        stderr = strip_runtime_warnings_func(exc.stderr) or ''
        timeout_message = f'SSH_COMMAND_TIMEOUT: exceeded {resolved_timeout_sec}s'
        if stderr:
            stderr = f'{stderr.rstrip()}\n{timeout_message}'
        else:
            stderr = timeout_message
        return timeout_rc, stdout, stderr
    stdout = strip_runtime_warnings_func(proc.stdout)
    stderr = strip_runtime_warnings_func(proc.stderr)
    return proc.returncode, stdout, stderr


def run_no_ssh(cmd, host, port, user, password, ssh_options):
    # SSH 사용 불가(로컬 항목에서 오동작 방지)
    return (1, '', 'ssh is not allowed for this item')
