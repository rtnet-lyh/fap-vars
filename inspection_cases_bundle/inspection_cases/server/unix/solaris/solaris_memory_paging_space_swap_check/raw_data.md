# 영역
MEMORY

# 세부 점검항목
Paging Space

# 점검 내용
가상 메모리(swap)의 전체 용량과 여유 공간을 기준으로 paging space 상태를 점검합니다.

# 구분
필수

# 명령어
```bash
swap -l
```

# 출력 결과
```text
swapfile           dev   swaplo   blocks    free
/dev/dsk/c0t0d0s1  118,1 16       1048576   524288
/dev/dsk/c0t0d0s2  118,2 16       2097152   1048576
```

# 설명
- `blocks`는 전체 swap 용량, `free`는 남은 swap 용량입니다.
- 사용률이 높거나 free 비율이 낮으면 메모리 압박 또는 swap 부족 상태를 의심할 수 있습니다.
- 장치 수와 총 용량을 함께 확인해 swap 구성이 충분한지 판단합니다.

# 임계치
- `max_swap_used_percent`: `80`
- `min_swap_free_percent`: `20`
- `min_swap_device_count`: `1`
- `failure_keywords`: 없음

# 판단기준
- **정상**: swap 사용률이 기준 이하이고 free 비율이 기준 이상인 경우
- **실패**: swap 장치 수가 부족하거나 사용률/여유율이 기준을 벗어난 경우
- **실패**: `swap -l` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
