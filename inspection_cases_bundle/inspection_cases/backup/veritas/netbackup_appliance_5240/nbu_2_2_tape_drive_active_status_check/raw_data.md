# 영역
물리 점검

# 세부 점검항목
장비 Tape 인식 상태 점검

# 점검 내용
드라이브, 라이브러리 Active 상태 점검

# 구분
필수

# 명령어
```bash
vmoprcmd -d ds
```

# 출력 결과(결과있음 - 172.18.8.28)
```text

netbackup:/home/maintenance # vmoprcmd -d ds

                                  DRIVE STATUS

Drv Type   Control  User      Label  RecMID  ExtMID  Ready   Wr.Enbl.  ReqId
  0 hcart3 DOWN-TLD             -                     No       -         0
  1 hcart3 DOWN-TLD             -                     No       -         0

```
# 출력 결과(결과없음 - 172.18.8.27,30)
```text

tggitsbackup:/home/maintenance # vmoprcmd -d ds
The Media Manager device daemon (ltid) is not active on host tggitsbackup

```
# 설명
- 명령어: NetBackup media Manager에서 관리하는 Tape Drive의 운용 상태를 확인하는 명령어.
- Ready 값이 Yes이면 드라이브가 사용가능한 상태로 판단.
- Tape 미 사용 장비(출력 결과: 결과없음)에는 '해당 없음','양호' 처리가 옳아보임.

[참고]
- 'Control' 컬럼 내 어떤 문구가 올 수 있는지 확인 불가
- AI: 'Control' 컬럼의 값이 'TLD', 'ACS', 'TLH', 'AVR' 이면 양호라고 함.

# 임계치
control_values
- control 컬럼의 정상 값

# 판단기준
- **양호**: 'DRIVE STATUS'값이 존재하지 않거나, 각 라인마다 Ready 값이 'Yes'이면서, control 값이 `control_values`인 경우.
- **경고**: 'DRIVE STATUS'값이 존재하면서 각 라인마다 Ready 값이 'Yes'가 아니거나, control 값이 `control_values`에 없는 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.