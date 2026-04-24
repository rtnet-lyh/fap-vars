# 영역
커널

# 세부 점검항목
Kernel Parameter Check

# 점검 내용
커널 파라미터 설정값이 운영 기준에 맞게 적용되어 있는지 점검한다.

# 구분
권고

# 명령어
```bash
kctune
```

# 출력 결과
```text
Tunable                      Value  Expression  Changes
max_thread_proc              1024   Default     Immed
maxfiles                     2048   Default     Immed
nproc                        4200   Default     Immed
semmns                       4096   Default     Immed
```

# 설명
- `kctune` 명령으로 HP-UX 커널 튜너블 파라미터의 현재 값을 확인한다.
- 업무 시스템, DBMS, WAS 권장값과 OS 기본값이 다를 수 있으므로 서비스 기준값과 비교한다.
- 중요한 파라미터가 권장값보다 낮으면 프로세스, 파일 디스크립터, IPC 리소스 부족이 발생할 수 있다.
- 변경이 필요한 경우 적용 시점, 재부팅 필요 여부, 서비스 영향도를 사전에 검토한다.

# 임계치
required_kernel_parameters

# 판단기준
- **양호**: 필수 커널 파라미터가 운영 기준값을 만족하는 경우
- **경고**: 필수 커널 파라미터가 기준값보다 낮거나 잘못 설정된 경우
- **확인 필요**: 시스템별 기준값이 정의되지 않았거나 `kctune` 결과 확인이 불가능한 경우
