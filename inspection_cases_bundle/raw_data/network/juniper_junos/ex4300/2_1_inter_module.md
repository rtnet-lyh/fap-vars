# 영역
HW 상태

# 세부 점검항목
인터페이스/모듈 상태

# 점검 내용
인터페이스/모듈의 Down/Up 상태 점검

# 구분
필수

# 명령어
```bash
show interfaces terse
```

# 출력 결과
```text
falcon@Center_Server_J4300_A> show interfaces terse
Interface               Admin Link Proto    Local                 Remote
ge-0/0/0                up    up
ge-0/0/0.0              up    up   eth-switch
gr-0/0/0                up    up
pfe-0/0/0               up    up
pfe-0/0/0.16383         up    up   inet
                                   inet6
pfh-0/0/0               up    up
pfh-0/0/0.16383         up    up   inet
pfh-0/0/0.16384         up    up   inet
ge-0/0/1                up    up
ge-0/0/1.0              up    up   eth-switch
me0                     down  down
me0.0                   up    down eth-switch
mtun                    up    up
pimd                    up    up
pime                    up    up
tap                     up    up
vme                     up    down
vme.0                   up    down inet


```

# 설명
- 명령어: 인터페이스 상태를 요약하여 확인하는 명령어.
- admin: 관리상태를 의미, up이면 설정상 활성화 된 상태이고 down 이면 관리적으로 비활성화 된 상태임.
- Link: 물리 링크 상태를 의미, up이면 정상 연결이고 down 이면 링크가 내려간 상태임. 

[참고]
- 운영대상 인터페이스를 변수로 설정하는것이 옳아보이나, 많은 변수를 선언해야하는 문제가 있음
- 운영 대상 목록 없이 자동화 시 admin up + link down만 취약처리.


# 임계치


# 판단기준
- **양호**: admin이 down이거나 admin이 up이고 link가 up인 경우
- **경고**: admin이 up이고 link가 down인 경우
- **확인 필요**: 명령어 실패 및 파싱 불가