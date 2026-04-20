# Live Input Overrides

`replay_cli.py --mode live` 에서 `case.json` 값을 덮어쓸 필요가 있을 때 사용할 JSON 파일 권장 위치다.

- 이 디렉터리 아래의 `*.json` 파일은 저장소에서 무시된다.
- `case.json`을 직접 수정하지 않고 host, credentials, threshold override를 분리해 둘 때만 사용한다.
- override JSON은 `case.json`과 같은 루트 구조를 부분적으로 담으면 된다. dict는 재귀 병합되고 list는 전체 교체된다.

예시:

```json
{
  "host": "10.10.10.20",
  "credentials": {
    "LINUX": [
      {
        "application_type_name": "LINUX",
        "credential_type_name": "SSH",
        "data": {
          "username": "inspector",
          "password": "secret"
        }
      }
    ]
  },
  "item": {
    "threshold_list": [
      {
        "name": "min_available_memory_percent",
        "value1": "15"
      }
    ]
  }
}
```

실행 예시:

```bash
python3 inspection_cases_bundle/inspection_runtime/replay_cli.py \
  --mode live \
  --override-file inspection_cases_bundle/live_inputs/rocky_memory_usage_free_check.json \
  inspection_cases_bundle/inspection_cases/server/rocky/rocky_memory_usage_free_check
```
