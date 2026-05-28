# 영역
용량 점검

# 세부 점검항목
용량 점검

# 점검 내용
백업 수행 용량(기존 백업 용량과 차이 확인) 및 포트 사용 상태 점검

# 구분
필수

# 명령어
```bash
/usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN
```

# 출력 결과
```text

netbackup:/home/maintenance # /usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN

************ Data Store statistics ************
Data storage      Raw     Size    Used    Avail   Use%    Free%
                  34.8T   33.4T   13.9T   19.5T   42%     58.3%

Number of containers             : 207392
Average container size           : 73505465 bytes (70.10MB)
Space allocated for containers   : 15244445468144 bytes (13.86TB)
Reserved space                   : 1540390020096 bytes (1.40TB)
Reserved space percentage        : 4.0%
Reserved space for cloud cache   : 0.0B (0.0%)

Use "--dsstat 1" to get more accurate statistics
Use "--dsstat 2" to get statistics for each partition
Use "--dsstat 3" to get more accurate statistics for each partition

tcp        0      0 0.0.0.0:13778           0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:13779           0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:3443          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:2323          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:13780         0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:1556            0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:36629         0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:36821         0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:1557          0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:42581           0.0.0.0:*               LISTEN



```
# 설명
- /usr/openv/pdde/pdcr/bin/crcontrol --dsstat 명령어: MSDP 저장소의 용량 사용 현황을 확인하는 명령어.
- netstat -tuln | grep LISTEN 명령어: 현재 장비에서 LISTEN 중인 TCP/UDP 포트를 확인하는 명령어.


# 임계치
max_usage_percent
- 사용률 최대 값
denied_ports
- 취약한 포트 목록

# 판단기준
- **양호**: 'Use%'가 `max_usage_percent` 이하이고, 주소 값 중 : 다음 값이 `denied_ports`와 일치하지 않는 경우.
- **경고**: 'Use%'가 `max_usage_percent` 초과이거나, 주소 값 중 : 다음 값이 `denied_ports`와 일치할 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.