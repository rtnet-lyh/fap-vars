# 영역
KERNAL

# 세부 점검항목
Kernel Parameter Check

# 점검 내용
Solaris 서버에서 정의된 커널 파라미터, 네트워크 튜닝값, 파일 디스크립터 제한값이 조회되는지 점검합니다.

# 구분
필수

# 명령어
```bash
printf '%s\n' shmmax/D seminfo_semmsl/D maxfiles/D maxuproc/D minfree/D msginfo_msgmax/D '$q' | mdb -k
ndd -get /dev/tcp tcp_conn_req_max_q
ndd -get /dev/tcp tcp_conn_req_max_q0
ndd -get /dev/tcp tcp_keepalive_interval
ndd -get /dev/tcp tcp_time_wait_interval
ndd -get /dev/ip ip_forwarding
ulimit -n
```

# 출력 결과
```text
shmmax: 0t4294967295
seminfo_semmsl: 256
maxfiles: 8192
maxuproc: 512
minfree: 200
msginfo_msgmax: 8192

ndd -get /dev/tcp tcp_conn_req_max_q
128

ndd -get /dev/tcp tcp_conn_req_max_q0
1024

ndd -get /dev/tcp tcp_keepalive_interval
7200000

ndd -get /dev/tcp tcp_time_wait_interval
60000

ndd -get /dev/ip ip_forwarding
0

ulimit -n
1024
```

# 설명
- 운영 표준에서 참조하는 핵심 커널 심볼은 `mdb -k`로 조회합니다.
- 네트워크 튜닝값은 `ndd -get`으로 조회하며, 스크립트 기본값은 TCP 큐/keepalive/time-wait 및 IP forwarding 항목입니다.
- 파일 디스크립터 제한값은 `ulimit -n`으로 조회합니다.
- 기준값이 정의된 항목은 실제값과 비교하고, 기준값이 비어 있거나 없으면 값이 조회되는지만 확인합니다.
- `not found`, `cannot`, `unknown`, `module` 같은 실행 오류 문구가 보이면 실패로 처리합니다.

# 임계치
- `required_parameters`: `shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax`
- `required_ndd_parameters`: `/dev/tcp:tcp_conn_req_max_q,/dev/tcp:tcp_conn_req_max_q0,/dev/tcp:tcp_keepalive_interval,/dev/tcp:tcp_time_wait_interval,/dev/ip:ip_forwarding`
- `ndd:/dev/tcp:tcp_conn_req_max_q`: 선택 기준값
- `ulimit_n`: 선택 기준값
- `failure_keywords`: `not found,cannot,unknown,module,invalid argument`

# 판단기준
- **정상**: `mdb -k`, `ndd -get`, `ulimit -n` 기준 항목이 모두 조회되고 기준값이 있는 항목은 일치하는 경우
- **실패**: 필수 항목 일부가 누락되거나 값이 비어 있는 경우
- **실패**: 기준값이 있는 항목의 실제값이 일치하지 않는 경우
- **실패**: 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
