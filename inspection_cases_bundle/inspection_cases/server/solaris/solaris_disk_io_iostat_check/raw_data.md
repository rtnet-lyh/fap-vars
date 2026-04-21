# 영역
DISK

# 세부 점검항목
Disk I/O 점검

# 점검 내용
Solaris 서버의 디스크별 I/O 대기와 바쁨률을 확인해 병목 가능성을 점검합니다.

# 구분
필수

# 명령어
```bash
iostat -x
```

# 출력 결과
```text
extended device statistics
device   r/s   w/s   kr/s   kw/s   wait actv svc_t  %w  %b
sd0     15.0  10.0  150.0  100.0   0.0  1.0  10.5   5  50
sd1      5.0   3.0   50.0   30.0   0.0  0.5   8.0   0  25
sd2      0.5   0.2    5.0    2.0   0.0  0.1   7.0   0  10
```

# 설명
- `svc_t`가 20ms 이상이면 디스크 응답 지연 가능성이 큽니다.
- `%b`가 80% 이상이면 디스크가 과도하게 사용 중인 상태로 판단합니다.
- `wait`, `actv`, `r/s`, `w/s`를 함께 보고 병목 여부를 확인합니다.
- `not found`, `cannot`, `unknown` 같은 실행 오류 문구가 보이면 실패로 처리합니다.

# 임계치
- `max_service_time_ms`: `20`
- `max_busy_percent`: `80`
- `failure_keywords`: `not found,cannot,unknown`

# 판단기준
- **정상**: 모든 디스크의 `svc_t`가 20ms 미만이고 `%b`가 80% 미만인 경우
- **실패**: 어느 하나라도 `svc_t`가 20ms 이상이거나 `%b`가 80% 이상인 경우
- **실패**: `iostat -x` 명령 실행 실패, 파싱 실패, 오류 메시지 확인 시
