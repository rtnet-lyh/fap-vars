# 영역
로그

# 세부 점검항목
서비스 로그 이상 유무 점검

# 점검 내용
각 서비스 컨테이너 로그 점검(비정상 SQL 존재 여부, Trasaction commit 확인 등 서비스 로그 점검)

# 구분
필수

# 명령어 - admin_log_path: /home/exTMS/tmax/jeus/log/adminServer
```bash
tail -f {{ admin_log_path }}/JeusServer.log
```

# 출력 결과
```text
[exTMS@tips_was1:/home/exTMS/tmax/jeus/log/adminServer]$ tail -f /home/exTMS/tmax/jeus/log/adminServer/JeusServer.log
[2026.05.14 13:10:28:479][2] [adminServer-777] [SERVER-0208] Operation: DOWNLOAD_CONFIG [extms2]
[2026.05.14 13:10:28:480][2] [adminServer-777] [SERVER-0228] The files on the managed server are up-to-date, so the configuration files will not be sent..
[2026.05.14 13:10:30:079][2] [adminServer-15] [SCF-0121] SCF Connection from extms2 has been allowed. Handler is SocketStream@3b0d6807(172.18.9.62:10000(SCF) -> 172.18.9.63:10010(SCF)).
[2026.05.14 13:10:30:079][2] [adminServer-15] [SCF-0310] State of member [extms2] changed. STOPPED -> ALIVE
[2026.05.14 13:10:30:186][2] [adminServer-1044] [Domain-0037] Sending a resynchronization request to extms2[172.18.9.63:10010(SCF)]
[2026.05.14 13:10:30:290][2] [adminServer-777] [SERVER-0208] Operation: DOWNLOAD_CONFIG [extms2]
[2026.05.14 13:10:30:291][2] [adminServer-777] [SERVER-0228] The files on the managed server are up-to-date, so the configuration files will not be sent..
[2026.05.14 13:10:42:608][2] [adminServer-399] [Deploy-0376] The state of the application [exTMS] in the server [extms2] is DISTRIBUTED. Final state is DISTRIBUTED
[2026.05.14 13:10:42:620][2] [adminServer-68] [Deploy-0376] The state of the application [exTMS] in the server [extms2] is RUNNING. Final state is RUNNING
[2026.05.14 13:10:42:696][2] [adminServer-768] [Domain-0022] Domain Administration Server succeeded to start server extms2.
```

# 설명

# 임계치

# 판단기준 - 양호, 경고 수동 확인 필요
- **양호**: 
- **경고**: 
- **확인 필요**: 출력 및 로그파일이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
