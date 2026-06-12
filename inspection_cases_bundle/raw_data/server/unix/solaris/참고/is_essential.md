# Ⅱ. 정보시스템 예방점검 항목

## 1. 일상점검

### 1.1 상태점검

#### 1.1.1 서버 점검

| 영역 | 세부 점검항목 | 점검 내용 | 구분 |
|---|---|---|---|
| ① CPU | CPU 사용률 | CPU 사용률 점검 | 필수 |
| ① CPU | 코어별 상태 점검 | 물리적 코어의 정상(Online/Offline) 유무 점검 | 권고 |
| ② MEMORY | 메모리 사용률 | 메모리 사용률 확인 | 필수 |
| ② MEMORY | 메모리 상태 확인 | 할당된 메모리의 정상 인식 여부 확인 | 권고 |
| ② MEMORY | Paging Space | 사용 가능한 가상 메모리 사용률 확인<br>(해당 수치가 높은 경우 메모리의 부족 판단 시 사용) | 필수 |
| ③ DISK | 파일시스템 사용량 | 파일시스템 사용량 점검 | 필수 |
| ③ DISK | Disk Swap 사용률 | 사용 가능한 가상 메모리 크기 확인<br>(하드디스크를 메모리처럼 사용하여 부족한 메모리의 용량을 증대, 가상 메모리가 사용한 크기와 사용 가능한 크기를 확인) | 필수 |
| ③ DISK | Disk 이중화 정상 여부 | Disk 이중화 정상 유무 점검<br>(레이드 구성 및 State의 상태가 Ok/Maintenance) | 권고 |
| ③ DISK | Disk 인식 여부 점검 | Disk 인식 정상 유무 점검<br>(Disk Status : Unknown/Drive not available) | 권고 |
| ③ DISK | Disk I/O 점검 | Disk I/O 점검<br>(Soft Errors, Hard Errors, Transport Errors, Iowait의 지연 확인) | 권고 |
| ③ DISK | I-Node 사용률 | I-Node 사용률 점검 | 권고 |
| ④ 커널 | Kernel Parameter Check | 커널 파라미터 설정값의 기본 설정이 적용되어 있는지를 확인하여 서비스 및 OS 장애를 예방하기 위하여 점검 | 권고 |
| ⑤ 로그 | 로그 점검 | 시스템, 커널, 메모리, I/O 에러 등 각종 로그를 통한 장치 및 인스턴스, 서비스 이상 유무 확인 | 필수 |
| ⑥ Cluster | Cluster 데몬 상태 | Cluster 정상 유무 점검<br>(클러스터의 데몬 Maintenance/Offline 점검) | 권고 |
| ⑥ Cluster | 공유 볼륨 상태 점검 | 공유 볼륨 Read/Write 상태 및 마운트 정상 유무 점검<br>(File System State On, HSM Server Not Responding) | 권고 |
| ⑦ Network | NW 링크 상태 점검 | Network 연결상태 정상 유무 점검<br>(NIC별 STATE Up, Down, Unknown 상태 확인) | 필수 |
| ⑦ Network | NIC 이중화 점검 | NIC 이중화(IPMP) 및 Daemon 상태 점검<br>(STATE Down/Up, ACTIVE No/Yes, GROUPNAME 상태) | 권고 |
| ⑦ Network | Ping Loss | Network 통신 상태 점검<br>(Default Router로 Ping 테스트) | 권고 |
| ⑧ OS | Path 이중화 점검 | Multipath 이중화 정상 유무 점검<br>(CONNECTED 상태 확인) | 권고 |
| ⑧ OS | HBA 연결 상태 점검 | HBA 연결 정상 유무 점검<br>(State Online, Current Speed) | 권고 |

> ※ 클라우드 운영환경 구성에 따라 점검 항목은 조정 가능