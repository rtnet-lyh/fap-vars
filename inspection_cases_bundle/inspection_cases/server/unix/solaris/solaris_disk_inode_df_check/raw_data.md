# 영역
DISK

# 세부 점검항목
I-Node 사용률 점검

# 점검 내용
Solaris 서버의 파일시스템별 inode 사용률과 잔여 inode 비율을 점검합니다.

# 구분
필수

# 명령어
```bash
df -o i
```

# 출력 결과
```text
Filesystem          iused  ifree %iused Mounted on
/dev/dsk/c0t0d0s0   10234  89765   10%  /
/dev/dsk/c0t0d0s1    5678  12345   30%  /var
```

# 설명
- `%iused`가 80%를 초과하면 inode 부족 가능성을 검토합니다.
- `ifree`가 전체의 20% 미만이면 파일 정리 또는 파일시스템 확장을 검토합니다.
- 파일시스템별로 `iused`, `ifree`, `%iused`를 함께 확인합니다.
- `not found`, `cannot`, `unknown` 같은 실행 오류 문구가 보이면 실패로 처리합니다.

# 임계치
- `max_inode_used_percent`: `80`
- `min_inode_free_percent`: `20`
- `failure_keywords`: `not found,cannot,unknown`

# 판단기준
- **정상**: 모든 파일시스템의 inode 사용률이 80% 이하이고 잔여 inode 비율이 20% 이상인 경우
- **실패**: 어느 하나라도 inode 사용률이 80%를 초과하거나 잔여 inode 비율이 20% 미만인 경우
- **실패**: `df -o i` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
