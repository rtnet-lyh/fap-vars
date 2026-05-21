# runner_core 유지보수 안내

`runner_core`는 `runner.py`에서 분리된 실행 오케스트레이션 구현 패키지입니다. `runner.py`는 계속 public facade와 CLI entrypoint 역할을 유지하고, item loading, precheck, item execution, remote execution, result building 같은 구현 세부사항은 `runner_core`가 담당합니다.

## 기본 관계

- `runner.py` → `runner_core.*` 방향의 import만 허용합니다.
- `runner_core.*` → `runner.py` import는 금지합니다.
- `replay_cli.py`는 루트에 남아 있으며 `python3 inspection_runtime/replay_cli.py inspection_cases` 실행 방식을 유지해야 합니다.
- Stage 10-5I 이후 루트 `runner_*.py` compatibility shim은 제거되었습니다. 새 코드와 유지보수 코드는 `runner_core.*`를 직접 import해야 합니다.
- public compatibility surface는 `runner.py` wrapper가 담당합니다. 단순 pass-through처럼 보여도 외부 테스트, monkeypatch, 기존 runner facade 호출이 의존할 수 있으므로 임의 삭제하지 않습니다.

## wrapper 계층 경계

- runner 계층: `runner.py`, `runner_core/facade_wrappers.py`, `runner_core/facade_policy.py`
- BaseCheck 계층: `items/common/_base.py`, `items/common/base_wrappers.py`, `items/common/base_facade_policy.py`
- 순수 helper 계층: `items/common/utils/*`

`runner_core/facade_wrappers.py`와 `items/common/base_wrappers.py`는 합치지 않습니다. runner 계층은 실행 오케스트레이션과 public runner facade 지원을 담당하고, BaseCheck 계층은 item script가 `self._ssh(...)`, `self.ok(...)`처럼 호출하는 public-ish method surface를 지원합니다. `items.common._base`가 `runner_core`를 import하는 구조도 금지합니다.

`facade_policy.py`와 `base_facade_policy.py`는 validation과 compatibility metadata 역할이 있으므로 현재는 유지합니다. validation이 안정화된 뒤 사용처가 없다고 확인되면 문서 또는 wrapper 모듈로 병합을 별도 단계에서 검토할 수 있습니다.

## 파일별 책임

| 파일 | 책임 | 주요 함수/클래스 | 주의할 compatibility 조건 | 관련 검증 |
|---|---|---|---|---|
| `connection_policy.py` | item/module 실행에 필요한 connection method, credential 선택, connection value resolve 정책 | `needs_host_connection`, `get_connection_method`, `select_connection_credential`, `resolve_connection_values`, `select_application_credential` | `items.common.utils.credentials` canonical helper를 감싼 wrapper는 runner facade 노출 때문에 유지 | replay diff, public facade wrapper validation, helper equivalence validation |
| `context.py` | item module 실행 context와 SSH/WinRM adapter 구성 | `build_item_base_context`, `build_winrm_ssh_adapter`, `build_ssh_adapter`, `build_paramiko_ssh_blocker` | context key 이름과 adapter 호출 signature 변경 금지 | replay diff, result schema diff |
| `facade_policy.py` | `runner.py` public facade wrapper 분류 metadata | `REQUIRED_RUNNER_WRAPPERS`, `MONKEYPATCH_SENSITIVE_WRAPPERS`, `FACADE_HELPER_WRAPPERS` | runtime execution logic 추가 금지. validation source로 유지 | public facade wrapper validation |
| `facade_wrappers.py` | `runner.py`의 저위험 helper public export aggregator | payload/result/loading/credential/options/text 계열 helper direct re-export/alias | public symbol은 `runner.py`에 유지. high-risk wrapper 단순 alias화 금지 | facade wrapper migration validation, wrapper module slimming validation |
| `item_execution.py` | item precheck gate, item dispatch, item execution loop 오케스트레이션 | `evaluate_item_precheck_gate`, `execute_item_after_precheck_gate`, `run_item_execution_loop`, `ItemExecution*`, `ItemPrecheckGate*` | gate result key와 result schema 변경 금지. public-compatible long signature 유지 | replay diff, gate key validation, public facade validation |
| `item_loading.py` | filesystem/db item module lookup과 module key resolve | `load_item_module`, `resolve_runtime_item_module`, `load_available_items`, `build_module_lookup_key` | script execution 기준에서 base path 계산이 깨지면 item lookup 결과가 달라질 수 있음 | replay diff, py_compile |
| `logging.py` | runner logger 초기화와 result/item logging | `init_logger`, `log_item_start`, `log_result_json`, `log_item_result_summary` | 로그 형식은 result schema는 아니지만 문제 분석에 쓰이므로 불필요한 변경 자제 | replay, smoke validation |
| `paramiko.py` | Paramiko precheck, exec command, su precheck 흐름 | `run_paramiko_precheck`, `run_paramiko_exec_command`, `run_paramiko_su_precheck`, `load_paramiko_private_key`, `parse_unix_id_uid` | optional `paramiko` import를 top-level로 올리지 않음. session reuse client_factory 의미 보존 | Paramiko session reuse static validation, unittest known issue 비교 |
| `payload.py` | item payload normalize와 lookup payload 구성 | `normalize_item`, `sanitize_item_payload`, `build_lookup_payload` | item id/code/payload 구성 변경은 replay 결과에 직접 영향 | replay diff |
| `precheck.py` | host precheck와 become precheck loop 오케스트레이션 | `run_host_precheck_loop`, `run_become_precheck_loop`, `HostPrecheckLoop*`, `BecomePrecheckLoop*` | host precheck error key는 method, become error key는 `become_request['key']` 유지 | replay diff, precheck flow validation |
| `remote.py` | SSH/WinRM/no-ssh low-level helper와 runtime warning 정리 | `create_winrm_session`, `run_winrm_with_session`, `run_ssh_with_helpers`, `run_no_ssh`, `strip_runtime_warnings` | `winrm` optional import를 session 생성 내부에 유지. `strip_runtime_warnings` wrapper signature 유지 | WinRM compatibility, helper equivalence validation |
| `remote_exec.py` | public facade에 가까운 SSH/WinRM/no-ssh adapter와 shell/module dispatch | `run_winrm`, `run_ssh`, `run_no_ssh`, `_winrm_session`, `run_shell_item`, `call_module_run` | `runner.run_winrm(...)`이 `runner._winrm_session`을 `session_factory`로 넘기는 monkeypatch path 유지 | WinRM compatibility validation, public facade validation |
| `results.py` | runner result dict 생성과 요약 | `build_runner_output`, `build_precheck_fail_result`, `build_become_precheck_fail_result`, `build_missing_item_result`, `build_exec_error_result` | status/message/stdout/stderr/rc/metrics/thresholds/reasons/raw_output 의미 변경 금지 | replay diff, result schema diff |
| `ssh_options.py` | SSH command timeout resolve와 executor 호출 adapter | `resolve_ssh_command_timeout_sec`, `call_ssh_executor`, `ensure_ssh_options_defaults` | timeout 기본값과 executor signature 감지 의미 변경 금지 | replay diff, SSH path validation |
| `winrm_options.py` | WinRM shell/options 구성 | `get_winrm_shell`, `build_winrm_options` | module option과 global winrm option 우선순위 변경 금지 | WinRM compatibility, replay diff |

## item execution notes

`item_execution.py`는 item normalize, runtime module lookup, precheck gate 평가, skip/fail result 생성, 실제 item dispatch, item loop logging/sleep을 연결합니다. Stage 10-1A~10-3A에서 긴 인자 목록과 gate 책임을 context/runtime/deps 구조로 나누었습니다.

주요 구조:

- `ItemPrecheckGateDeps`, `ItemPrecheckGateContext`, `ItemPrecheckGateItemPayload`, `ItemPrecheckGateState`
- `ItemExecutionDispatchDeps`, `ItemExecutionContext`, `ItemExecutionRuntime`
- `ItemExecutionLoopContext`, `ItemExecutionLoopRuntime`, `ItemExecutionDeps`

특히 `evaluate_item_precheck_gate(...)`, `execute_item_after_precheck_gate(...)`, `run_item_execution_loop(...)`는 result 의미와 public-compatible long signature에 직접 닿는 고위험 함수입니다. 아래 gate result key는 precheck skip, become skip, executable path 모두에서 유지되어야 합니다.

```text
should_skip result item code item_id item_payload result_item_payload lookup_payload
mod module_key module_source db_error method ssh_command_timeout_sec
connection_credential connection_values app_credential app_credential_data become_request
```

## precheck notes

`precheck.py`는 item 실행 전 host connection precheck와 become precheck를 수행합니다. Stage 10-4A에서 `HostPrecheckLoopContext/Runtime/Deps`와 `BecomePrecheckLoopContext/Runtime/Deps`가 도입되었습니다.

- host precheck error key는 `method`입니다. 예: `ssh`, `paramiko`, `winrm`.
- become precheck error key는 `become_request['key']`입니다.
- host precheck가 실패한 method는 become precheck에서도 skip되어야 합니다.
- Paramiko precheck와 become precheck 경로에서 `paramiko_client_factory` 전달 의미를 유지해야 합니다.

method별 precheck 실행 여부, WinRM/SSH/Paramiko 선택 기준, Paramiko session reuse client factory 전달 의미를 바꾸면 replay diff가 발생할 수 있습니다.

## remote execution notes

`remote_exec.py`는 runner public facade에 가까운 command execution adapter 계층입니다. SSH, WinRM, no-ssh 실행 wrapper와 shell item dispatch, module run fallback을 제공합니다.

반드시 유지해야 하는 WinRM monkeypatch 경로:

```python
mock.patch.object(runner, "_winrm_session", return_value=session)
runner.run_winrm(...)
```

`runner.py`에서는 `runner.run_winrm(...)` wrapper가 항상 현재 `runner._winrm_session` wrapper를 `session_factory`로 넘겨야 합니다. `runner_core.remote_exec`는 `runner.py`를 import하면 안 되며, `winrm` optional import를 top-level로 올리면 안 됩니다.

`shell item dispatch`는 shell item이 JSON만 출력한다는 전제에 의존합니다. rc, stdout, stderr, raw_output 처리 의미를 바꾸면 result schema와 replay diff가 깨질 수 있습니다.

## Paramiko notes

`paramiko.py`는 Paramiko 기반 host precheck, command execution, su precheck 흐름을 담당합니다. optional dependency와 session reuse 의미에 직접 닿는 고위험 파일입니다.

- `paramiko`는 optional dependency이므로 top-level import하지 않습니다.
- `client_factory` 주입 의미는 session reuse static validation 대상입니다.
- `load_paramiko_private_key(...)`는 `items.common.utils.paramiko_config.load_paramiko_private_key(...)` canonical 구현을 delegation합니다.
- `parse_unix_id_uid(...)`는 `items.common.utils.become.parse_unix_id_uid(..., missing_uid=None)`으로 호출해 legacy parse miss 결과 `(None, '')`를 보존합니다.

Paramiko가 설치되지 않은 환경의 unittest 실패는 기존 known issue입니다. 이를 runtime code에서 숨기거나 우회하지 않습니다.

## 고위험 파일

특히 아래 파일은 replay result와 compatibility에 직접 닿습니다.

- `item_execution.py`: precheck gate와 item execution result schema에 직접 영향.
- `precheck.py`: host/become precheck skip 여부와 error key에 직접 영향.
- `remote_exec.py`: `runner._winrm_session` monkeypatch 경로와 shell/module dispatch에 직접 영향.
- `results.py`: result JSON schema와 message/stdout/stderr/raw_output 의미에 직접 영향.
- `paramiko.py`: optional dependency, session reuse, su precheck 의미에 직접 영향.

## runner_core와 utils 경계

`runner_core`에는 runner 실행 정책과 orchestration 결합도가 높은 함수를 둡니다. BaseCheck나 item script에서도 재사용 가능한 순수 helper는 `items.common.utils`가 canonical 위치입니다.

`runner_core`에 남길 것:

- runner precheck/result/module loading과 결합된 함수
- public facade compatibility wrapper
- monkeypatch path나 executor adapter와 관련된 함수
- runner 실행 상태, logger, available module map, credentials policy에 의존하는 함수

`items.common.utils`로 둘 것:

- 입력/출력 의미가 일반화 가능한 순수 함수
- BaseCheck와 item script에서도 사용할 수 있는 함수
- runner 실행 상태나 logger에 의존하지 않는 함수


## Stage 10-5K runner facade slimming note


Stage 10-5L changed `runner_core.facade_wrappers` from a collection of thin delegation `def` wrappers into a direct re-export/alias layer. This removes one extra call layer for low-risk helpers while keeping `runner.<helper>(...)` available through direct imports in `runner.py`.

Stage 10-5K changed low-risk runner helper exposure from thin `def` wrappers in `runner.py` to direct imports from `runner_core.facade_wrappers`. Public calls such as `runner.normalize_item(...)`, `runner.build_lookup_payload(...)`, and `runner.decode_stream_bytes(...)` remain available, but their function `__module__` may now be `runner_core.facade_wrappers`.

High-risk and monkeypatch-sensitive wrappers remain explicit `def` functions in `runner.py`, including `execute_runner`, `main`, `_winrm_session`, `run_winrm`, `run_ssh`, `run_no_ssh`, `run_paramiko_*`, host/become precheck loops, and item execution gate/loop wrappers. Do not convert `_winrm_session` or `run_winrm` to direct imports or aliases; `runner.run_winrm(...)` must continue to pass the current `runner._winrm_session` as `session_factory`.

`facade_policy.py` now names these low-risk symbols as `DIRECT_IMPORTED_HELPER_SYMBOLS`. The older `FACADE_HELPER_WRAPPERS` metadata name remains as a compatibility alias for validation and documentation.

## 수정 후 검증 체크리스트

runner_core 코드를 수정한 뒤에는 최소 다음을 실행합니다.

```bash
python3 -m compileall -q inspection_runtime
python3 inspection_runtime/replay_cli.py inspection_cases
```

그리고 변경 범위에 따라 다음 validation을 확인합니다.

- Stage baseline 대비 `diff_case_count = 0`, `diff_result_count = 0`
- WinRM compatibility validation failures 0
- Paramiko session reuse static validation failures 0
- circular/import validation cycles_count 0
- public facade wrapper validation failures 0
- BaseCheck public API validation failures 0 if `items/common` 경계에 닿는 변경 포함

Paramiko가 설치되지 않은 환경의 unittest 실패는 기존 known issue로 분리합니다. 이를 runtime code에서 숨기거나 우회하지 않습니다.


## Stage 10-5J utils boundary note

Additional pure helper logic was moved below runner_core into `items.common.utils` in Stage 10-5J. Runner orchestration modules may import these utils directly when the helper is independent of runner state, BaseCheck state, logger, result objects, or monkeypatch-sensitive compatibility paths. Runner facade wrappers and BaseCheck wrappers remain separate and must not be merged.
