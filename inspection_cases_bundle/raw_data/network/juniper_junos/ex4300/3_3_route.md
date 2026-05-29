# 영역
서비스

# 세부 점검항목
라우팅 Table 상태

# 점검 내용
라우팅 Table 정상 여부 확인

# 구분
권고

# 명령어
```bash
show route 0.0.0.0
```

# 출력 결과(193.1.0.206)
```text
falcon@Center_Server_J4300_A> show route 0.0.0.0

inet.0: 3 destinations, 3 routes (3 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

0.0.0.0/0          *[Static/5] 289w0d 15:39:48
                    >  to 172.18.8.254 via irb.808



```

# 설명
- 명령어: IP 라우팅 테이블 상태를 확인하는 명령어
- Default Route가 목적지 경로를 찾지 못할 때 트래픽을 전송할 경로인 기본 gateway인 0.0.0.0으로 설정되어있어야함.


# 임계치


# 판단기준
- **양호**: 결과 값 내 '0.0.0.0' 문구 존재
- **경고**: 결과 값 내 '0.0.0.0' 문구 미 존재
- **확인 필요**: 명령어 실패 및 파싱 불가