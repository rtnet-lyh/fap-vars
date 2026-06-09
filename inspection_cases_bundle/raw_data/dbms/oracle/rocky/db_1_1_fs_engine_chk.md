# 영역
OS 파일시스템 사용률

# 세부 점검항목
DB엔진 파일시스템

# 점검 내용
DB 엔진이 설치된 파일시스템의 물리적인 저장 공간 사용률 점검(Full 시 서비스 불가)

# 구분
필수

# 명령어
```bash
df -h
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> df -h
Filesystem           Size  Used Avail Use% Mounted on
devtmpfs             4.0M     0  4.0M   0% /dev
tmpfs                 32G     0   32G   0% /dev/shm
tmpfs                 13G  1.3G   12G  10% /run
/dev/mapper/rl-root  200G   39G  162G  20% /
/dev/md126p2         960M  298M  663M  32% /boot
/dev/mapper/rl-home  617G  4.4G  612G   1% /home
/dev/mapper/vg0-lv0  196G   42G  145G  23% /koem/oracle
/dev/mapper/vg2-lv1  1.5T  476G  970G  33% /koem/oradata/data
/dev/mapper/vg1-lv0  295G  6.7G  273G   3% /koem/oradata/arch
/dev/md126p1         599M  7.1M  592M   2% /boot/efi
tmpfs                6.3G  104K  6.3G   1% /run/user/0
/dev/loop0            11G   11G     0 100% /mnt
tmpfs                6.3G   36K  6.3G   1% /run/user/1000



---
```

# 설명
- `df -h` 명령을 통해 DB 엔진, 아카이브 로그, DB 시스템 로그가 위치한 파일시스템의 사용률을 확인합니다.

# 임계치
max_usage_percent: 최대 허용 디스크 사용률 (예: 80%)

# 판단기준
- **양호**: 파일시스템 사용률이 임계치 이하로 유지됨
- **경고**: 파일시스템 사용률이 임계치를 초과하여 디스크 고갈 위험이 있음
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태
