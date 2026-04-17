Inspection Cases Portable Bundle

이 번들은 다른 OS에서 replay 테스트를 바로 재생할 수 있도록 점검 케이스와 최소 Python 소스 런타임만 함께 묶은 패키지입니다.

요구 사항
- `python3`

번들 구성
- `inspection_cases/`: 샘플 replay 케이스, 기대 결과, 가이드 문서
- `inspection_runtime/`: `replay_cli.py`, `runner.py`, 최소 `items` 공통 런타임

실행 방법
```bash
cd inspection_cases_bundle
python3 inspection_runtime/replay_cli.py inspection_cases/linux_sample
python3 inspection_runtime/replay_cli.py inspection_cases
```

참고 사항
- `result.json`과 `summary.json`은 실행 시 다시 생성됩니다.
- `result.json`/stdout에는 줄바꿈 문자열을 읽기 쉽게 보조하는 `raw_output_lines`, `check_script_lines` 같은 보기용 필드가 포함될 수 있습니다.
- `.pyc`, `__pycache__`는 포함하지 않았습니다. 다른 OS와 다른 Python 버전에서 그대로 재생할 수 있게 소스 파일만 번들링했습니다.
- 현재 기대 결과 기준으로 `linux_df_sample`은 실패 상태입니다. `max_usage_percent` 임계치가 `1`인데 replay된 `df -h` 출력에는 그보다 큰 사용률이 포함되어 있기 때문입니다.
