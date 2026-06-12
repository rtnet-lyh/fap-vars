# 영역
DISK

# 세부 점검항목
파일시스템 사용량

# 점검 내용
파일시스템 사용량 점검

# 구분
권고

# 명령어
```bash
df
```

# 출력 결과
```text
Filesystem          1K-blocks      Used Available Use% Mounted on
devtmpfs              7831328         0   7831328   0% /dev
tmpfs                 7863464         8   7863456   1% /dev/shm
tmpfs                 3145388    338060   2807328  11% /run
/dev/mapper/rl-root  73364480  26892896  46471584  37% /
/dev/sda1             1038336    396548    641788  39% /boot
/dev/mapper/rl-home 793069212 174973520 618095692  23% /home
tmpfs                 1572692        36   1572656   1% /run/user/1000
```

# 설명
- `df` 명령을 실행해서 파일시스템별 사용률 정보를 가져온다.
- 임계치 `max_usage_percent`와 제외 목록 `exclude_mount_points`를 읽고, 제외 목록은 `|` 기준으로 분리한다.
- 각 행에서 파일시스템, 마운트포인트, 사용률을 파싱한 뒤 제외 대상은 점검 목록에서 뺀다.
- 제외 후 남은 파일시스템 중 사용률이 임계치를 넘는 항목이 하나라도 있으면 실패한다.
- 모두 임계치 이하이면 최대 사용률 파일시스템, 제외 항목, 전체 개수를 metrics로 남기고 정상 처리한다.

# 임계치
max_usage_percent, exclude_mount_points

# 판단기준
- **양호**: `exclude_mount_points`에 포함된 마운트포인트를 제외한 모든 파일시스템의 `Use%` 값이 `max_usage_percent` 이하인 상태
- **실패**: 제외 후 점검 대상 파일시스템 중 하나 이상에서 `Use%` 값이 `max_usage_percent`를 초과한 상태
- **점검 제외**: `exclude_mount_points`에 지정된 마운트포인트는 용도나 정책상 별도 관리 대상으로 보고 파일시스템 사용량 판정에서 제외
- **확인 필요**: `df` 명령 실행에 실패하거나 출력 형식이 달라 파일시스템, 마운트포인트, 사용률을 파싱할 수 없는 상태
