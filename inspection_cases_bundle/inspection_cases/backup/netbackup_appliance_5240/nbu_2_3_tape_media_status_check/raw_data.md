# 영역
물리 점검

# 세부 점검항목
Tape 정상 점검

# 점검 내용
테이프 미디어 불량 상태 점검 및 사용상태 점검

# 구분
필수

# 명령어
```bash
bpmedialist -mlist -U
```

# 출력 결과(결과있음 - 172.18.8.28)
```text

netbackup:/home/maintenance # bpmedialist -mlist -U
Server Host = netbackup

 id     rl  images   allocated        last updated      density  kbytes restores
           vimages   expiration       last read         <------- STATUS ------->
           On Hold
--------------------------------------------------------------------------------
EMR162   9     17   03/12/2026 16:29  03/14/2026 15:56  hcart3  9207800736     0
               17   INFINITY              N/A         FULL
           0

EMR166  24     20   03/13/2026 15:21  03/13/2026 21:40  hcart3  7579495552     0
               20   INFINITY              N/A
           0

EMR167   9     13   03/14/2026 15:56  03/14/2026 23:03  hcart3  7494612576     0
               13   INFINITY              N/A
           0


```
# 출력 결과(결과없음 - 172.18.8.27,30)
```text

tggitsbackup:/home/maintenance # bpmedialist -mlist -U
tggitsbackup:/home/maintenance #

```
# 설명
- 명령어: Tape Media 정보를 확인하는 명령어.
- '<------- STATUS ------->' 컬럼은 Tape Media 사용 상태를 나타낸다.


[참고]
- '<------- STATUS ------->' 컬럼 내 어떤 문구가 올 수 있는지 확인 불가
- AI: 'FROZEN', 'SUSPENDED', 'UNAVAIL' 값은 경고라고 함.

# 임계치
media_status_value
- STATUS 컬럼의 정상 값

# 판단기준
- **양호**: 명령어 결과가 존재하지 않거나, 각 라인마다 STATUS 값이 `media_status_value`인 경우.
- **경고**: 명령어 결과가 존재하지 않거나, 각 라인마다 STATUS 값이 `media_status_value`이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.