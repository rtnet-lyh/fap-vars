Inspection Cases Portable Bundle

이 번들은 다른 OS에서 replay 테스트를 바로 재생할 수 있도록 점검 케이스와 최소 Python 소스 런타임만 함께 묶은 패키지입니다.

요구 사항
- `python3`
- live 모드에서 비밀번호 SSH 인증이 필요하면 `sshpass`
- live 모드에서 Windows 점검이 필요하면 `pywinrm`
- live 모드에서 ESXi API 점검이 필요하면 `pyVmomi`

번들 구성
- `inspection_cases/`: 샘플 replay 케이스, 기대 결과, 가이드 문서
- `inspection_runtime/`: `replay_cli.py`, `runner.py`, 최소 `items` 공통 런타임

실행 방법
```bash
cd inspection_cases_bundle
python3 inspection_runtime/replay_cli.py inspection_cases/linux_sample
python3 inspection_runtime/replay_cli.py inspection_cases
```

실제 접속 기반 live 실행은 단일 케이스 디렉터리만 지원하며, 대상 케이스의 `case.json`을 그대로 사용한다.

```bash
cd inspection_cases_bundle
python3 inspection_runtime/replay_cli.py \
  --mode live \
  inspection_cases/server/rocky/rocky_memory_usage_free_check
```

live 실행 결과는 해당 케이스의 `result.json`을 갱신한다.

Paramiko 장비에서 SSH 접속 후 interactive shell 진입 직후 추가 비밀번호를 한 번 더 요구하는 경우에는 케이스 스크립트에서 첫 command로 해당 값을 보내는 패턴을 사용한다.

```python
class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_PROBE_PROMPT = False

    def run(self):
        post_login_password = str(self.get_connection_value('post_login_password', '') or '')
        results = self._run_paramiko_commands([
            {
                'command': post_login_password,
                'hide_command': True,
                'ignore_prompt': True,
            },
            {
                'command': 'show version',
            },
        ])
```

주의 사항
- `PARAMIKO_PROBE_PROMPT = False`는 shell 오픈 직후 엔터를 먼저 보내지 않게 해서, 빈 입력이 비밀번호 제출처럼 처리되는 장비에서 안전하다.
- 첫 비밀번호 입력 단계는 기존 prompt가 `Password:`로 학습되어 있을 수 있으므로 보통 `ignore_prompt: True`를 함께 사용한다.
- `hide_command: True`를 주면 raw output과 command history에는 실제 비밀번호 대신 `*******`가 기록된다.
- 이 패턴은 SSH 인증이 끝난 뒤 shell 안에서 추가 입력을 요구하는 경우에만 해당한다. SSH auth 단계의 keyboard-interactive/MFA는 이 방식으로 처리하지 않는다.

참고 사항
- `result.json`과 `summary.json`은 실행 시 다시 생성됩니다.
- `result.json`/stdout에는 줄바꿈 문자열을 읽기 쉽게 보조하는 `raw_output_lines`, `check_script_lines` 같은 보기용 필드가 포함될 수 있습니다.
- `.pyc`, `__pycache__`는 포함하지 않았습니다. 다른 OS와 다른 Python 버전에서 그대로 재생할 수 있게 소스 파일만 번들링했습니다.
- 현재 기대 결과 기준으로 `linux_df_sample`은 실패 상태입니다. `max_usage_percent` 임계치가 `1`인데 replay된 `df -h` 출력에는 그보다 큰 사용률이 포함되어 있기 때문입니다.
