# items.common.utils 유지보수 안내

`items.common.utils`는 BaseCheck, item script, runner_core가 함께 재사용할 수 있는 순수 helper의 canonical 위치입니다. runner 실행 상태나 orchestration 정책에 의존하지 않는 함수만 이 계층에 둡니다.

## runner_core와의 경계

`items.common.utils`로 둘 것:

- BaseCheck나 item script에서도 쓸 수 있는 순수 함수
- runner 실행 상태, logger, module loading, precheck loop에 의존하지 않는 함수
- 입력/출력 의미가 일반화 가능하고 side effect가 없는 함수
- None 처리, 기본값 처리, 예외 처리 의미를 독립적으로 테스트할 수 있는 함수

`runner_core`에 둘 것:

- runner orchestration 정책
- precheck/result/module loading과 결합된 함수
- public facade 또는 root shim compatibility wrapper
- monkeypatch 또는 `runner.py` compatibility surface와 관련된 함수
- executor 선택, credential policy 적용, item gate 판단처럼 runner 실행 흐름에 종속된 함수

## 파일별 책임

| 파일 | 책임 | 주요 함수 | runner_core와의 관계 |
|---|---|---|---|
| `credentials.py` | credential key normalize, credential flatten/filter/pick/select, credential value fallback | `normalize_credential_key`, `flatten_credentials`, `filter_credentials`, `pick_credential`, `select_application_credential`, `preferred_credential_value` | credential 순수 helper의 canonical 위치. `runner_core.connection_policy` wrapper는 compatibility 때문에 유지 |
| `become.py` | become method/user normalize와 Unix `id` 출력 파싱 | `normalize_become_method`, `validate_become_user`, `parse_unix_id_uid` | `runner_core.paramiko.parse_unix_id_uid`는 legacy parse miss 의미를 위해 `missing_uid=None`으로 호출 |
| `paramiko_config.py` | Paramiko auth attempt 구성과 private-key loader | `paramiko_auth_attempts`, `load_paramiko_private_key` | Paramiko private-key loader의 canonical 위치. `runner_core.paramiko.load_paramiko_private_key` wrapper는 facade compatibility 때문에 유지 |
| `encoding.py` | bytes/text normalize와 runtime warning stripping | `decode_bytes`, `coerce_text`, `strip_runtime_warnings`, `normalize_terminal_text` | warning stripping canonical 위치. `runner_core.remote.strip_runtime_warnings`는 더 좁은 runner facade signature 보존 |
| `command_result.py` | command output 정리, raw_output 구성, error classification, command history 기록 | `resolve_raw_output`, `strip_shell_output_text`, `build_paramiko_result`, `detect_command_error`, `record_command` | BaseCheck와 runner execution result 의미를 공유하므로 schema 영향에 주의 |
| `options.py` | bool/csv/threshold option normalize와 Paramiko option object 변환 | `parse_bool_option`, `normalize_csv_tuple`, `threshold_list_to_map`, `build_paramiko_options_from_object` | runner_core option resolve에서 재사용 가능하지만 runner 정책 자체는 runner_core에 둠 |
| `paramiko_commands.py` | Paramiko interactive command/send/receive helper | `normalize_paramiko_commands`, `paramiko_sendline`, `extract_paramiko_prompt` | Paramiko channel handling의 순수 helper. session reuse policy는 runner_core/runner layer에 둠 |
| `paramiko_session.py` | Paramiko session key/hash/live-check helper | `build_paramiko_session_key`, `is_paramiko_session_alive`, `close_paramiko_session` | session key 생성은 순수 helper, session lifecycle policy는 runner_core에 둠 |
| `remote_execution.py` | Solaris/become command spec normalize와 검증 helper | `normalize_solaris_command_specs`, `build_solaris_become_commands`, `verify_solaris_become_result` | BaseCheck remote execution에서도 쓰는 순수 helper |
| `thresholds.py` | threshold value type inference/casting/getter | `infer_threshold_value_type`, `cast_threshold_value`, `get_threshold_value` | item script threshold 처리의 canonical helper |
| `policy.py` | Text-policy evaluation and command/connection error classification | `evaluate_policy_text`, `extract_lines`, `detect_command_error`, `is_connection_error`, `is_not_applicable` | Shared by BaseCheck wrappers and command result handling; no runner/BaseCheck state dependency |
| `parsing.py` | Generic parsing and unit conversion helpers | `to_mb`, `parse_mpstat_field` | Canonical home for pure parsing helpers extracted from BaseCheck wrapper support |

## Stage 10-5E helper overlap 결론

Stage 10-5E에서는 runner_core와 utils의 중복 후보를 재확인했고, 무리한 병합 없이 다음 결론을 냈습니다.

- `credentials.py`는 credential normalize/filter/pick/select 계열의 canonical 위치입니다.
- `runner_core.connection_policy.normalize_credential_key`, `flatten_credentials`, `select_application_credential`은 이미 utils canonical 구현을 delegation합니다.
- `runner_core.connection_policy._filter_credentials`, `_pick_credential`도 delegation이지만 root shim을 통해 import 가능하므로 유지합니다.
- `paramiko_config.py`는 Paramiko private-key loader canonical 위치입니다.
- `runner_core.paramiko.load_paramiko_private_key`는 public facade compatibility 때문에 wrapper로 유지합니다.
- `become.py`의 `parse_unix_id_uid`는 canonical parser입니다. 다만 `runner_core.paramiko.parse_unix_id_uid`는 legacy parse miss 결과 `(None, '')`를 보존하기 위해 `missing_uid=None`으로 호출합니다.
- `encoding.py`의 `strip_runtime_warnings`는 canonical 구현입니다. `runner_core.remote.strip_runtime_warnings`는 더 좁은 facade signature를 유지하는 wrapper입니다.

## Stage 10-5I 구조 정리 반영

Stage 10-5I 이후 루트 `runner_*.py` shim은 제거되었습니다. runner 구현 모듈을 참조할 때는 `runner_core.*`를 사용하고, public runner facade가 필요한 호출은 `runner.py`를 사용합니다.

wrapper 계층은 계속 분리합니다. `runner_core/facade_wrappers.py`는 runner facade support 계층이고, `items/common/base_wrappers.py`는 BaseCheck facade support 계층입니다. 두 wrapper 계층은 합치지 않습니다. `items.common.utils`는 이 둘보다 아래의 순수 helper canonical 계층으로 유지합니다.

`items.common.utils`는 `runner.py`나 `runner_core`에 의존하지 않아야 합니다. runner orchestration 정책, monkeypatch-sensitive wrapper, BaseCheck method surface 유지 목적의 wrapper는 이 패키지에 두지 않습니다.

## 변경 시 검증

utils helper를 변경하면 runner_core뿐 아니라 BaseCheck와 item script도 영향을 받을 수 있습니다. 최소 다음을 확인합니다.

```bash
python3 -m compileall -q inspection_runtime
python3 inspection_runtime/replay_cli.py inspection_cases
```

credential, Paramiko, encoding helper를 바꾼 경우에는 helper equivalence/sample validation을 함께 갱신해야 합니다.


## Stage 10-5J common helper extraction

Stage 10-5J moved additional pure helper logic into utils while keeping public runner and BaseCheck symbols in place.

- `policy.py` is now the canonical location for text policy evaluation and command/connection error classification. `command_result.py` re-exports the same names for compatibility with existing imports.
- `parsing.py` is now the canonical location for generic unit/field parsing such as `to_mb` and `parse_mpstat_field`. `items.common.base_wrappers` delegates to these helpers so `BaseCheck._to_mb(...)` and `BaseCheck._parse_mpstat_field(...)` remain available.
- Wrapper layers are still separate: `runner_core/facade_wrappers.py` supports `runner.py`, while `items/common/base_wrappers.py` supports `BaseCheck`. Both may call utils, but utils must not import runner, runner_core, or `_base.py`.


## Stage 10-5L wrapper re-export note

Stage 10-5L converted simple delegation functions in `runner_core.facade_wrappers` and `items.common.base_wrappers` into direct re-export/alias symbols where behavior was already canonical in lower modules. `items.common.base_wrappers` remains the BaseCheck-facing support layer, while pure helper implementations remain in this `utils` package.
