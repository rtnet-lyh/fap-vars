# 영역
로그

# 세부 점검항목
MEMORY 로그

# 점검 내용
메모리 오류 에러로그 점검(Singlebit/Multibit Errors, Uncorrectable ECC Errors)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'ecc error|single[- ]?bit|multi[- ]?bit|uncorrectable'
```

# 출력 결과
```text
Multi-bit ECC error detected on memory bank 1
```

# 설명
- `dmesg` 로그에서 메모리 ECC, single-bit, multi-bit, uncorrectable 오류를 확인한다.
- single-bit 오류가 반복되거나 multi-bit/uncorrectable 오류가 있으면 메모리 모듈 장애 가능성이 높다.
- 오류 발생 위치가 표시되면 해당 메모리 뱅크 또는 DIMM 정보를 확인한다.
- 장애 로그가 반복되면 벤더 점검과 부품 교체를 검토한다.

# 임계치
memory_bad_log_keywords

# 판단기준
- **양호**: 메모리 ECC 또는 uncorrectable 오류 로그가 없는 경우
- **경고**: ECC, single-bit, multi-bit, uncorrectable 관련 로그가 확인되는 경우
- **확인 필요**: 로그 확인이 불가능하거나 오류 위치를 식별할 수 없는 경우
