# 영역
HW 상태

# 세부 점검항목
인터페이스/모듈 상태

# 점검 내용
인터페이스 /모듈의 Down/Up 상태 점검

# 구분
필수

# 명령어
```bash
show interface brief
```

# 출력 결과
```text
CITS-SAN1# show interface brief

-------------------------------------------------------------------------------
Interface  Vsan   Admin  Admin   Status       SFP    Oper  Oper   Port
                  Mode   Trunk                       Mode  Speed  Channel
                         Mode                              (Gbps)
-------------------------------------------------------------------------------
fc1/1      10     auto   on      up           swl   F      8      --
fc1/2      10     auto   on      up           swl   F      8      --
fc1/3      10     auto   on      notConnected swl    --    --     --
fc1/4      10     auto   on      up           swl   F      8      --
fc1/5      10     auto   on      up           swl   F      8      --
fc1/6      10     auto   on      up           swl   F      8      --
fc1/7      10     auto   on      up           swl   F      8      --
fc1/8      10     auto   on      up           swl   F      8      --
fc1/9      10     auto   on      up           swl   F      8      --
fc1/10     10     auto   on      up           swl   F      8      --
fc1/11     10     auto   on      notConnected swl    --    --     --
fc1/12     10     auto   on      errDisabled  swl    --    --     --
fc1/13     1      auto   on      sfpAbsent    --     --    --     --
fc1/14     1      auto   on      licenseNotAv --     --    --     --
fc1/15     1      auto   on      sfpAbsent    --     --    --     --

```

# 설명
- 명령어: 인터페이스 상태를 요약하여 확인하는 명령어.
- 운영대상 인터페이스의 Status가 up 이면 정상 링크 업 상태.
- 운영대상 인터페이스를 호스트 변수로 받아와야함.

[참고]
- notconnected: 포트는 활성상태이나 물리링크가 연결되지 않았거나 상대 장비와 링크가 올라오지 않은 상태.
- sfpabsent: 모듈이 장착되지 않았거나, 인식을 못하는 상태.
- down: 인터페이스 다운 상태.
- 운영대상 인터페이스 목록을 변수로 정의 하기 힘든 환경에서는 담당자확인필요 처리.



# 임계치
up_interface
- 운영대상 인터페이스 목록 변수로 설정

# 판단기준
- **양호**: `up_interface`에 포함된 인터페이스의 status 값이 up인 경우
- **경고**: `up_interface`에 포함된 인터페이스의 status 값이 up이 아닌 경우
- **확인 필요**: 명령어 실패 및 `up_interface` 변수 미 선언, 파싱 불가