# 영역
MEMORY

# 세부 점검항목
메모리 상태 확인

# 점검 내용
할당된 메모리의 정상 인식 여부를 점검한다.

# 구분
필수

# 명령어
```bash
machinfo
```

# 출력 결과
```text
CPU info:
  4 Intel(R) Itanium 2 processors

Memory: 16384 MB (16 GB)
Firmware info:
  Firmware revision:  03.30
```

# 설명
- `machinfo` 명령으로 HP-UX 시스템이 인식한 물리 메모리 총량을 확인한다.
- 장비 구성 기준의 설치 메모리와 OS 인식 메모리가 일치하는지 비교한다.
- 기대보다 적게 인식되면 메모리 모듈 장애, 파티션 할당, 펌웨어 설정, 하드웨어 구성 변경 여부를 확인한다.
- 일부 모델에서는 `cstm`, `stm`, MP/GSP 로그 등 장비 진단 도구 결과를 함께 확인한다.

# 임계치
expected_memory_gb

# 판단기준
- **양호**: OS 인식 메모리가 기대 설치 메모리와 일치하거나 허용 범위 이내인 경우
- **경고**: OS 인식 메모리가 기대값보다 부족한 경우
- **확인 필요**: 기대 메모리 기준이 없거나 `machinfo`를 사용할 수 없는 경우
