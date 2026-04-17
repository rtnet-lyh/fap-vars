# 영역
MEMORY

# 세부 점검항목
메모리 사용률

# 점검 내용
메모리 사용률 확인

# 구분
권고

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
- `swapinfo -tam` 명령의 `memory` 행을 기준으로 물리 메모리 사용량과 여유량을 확인한다.
- 사용 가능한 물리 메모리 비율이 낮고 여유 메모리 용량도 부족하면 메모리 압박 상태로 본다.
- 메모리 부족이 확인되면 과다 사용 프로세스, 최근 배치 작업, WAS/DB 메모리 설정을 확인한다.
- free가 총 메모리의 권장 비율 이상이거나 절대 여유량 기준을 만족하면 여유로 판단한다.

# 임계치
FREE_MIN_RATIO_PCT
FREE_MIN_GB

# 판단기준
- **양호**: free 비율이 `FREE_MIN_RATIO_PCT` 이상이거나 free 용량이 `FREE_MIN_GB` 이상인 경우
- **경고**: free 비율이 `FREE_MIN_RATIO_PCT` 미만이고 free 용량이 `FREE_MIN_GB` 미만인 경우
- **확인 필요**: `swapinfo` 결과 확인 또는 메모리 행 파싱이 불가능한 경우
