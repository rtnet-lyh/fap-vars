# 영역
DISK

# 세부 점검항목
Disk Swap 사용률

# 점검 내용
디스크 기반 스왑 영역의 사용률과 여유 공간을 점검한다.

# 구분
필수

# 명령어
```bash
swapinfo -a
```

# 출력 결과
```text
TYPE      AVAIL    USED    FREE  PCT  START/   LIMIT RESERVE  PRI  NAME
dev        8192    1024    7168   12%       0       -       -    1  /dev/dsk/c0t0d0s2
```

# 설명
- `swapinfo -a` 명령으로 HP-UX 디스크 스왑 장치의 총량, 사용량, 여유량, 사용률을 확인한다.
- 디스크 스왑 사용률이 높으면 물리 메모리 부족 또는 비정상 프로세스 메모리 사용 가능성이 있다.
- 스왑 공간이 부족하면 프로세스 생성 실패, 성능 저하, 장애로 이어질 수 있다.
- 일부 환경에서는 `swapinfo` 실행에 root 권한이 필요할 수 있다.

# 임계치
USED_MAX_PCT
FREE_MIN_RATIO_PCT

# 판단기준
- **양호**: 디스크 스왑 사용률이 `USED_MAX_PCT` 이하이고 여유율이 `FREE_MIN_RATIO_PCT` 이상인 경우
- **경고**: 사용률이 `USED_MAX_PCT`를 초과하거나 여유율이 `FREE_MIN_RATIO_PCT` 미만인 경우
- **확인 필요**: 명령 실행 또는 결과 파싱이 불가능한 경우
