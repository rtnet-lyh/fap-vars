# Solaris 점검 항목 정리 (Markdown 변환)

원본: `solaris.pdf`

> PDF의 표/스크린샷 내용을 기준으로 Markdown 형식으로 재구성했습니다.  
> 각 항목은 **점검 항목 / 명령어 / 출력값 / 설명** 4개 필드로 정리했습니다.

---

## ① CPU

### ①-1 CPU 사용률
- **점검 항목**: CPU 사용률 점검
- **명령어**:

```bash
prstat 1
```

- **출력값**:

```text
PID USERNAME SIZE  RSS   STATE PRI NICE TIME      CPU   STIME %MEM %CPU COMMAND
12345 user1  1024M 512M  R     10  0    00:00:01 90.0  11:00 2.0  0.0  myprocess
12346 user2  2048M 1024M S     20  0    00:00:02 0.0   12:00 3.0  0.1  anotherprocess
```

- **설명**:
  - `%CPU`는 개별 프로세스 기준 0~5%, 시스템 전체 기준 70% 이하를 권장.
  - 사용률이 과도하면 해당 프로세스 성능 검토가 필요.
  - `mpstat` 명령어도 보조적으로 사용 가능.

### ①-2 CPU 코어별 상태 점검
- **점검 항목**: 물리적 코어의 정상(online/offline) 유무 점검
- **명령어**:

```bash
psrinfo -v
psrinfo -pv
```

- **출력값**:

```text
Status of virtual processor 0 as of 09/10/2024 12:34:56:
Processor has been on-line since 09/10/2024 12:00:00
Processor is part of the following processor set(s): 0

Status of virtual processor 1 as of 09/10/2024 12:34:56:
Processor has been on-line since 09/10/2024 12:00:00
Processor is part of the following processor set(s): 0

The physical processor has 2 virtual processors (0-1)
x86 (chipid 0x0001) 3000 MHz
Intel(r) Core(tm) i7-9700 CPU
```

- **설명**:
  - 모든 프로세서는 `Processor has been on-line since` 상태여야 함.
  - `off-line`이면 코어 점검 및 복구 필요.
  - `psrinfo -pv`는 물리 CPU 수와 각 CPU의 논리 프로세서 수 확인에 사용.

---

## ② MEMORY

### ②-1 메모리 사용률
- **점검 항목**: 메모리 사용율 점검
- **명령어**:

```bash
vmstat
```

- **출력값**:

```text
kthr      memory            page            disk          faults      cpu
r b   swap  free   re mf pi po fr sr  in  sy  cs us sy id
1 0   1024  2048   0  0  0  0  0  0   10  20  30  5  3 92
```

- **설명**:
  - `free`는 사용 가능한 물리 메모리이며, 총 메모리의 약 20% 이상을 권장.
  - `swap`, `pi`, `po` 증가는 메모리 압박 신호로 볼 수 있음.
  - `us`, `sy`, `id`를 함께 확인해 CPU와 메모리 병목을 같이 판단.

### ②-2 메모리 상태 확인
- **점검 항목**: 할당된 메모리의 정상 인식 여부 확인
- **명령어**:

```bash
prtdiag
```

- **출력값**:

```text
System Configuration: Sun Microsystems sun4u
Memory size: 8192 Megabytes
Memory Module:
DIMM 0: 4096 MB, 64-bit, Error Correcting Code
DIMM 1: 4096 MB, 64-bit, Error Correcting Code
```

- **설명**:
  - `Memory size`로 시스템이 인식한 총 메모리 용량을 확인.
  - 예시 기준 총 8GB가 정상 인식됨.
  - DIMM 단위 정보로 메모리 모듈 상태도 함께 점검 가능.

### ②-3 Paging Space
- **점검 항목**: 사용 가능한 가상 메모리 사용률 확인
- **명령어**:

```bash
swap -l
```

- **출력값**:

```text
swapfile           dev   swaplo   blocks    free
/dev/dsk/c0t0d0s1  118,1 16       1048576   524288
/dev/dsk/c0t0d0s2  118,2 16       2097152   1048576
```

- **설명**:
  - `blocks`는 전체 스왑 용량, `free`는 사용 가능한 스왑 공간.
  - 일반적으로 물리 메모리의 1~2배 이상 스왑 구성을 권고.
  - `free`가 충분하지 않으면 메모리 부족 가능성을 점검해야 함.

---

## ③ DISK

### ③-1 파일시스템 사용량
- **점검 항목**: 파일시스템 사용량 점검
- **명령어**:

```bash
df -h
```

- **출력값**:

```text
Filesystem      Size Used Avail Use% Mounted on
/dev/dsk/s1      50G  25G   23G  53% /
/dev/dsk/s2     100G  60G   35G  66% /var
```

- **설명**:
  - `Use%`가 80% 이상이면 디스크 공간 부족 위험이 큼.
  - `Avail`이 20% 미만이면 정리 또는 증설을 검토.
  - `Mounted on`으로 어느 경로가 영향을 받는지 확인.

### ③-2 Disk Swap 사용률
- **점검 항목**: 사용 가능한 가상 메모리 크기 확인
- **명령어**:

```bash
swap -l
```

- **출력값**:

```text
swapfile           dev   swaplo   blocks    free
/dev/dsk/c0t0d0s1  118,1 16       1048576   524288
/dev/dsk/c0t0d0s2  118,2 16       2097152   1048576
```

- **설명**:
  - 하드디스크를 가상 메모리처럼 사용하는 영역의 전체 크기와 여유 공간을 확인.
  - `blocks`와 `free`를 같이 보며 스왑 압박 여부를 판단.
  - 물리 메모리 대비 스왑 구성이 충분한지 확인 권고.

### ③-3 Disk 이중화 정상 여부
- **점검 항목**: Disk 이중화 정상 유무 점검
- **명령어**:

```bash
metastat
```

- **출력값**:

```text
d0: Mirror
    Submirror 0: d10
      State: Okay
    Submirror 1: d11
      State: Okay
    State: Okay
    Status: The volume is functioning properly.

d10: Submirror of d0
    State: Okay

d11: Submirror of d0
    State: Okay
```

- **설명**:
  - RAID 미러 볼륨 `d0`의 상태는 `Okay`여야 함.
  - `Maintenance` 상태면 디스크 이상 가능성이 있으므로 점검 필요.
  - `Status`는 `The volume is functioning properly.`가 정상.

### ③-4 Disk 인식 여부 점검
- **점검 항목**: Disk 인식 정상 유무 점검
- **명령어**:

```bash
format
```

- **출력값**:

```text
AVAILABLE DISK SELECTIONS:
0. c0t0d0 <ST3200822AS> (16.8GB)
1. c0t1d0 <ST3200822AS> (16.8GB)
2. c0t2d0 <ST3200822AS> (16.8GB)
3. c0t3d0 <ST3200822AS> (16.8GB)
Specify disk (enter its number):
```

- **설명**:
  - 모든 디스크가 `AVAILABLE DISK SELECTIONS`에 정상 표시되어야 함.
  - `Unknown` 또는 `Drive not available`이면 장치 점검 필요.

### ③-5 Disk I/O 점검
- **점검 항목**: Disk I/O 점검
- **명령어**:

```bash
iostat -x
```

- **출력값**:

```text
extended device statistics
device   r/s   w/s   kr/s   kw/s   wait actv svc_t  %w  %b
sd0     15.0  10.0  150.0  100.0   0.0  1.0  10.5   5  50
sd1      5.0   3.0   50.0   30.0   0.0  0.5   8.0   0  25
sd2      0.5   0.2    5.0    2.0   0.0  0.1   7.0   0  10
```

- **설명**:
  - `svc_t`가 20ms 이상이면 성능 문제 가능성이 큼.
  - `%b`가 80% 이상이면 디스크가 과도하게 사용 중인 상태.
  - `wait`, `actv`, `r/s`, `w/s`를 함께 보고 병목 여부를 판단.

### ③-6 I-Node 사용률
- **점검 항목**: I-Node 사용률 점검
- **명령어**:

```bash
df -o i
```

- **출력값**:

```text
Filesystem          iused  ifree %iused Mounted on
/dev/dsk/c0t0d0s0   10234  89765   10%  /
/dev/dsk/c0t0d0s1    5678  12345   30%  /var
```

- **설명**:
  - `%iused`가 80%를 초과하면 파일시스템 확장 검토.
  - `ifree`가 전체의 20% 미만이면 파일 정리 또는 확장 필요.

---

## ④ 커널

### ④-1 Kernel Parameter Check
- **점검 항목**: 커널 파라미터 기본 설정 적용 여부 점검
- **명령어**:

```bash
sysdef
```

- **출력값**:

```text
*Tunable Parameters*
shmmax: 4294967295
shminfo_shmmin: 1
seminfo_semmsl: 256
seminfo_semmns: 32000
seminfo_semopm: 32

*File System Parameters*
maxfiles: 8192
maxuproc: 512

*Memory Management Parameters*
maxpgio: 8192
minfree: 200
desfree: 400
lotsfree: 1024

*IPC Parameters*
msginfo_msgmax: 8192
msginfo_msgmnb: 16384
msginfo_msgtql: 40
msginfo_msgseg: 2048
```

- **설명**:
  - 시스템 운영자가 커널 파라미터를 조정할 때 기준값 확인용으로 사용.
  - 예시에서는 공유 메모리 최대 크기 `shmmax=4294967295`를 확인.
  - File System, Memory, IPC 관련 파라미터를 함께 점검 가능.

---

## ⑤ 로그

### ⑤-1 시스템 로그
- **점검 항목**: 장치/인스턴스의 오류·경고 여부 점검
- **명령어**:

```bash
dmesg | grep -i 'error|fail|warning'
```

- **출력값**:

```text
Error: Device sda1 failure detected
Warning: Disk space low on /dev/sdb
Fail: Network interface eth0 down
```

- **설명**:
  - 장치 오류, 디스크 공간 부족, 네트워크 인터페이스 다운 여부를 확인.
  - 에러 메시지가 보이면 해당 장치 또는 인터페이스 점검 및 복구 필요.

### ⑤-2 커널 로그
- **점검 항목**: 하드웨어 이상에 따른 커널 패닉 로그 점검
- **명령어**:

```bash
dmesg | grep -i 'panic|kernel panic'
```

- **출력값**:

```text
Kernel panic: CPU context corrupt
Panic: Attempted to access invalid memory address
```

- **설명**:
  - 커널 패닉 발생 이력을 확인하는 항목.
  - CPU 컨텍스트 손상, 잘못된 메모리 접근 등은 즉시 하드웨어 점검 필요.

### ⑤-3 CPU 로그
- **점검 항목**: CPU 에러 로그 점검
- **명령어**:

```bash
dmesg | grep -i 'ecc error|uncorrectable|offline'
```

- **출력값**:

```text
ECC error detected on CPU0
Uncorrectable ECC error on CPU1
CPU2 offline due to hardware failure
```

- **설명**:
  - ECC 오류, 정정 불가 오류, CPU 오프라인 상태를 확인.
  - 해당 메시지가 있으면 CPU 모듈 점검 또는 교체 필요.

### ⑤-4 MEMORY 로그
- **점검 항목**: 메모리 오류 에러 로그 점검
- **명령어**:

```bash
dmesg | grep -i 'ecc error|singlebit|multibit|uncorrectable'
```

- **출력값**:

```text
Single-bit ECC error detected on memory module 0
Multi-bit ECC error reported on memory bank 1
Uncorrectable ECC error found on memory slot 2
```

- **설명**:
  - 단일비트/멀티비트 ECC 오류 및 정정 불가 오류를 확인.
  - 메모리 모듈, 뱅크, 슬롯 단위로 점검 및 교체 판단 가능.

### ⑤-5 FAN 로그
- **점검 항목**: FAN 작동 이상 유무 점검
- **명령어**:

```bash
dmesg | grep -i 'fan|fail'
```

- **출력값**:

```text
FAN1 failed: Over-temperature detected
Warning: FAN2 not spinning
FAN3 operational
```

- **설명**:
  - 팬 과열 실패, 회전 불가, 정상 작동 여부를 확인.
  - `failed`, `not spinning` 메시지는 즉시 점검 필요.

### ⑤-6 POWER 로그
- **점검 항목**: 전원공급장치 오류 및 이상 유무 점검
- **명령어**:

```bash
dmesg | grep -i 'psu|power supply|failed'
```

- **출력값**:

```text
PSU1 failed: Power supply unit error
Warning: Power supply unit PS2 not detected
Power supply unit PS3 operational
```

- **설명**:
  - PSU 실패, 미감지, 정상 작동 상태를 확인.
  - 전원공급장치 관련 에러가 있으면 교체 또는 연결 점검 필요.

### ⑤-7 HBA 로그
- **점검 항목**: HBA 작동 이상 유무 점검
- **명령어**:

```bash
dmesg | grep -i 'hba|loop|port|offline|online'
```

- **출력값**:

```text
HBA1: Loop detected on port 0
Port 1 offline due to error
HBA2: Port 2 online
```

- **설명**:
  - HBA 루프 감지, 포트 offline/online 상태를 점검.
  - offline 또는 loop 메시지는 포트 및 HBA 장치 점검 필요.

### ⑤-8 NIC 로그
- **점검 항목**: NIC 정상 유무 점검
- **명령어**:

```bash
dmesg | grep -i 'nic|link|failover|status|down'
```

- **출력값**:

```text
NIC0: Link Down
NIC1: IPMP failover occurred on interface
NIC2: Status Up
NIC3: Link Down
```

- **설명**:
  - NIC 링크 다운, IPMP failover, 상태 정상 여부를 확인.
  - `Link Down` 또는 failover 빈발 시 케이블/포트/NIC 점검 권고.

### ⑤-9 I/O 에러 로그
- **점검 항목**: 입출력 작동 이상 유무 점검
- **명령어**:

```bash
dmesg | grep -i 'timeout|i/o error|transport failed|media error'
```

- **출력값**:

```text
I/O Error: Device /dev/sda1 reported error
Timeout occurred while waiting for device
Transport failed for SCSI device /dev/sdb
Media error detected on /dev/sdc
```

- **설명**:
  - I/O 오류, 타임아웃, 전송 실패, 미디어 에러를 확인.
  - 스토리지 장치 상태와 연결 경로를 함께 점검해야 함.

### ⑤-10 클러스터 로그
- **점검 항목**: 서버 클러스터 노드 상태변경 발생 점검
- **명령어**:

```bash
clog | grep -i 'status change|offline|online|cluster error'
```

- **출력값**:

```text
[2024-09-16T10:00:00] Resource Status Change: Node1 Offline
[2024-09-16T10:05:00] Cluster Error: Node2 communication failure
[2024-09-16T10:10:00] Resource Status Change: Node3 Online
```

- **설명**:
  - 노드 online/offline 변경 및 클러스터 통신 오류를 확인.
  - 노드 오프라인이나 통신 실패 메시지가 있으면 클러스터 상태 점검 필요.

---

## ⑥ 클러스터

### ⑥-1 Cluster 데몬 상태
- **점검 항목**: Cluster 정상 유무 점검
- **명령어**:

```bash
scstat
```

- **출력값**:

```text
=== Cluster Nodes ===
node1  Online
node2  Online

=== Cluster Transport Paths ===
node1 -> node2  Path online
node2 -> node1  Path online

=== Resource Groups ===
resource_grp1  node1  Online
resource_grp2  node2  Online

=== Network Interfaces ===
net0  node1  Online
net1  node2  Online
```

- **설명**:
  - Cluster Nodes, Transport Paths, Resource Groups, Network Interfaces 상태를 확인.
  - `Offline`, `Maintenance`, `Path down` 상태면 즉시 점검 필요.

### ⑥-2 공유 볼륨 상태 점검
- **점검 항목**: 공유 볼륨 Read/Write 상태 및 마운트 정상 유무 점검
- **명령어**:

```bash
mount | grep <mount_point>
```

- **출력값**:

```text
/dev/dsk/c0t0d0s0 on / type ufs (rw, logging)
/dev/dsk/shared_vol on /mnt/shared type ufs (rw, logging)
```

- **설명**:
  - `rw`면 읽기/쓰기 가능 상태, `ro`면 읽기 전용 상태.
  - 공유 볼륨이 정상 마운트되었는지와 파일시스템 유형을 함께 확인.

---

## ⑦ 네트워크

### ⑦-1 NW 링크 상태 연결속도 설정
- **점검 항목**: Network 연결상태 정상 유무 점검
- **명령어**:

```bash
dladm show-phys
```

- **출력값**:

```text
LINK     MEDIA      STATE    SPEED   DUPLEX
e1000g0  1000baseT  up       1000    full
e1000g1  1000baseT  down     1000    full
e1000g2  1000baseT  unknown  1000    full
```

- **설명**:
  - `STATE`는 `up`이어야 정상.
  - `down` 또는 `unknown`이면 인터페이스, 케이블, 설정 점검 필요.
  - `SPEED`, `DUPLEX`가 설정값과 일치하는지 확인.

### ⑦-2 NIC 이중화 점검
- **점검 항목**: NIC 이중화(IPMP) 및 Daemon 상태 점검
- **명령어**:

```bash
ipmpstat -i
```

- **출력값**:

```text
INTERFACE ACTIVE GROUP FLAGS  LINK STATE
net0      yes    ipmp0 ------ up   ok
net1      yes    ipmp0 ------ up   ok
```

- **설명**:
  - 같은 IPMP 그룹 내 2개 인터페이스가 `ACTIVE: yes`, `LINK: up`, `STATE: ok`여야 정상.
  - 이 값이 다르면 NIC, 케이블, 그룹 설정 점검 필요.

### ⑦-3 Ping Loss
- **점검 항목**: Network 통신 상태 점검
- **명령어**:

```bash
ping 8.8.8.8
```

- **출력값**:

```text
PING 8.8.8.8: 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=0 ttl=118 time=15.4 ms
64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=14.6 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=15.2 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=118 time=15.3 ms
--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss
round-trip (ms) min/avg/max = 14.6/15.1/15.4
```

- **설명**:
  - 평균 응답시간이 15.1ms 수준으로 양호한 예시.
  - 패킷 손실률 0%이면 네트워크가 안정적이라고 판단 가능.
  - RTT 최소/평균/최대값을 함께 확인.

---

## ⑧ OS

### ⑧-1 Path 이중화 점검
- **점검 항목**: Multipath 이중화 정상 유무 점검
- **명령어**:

```bash
mpathadm show lu
```

- **출력값**:

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

- **설명**:
  - `Stms State`는 `ENABLED`여야 함.
  - `Path Status`는 `CONNECTED`가 정상.
  - `DISABLED` 경로가 있으면 멀티패스 경로 점검 필요.

### ⑧-2 HBA 연결 상태 점검
- **점검 항목**: HBA 연결 정상 유무 점검
- **명령어**:

```bash
fcinfo hba-port
```

- **출력값**:

```text
# fcinfo hba-port
HBA Port WWN: 10000000c9612345
OS Device Name: /dev/cfg/c2
Manufacturer: Emulex
Model: LPe12062
Firmware Version: 2.02a16
FCode/BIOS Version: 3.33a4
Serial Number: MY12345
Driver Name: lpfc
Driver Version: 9.2.0
State: online
Supported Speeds: 2Gb 4Gb 8Gb
Current Speed: 8Gb
Node WWN: 20000000c9612345
```

- **설명**:
  - `State`는 `online`이어야 정상.
  - `Current Speed`는 예시 기준 `8Gb`.
  - 속도 저하나 `offline` 상태면 포트 연결/설정 점검 필요.

---

## 비고
- 일부 **출력값**은 PDF 내부 스크린샷을 기준으로 텍스트화하면서 가독성을 위해 정리한 예시입니다.
- 설명 문구는 원본 PDF의 의미를 유지하도록 Markdown 형식에 맞게 재구성했습니다.
