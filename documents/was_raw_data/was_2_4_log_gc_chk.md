# 영역
로그

# 세부 점검항목
메모리 로그 이상 유무 점검

# 점검 내용
Full GC(Garbage Collection) 발생 빈도 점검(오래된 객체에 대한 삭제 등의 메모리 공간 확보 작업의 발생 빈도 체크, 일정기간 로그분석을 통해 GC 튜닝 여부 결정)


# 구분
필수

# 명령어 - gc_log_path: /home/exTMS/tmax/jeus/log/gclog
```bash
grep -i "Full GC" $(ls {{ gc_log_path }}/*gc.log*|sort|tail -n 1) | wc -l
```

# 출력 결과
```text
[root@sg_tipswebwas gclog]# grep -i "Full GC" /home/exTMS/tmax/jeus/log/gclog/tips_gc.log_20260414103124 | wc -l
1
```

# 설명
- Full GC 발생 횟수: 시스템에서 발생한 Full GC 이벤트의 총 횟수를 나타냄. Full GC가 하루에 1~2회 발생하는 것은 정상 범위로 볼 수 있지만, Full GC가 빈번하게 발생하면 메모리 관리 설정을 점검하고, JVM 옵션을 조정하거나 메모리 용량을 늘리는 것이 필요. 
※ 메모리 사용량을 주기적으로 모니터링하여, 메모리 부족으로 인한 Full GC 발생을 방지하기 위해 메모리 최적화 또는 증설이 필요.

# 임계치
max_frequency: 최대 "Full GC" 발생 빈도

# 판단기준
- **양호**: 출력값이 `max_frequency`를 초과하지 않는 상태
- **경고**: 출력값이 `max_frequency`를 초과한 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
