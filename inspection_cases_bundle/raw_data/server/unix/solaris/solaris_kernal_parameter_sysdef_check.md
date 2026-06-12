# type_name

일상점검(상태점검)

# area_name

서버

# category_name

KERNAL

# application_type

UNIX

# application

solaris

# inspection_code

SVR-4-1

# is_required

권고

# inspection_name

Kernel Parameter Check

# inspection_content

Solaris 서버에서 정의된 커널 파라미터, 네트워크 튜닝값, 파일 디스크립터 제한값이 조회되는지 점검합니다.

# inspection_command

```bash
printf '%s\n' shmmax/D seminfo_semmsl/D maxfiles/D maxuproc/D minfree/D msginfo_msgmax/D '$q' | mdb -k
ndd -get /dev/tcp tcp_conn_req_max_q
ndd -get /dev/tcp tcp_conn_req_max_q0
ndd -get /dev/tcp tcp_keepalive_interval
ndd -get /dev/tcp tcp_time_wait_interval
ndd -get /dev/ip ip_forwarding
ulimit -n
```

# inspection_output

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

# description

- 시스템 운영자가 커널 파라미터를 조정할 때 기준값 확인용으로 사용.
  - 커널 심볼은 `mdb -k`로 조회한다.
  - 네트워크 튜닝값은 `ndd -get`으로 조회한다.
  - 파일 디스크립터 제한값은 `ulimit -n`으로 조회한다.
  - 기준값이 정의된 항목은 실제값과 비교하고, 기준값이 비어 있거나 없으면 값이 조회되는지만 확인한다.

# thresholds

[
    {id: null, key: "required_parameters", value: "shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax", sortOrder: 0}
,
    {id: null, key: "required_ndd_parameters", value: "/dev/tcp:tcp_conn_req_max_q,/dev/tcp:tcp_conn_req_max_q0,/dev/tcp:tcp_keepalive_interval,/dev/tcp:tcp_time_wait_interval,/dev/ip:ip_forwarding", sortOrder: 1}
,
    {id: null, key: "ulimit_n", value: "", sortOrder: 2}
,
    {id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,unknown,command not found,module missing,invalid argument", sortOrder: 3}
]

# inspection_script

`inspection_cases/server/unix/solaris/solaris_kernal_parameter_sysdef_check/script.py`를 정본으로 사용한다.
