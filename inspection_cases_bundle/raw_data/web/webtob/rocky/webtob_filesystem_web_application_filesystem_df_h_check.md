# 영역
파일시스템

# 세부 점검항목
WEB 어플리케이션 설치 파일시스템 점검

# 점검 내용
WEB 소스가 설치되어 있는 파일시스템 FULL로 인한 서비스 불가 확인을 위한 파일시스템 점검

# 구분
필수

# 명령어

- web_app_fs_path 변수
```bash
df -h "{{ web_app_fs_path }}" # web_app_fs_path: /home/exTMS/tmax/webtob/docs
```

# 출력 결과
```text
[root@sd_tipswebwas ~]# df -h /home/exTMS/tmax/webtob/docs
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   30G   28G  2.6G  92% /
```

# 설명
- Use% (60%): 사용량이 과도하여 용량 부족 시 증설 필요. 
- Avail (20G): 남은 용량이 부족할 경우 증설 필요. ※ 기본 경로로 나타냈으며, 사용자가 임의로 경로를 변경했을 경우 수정되어야 함. 

# 임계치
max_use_percent: 파일시스템 사용률(ex.80%)
min_avail_gb: 파일시스템 여유 공간(ex.20G)

# 판단기준
- **양호**: 파일시스템 사용률이 `max_use_percent`를 초과하지 않고, 여유공간이 `min_avail_gb`이상인 상태
- **경고**: 파일시스템 사용률이 `max_use_percent`를 초과하고, 여유공간이 `min_avail_gb`미만인 상태
- **확인 필요**: 출력이 비어 있거나 명령 실행 불가/권한/미지원 등의 사유로 점검 불가한 상태
