# 영역
MEMORY

# 세부 점검항목
메모리 사용률

# 점검 내용
가용 메모리와 페이지 입출력 수치를 기반으로 메모리 압박 여부를 점검합니다.

# 구분
필수

# 명령어
```bash
vmstat
```

# 출력 결과
```text
kthr      memory            page            disk          faults      cpu
r b   swap  free   re mf pi po fr sr  in  sy  cs us sy id
1 0   1024  2048   0  0  0  0  0  0   10  20  30  5  3 92
```

# 설명
- `free`는 사용 가능한 물리 메모리이며, 운영 기준에 따라 충분한 여유가 유지되는지 확인합니다.
- `swap`, `pi`, `po` 증가는 메모리 압박 신호로 볼 수 있습니다.
- `us`, `sy`, `id`를 함께 확인해 CPU와 메모리 병목을 같이 판단합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.
- `vmstat`의 `sy`는 system calls와 CPU system 비율이 모두 나타날 수 있어 위치 기준으로 해석해야 합니다.

# 임계치
- `min_free_kb`: `1024`
- `max_page_in_count`: `0`
- `max_page_out_count`: `0`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: `free`가 기준 이상이고 `pi`, `po`가 기준 이내인 경우
- **실패**: 가용 메모리가 부족하거나 page in/out 수치가 기준을 초과한 경우
- **실패**: `stderr`가 있거나 `vmstat` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
