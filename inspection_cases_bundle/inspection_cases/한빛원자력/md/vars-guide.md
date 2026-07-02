# 예방점검 스크립트 작업 가이드

이 문서는 지금까지 진행한 `centos7`, `windows2019` 계열 예방점검 스크립트 작성/수정 방식을 정리한 기준 문서다.

앞으로 `oracle`, `postgres`, `mysql` 같은 다른 애플리케이션/플랫폼을 추가할 때도 이 문서를 기준으로 동일한 형태의 점검 스크립트를 만들 수 있어야 한다.

## 1. 작업 목적

목표는 각 점검 항목별 `script.py`를 일정한 형식으로 작성해서:

- 점검 명령을 실행하고
- 출력값을 파싱하고
- 기준값으로 판정하고
- UI에 `점검 결과`, `판단 기준`, `메시지`가 잘 보이도록
- 최종적으로 `self.result(...)` 형태로 반환하는 것이다.

핵심은 단순히 명령이 실행되는 것만이 아니라, UI에서 사람이 읽는 결과가 잘 보이도록 만드는 것이다.

## 2. 절대 규칙

다음 규칙은 반드시 지킨다.

- 기준 베이스는 `/fap/ansible/scripts/inspection/items/common/_base.py`
- `_base.py`는 절대 수정하지 않는다.
- `/fap/ansible/scripts/inspection/runner.py` 는 수정하지 않는다.
- `/fap/ansible/scripts/inspection/replay_cli.py` 는 수정하지 않는다.
- 가능하면 수정 대상은 각 항목 폴더 내부의 `script.py`만으로 제한한다.
- `message`, `results`, `criteria`는 반드시 최종 반환에 포함되도록 만든다.

## 3. 기본 스크립트 구조

모든 스크립트는 아래 흐름을 기본으로 한다.

1. `CHECK_COMMAND` 정의
2. `parse_output(output)`
3. `evaluate(metrics, ...)`
4. `build_result(metrics, ..., status)`
5. `run()`
6. `CHECK_CLASS = Check`

기본 골격 예시는 아래와 같다.

```python
# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CHECK_COMMAND = 'example command'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def parse_output(self, output):
        return {}

    def evaluate(self, metrics):
        return 'ok'

    def build_result(self, metrics, status):
        return {
            'message': '점검 메시지',
            'results': '사람이 읽을 점검 결과',
            'criteria': '사람이 읽을 판단 기준',
        }

    def run(self):
        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics)
        result = self.build_result(metrics, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check
```

## 4. UI에 값이 잘 보이게 하는 핵심 규칙

UI에 아래 항목이 보이려면:

- 점검 결과
- 판단 기준
- 메시지

반드시 `build_result()`에서 아래 키를 문자열로 만들어야 한다.

- `message`
- `results`
- `criteria`

그리고 `run()` 마지막에서 반드시 그대로 `self.result(...)`에 넘겨야 한다.

정석 형태:

```python
return self.result(
    status=status,
    message=result['message'],
    metrics=metrics,
    results=result['results'],
    criteria=result['criteria'],
)
```

주의:

- `results`는 사람이 읽을 수 있는 문장/요약 문자열이어야 한다.
- `criteria`도 사람이 읽을 수 있는 문자열이어야 한다.
- `thresholds` 딕셔너리만 넣고 끝내면 UI가 기대하는 모양과 달라질 수 있다.
- `reasons`만 채우고 `results`를 비우면 UI에서 비어 보일 수 있다.

좋은 예:

```python
results = '메모리 사용률=10.0%, 가용 메모리 비율=81.9%'
criteria = '정상: 메모리 사용률 <= 80.0% 및 가용 메모리 비율 >= 20.0%'
```

## 5. Windows 최신 표준 패턴

최근 Windows 항목은 `01_windows_cpu_usage_counter_check/script.py` 형식을 기준으로 맞춘다.

핵심 구조:

1. 실제 점검/파싱/임계치 판정은 `execute_check()`에서 수행
2. `execute_check()`는 `self.ok()`, `self.warn()`, `self.fail()`, `self.not_applicable()` 중 하나를 먼저 만든다
3. `parse_output()`은 위 반환값에서 `metrics`를 꺼내고 `_legacy_result`를 함께 보관한다
4. `build_result()`는 `message`, `results`, `criteria`를 UI 친화적인 문자열로 다시 정리한다
5. `run()`은 최종적으로 `results`, `criteria`, `message`를 빠짐없이 담아 반환한다

이 패턴을 쓰는 이유:

- 기존 점검 로직은 유지하면서
- UI에 보이는 문자열 형식을 일관되게 맞추고
- `results` 또는 `criteria`가 비어 보이는 문제를 줄이기 쉽기 때문이다

Windows 계열 권장 흐름 예시는 아래와 같다.

```python
def run(self):
    legacy_result = self.execute_check()
    metrics = self.parse_output(legacy_result)
    status = self.evaluate(metrics)
    result = self.build_result(metrics, status)

    return self.fail(
        error=result.get('error') or result['message'],
        message=result['message'],
        metrics=result['metrics'],
        thresholds={'criteria': result['criteria']},
        reasons=result['results'],
        results=result['results'],
        criteria=result['criteria'],
    )
```

주의:

- `execute_check()` 안에서 이미 `self.ok()` 또는 `self.fail()`을 만들더라도, 최종 UI 표시는 `run()`에서 다시 정리될 수 있다
- `build_result()`에서 `results`가 비면 `reasons`, `message`, `metrics` 순서로 보완하는 식이 안전하다
- 한글 메시지는 UTF-8 기준으로 직접 확인해서 깨진 문자열이 남지 않게 한다

## 6. Windows 항목 백업 규칙

Windows 항목을 최신 형식으로 정리할 때는 기존 `script.py`를 같은 폴더의 `script_old.py`로 먼저 백업해 둔다.

실무 기준:

- 기존 로직 보존이 목적이므로 `script_old.py`는 덮어쓰지 않는다
- 새 `script.py`는 최신 표준 형식으로 유지한다
- 비교가 필요할 때는 `script.py`, `script_old.py`, `replay.json`, `case.json`을 함께 본다

## 7. `ssh` 방식 사용 기준

일반 리눅스/유닉스 점검은 기본적으로 아래 패턴을 사용한다.

```python
rc, output, error = self._ssh(CHECK_COMMAND)
```

적합한 경우:

- 일반 명령 실행
- sudo/become 없이도 가능한 명령
- 운영 중 이미 잘 쓰고 있는 `ssh` 기반 항목

## 8. `paramiko` 방식 사용 기준

일부 항목은 `paramiko` 기준으로 맞췄다. 이 경우 구조는 같고 `run()` 실행부만 달라진다.

기본 규칙:

- `CONNECTION_METHOD = 'paramiko'`
- 필요 시 `PARAMIKO_AUTH_TIMEOUT_SEC = 30`
- 명령 실행은 `_run_paramiko_commands(...)`
- 반환값은 `(rc, output, error)` 3개가 아니라 결과 목록이다

정석 패턴:

```python
results = self._run_paramiko_commands(CHECK_COMMAND, become=True)
last = results[-1] if results else {}

rc = last.get('rc', 1)
output = last.get('stdout', '')
error = last.get('stderr', '')
```

중요:

아래처럼 쓰면 안 된다.

```python
rc, output, error = self._run_paramiko_commands(CHECK_COMMAND, become=True)
```

이렇게 하면 아래 에러가 날 수 있다.

```text
not enough values to unpack (expected 3, got 1)
```

## 9. `paramiko`로 변경했던 항목 정리

대화 기준으로 `paramiko` 방식으로 맞췄던 번호는 아래와 같다.

- `04`
- `12`
- `16`
- `18`
- `19`

의미:

- `04`: 메모리 인식
- `12`: 커널 파라미터
- `16`: 네트워크 링크
- `18`: ping 손실률
- `19`: multipath / MPIO

이 항목들은 같은 규칙으로 다른 플랫폼에도 확장 가능하다.

## 10. `excluded` / `not_applicable`

대상 장비나 환경상 점검이 불가능할 때는 `excluded` 성격이 필요할 수 있다.

실무적으로는 아래처럼 처리한다.

- `evaluate()`에서 `excluded` 반환 가능
- 최종 반환은 `self.result(...)`에 `status='excluded'`

예:

```python
if metrics.get('not_applicable'):
    return 'excluded'
```

그리고 `build_result()`에서:

```python
return {
    'message': 'multipath 점검 대상이 아닙니다.',
    'results': metrics.get('reason', ''),
    'criteria': criteria,
}
```

## 11. 명령어와 replay의 일치

`replay.json`을 사용하는 항목은 `script.py`의 `CHECK_COMMAND`와 `replay.json`의 `matcher_value`가 정확히 일치해야 한다.

일치하지 않으면 다음 문제가 생길 수 있다.

- `REPLAY_MISS`
- 결과는 fail인데 실제 코드 문제처럼 보임
- UI에는 값이 나오더라도 테스트 자체는 실패

따라서 수정할 때는 반드시 같이 본다.

- `script.py`
- `replay.json`
- 필요 시 `case.json`
- 필요 시 기존 `result.json`

## 12. 결과 확인 시 체크 포인트

결과가 이상할 때는 아래 순서로 확인한다.

1. 실제 실행된 명령어가 맞는가
2. `script.py`가 현재 파일 기준인가
3. `result.json`이 예전 실행 결과가 아닌가
4. `results`, `criteria`, `message`가 최종 결과에 실제로 들어갔는가
5. `replay.json`과 명령어가 일치하는가

특히 `script.py`는 바뀌었는데 `result.json`은 예전 결과가 남아 있으면 혼동이 생긴다.

## 13. 파일 작성 기준

새 애플리케이션을 만들 때도 폴더 단위로 항목을 만든다.

예상 구조:

```text
inspection_cases/
  server/
    centos7__/
      01_xxx/
        script.py
        case.json
        replay.json
        outputs/
    windows/
      01_xxx/
        script.py
        case.json
        replay.json
        outputs/
    oracle/
    postgres/
    mysql/
```

핵심은 각 항목 폴더 안의 `script.py`가 위의 동일한 규칙을 따른다는 점이다.

## 14. 새 항목 만들 때 작업 순서

새 점검 항목을 만들 때는 아래 순서로 진행한다.

1. 기존 유사 항목을 하나 찾는다.
2. `CHECK_COMMAND`를 실제 점검 명령으로 바꾼다.
3. `parse_output()`을 새 출력 형식에 맞게 작성한다.
4. `evaluate()`에서 임계치를 기준으로 `ok/fail/excluded`를 판단한다.
5. `build_result()`에서 사람이 읽는 `message/results/criteria`를 만든다.
6. `run()`은 기존 정석 구조를 유지한다.
7. 필요하면 `replay.json`도 실제 명령 기준으로 맞춘다.

## 15. 플랫폼별 권장 방식

### CentOS / Linux 계열

- 기본은 `ssh`
- 명령 출력이 단순하면 `parse_output()`도 최대한 단순하게 유지
- 예: `free -m`, `sysctl -a`, `ip link`, `ping`, `multipath -ll`

### Windows 계열

- `winrm` 명령 실행 결과를 사람이 읽을 수 있는 문자열로 다시 정리해야 함
- `execute_check()`를 쓸 수도 있지만, 최종 `run()`은 가능하면 `self.result(...)` 흐름으로 단순화하는 것이 좋음
- `results`와 `criteria`를 문자열로 만들지 않으면 UI가 비어 보일 수 있음

### Oracle / PostgreSQL / MySQL 계열 확장 시

권장 방식:

- DB 접속 명령 또는 클라이언트 명령을 `CHECK_COMMAND`로 둔다
- 출력은 가능한 한 고정 형식으로 만든다
- `parse_output()`은 숫자/상태값 중심으로 추출한다
- `build_result()`는 운영자가 바로 이해할 수 있게 작성한다

예:

- Oracle tablespace 사용률
- PostgreSQL replication 상태
- MySQL slave/replica 상태

## 16. 좋은 `build_result()` 작성 규칙

좋은 `build_result()`는 다음 조건을 만족해야 한다.

- `message`: 최종 상태를 한 문장으로 설명
- `results`: 실제 측정값 요약
- `criteria`: 정상 기준 요약

예:

```python
criteria = '정상: 패킷 손실률 <= 0.0% 및 평균 응답시간 <= 100.0 ms'
results = '패킷 손실률=0.0%, 평균 응답시간=0.4 ms'
message = 'ping 손실률 점검 양호'
```

나쁜 예:

- `results`에 딕셔너리를 그대로 넣음
- `criteria`에 임계치 dict만 넣고 사람이 읽는 설명이 없음
- `message`가 비어 있음

## 17. 디버깅 포인트

자주 나오는 문제와 원인:

### 1. `not enough values to unpack (expected 3, got 1)`

원인:

- `_run_paramiko_commands()` 반환값을 `_ssh()`처럼 받음

해결:

```python
results = self._run_paramiko_commands(...)
last = results[-1] if results else {}
```

### 2. UI에 `점검 결과`, `판단 기준`이 비어 보임

원인:

- `results`, `criteria`가 최종 반환에 안 들어감
- `build_result()`가 문자열을 안 만들고 다른 값만 반환

해결:

- `build_result()`에서 문자열 생성
- `self.result(...)`에 그대로 넘김

### 3. 실행된 명령이 기대와 다름

원인:

- 다른 `script.py`가 연결됨
- `replay.json` 불일치
- 오래된 `result.json` 확인 중

## 18. 최종 기준

앞으로 새 스크립트를 만들 때는 아래 기준을 그대로 따른다.

- `items.common._base.BaseCheck` 사용
- `parse_output/evaluate/build_result/run` 구조 유지
- `message/results/criteria`를 반드시 문자열로 생성
- 최종 반환은 `self.result(...)`
- `ssh` 또는 `paramiko`는 항목 성격에 맞게 선택
- `paramiko`일 때는 `_run_paramiko_commands()` 반환 형식을 정확히 처리
- `_base.py`, `runner.py`, `replay_cli.py`는 수정하지 않음

이 문서만 있으면 앞으로 `centos7`, `windows2019`, `oracle`, `postgres`, `mysql` 계열 예방점검 스크립트를 같은 규칙으로 계속 확장할 수 있다.
