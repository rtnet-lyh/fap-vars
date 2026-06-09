# 영역
Connection Pool 상태

# 세부 점검항목
DB연결 상태 점검

# 점검 내용
DB에 연결된 객체 저장공간인 DB Connection Pool 확인(각 컨테이너별 Enable상태 확인)

# 구분
필수

# 명령어
```bash
netstat -ntp | grep '3306' | awk '{print $6}' | sort | uniq -c
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
- 선행작업 필요
- ps -ef | grep tomcat 해서 피드 확인해서 {피드} 부분에 입력 필요

[root@re-test-POTAL logs]# /home/koem01/elasticsearch-7.6.2/jdk/bin/jstat -gcutil {피드}
  S0     S1     E      O      M     CCS    YGC     YGCT    FGC    FGCT    CGC    CGCT     GCT
  0.00   0.00  17.44   2.75  98.51  96.42      5    0.282     3    0.529     -        -    0.811

---
```

# 설명
- `netstat -ntp` 명령어를 사용하여 WAS 서비스 포트(8080/8009) 혹은 DB 포트(3306)에 연결된 네트워크 세션의 상태(ESTABLISHED, CLOSE_WAIT 등) 통계를 확인합니다. 이를 통해 워커 스레드나 커넥션 풀의 고갈 여부를 파악합니다.

# 임계치
max_established_conn: 서비스 및 DB 커넥션 풀의 최대 허용 한계치

# 판단기준
- **양호**: 활성화된 연결(ESTABLISHED) 수가 임계치 내에서 안정적으로 관리됨
- **경고**: 연결 수가 한계치에 도달하거나, 반환되지 않는 `CLOSE_WAIT` 상태가 다수 누적됨
- **확인 필요**: 명령어 오류 또는 수집된 네트워크 통계 결과와 포맷이 달라 점검이 불가한 상태
