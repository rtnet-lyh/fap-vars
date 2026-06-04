# 영역
로그 

# 세부 점검항목
시스템 로그

# 점검 내용
HW 상태와 관련된 Error 로그(Fail, Error, Warning, Stop, Down) 발생 유무 점검

# 구분
필수

# 명령어
```bash
show log
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show log
2026/05/27 16:32:58 Center_PAS-K3200X_A (notice) sshd[28319]: (AUDIT)  pam_unix(sshd:session): session opened for service sshd
2026/05/27 16:32:58 Center_PAS-K3200X_A (notice) sshd[28319]: (AUDIT)  pam_unix(sshd:session): session opened for user falcon by (uid=0)
2026/05/27 16:32:58 Center_PAS-K3200X_A (notice) sshd[28319]: (AUDIT)  notice: Accepted password for falcon from 172.18.8.191 port 34156 ssh2
2026/05/27 16:29:04 Center_PAS-K3200X_A (notice) sshd[24761]: (AUDIT)  pam_unix(sshd:session): session closed for user falcon by (uid=0)
2026/05/27 16:23:32 Center_PAS-K3200X_A (notice) [amss.cli.backend] (AUDIT)  last message repeated 2 times
2026/05/27 16:22:04 Center_PAS-K3200X_A (notice) [amss.cli.backend] (AUDIT)  Config Success: Done [172.18.8.191]
2026/05/27 16:19:15 Center_PAS-K3200X_A (notice) [amss.cli.backend] (AUDIT)  Config Success: Done [172.18.8.191]
2026/05/27 16:19:02 Center_PAS-K3200X_A (notice) sshd[24761]: (AUDIT)  pam_unix(sshd:session): session opened for service sshd
2026/05/27 16:19:02 Center_PAS-K3200X_A (notice) sshd[24761]: (AUDIT)  pam_unix(sshd:session): session opened for user falcon by (uid=0)
2026/05/27 16:19:02 Center_PAS-K3200X_A (notice) sshd[24761]: (AUDIT)  notice: Accepted password for falcon from 172.18.8.191 port 48804 ssh2

```

# 설명
※ 로그레벨
- (notice): 일반 운영 정보
- (warning): 경고
- (err): 오류
- (fail): 기능 실패
- (down): 인터페이스/서비스 비정상 상태

# 임계치

# 판단기준
- **양호**: (err), (fail), (down), (stop), (warning) 관련 치명 로그 미발생 상태
- **경고**: (err), (fail), (down), (stop), (warning) 관련 치명 로그 발생 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
