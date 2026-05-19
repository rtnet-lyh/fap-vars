# 영역
설정파일

# 세부 점검항목
기동 스크립트 확인

# 점검 내용
각 인스턴스별 기동 스크립트 변경 여부 확인

# 구분
권고

# 명령어 - jeus_inst_path: /home/exTMS/tmax/jeus/bin
```bash 
stat {{ jeus_inst_path }}/startDomainAdminServer
```

# 출력 결과
```text
[exTMS@tips_was1:/home/exTMS/tmax/jeus/bin]$ stat /home/exTMS/tmax/jeus/bin/startDomainAdminServer
  File: /home/exTMS/tmax/jeus/bin/startDomainAdminServer
  Size: 3507            Blocks: 8          IO Block: 4096   일반 파일
Device: fd00h/64768d    Inode: 37690590    Links: 1
Access: (0700/-rwx------)  Uid: ( 1001/   exTMS)   Gid: ( 1001/   exTMS)
Context: unconfined_u:object_r:user_home_t:s0
Access: 2026-05-15 15:51:28.263962332 +0900
Modify: 2025-07-25 11:22:36.982827460 +0900
Change: 2025-07-25 11:22:36.982827460 +0900
 Birth: 2025-07-25 11:22:36.982827460 +0900
```

# 설명
- 기동 스크립트의 파일 상태 정보를 확인하여, 수정 시간, 액세스 시간, 생성 시간 등을 포함한 정보를 확인할 수 있음. 이를 통해 스크립트 변경 여부를 확인할 수 있음.

# 임계치

# 판단기준 - 수동 확인 필요
- **양호**: Access, Modify, Change 값에 이상이 없는 상태
- **경고**: Access, Modify, Change 값에 이상이 있는 상태
- **확인 필요**: 파일이 없거나 실행불가(권한/미설치/미기동 등)로 점검 불가한 상태