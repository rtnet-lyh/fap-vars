# 영역
KERNAL

# 세부 점검항목
Kernel Parameter Check

# 점검 내용
Solaris 서버의 기본 커널 파라미터가 조회되는지와 핵심 파라미터 존재 여부를 점검합니다.

# 구분
필수

# 명령어
```bash
sysdef
```

# 출력 결과
```text
*Tunable Parameters*
shmmax: 4294967295
shminfo_shmmin: 1
seminfo_semmsl: 256
seminfo_semmns: 32000
seminfo_semopm: 32

*File System Parameters*
maxfiles: 8192
maxuproc: 512

*Memory Management Parameters*
maxpgio: 8192
minfree: 200
desfree: 400
lotsfree: 1024

*IPC Parameters*
msginfo_msgmax: 8192
msginfo_msgmnb: 16384
msginfo_msgtql: 40
msginfo_msgseg: 2048
```

# 설명
- 운영 표준에서 참조하는 핵심 커널 파라미터가 조회되는지 확인합니다.
- 예시에서는 `shmmax`, `seminfo_semmsl`, `maxfiles`, `maxuproc`, `minfree`, `msginfo_msgmax`를 확인합니다.
- `not found`, `cannot`, `unknown`, `module` 같은 실행 오류 문구가 보이면 실패로 처리합니다.

# 임계치
- `required_parameters`: `shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax`
- `failure_keywords`: `not found,cannot,unknown,module`

# 판단기준
- **정상**: 핵심 파라미터가 모두 조회되는 경우
- **실패**: 핵심 파라미터 일부가 누락되거나 값을 해석할 수 없는 경우
- **실패**: `sysdef` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
