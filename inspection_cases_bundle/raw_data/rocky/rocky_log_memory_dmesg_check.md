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
dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'
```

# 출력 결과
```text
[   12.345678] EDAC MC0: ECC error detected on CPU#0Channel#1_DIMM#0
[   12.345912] EDAC MC0: Single-bit ECC error corrected on DIMM_A1
[  128.456789] mce: [Hardware Error]: Memory error detected: Uncorrectable ECC error
[  128.457103] EDAC MC0: Multi-bit ECC error detected on DIMM_B2
[  128.457821] EDAC MC0: Uncorrectable ECC error on CPU_SrcID#0_Ha#0_Chan#1_DIMM#1
```

# 설명
- (ECC 오류 메시지) ECC error detected 메시지가 발견되면, 메모리 모듈에 오류가 발생했음을 나타내며, 메모리 모듈 점검 및 교체 필요
- (단일 비트 오류 메시지) Single-bit ECC error corrected 메시지는 단일 비트 오류가 수정되었음을 나타내며, 이러한 오류가 자주 발생하면 메모리 모듈 점검 권고
- (다중 비트 오류 메시지) Multi-bit ECC error detected 메시지가 발견되면, 다중 비트 오류가 감지되었음을 나타내며, 메모리 모듈 점검 및 교체 필요
- (수정 불가능한 ECC 오류 메시지) Uncorrectable ECC error 메시지가 발견되면, 수정 불가능한 ECC 오류가 발생했음을 나타내며, 메모리 모듈 점검 및 교체 필요

# 임계치
memory_error_keywords

# 판단기준
- **양호**: `dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'` 결과에 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 메모리 오류 징후로 간주함