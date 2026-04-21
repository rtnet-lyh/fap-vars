# 영역
OS

# 세부 점검항목
Multipath 이중화 정상 유무 점검

# 점검 내용
Solaris 서버의 STMS 활성 여부와 각 Logical Unit의 멀티패스 경로 상태를 점검합니다.

# 구분
필수

# 명령어
```bash
mpathadm show lu
```

# 출력 결과
```text
Logical Unit: 600144F0A08A4DB300005E1000000456
mpath-support: libmpscsi_vhci.so
Vendor: HITACHI
Product: OPEN-V
Revision: 6000
Stms State: ENABLED
Available Spare: NO
Active Spare: NO
Current Path: /dev/dsk/c0t50060E801049C1F0d0s2
Path Status: CONNECTED
Path /dev/dsk/c0t50060E801049C1F1d0s2: CONNECTED
Path /dev/dsk/c0t50060E801049C1F2d0s2: DISABLED
Path /dev/dsk/c0t50060E801049C1F3d0s2: CONNECTED
```

# 설명
- `Stms State`는 `ENABLED`여야 합니다.
- `Path Status`는 `CONNECTED`가 정상입니다.
- 개별 `Path ...` 상태도 `CONNECTED`여야 하며, `DISABLED` 경로가 있으면 멀티패스 경로 점검이 필요합니다.
- `mpathadm` 명령이 없거나 출력 형식을 해석하지 못하면 실패로 처리합니다.

# 임계치
- `expected_stms_state`: `ENABLED`
- `expected_path_status`: `CONNECTED`
- `expected_path_state`: `CONNECTED`
- `disallowed_path_states`: `DISABLED`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 모든 Logical Unit의 `Stms State`가 `ENABLED`, `Path Status`가 `CONNECTED`, 개별 경로 상태가 모두 `CONNECTED`인 경우
- **실패**: `DISABLED` 등 비정상 경로가 하나라도 있거나 `Stms State`, `Path Status`가 기준과 다른 경우
- **실패**: `mpathadm` 명령 실행 실패, 명령 미설치, 출력 파싱 실패, 오류 로그 확인 시
