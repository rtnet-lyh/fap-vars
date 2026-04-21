# 영역
MEMORY

# 세부 점검항목
메모리 상태 확인

# 점검 내용
시스템이 총 메모리 용량과 DIMM 모듈 정보를 정상적으로 인식하는지 점검합니다.

# 구분
필수

# 명령어
```bash
prtdiag
```

# 출력 결과
```text
System Configuration: Sun Microsystems sun4u
Memory size: 8192 Megabytes
Memory Module:
DIMM 0: 4096 MB, 64-bit, Error Correcting Code
DIMM 1: 4096 MB, 64-bit, Error Correcting Code
```

# 설명
- `Memory size`는 시스템이 인식한 총 메모리 크기입니다.
- DIMM 정보가 누락되거나 총 메모리가 기대치보다 적으면 인식 불량 또는 장착 이상을 의심할 수 있습니다.
- DIMM 단위 정보와 총 메모리 크기를 함께 확인합니다.

# 임계치
- `expected_memory_mb`: `8192`
- `min_dimm_count`: `1`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 총 메모리가 기대치 이상이고 DIMM 항목이 정상적으로 표시되는 경우
- **실패**: 총 메모리 용량이 부족하거나 DIMM 정보가 부족한 경우
- **실패**: `prtdiag` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
