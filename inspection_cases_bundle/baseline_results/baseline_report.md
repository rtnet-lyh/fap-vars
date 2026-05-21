# Live Runtime Comparison Report

- 기준 일시: 2026-05-21 17:34:30
- 실행 모드: `replay_cli.py --mode live`
- 실행 대상: `inspection_cases` 아래 단일 케이스 177개
- 케이스별 제한 시간: 90초
- 비교 기준: CLI return code, timeout 여부, result status/error/message/metrics/thresholds/reasons/stdout/stderr/raw_output
- 전체 비교 실행은 원본 `inspection_cases/*/result.json`을 덮어쓰지 않도록 `/tmp/fap_live_compare_work` 복사본에서 수행

## Runtime Files

- `inspection_runtime`
  - `inspection_runtime/runner.py`: `2983f7f92ac27bb5`
  - `inspection_runtime/items/common/_base.py`: `be097d02d5e7661a`
- `inspection_runtimebak`
  - `inspection_runtimebak/runner.py`: `50ea42ee43c2bda7`
  - `inspection_runtimebak/items/common/_base.py`: `aad32ad8d6869e24`

## Summary

- 전체 case 수: 177
- 동일 결과 case 수: 151
- 차이 발생 case 수: 26
- `inspection_runtime` 상태 분포: fail: 94, ok: 72, warn: 11
- `inspection_runtimebak` 상태 분포: fail: 94, ok: 72, warn: 11
- status가 서로 달라진 case는 없으며, 차이 26건은 live 시점에 변동되는 metrics/message/raw_output 값 차이입니다.

## Changed Cases

### `server/esxi/esxi_status_basic_check`

- host: `192.168.1.85` / port: `443`
- inspection_code: `ESXI-STATUS-API-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=0.215s` / `inspection_runtimebak=0.214s`
- message: `inspection_runtime=ESXi 상태 확인이 정상입니다. 현재 상태: host=localhost.rtnet, CPU 7.81% (기준 80.00% 이하), 메모리 90.93% (기준 95.00% 이하), 전원 상태 poweredOn (기준 poweredOn), 연결 상태 connected (기준 connected). CPU/메모리 사용률과 전원/연결 상태가 모두 기준을 충족했습니다.` / `inspection_runtimebak=ESXi 상태 확인이 정상입니다. 현재 상태: host=localhost.rtnet, CPU 7.46% (기준 80.00% 이하), 메모리 91.03% (기준 95.00% 이하), 전원 상태 poweredOn (기준 poweredOn), 연결 상태 connected (기준 connected). CPU/메모리 사용률과 전원/연결 상태가 모두 기준을 충족했습니다.`
- metrics: `inspection_runtime={'name': 'localhost.rtnet', 'full_name': 'VMware ESXi 8.0.3 build-24022510', 'version': '8.0.3', 'build': '24022510', 'api_version': '8.0.3.0', 'uuid': '63ca02ce-3610-11e6-bf03-749d8f88c836', 'vendor': 'Huawei', 'mode...` / `inspection_runtimebak={'name': 'localhost.rtnet', 'full_name': 'VMware ESXi 8.0.3 build-24022510', 'version': '8.0.3', 'build': '24022510', 'api_version': '8.0.3.0', 'uuid': '63ca02ce-3610-11e6-bf03-749d8f88c836', 'vendor': 'Huawei', 'mode...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: (명령 이력 없음) - 명령 종료코드: rc=unknown (명령 이력 없음) - 출력 내용: ESXi HostSystem.summary API 조회 결과 - source: pyvmomi - name: localhost.rtnet - full_name: VMware ESXi 8.0.3 build-24022510 - api_version: 8.0.3.0...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: (명령 이력 없음) - 명령 종료코드: rc=unknown (명령 이력 없음) - 출력 내용: ESXi HostSystem.summary API 조회 결과 - source: pyvmomi - name: localhost.rtnet - full_name: VMware ESXi 8.0.3 build-24022510 - api_version: 8.0.3.0...`

### `server/rocky/rocky_cpu_usage_procstat_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-CPU-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.867s` / `inspection_runtimebak=1.847s`
- message: `inspection_runtime=CPU 사용률 점검이 정상 수행되었습니다. 임계치 정보: max_cpu_usage_percent=90.0%. 판단근거: 측정 CPU 사용률 0.5%가 임계치 90.0% 이하입니다.` / `inspection_runtimebak=CPU 사용률 점검이 정상 수행되었습니다. 임계치 정보: max_cpu_usage_percent=90.0%. 판단근거: 측정 CPU 사용률 0.29%가 임계치 90.0% 이하입니다.`
- metrics: `inspection_runtime={'cpu_usage_percent': 0.5}` / `inspection_runtimebak={'cpu_usage_percent': 0.29}`
- reasons: `inspection_runtime=측정 CPU 사용률 0.5%가 임계치 90.0% 이하입니다.` / `inspection_runtimebak=측정 CPU 사용률 0.29%가 임계치 90.0% 이하입니다.`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: bash -lc 'read cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; total1=$((user + nice + system + idle + iowait + irq + softirq + steal)); idle1=$((idle + iowait)); ...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: bash -lc 'read cpu user nice system idle iowait irq softirq steal guest guest_nice < /proc/stat; total1=$((user + nice + system + idle + iowait + irq + softirq + steal)); idle1=$((idle + iowait)); ...`

### `server/rocky/rocky_disk_filesystem_inode_df_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-INODE-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=0.811s` / `inspection_runtimebak=0.787s`
- metrics: `inspection_runtime={'filesystem_count': 7, 'max_inode_usage_percent': 2, 'max_inode_usage_filesystem': '/dev/mapper/rl-root', 'max_inode_usage_mount_point': '/', 'checked_filesystems': [{'filesystem': 'devtmpfs', 'inode_used_raw': '1957...` / `inspection_runtimebak={'filesystem_count': 7, 'max_inode_usage_percent': 2, 'max_inode_usage_filesystem': '/dev/mapper/rl-root', 'max_inode_usage_mount_point': '/', 'checked_filesystems': [{'filesystem': 'devtmpfs', 'inode_used_raw': '1957...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: df -i - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): Filesystem Inodes IUsed IFree IUse% Mounted on devtmpfs 1957832 531 1957301 1% /dev tmpfs 1965866 3 1965863 1% /dev/shm tmpfs 819200 1297 817903 1% /r...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: df -i - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): Filesystem Inodes IUsed IFree IUse% Mounted on devtmpfs 1957832 531 1957301 1% /dev tmpfs 1965866 3 1965863 1% /dev/shm tmpfs 819200 1299 817901 1% /r...`

### `server/rocky/rocky_disk_filesystem_usage_df_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-DF-EX-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=0.81s` / `inspection_runtimebak=0.798s`
- metrics: `inspection_runtime={'filesystem_count': 6, 'max_usage_percent': 39, 'max_usage_filesystem': '/dev/sda1', 'max_usage_mount_point': '/boot', 'excluded_targets': ['/'], 'excluded_filesystems': [{'filesystem': '/dev/mapper/rl-root', 'size_1...` / `inspection_runtimebak={'filesystem_count': 6, 'max_usage_percent': 39, 'max_usage_filesystem': '/dev/sda1', 'max_usage_mount_point': '/boot', 'excluded_targets': ['/'], 'excluded_filesystems': [{'filesystem': '/dev/mapper/rl-root', 'size_1...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: df - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): Filesystem 1K-blocks Used Available Use% Mounted on devtmpfs 7831328 0 7831328 0% /dev tmpfs 7863464 8 7863456 1% /dev/shm tmpfs 3145388 318936 2826452 1...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: df - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): Filesystem 1K-blocks Used Available Use% Mounted on devtmpfs 7831328 0 7831328 0% /dev tmpfs 7863464 8 7863456 1% /dev/shm tmpfs 3145388 327132 2818256 1...`

### `server/rocky/rocky_disk_io_diskstats_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-DISK-IO-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.83s` / `inspection_runtimebak=1.839s`
- message: `inspection_runtime=디스크 I/O 상태 점검이 정상 수행되었습니다. max_rw_delta=2(dm-2), max_io_ms_delta=2(dm-2)` / `inspection_runtimebak=디스크 I/O 상태 점검이 정상 수행되었습니다. max_rw_delta=0(dm-0), max_io_ms_delta=0(dm-0)`
- metrics: `inspection_runtime={'snapshot_line_count': 19, 'device_count': 9, 'max_read_write_delta': 2, 'max_read_write_target': 'dm-2', 'max_io_time_delta_ms': 2, 'max_io_time_target': 'dm-2', 'device_deltas': [{'device_name': 'dm-2', 'read_reque...` / `inspection_runtimebak={'snapshot_line_count': 19, 'device_count': 9, 'max_read_write_delta': 0, 'max_read_write_target': 'dm-0', 'max_io_time_delta_ms': 0, 'max_io_time_target': 'dm-0', 'device_deltas': [{'device_name': 'dm-0', 'read_reque...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: bash -lc 'cat /proc/diskstats; printf "__DISKSTATS_SPLIT__\n"; sleep 1; cat /proc/diskstats' - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): 8 16 sdb 1426035 1341 181341390 2821992 18022523 4185492 150170...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: bash -lc 'cat /proc/diskstats; printf "__DISKSTATS_SPLIT__\n"; sleep 1; cat /proc/diskstats' - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): 8 16 sdb 1426035 1341 181341390 2821992 18037186 4185492 150238...`

### `server/rocky/rocky_kernel_parameter_sysctl_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-SYSCTL-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.056s` / `inspection_runtimebak=0.999s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: bash -lc 'printf '"'"'%s\n'"'"' '"'"'*****'"'"' | su - root -c '"'"'bash -lc '"'"'"'"'"'"'"'"'current_user=$(whoami); echo __BECOME_USER__:${current_user}; sysctl -a'"'"'"'"'"'"'"'"''"'"'' - 명령 종료코...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: bash -lc 'printf '"'"'%s\n'"'"' '"'"'*****'"'"' | su - root -c '"'"'bash -lc '"'"'"'"'"'"'"'"'current_user=$(whoami); echo __BECOME_USER__:${current_user}; sysctl -a'"'"'"'"'"'"'"'"''"'"'' - 명령 종료코...`

### `server/rocky/rocky_memory_usage_free_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-FREE-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=0.81s` / `inspection_runtimebak=0.809s`
- message: `inspection_runtime=free 기준 메모리 사용률 점검이 정상 수행되었습니다. 임계치 정보: min_available_memory_percent=10.0%, max_swap_usage_percent=50.0%. 판단근거: available_memory_percent=66.27%, swap_usage_percent=3.28%, mem_available_kib=10422656, swap_used_kib=264252.` / `inspection_runtimebak=free 기준 메모리 사용률 점검이 정상 수행되었습니다. 임계치 정보: min_available_memory_percent=10.0%, max_swap_usage_percent=50.0%. 판단근거: available_memory_percent=65.6%, swap_usage_percent=3.28%, mem_available_kib=10317024, swap_used_kib=264252.`
- metrics: `inspection_runtime={'mem_total_kib': 15726928, 'mem_used_kib': 5304272, 'mem_free_kib': 4060060, 'mem_shared_kib': 174828, 'mem_buff_cache_kib': 6959792, 'mem_available_kib': 10422656, 'available_memory_percent': 66.27, 'swap_total_kib'...` / `inspection_runtimebak={'mem_total_kib': 15726928, 'mem_used_kib': 5409904, 'mem_free_kib': 3953932, 'mem_shared_kib': 183032, 'mem_buff_cache_kib': 6968496, 'mem_available_kib': 10317024, 'available_memory_percent': 65.6, 'swap_total_kib':...`
- reasons: `inspection_runtime=available_memory_percent=66.27%가 최소 기준 10.0% 이상이고 swap_usage_percent=3.28%가 최대 기준 50.0% 이하입니다.` / `inspection_runtimebak=available_memory_percent=65.6%가 최소 기준 10.0% 이상이고 swap_usage_percent=3.28%가 최대 기준 50.0% 이하입니다.`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: free - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): total used free shared buff/cache available Mem: 15726928 5304272 4060060 174828 6959792 10422656 Swap: 8060924 264252 7796672 - 출력 내용(stderr): Warning...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: free - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): total used free shared buff/cache available Mem: 15726928 5409904 3953932 183032 6968496 10317024 Swap: 8060924 264252 7796672 - 출력 내용(stderr): Warning...`

### `server/rocky/rocky_network_ping_loss_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-PING-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=9.742s` / `inspection_runtimebak=9.737s`
- metrics: `inspection_runtime={'command': 'ping -c 10 192.168.1.1', 'target': '192.168.1.1', 'sent_count': 10, 'received_count': 10, 'loss_percent': 0.0, 'response_received': True, 'reply_count': 10, 'reply_sources': ['192.168.1.1', '192.168.1.1',...` / `inspection_runtimebak={'command': 'ping -c 10 192.168.1.1', 'target': '192.168.1.1', 'sent_count': 10, 'received_count': 10, 'loss_percent': 0.0, 'response_received': True, 'reply_count': 10, 'reply_sources': ['192.168.1.1', '192.168.1.1',...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: ip route - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): default via 192.168.1.1 dev eno1 proto static metric 100 10.100.100.0/24 dev docker0 proto kernel scope link src 10.100.100.1 linkdown 10.254.10.0/...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: ip route - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): default via 192.168.1.1 dev eno1 proto static metric 100 10.100.100.0/24 dev docker0 proto kernel scope link src 10.100.100.1 linkdown 10.254.10.0/...`

### `server/rocky/rocky_os_path_redundancy_multipath_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `U-REPLAY-MULTIPATH-01`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=1.0s` / `inspection_runtimebak=0.987s`
- stderr: `inspection_runtime=Warning: Permanently added '192.168.1.123' (ED25519) to the list of known hosts. ** WARNING: connection is not using a post-quantum key exchange algorithm. ** This session may be vulnerable to "store now, decrypt late...` / `inspection_runtimebak=Warning: Permanently added '192.168.1.123' (ED25519) to the list of known hosts. ** WARNING: connection is not using a post-quantum key exchange algorithm. ** This session may be vulnerable to "store now, decrypt late...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: bash -lc 'printf '"'"'%s\n'"'"' '"'"'*****'"'"' | su - root -c '"'"'bash -lc '"'"'"'"'"'"'"'"'current_user=$(whoami); echo __BECOME_USER__:${current_user}; exec multipath -ll'"'"'"'"'"'"'"'"''"'"''...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: bash -lc 'printf '"'"'%s\n'"'"' '"'"'*****'"'"' | su - root -c '"'"'bash -lc '"'"'"'"'"'"'"'"'current_user=$(whoami); echo __BECOME_USER__:${current_user}; exec multipath -ll'"'"'"'"'"'"'"'"''"'"''...`

### `server/solaris/solaris_cpu_usage_prstat_check`

- host: `192.168.1.163` / port: `22`
- inspection_code: `SOL-REPLAY-CPU-01`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=23.086s` / `inspection_runtimebak=23.074s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...`

### `server/solaris/solaris_memory_usage_vmstat_check`

- host: `192.168.1.163` / port: `22`
- inspection_code: `SOL-REPLAY-MEM-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=8.005s` / `inspection_runtimebak=7.973s`
- message: `inspection_runtime=Solaris 메모리 사용률이 정상입니다. 현재 상태: free 1479524KB (기준 1024KB 이상), swap 1760656KB, pi 0회 (기준 0회 이하), po 0회 (기준 0회 이하), run queue 0, blocked 0, User 0.00%, System 1.00%, User+System 1.00%, Idle 99.00%.` / `inspection_runtimebak=Solaris 메모리 사용률이 정상입니다. 현재 상태: free 1479520KB (기준 1024KB 이상), swap 1760648KB, pi 0회 (기준 0회 이하), po 0회 (기준 0회 이하), run queue 0, blocked 0, User 0.00%, System 1.00%, User+System 1.00%, Idle 99.00%.`
- metrics: `inspection_runtime={'swap_kb': 1760656, 'free_kb': 1479524, 'page_in_count': 0, 'page_out_count': 0, 'user_percent': 0.0, 'system_percent': 1.0, 'cpu_busy_percent': 1.0, 'idle_percent': 99.0, 'run_queue_count': 0, 'blocked_queue_count':...` / `inspection_runtimebak={'swap_kb': 1760648, 'free_kb': 1479520, 'page_in_count': 0, 'page_out_count': 0, 'user_percent': 0.0, 'system_percent': 1.0, 'cpu_busy_percent': 1.0, 'idle_percent': 99.0, 'run_queue_count': 0, 'blocked_queue_count':...`
- reasons: `inspection_runtime=가용 메모리 1479524KB가 기준 이상이고 page in/out 수치도 기준 이내이며 CPU/메모리 병목 징후가 크지 않습니다.` / `inspection_runtimebak=가용 메모리 1479520KB가 기준 이상이고 page in/out 수치도 기준 이내이며 CPU/메모리 병목 징후가 크지 않습니다.`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...`

### `server/solaris/solaris_network_ping_loss_ping_check`

- host: `192.168.1.163` / port: `22`
- inspection_code: `SOL-REPLAY-NET-03`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=11.038s` / `inspection_runtimebak=11.018s`
- stdout: `inspection_runtime=PING 8.8.8.8: 56 data bytes 64 bytes from dns.google (8.8.8.8): icmp_seq=0. time=32.5 ms 64 bytes from dns.google (8.8.8.8): icmp_seq=1. time=32.6 ms 64 bytes from dns.google (8.8.8.8): icmp_seq=2. time=32.4 ms 64 byt...` / `inspection_runtimebak=PING 8.8.8.8: 56 data bytes 64 bytes from dns.google (8.8.8.8): icmp_seq=0. time=32.8 ms 64 bytes from dns.google (8.8.8.8): icmp_seq=1. time=32.5 ms 64 bytes from dns.google (8.8.8.8): icmp_seq=2. time=31.9 ms 64 byt...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: su - root - 명령 종료코드: rc=124 (명령 시간 초과) - 출력 내용(stdout): Password: - 출력 내용(stderr): PARAMIKO_COMMAND_TIMEOUT: prompt was not received [점검 단계 2] - 실행 명령어: ******* - 명령 종료코드: rc=0 (정상 종료) - 출력 내용: Ora...`

### `server/windows/windows_cpu_usage_counter_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-CPU-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=4.261s` / `inspection_runtimebak=4.083s`
- message: `inspection_runtime=Windows CPU 사용률 점검이 정상입니다. 현재 상태: host=WIN-62M5CCFUE2J, User 0.00%, Privileged 0.00%, User+System 0.00% (기준 80.00% 이하), Idle 99.36% (기준 20.00% 이상), Interrupt 0.00% (기준 5.00% 이하).` / `inspection_runtimebak=Windows CPU 사용률 점검이 정상입니다. 현재 상태: host=WIN-62M5CCFUE2J, User 0.26%, Privileged 0.00%, User+System 0.26% (기준 80.00% 이하), Idle 99.09% (기준 20.00% 이상), Interrupt 0.00% (기준 5.00% 이하).`
- metrics: `inspection_runtime={'sample_count': 3, 'host_name': 'WIN-62M5CCFUE2J', 'avg_user_percent': 0.0, 'avg_privileged_percent': 0.0, 'avg_usr_sys_percent': 0.0, 'avg_idle_percent': 99.36, 'avg_interrupt_percent': 0.0, 'max_usr_sys_percent': 0...` / `inspection_runtimebak={'sample_count': 3, 'host_name': 'WIN-62M5CCFUE2J', 'avg_user_percent': 0.26, 'avg_privileged_percent': 0.0, 'avg_usr_sys_percent': 0.26, 'avg_idle_percent': 99.09, 'avg_interrupt_percent': 0.0, 'max_usr_sys_percent':...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); typeperf "\Processor(_Total)\% User Time" "\Processor(_Total)\% Privi...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); typeperf "\Processor(_Total)\% User Time" "\Processor(_Total)\% Privi...`

### `server/windows/windows_disk_ swap_usage_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-SWAP-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.59s` / `inspection_runtimebak=2.134s`
- message: `inspection_runtime=Windows 스왑 메모리 사용률 점검이 정상입니다. 현재 상태: 파일=C:\pagefile.sys, 총 1.12GiB, 사용 0.29GiB, 여유 0.83GiB, 사용률 26.22% (기준 50.00% 미만), 피크 0.60GiB.` / `inspection_runtimebak=Windows 스왑 메모리 사용률 점검이 정상입니다. 현재 상태: 파일=C:\pagefile.sys, 총 1.12GiB, 사용 0.32GiB, 여유 0.81GiB, 사용률 28.30% (기준 50.00% 미만), 피크 0.60GiB.`
- metrics: `inspection_runtime={'filename': 'C:\\pagefile.sys', 'swap_type': 'file', 'swap_size_mb': 1152.0, 'swap_used_mb': 302.0, 'swap_free_mb': 850.0, 'swap_usage_percent': 26.22, 'peak_usage_mb': 610.0, 'swap_size_gib': 1.12, 'swap_used_gib': ...` / `inspection_runtimebak={'filename': 'C:\\pagefile.sys', 'swap_type': 'file', 'swap_size_mb': 1152.0, 'swap_used_mb': 326.0, 'swap_free_mb': 826.0, 'swap_usage_percent': 28.3, 'peak_usage_mb': 610.0, 'swap_size_gib': 1.12, 'swap_used_gib': 0...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PageFileUsage | Select-Object @{N='Filename';E=...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PageFileUsage | Select-Object @{N='Filename';E=...`

### `server/windows/windows_disk_filesystem_usage_cim_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-DISK-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=2.706s` / `inspection_runtimebak=1.1s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and...`

### `server/windows/windows_disk_io_counter_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-DISK-IO-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=6.682s` / `inspection_runtimebak=1.612s`
- metrics: `inspection_runtime={'device_count': 1, 'busiest_device': '0 C:', 'max_busy_percent': 0.0, 'slowest_device': '0 C:', 'max_wait_ms': 0.0, 'longest_queue_device': '0 C:', 'max_queue_length': 0.0, 'max_read_kb_per_sec': 0.0, 'max_write_kb_p...` / `inspection_runtimebak={'device_count': 1, 'busiest_device': '0 C:', 'max_busy_percent': 0.0, 'slowest_device': '0 C:', 'max_wait_ms': 0.0, 'longest_queue_device': '0 C:', 'max_queue_length': 0.0, 'max_read_kb_per_sec': 0.0, 'max_write_kb_p...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Where...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Where...`

### `server/windows/windows_disk_recognition_cim_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-DISK-MOUNT-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=6.248s` / `inspection_runtimebak=5.852s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $d=Get-Disk -ErrorAction SilentlyContinue; @(@($d|ForEach-Object{[psc...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $d=Get-Disk -ErrorAction SilentlyContinue; @(@($d|ForEach-Object{[psc...`

### `server/windows/windows_kernel_parameter_nettcp_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-KERNEL-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=3.467s` / `inspection_runtimebak=1.79s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $os=Get-CimInstance Win32_OperatingSystem; $tcp=Get-ItemProperty 'HKL...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $os=Get-CimInstance Win32_OperatingSystem; $tcp=Get-ItemProperty 'HKL...`

### `server/windows/windows_log_hba_manual_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-HBA-LOG-01`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=4.648s` / `inspection_runtimebak=4.047s`
- stderr: `inspection_runtime=#< CLIXML <Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N...` / `inspection_runtimebak=#< CLIXML <Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $ip=Get-InitiatorPort -ErrorAction SilentlyContinue; $fc=Get-CimInsta...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $ip=Get-InitiatorPort -ErrorAction SilentlyContinue; $fc=Get-CimInsta...`

### `server/windows/windows_log_io_event_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-IO-LOG-01`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=7.667s` / `inspection_runtimebak=7.784s`
- stdout: `inspection_runtime=[ { "TimeCreated": "\/Date(1779351167820)\/", "ProviderName": "Microsoft-Windows-DNS-Client", "Id": 1014, "LevelDisplayName": "Warning", "Message": "Name resolution for the name wpad timed out after none of the config...` / `inspection_runtimebak=[ { "TimeCreated": "\/Date(1779351774882)\/", "ProviderName": "Microsoft-Windows-DNS-Client", "Id": 1014, "LevelDisplayName": "Warning", "Message": "Name resolution for the name wpad timed out after none of the config...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Da...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Da...`

### `server/windows/windows_log_nic_event_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-NIC-LOG-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=6.515s` / `inspection_runtimebak=4.196s`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $nic=Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | Se...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $nic=Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | Se...`

### `server/windows/windows_log_system_event_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-LOG-01`
- status: `inspection_runtime=fail` / `inspection_runtimebak=fail`
- duration: `inspection_runtime=2.447s` / `inspection_runtimebak=1.77s`
- message: `inspection_runtime=Windows 시스템 로그 점검에 실패했습니다. 현재 상태: Critical/Error 1건 (기준 0건 이하), Warning 3건.Warning 키워드 3건.: The Collect procedure for service "Spooler" in DLL "C:\Windows\System32\winspool.drv" failed with error code The RPC server i...` / `inspection_runtimebak=Windows 시스템 로그 점검에 실패했습니다. 현재 상태: Critical/Error 1건 (기준 0건 이하), Warning 4건.Warning 키워드 4건.: The Collect procedure for service "Spooler" in DLL "C:\Windows\System32\winspool.drv" failed with error code The RPC server i...`
- stdout: `inspection_runtime=[ { "TimeCreated": "\/Date(1779350460853)\/", "LogName": "System", "ProviderName": "Microsoft-Windows-WindowsUpdateClient", "Id": 20, "LevelDisplayName": "Error", "Message": "Installation Failure: Windows failed to in...` / `inspection_runtimebak=[ { "TimeCreated": "\/Date(1779351930968)\/", "LogName": "Application", "ProviderName": "Microsoft-Windows-Perflib", "Id": 1014, "LevelDisplayName": "Warning", "Message": "The Collect procedure for service \"Spooler\"...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-WinEvent -FilterHashtable @{LogName=@('System','Application','Sec...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-WinEvent -FilterHashtable @{LogName=@('System','Application','Sec...`

### `server/windows/windows_memory_pagefile_usage_cim_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-SWAP-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.108s` / `inspection_runtimebak=1.184s`
- message: `inspection_runtime=Windows 스왑 메모리 사용률 점검이 정상입니다. 현재 상태: 파일=C:\pagefile.sys, 총 1.12GiB, 사용 0.29GiB, 여유 0.83GiB, 사용률 26.22% (기준 50.00% 미만), 피크 0.60GiB.` / `inspection_runtimebak=Windows 스왑 메모리 사용률 점검이 정상입니다. 현재 상태: 파일=C:\pagefile.sys, 총 1.12GiB, 사용 0.32GiB, 여유 0.81GiB, 사용률 28.30% (기준 50.00% 미만), 피크 0.60GiB.`
- metrics: `inspection_runtime={'filename': 'C:\\pagefile.sys', 'swap_type': 'file', 'swap_size_mb': 1152.0, 'swap_used_mb': 302.0, 'swap_free_mb': 850.0, 'swap_usage_percent': 26.22, 'peak_usage_mb': 610.0, 'swap_size_gib': 1.12, 'swap_used_gib': ...` / `inspection_runtimebak={'filename': 'C:\\pagefile.sys', 'swap_type': 'file', 'swap_size_mb': 1152.0, 'swap_used_mb': 326.0, 'swap_free_mb': 826.0, 'swap_usage_percent': 28.3, 'peak_usage_mb': 610.0, 'swap_size_gib': 1.12, 'swap_used_gib': 0...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PageFileUsage | Select-Object @{N='Filename';E=...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PageFileUsage | Select-Object @{N='Filename';E=...`

### `server/windows/windows_memory_usage_cim_check`

- host: `192.168.1.203` / port: `5985`
- inspection_code: `W-REPLAY-MEM-01`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.214s` / `inspection_runtimebak=1.902s`
- message: `inspection_runtime=Windows 메모리 사용률 점검이 정상입니다. 현재 상태: 물리 메모리 총 2.00GiB, 사용 1.32GiB, 여유 0.68GiB, 사용률 65.81% (기준 90.00% 미만), 여유율 34.00% (기준 10.00% 초과), 스왑 사용률 25.66% (기준 50.00% 미만).` / `inspection_runtimebak=Windows 메모리 사용률 점검이 정상입니다. 현재 상태: 물리 메모리 총 2.00GiB, 사용 1.28GiB, 여유 0.72GiB, 사용률 64.24% (기준 90.00% 미만), 여유율 36.00% (기준 10.00% 초과), 스왑 사용률 28.32% (기준 50.00% 미만).`
- metrics: `inspection_runtime={'memory_total_gib': 2.0, 'memory_used_gib': 1.32, 'memory_free_gib': 0.68, 'memory_usage_percent': 65.81, 'memory_free_percent': 34.0, 'swap_total_gib': 1.13, 'swap_used_gib': 0.29, 'swap_free_gib': 0.83, 'swap_usage...` / `inspection_runtimebak={'memory_total_gib': 2.0, 'memory_used_gib': 1.28, 'memory_free_gib': 0.72, 'memory_usage_percent': 64.24, 'memory_free_percent': 36.0, 'swap_total_gib': 1.13, 'swap_used_gib': 0.32, 'swap_free_gib': 0.81, 'swap_usage...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $os=Get-CimInstance Win32_OperatingSystem;$pf=Get-CimInstance Win32_P...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: $OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $os=Get-CimInstance Win32_OperatingSystem;$pf=Get-CimInstance Win32_P...`

### `tutorial/rocky/rocky_ssh_04_multi_command_health_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `TUTORIAL-ROCKY-SSH-04`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=1.239s` / `inspection_runtimebak=1.214s`
- message: `inspection_runtime=_ssh 다중 명령 예제가 정상 수행되었습니다. cores=24, available_memory_mb=10160` / `inspection_runtimebak=_ssh 다중 명령 예제가 정상 수행되었습니다. cores=24, available_memory_mb=10149`
- metrics: `inspection_runtime={'cpu_core_count': 24, 'total_memory_mb': 15358, 'used_memory_mb': 5198, 'available_memory_mb': 10160, 'uptime_text': '17:18:54 up 247 days, 1:43, 2 users, load average: 0.27, 0.12, 0.04', 'load_average': '0.27, 0.12,...` / `inspection_runtimebak={'cpu_core_count': 24, 'total_memory_mb': 15358, 'used_memory_mb': 5208, 'available_memory_mb': 10149, 'uptime_text': '17:29:55 up 247 days, 1:54, 2 users, load average: 0.09, 0.11, 0.09', 'load_average': '0.09, 0.11,...`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: nproc - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): 24 - 출력 내용(stderr): Warning: Permanently added '192.168.1.123' (ED25519) to the list of known hosts. ** WARNING: connection is not using a post-quantu...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: nproc - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): 24 - 출력 내용(stderr): Warning: Permanently added '192.168.1.123' (ED25519) to the list of known hosts. ** WARNING: connection is not using a post-quantu...`

### `tutorial/rocky/rocky_ssh_06_shell_script_check`

- host: `192.168.1.123` / port: `22`
- inspection_code: `TUTORIAL-ROCKY-SSH-06`
- status: `inspection_runtime=ok` / `inspection_runtimebak=ok`
- duration: `inspection_runtime=0.853s` / `inspection_runtimebak=0.845s`
- metrics: `inspection_runtime={'hostname': 'localhost.localdomain', 'uptime_text': '17:18:58 up 247 days, 1:43, 2 users, load average: 0.24, 0.12, 0.04'}` / `inspection_runtimebak={'hostname': 'localhost.localdomain', 'uptime_text': '17:30:00 up 247 days, 1:54, 2 users, load average: 0.08, 0.11, 0.09'}`
- raw_output: `inspection_runtime=[점검 단계 1] - 실행 명령어: bash -lc 'hostname_value=$(hostname) uptime_value=$(uptime) printf '"'"'HOSTNAME=%s\n'"'"' "$hostname_value" printf '"'"'UPTIME=%s\n'"'"' "$uptime_value"' - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): H...` / `inspection_runtimebak=[점검 단계 1] - 실행 명령어: bash -lc 'hostname_value=$(hostname) uptime_value=$(uptime) printf '"'"'HOSTNAME=%s\n'"'"' "$hostname_value" printf '"'"'UPTIME=%s\n'"'"' "$uptime_value"' - 명령 종료코드: rc=0 (정상 종료) - 출력 내용(stdout): H...`

## Same Cases

- `network/cisco_ios/cisco_ios_자원사용률점검_CPU사용률`
- `server/esxi/esxi_datastore_path_check`
- `server/esxi/esxi_status_agent_service_check`
- `server/esxi/esxi_status_hardware_health_check`
- `server/esxi/esxi_status_vcenter_agent_check`
- `server/esxi/esxi_status_vm_list_check`
- `server/hpux/hpux_cluster_daemon_cmviewcl_check`
- `server/hpux/hpux_cluster_shared_volume_mount_check`
- `server/hpux/hpux_cpu_core_ioscan_check`
- `server/hpux/hpux_cpu_usage_sar_check`
- `server/hpux/hpux_disk_filesystem_inode_bdf_check`
- `server/hpux/hpux_disk_filesystem_usage_bdf_check`
- `server/hpux/hpux_disk_io_sar_check`
- `server/hpux/hpux_disk_raid_vgdisplay_check`
- `server/hpux/hpux_disk_recognition_ioscan_check`
- `server/hpux/hpux_disk_swap_swapinfo_check`
- `server/hpux/hpux_kernel_parameter_kctune_check`
- `server/hpux/hpux_log_cluster_serviceguard_check`
- `server/hpux/hpux_log_cpu_dmesg_check`
- `server/hpux/hpux_log_fan_dmesg_check`
- `server/hpux/hpux_log_hba_dmesg_check`
- `server/hpux/hpux_log_io_dmesg_check`
- `server/hpux/hpux_log_kernel_dmesg_check`
- `server/hpux/hpux_log_memory_dmesg_check`
- `server/hpux/hpux_log_nic_dmesg_check`
- `server/hpux/hpux_log_power_dmesg_check`
- `server/hpux/hpux_log_system_dmesg_check`
- `server/hpux/hpux_memory_recognition_machinfo_check`
- `server/hpux/hpux_memory_swap_swapinfo_check`
- `server/hpux/hpux_memory_usage_swapinfo_check`
- `server/hpux/hpux_network_link_status_lanscan_check`
- `server/hpux/hpux_network_nic_redundancy_hpapa_check`
- `server/hpux/hpux_network_ping_loss_check`
- `server/hpux/hpux_os_hba_connection_ioscan_check`
- `server/hpux/hpux_os_path_redundancy_scsimgr_check`
- `server/rocky/rocky_cluster_daemon_crm_mon_check`
- `server/rocky/rocky_cluster_shared_volume_mount_check`
- `server/rocky/rocky_cpu_core_check`
- `server/rocky/rocky_disk_raid_mdadm_check`
- `server/rocky/rocky_disk_recognition_lsblk_check`
- `server/rocky/rocky_disk_swap_swapon_check`
- `server/rocky/rocky_log_cluster_dmesg_check`
- `server/rocky/rocky_log_cpu_dmesg_check`
- `server/rocky/rocky_log_fan_dmesg_check`
- `server/rocky/rocky_log_hba_dmesg_check`
- `server/rocky/rocky_log_io_dmesg_check`
- `server/rocky/rocky_log_kernel_dmesg_check`
- `server/rocky/rocky_log_memory_dmesg_check`
- `server/rocky/rocky_log_nic_dmesg_check`
- `server/rocky/rocky_log_power_dmesg_check`
- `server/rocky/rocky_log_system_dmesg_check`
- `server/rocky/rocky_memory_recognition_dmidecode_check`
- `server/rocky/rocky_memory_swap_swapon_check`
- `server/rocky/rocky_network_link_status_ip_link_check`
- `server/rocky/rocky_network_nic_redundancy_bonding_check`
- `server/rocky/rocky_os_hba_connection_systool_check`
- `server/solaris/solaris_cluster_daemon_scstat_check`
- `server/solaris/solaris_cluster_shared_volume_mount_check`
- `server/solaris/solaris_cpu_core_psrinfo_check`
- `server/solaris/solaris_disk_filesystem_usage_df_check`
- `server/solaris/solaris_disk_inode_df_check`
- `server/solaris/solaris_disk_io_iostat_check`
- `server/solaris/solaris_disk_recognition_format_check`
- `server/solaris/solaris_disk_redundancy_metastat_check`
- `server/solaris/solaris_disk_swap_swap_check`
- `server/solaris/solaris_kernal_parameter_sysdef_check`
- `server/solaris/solaris_log_cluster_clog_check`
- `server/solaris/solaris_log_cpu_dmesg_check`
- `server/solaris/solaris_log_fan_dmesg_check`
- `server/solaris/solaris_log_hba_dmesg_check`
- `server/solaris/solaris_log_io_dmesg_check`
- `server/solaris/solaris_log_kernel_dmesg_check`
- `server/solaris/solaris_log_memory_dmesg_check`
- `server/solaris/solaris_log_nic_dmesg_check`
- `server/solaris/solaris_log_power_dmesg_check`
- `server/solaris/solaris_log_system_dmesg_check`
- `server/solaris/solaris_memory_paging_space_swap_check`
- `server/solaris/solaris_memory_recognition_prtdiag_check`
- `server/solaris/solaris_network_link_status_dladm_check`
- `server/solaris/solaris_network_nic_redundancy_ipmpstat_check`
- `server/solaris/solaris_os_hba_connection_status_fcinfo_check`
- `server/solaris/solaris_os_path_redundancy_mpathadm_check`
- `server/windows/windows_cluster_daemon_check`
- `server/windows/windows_cluster_shared_volume_check`
- `server/windows/windows_cpu_core_cim_check`
- `server/windows/windows_disk_inode_not_applicable_check`
- `server/windows/windows_disk_redundancy_health_check`
- `server/windows/windows_log_cluster_event_check`
- `server/windows/windows_log_cpu_event_check`
- `server/windows/windows_log_fan_manual_check`
- `server/windows/windows_log_kernel_event_check`
- `server/windows/windows_log_memory_event_check`
- `server/windows/windows_log_power_event_check`
- `server/windows/windows_memory_recognition_cim_check`
- `server/windows/windows_network_link_status_check`
- `server/windows/windows_network_nic_teaming_check`
- `server/windows/windows_network_ping_loss_check`
- `server/windows/windows_os_hba_connection_manual_check`
- `server/windows/windows_os_mpio_path_check`
- `tutorial/cisco_ios/cisco_ios_paramiko_01_show_clock_check`
- `tutorial/cisco_ios/cisco_ios_paramiko_02_show_version_check`
- `tutorial/cisco_ios/cisco_ios_paramiko_03_interface_brief_check`
- `tutorial/cisco_ios/cisco_ios_paramiko_04_running_hostname_check`
- `tutorial/cisco_ios/cisco_ios_paramiko_05_running_config_check`
- `tutorial/rocky/rocky_paramiko_07_become_root_exec_check`
- `tutorial/rocky/rocky_ssh_01_basic_identity_check`
- `tutorial/rocky/rocky_ssh_02_os_release_check`
- `tutorial/rocky/rocky_ssh_03_root_filesystem_df_check`
- `tutorial/rocky/rocky_ssh_05_become_root_access_check`
- `tutorial/unix/unix_test_check`
- `tutorial/windows/windows_winrm_01_hostname_check`
- `tutorial/windows/windows_winrm_02_os_info_check`
- `tutorial/windows/windows_winrm_03_disk_inventory_check`
- `tutorial/windows/windows_winrm_04_winrm_service_check`
- `tutorial/windows/windows_winrm_05_system_eventlog_check`
- `tutorial/windows/windows_winrm_06_powershell_script_check`
- `was/jeus/rocky/was_1_1_ps_cpu_chk`
- `was/jeus/rocky/was_1_2_ps_mem_chk`
- `was/jeus/rocky/was_1_3_ps_status_chk`
- `was/jeus/rocky/was_1_4_ps_startup_chk`
- `was/jeus/rocky/was_2_1_log_manage_chk`
- `was/jeus/rocky/was_2_2_log_service_chk`
- `was/jeus/rocky/was_2_3_log_cli_acs_chk`
- `was/jeus/rocky/was_2_4_log_gc_chk`
- `was/jeus/rocky/was_2_5_log_con_pool_chk`
- `was/jeus/rocky/was_3_1_jvm_heap_chk`
- `was/jeus/rocky/was_4_1_work_thrd_chk`
- `was/jeus/rocky/was_4_2_runnable_thrd_chk`
- `was/jeus/rocky/was_5_1_con_pool_chk`
- `was/jeus/rocky/was_5_2_db_con_chk`
- `was/jeus/rocky/was_6_1_dump_chk`
- `was/jeus/rocky/was_7_1_deploy_status_chk`
- `was/jeus/rocky/was_8_1_thrd_pool_status_chk`
- `was/jeus/rocky/was_9_1_start_script_chk`
- `web/webtob/rocky/webtob_config_web_was_connection_webtob_ctl_status_check`
- `web/webtob/rocky/webtob_filesystem_web_application_filesystem_df_h_check`
- `web/webtob/rocky/webtob_filesystem_web_engine_filesystem_df_h_check`
- `web/webtob/rocky/webtob_filesystem_web_log_filesystem_df_h_check`
- `web/webtob/rocky/webtob_log_access_log_awk_status_200_check`
- `web/webtob/rocky/webtob_log_error_log_grep_error_check`
- `web/webtob/rocky/webtob_log_request_document_unavailable_awk_status_404_check`
- `web/webtob/rocky/webtob_log_service_temporarily_unavailable_grep_status_503_check`
- `web/webtob/rocky/webtob_log_was_response_time_awk_response_time_check`
- `web/webtob/rocky/webtob_log_web_service_unavailable_grep_status_500_check`
- `web/webtob/rocky/webtob_process_cpu_usage_top_grep_check`
- `web/webtob/rocky/webtob_process_memory_usage_top_grep_check`
- `web/webtob/rocky/webtob_process_startup_ps_aux_grep_check`
- `web/webtob/rocky/webtob_process_status_top_grep_check`
- `web/webtob/rocky/webtob_service_port_connection_telnet_check`
- `web/webtob/rocky/webtob_service_port_open_netstat_grep_check`
- `web/webtob/rocky/webtob_service_request_count_webtob_ctl_status_check`
