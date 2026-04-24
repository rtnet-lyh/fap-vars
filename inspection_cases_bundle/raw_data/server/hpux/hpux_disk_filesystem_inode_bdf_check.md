# 영역
DISK

# 세부 점검항목
I-Node 사용률

# 점검 내용
파일시스템별 inode 사용률을 점검한다.

# 구분
권고

# 명령어
```bash
bdf -i
```

# 출력 결과
```text
Filesystem          kbytes    used   avail %used iused ifree %iuse Mounted on
/dev/vg00/lvol3   20971520  8300000 12671520  40%  4210 95000    5% /
/dev/vg00/lvol4   52428800 42000000 10428800  80% 81200 18800   81% /opt
/dev/vg00/lvol5  104857600 70000000 34857600  67% 14300 85700   15% /var
```

# 설명
- `bdf -i` 명령으로 파일시스템별 inode 사용량을 확인한다.
- inode 사용률이 높으면 디스크 용량이 남아 있어도 새 파일을 생성하지 못할 수 있다.
- 임시 파일, 로그 파일, 세션 파일처럼 작은 파일이 대량 생성되는 경로를 우선 확인한다.
- HP-UX 파일시스템 종류와 버전에 따라 inode 표시 컬럼이 다를 수 있으므로 출력 형식을 함께 검토한다.

# 임계치
INODE_USED_MAX_PCT

# 판단기준
- **양호**: 모든 운영 대상 파일시스템의 inode 사용률이 `INODE_USED_MAX_PCT` 미만인 경우
- **경고**: inode 사용률이 `INODE_USED_MAX_PCT` 이상인 파일시스템이 있는 경우
- **확인 필요**: `bdf -i` 결과에서 inode 정보를 확인할 수 없는 경우
