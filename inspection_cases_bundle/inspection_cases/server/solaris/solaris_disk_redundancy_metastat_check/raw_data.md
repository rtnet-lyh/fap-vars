# 영역
DISK

# 세부 점검항목
Disk 이중화 정상 여부

# 점검 내용
Solaris Volume Manager mirror 상태와 submirror 상태를 기준으로 디스크 이중화 정상 여부를 점검합니다.

# 구분
필수

# 명령어
```bash
metastat
```

# 출력 결과
```text
d0: Mirror
    Submirror 0: d10
      State: Okay
    Submirror 1: d11
      State: Okay
    State: Okay
    Status: The volume is functioning properly.

d10: Submirror of d0
    State: Okay

d11: Submirror of d0
    State: Okay
```

# 설명
- mirror 볼륨과 submirror의 `State`는 모두 `Okay`여야 정상입니다.
- `Status`는 `The volume is functioning properly.`가 정상 메시지입니다.
- submirror 수와 전체 mirror 상태를 함께 확인합니다.

# 임계치
- `required_state`: `Okay`
- `min_submirror_count`: `2`
- `failure_keywords`: 없음

# 판단기준
- **정상**: mirror와 submirror 상태가 모두 `Okay`이고 submirror 수가 기준 이상인 경우
- **실패**: 상태가 `Maintenance` 등 비정상이거나 submirror 수가 부족한 경우
- **실패**: `metastat` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
