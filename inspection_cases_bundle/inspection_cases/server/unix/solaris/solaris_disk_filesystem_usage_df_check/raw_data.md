# 영역
DISK

# 세부 점검항목
파일시스템 사용량

# 점검 내용
파일시스템별 사용률과 여유 공간 비율을 기준으로 디스크 공간 부족 여부를 점검합니다.

# 구분
필수

# 명령어
```bash
df -h
```

# 출력 결과
```text
Filesystem      Size Used Avail Use% Mounted on
/dev/dsk/s1      50G  25G   23G  53% /
/dev/dsk/s2     100G  60G   35G  66% /var
```

# 설명
- `Use%`가 높으면 디스크 부족 위험이 있습니다.
- `Avail`이 충분한지 함께 확인해 증설 또는 정리 필요성을 판단합니다.
- 어떤 mount point가 영향을 받는지 `Mounted on` 기준으로 확인합니다.

# 임계치
- `used_max_percent`: `80`
- `avail_min_percent`: `20`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 모든 파일시스템의 사용률이 기준 이하이고 여유 비율이 기준 이상인 경우
- **실패**: 하나라도 사용률 또는 여유 비율이 기준을 벗어난 경우
- **실패**: `df -h` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
