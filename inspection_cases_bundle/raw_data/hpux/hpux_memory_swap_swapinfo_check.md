# 영역
MEMORY

# 세부 점검항목
Paging Space

# 점검 내용
사용 가능한 가상 메모리 사용률을 점검한다.

# 구분
필수

# 명령어
```bash
swapinfo -tam
```

# 출력 결과
```text
TYPE      AVAIL    USED    FREE  PCT  START/   LIMIT RESERVE  PRI  NAME
dev        8192    1024    7168   12%       0       -       -    1  /dev/dsk/c0t0d0s2
reserve       -       -    2048
memory    16384    9200    7184   56%
total     24576   10224   14352   42%
```

# 설명
- `swapinfo -tam` 명령으로 HP-UX Paging Space 전체 사용률과 여유 공간을 확인한다.
- Paging Space 사용률이 높거나 여유율이 낮으면 메모리 부족 또는 프로세스 메모리 과다 사용 가능성이 있다.
- 디스크 기반 스왑과 메모리 기반 항목을 구분해 확인한다.
- 명령 실행 불가, 권한 문제, 파싱 실패 시에는 확인 필요로 분류한다.

# 임계치
FREE_MIN_RATIO_PCT
USED_MAX_PCT

# 판단기준
- **양호**: Paging Space 여유율이 `FREE_MIN_RATIO_PCT` 이상이고 사용률이 `USED_MAX_PCT` 이하인 경우
- **경고**: 여유율이 `FREE_MIN_RATIO_PCT` 미만이거나 사용률이 `USED_MAX_PCT`를 초과하는 경우
- **확인 필요**: `swapinfo` 결과 확인 또는 해석이 불가능한 경우
