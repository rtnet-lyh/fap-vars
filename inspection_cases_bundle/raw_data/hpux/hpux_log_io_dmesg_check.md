# 영역
로그

# 세부 점검항목
I/O 에러로그

# 점검 내용
입출력 작동 이상 유무 점검(Timeout, I/O Error, Transport Failed, Media Error)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'timeout|i/o error|transport failed|media error'
```

# 출력 결과
```text
Timeout occurred while waiting for device
I/O error on device /dev/dsk/c2t0d0
```

# 설명
- `dmesg` 로그에서 디스크, 스토리지, HBA, 드라이버 관련 I/O 오류 키워드를 확인한다.
- timeout, I/O error, transport failed, media error는 장치 응답 지연 또는 매체 장애의 주요 징후다.
- 동일 장치에서 오류가 반복되면 스토리지 경로, 디스크 상태, SAN 연결, 파일시스템 상태를 함께 점검한다.
- 오류가 확인되면 장애 시각과 업무 영향도를 대조한다.

# 임계치
io_bad_log_keywords

# 판단기준
- **양호**: I/O 오류 키워드가 확인되지 않는 경우
- **경고**: timeout, I/O error, transport failed, media error가 확인되는 경우
- **확인 필요**: 로그 확인 또는 장치 매핑이 불가능한 경우
