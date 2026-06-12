# 영역
DISK

# 세부 점검항목
Disk 인식 여부 점검

# 점검 내용
시스템이 디스크 목록을 정상적으로 표시하는지 기준으로 디스크 인식 상태를 점검합니다.

# 구분
필수

# 명령어
```bash
format
```

# 출력 결과
```text
AVAILABLE DISK SELECTIONS:
0. c0t0d0 <ST3200822AS> (16.8GB)
1. c0t1d0 <ST3200822AS> (16.8GB)
2. c0t2d0 <ST3200822AS> (16.8GB)
3. c0t3d0 <ST3200822AS> (16.8GB)
Specify disk (enter its number):
```

# 설명
- `AVAILABLE DISK SELECTIONS`에 모든 디스크가 표시되어야 정상입니다.
- `Unknown`, `Drive not available` 같은 문구는 비정상으로 판단합니다.
- 디스크 수와 장치명을 함께 확인합니다.

# 임계치
- `expected_disk_count`: `1`
- `failure_keywords`: `Unknown,Drive not available`

# 판단기준
- **정상**: 디스크가 기준 개수 이상 표시되고 비정상 문구가 없는 경우
- **실패**: 디스크 수가 부족하거나 `Unknown`, `Drive not available`가 표시되는 경우
- **실패**: `format` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
