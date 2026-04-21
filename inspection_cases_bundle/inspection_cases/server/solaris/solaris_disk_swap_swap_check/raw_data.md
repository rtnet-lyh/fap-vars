# 영역
DISK

# 세부 점검항목
Disk Swap 사용률

# 점검 내용
디스크 기반 swap 영역의 전체 크기와 여유 공간을 기준으로 swap 압박 여부를 점검합니다.

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
- disk swap은 디스크를 가상 메모리로 사용하는 영역입니다.
- 전체 `blocks`와 `free`를 같이 봐야 실제 여유 용량을 판단할 수 있습니다.
- 사용률이 높으면 메모리 부족이나 swap 과다 사용 상태를 의심해야 합니다.

# 임계치
- `max_swap_used_percent`: `80`
- `min_swap_free_percent`: `20`
- `min_swap_device_count`: `1`
- `failure_keywords`: 없음

# 판단기준
- **정상**: disk swap 사용률이 기준 이하이고 free 비율이 기준 이상인 경우
- **실패**: swap 장치 수가 부족하거나 사용률/여유율이 기준을 벗어난 경우
- **실패**: `swap -l` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
