# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

apache_tomcat

# application

rocky

# inspection_code

WAS-APACHE-TOMCAT-ROCKY-REPLAY-002

# is_required

필수

# inspection_name

프로세스 메모리 사용률

# inspection_content

WAS 서비스 부하 확인을 위한 WAS 프로세스가 사용하고 있는 메모리 자원 사용률 확인

# inspection_command

```bash
ps -eo pid,comm,%mem,rss --sort=-%mem
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL ~]# ps -eo pid,comm,%mem,rss --sort=-%mem
    PID COMMAND         %MEM   RSS
1277821 java            42.8 3368548
1277850 firefox          8.3 658704
1276745 gnome-shell      5.9 465024
1278187 Isolated Web Co  2.8 226576
1278140 Privileged Cont  1.8 146112
1278068 Isolated Web Co  1.6 129760
1278123 Isolated Web Co  1.6 126648
1278047 WebExtensions    1.4 116684
1277021 gnome-software   1.3 102568
1278401 Web Content      1.1 91616
1278350 Web Content      1.1 91256
1278378 Web Content      1.1 89672
1277161 gsd-xsettings    0.8 65088
1277399 gnome-terminal-  0.8 63076
1277000 evolution-alarm  0.6 53772
1277938 Socket Process   0.6 51328
1277086 Xwayland         0.5 46412
   1107 firewalld        0.5 43520
1277005 vmtoolsd         0.5 40688
1276871 evolution-calen  0.4 36088
1277963 xdg-desktop-por  0.4 34460
   2318 python3          0.4 34180
1276935 gsd-media-keys   0.4 33760
1276970 gsd-wacom        0.4 33528
1277168 ibus-extension-  0.4 33448
1276934 gsd-keyboard     0.4 33012
1276830 evolution-sourc  0.4 32300
1276920 gsd-color        0.4 32144
1276941 gsd-power        0.4 32120
1276898 evolution-addre  0.3 30740
1277175 ibus-x11         0.3 30628
1277147 fwupd            0.3 29892
1277973 xdg-desktop-por  0.3 29568
1277058 gjs              0.3 28968
1276910 gjs              0.3 26756
   1037 polkitd          0.3 25716
1276849 goa-daemon       0.3 25380
1277088 gsd-printer      0.3 24168
   1241 NetworkManager   0.2 23284
1276929 gsd-datetime     0.2 23276
1276721 gnome-session-b  0.2 22940
   2312 python3          0.2 22128
1276817 gnome-shell-cal  0.2 22104
    728 systemd-journal  0.2 20808
1277949 xdg-desktop-por  0.2 19720
1276648 gnome-session-b  0.2 19492
      1 systemd          0.2 18132
1277981 wireplumber      0.2 16384
   1714 colord           0.2 16180
1276943 gsd-print-notif  0.1 15388
1276593 gdm-session-wor  0.1 15140
1276843 gvfs-udisks2-vo  0.1 15032
   2308 pmdaproc         0.1 14552
   1043 accounts-daemon  0.1 14480
   1047 udisksd          0.1 14456
1276863 goa-identity-se  0.1 14456
1276602 systemd          0.1 14380
1276959 gsd-smartcard    0.1 14272
    747 systemd-udevd    0.1 14268
1276964 gsd-sound        0.1 14072
 728825 systemd          0.1 13936
1277158 ibus-daemon      0.1 13844
   2952 pmlogger         0.1 13556
   2303 pmcd             0.1 13464
   1295 gdm              0.1 13224
1276957 gsd-sharing      0.1 13104
   1046 systemd-logind   0.1 12884
1276933 gsd-housekeepin  0.1 12612
   1103 ModemManager     0.1 12608
   1055 vmtoolsd         0.1 12544
 728816 sshd             0.1 11904
   1788 rsyslogd         0.1 11732
1276865 gvfs-gphoto2-vo  0.1 11260
1277980 pipewire         0.1 11008
1276876 gvfs-mtp-volume  0.1 10648
1276853 gvfs-goa-volume  0.1 10596
1276780 gvfsd-fuse       0.1 10516
   1053 VGAuthService    0.1 10496
   1266 cupsd            0.1 10368
1276641 gdm-wayland-ses  0.1 10172
1276882 sssd_kcm         0.1 10112
1276771 gvfsd            0.1 10076
 728827 (sd-pam)         0.1  9744
1276607 (sd-pam)         0.1  9744
   1039 power-profiles-  0.1  9724
1276790 at-spi-bus-laun  0.1  9628
1276968 gsd-usb-protect  0.1  9596
1277176 ibus-portal      0.1  9452
1277241 ibus-engine-sim  0.1  9432
1277167 ibus-dconf       0.1  9316
   1051 upowerd          0.1  9152
1276963 gsd-disk-utilit  0.1  9148
   1274 sshd             0.1  9088
1276919 gsd-a11y-settin  0.1  9048
1277953 xdg-document-po  0.1  9024
   1044 switcheroo-cont  0.1  8876
   2850 pmie             0.1  8832
1276946 gsd-rfkill       0.1  8812
1277556 gvfsd-metadata   0.1  8576
1276810 xdg-permission-  0.1  8528
1276951 gsd-screensaver  0.1  8404
 728877 su               0.1  8192
   2311 pmdalinux        0.1  7936
1276717 gnome-session-c  0.0  7748
1276635 gnome-keyring-d  0.0  7452
1276912 at-spi2-registr  0.0  7424
   2317 pmdadm           0.0  7168
 728841 sshd             0.0  7092
   2307 pmdaroot         0.0  6912
   1030 avahi-daemon     0.0  6784
   2310 pmdaxfs          0.0  6656
   2316 pmdakvm          0.0  6656
   1459 wpa_supplicant   0.0  6400
   2859 pmpause          0.0  6272
  10505 pmpause          0.0  6272
 728881 bash             0.0  6016
1277440 bash             0.0  6016
   1284 gssproxy         0.0  5964
 728842 bash             0.0  5888
   1029 dbus-broker      0.0  5712
   1001 rpcbind          0.0  5632
1276893 dconf-service    0.0  5632
   1028 dbus-broker-lau  0.0  4884
   1002 auditd           0.0  4656
1276643 dbus-broker-lau  0.0  4480
1276644 dbus-broker      0.0  4480
1276795 dbus-broker-lau  0.0  4096
 728985 ps               0.0  3968
   1294 crond            0.0  3712
   1004 sedispatch       0.0  3456
   1040 rtkit-daemon     0.0  3456
   1033 irqbalance       0.0  3072
   1058 chronyd          0.0  2736
1276796 dbus-broker      0.0  2688
   1293 atd              0.0  2560
   1071 avahi-daemon     0.0  2100
   1036 mcelog           0.0  2048
   1034 lsmd             0.0  1920
1277957 fusermount       0.0  1536
      2 kthreadd         0.0     0
      3 rcu_gp           0.0     0
      4 rcu_par_gp       0.0     0
      5 slub_flushwq     0.0     0
      6 netns            0.0     0
      8 kworker/0:0H-ev  0.0     0
     10 mm_percpu_wq     0.0     0
     12 rcu_tasks_kthre  0.0     0
     13 rcu_tasks_rude_  0.0     0
     14 rcu_tasks_trace  0.0     0
     15 ksoftirqd/0      0.0     0
     16 pr/tty0          0.0     0
     17 rcu_preempt      0.0     0
     18 migration/0      0.0     0
     19 idle_inject/0    0.0     0
     21 cpuhp/0          0.0     0
     22 cpuhp/1          0.0     0
     23 idle_inject/1    0.0     0
     24 migration/1      0.0     0
     25 ksoftirqd/1      0.0     0
     27 kworker/1:0H-ev  0.0     0
     29 kdevtmpfs        0.0     0
     30 inet_frag_wq     0.0     0
     31 kauditd          0.0     0
     32 khungtaskd       0.0     0
     33 oom_reaper       0.0     0
     35 writeback        0.0     0
     36 kcompactd0       0.0     0
     37 ksmd             0.0     0
     38 khugepaged       0.0     0
     39 cryptd           0.0     0
     40 kintegrityd      0.0     0
     41 kblockd          0.0     0
     42 blkcg_punt_bio   0.0     0
     43 tpm_dev_wq       0.0     0
     44 md               0.0     0
     45 md_bitmap        0.0     0
     46 edac-poller      0.0     0
     47 watchdogd        0.0     0
     49 kswapd0          0.0     0
     55 kthrotld         0.0     0
     62 irq/24-pciehp    0.0     0
     63 irq/25-pciehp    0.0     0
     64 irq/26-pciehp    0.0     0
     65 irq/27-pciehp    0.0     0
     66 irq/28-pciehp    0.0     0
     67 irq/29-pciehp    0.0     0
     68 irq/30-pciehp    0.0     0
     69 irq/31-pciehp    0.0     0
     70 irq/32-pciehp    0.0     0
     71 irq/33-pciehp    0.0     0
     72 irq/34-pciehp    0.0     0
     73 irq/35-pciehp    0.0     0
     74 irq/36-pciehp    0.0     0
     75 irq/37-pciehp    0.0     0
     76 irq/38-pciehp    0.0     0
     77 irq/39-pciehp    0.0     0
     78 irq/40-pciehp    0.0     0
     79 irq/41-pciehp    0.0     0
     80 irq/42-pciehp    0.0     0
     81 irq/43-pciehp    0.0     0
     82 irq/44-pciehp    0.0     0
     83 irq/45-pciehp    0.0     0
     84 irq/46-pciehp    0.0     0
     85 irq/47-pciehp    0.0     0
     86 irq/48-pciehp    0.0     0
     87 irq/49-pciehp    0.0     0
     88 irq/50-pciehp    0.0     0
     89 irq/51-pciehp    0.0     0
     90 irq/52-pciehp    0.0     0
     91 irq/53-pciehp    0.0     0
     92 irq/54-pciehp    0.0     0
     93 irq/55-pciehp    0.0     0
     94 acpi_thermal_pm  0.0     0
     95 kmpath_rdacd     0.0     0
     96 kaluad           0.0     0
     97 mld              0.0     0
     98 ipv6_addrconf    0.0     0
    108 kstrp            0.0     0
    113 zswap-shrink     0.0     0
    114 kworker/u5:0     0.0     0
    262 kworker/1:1H-kb  0.0     0
    427 scsi_eh_0        0.0     0
    428 scsi_tmf_0       0.0     0
    429 vmw_pvscsi_wq_0  0.0     0
    446 ata_sff          0.0     0
    450 scsi_eh_1        0.0     0
    451 scsi_tmf_1       0.0     0
    453 scsi_eh_2        0.0     0
    454 scsi_tmf_2       0.0     0
    457 scsi_eh_3        0.0     0
    459 scsi_tmf_3       0.0     0
    460 scsi_eh_4        0.0     0
    461 scsi_tmf_4       0.0     0
    462 scsi_eh_5        0.0     0
    463 scsi_tmf_5       0.0     0
    464 scsi_eh_6        0.0     0
    465 scsi_tmf_6       0.0     0
    466 scsi_eh_7        0.0     0
    467 scsi_tmf_7       0.0     0
    468 scsi_eh_8        0.0     0
    469 scsi_tmf_8       0.0     0
    470 scsi_eh_9        0.0     0
    471 scsi_tmf_9       0.0     0
    472 scsi_eh_10       0.0     0
    473 scsi_tmf_10      0.0     0
    474 scsi_eh_11       0.0     0
    475 scsi_tmf_11      0.0     0
    476 scsi_eh_12       0.0     0
    477 scsi_tmf_12      0.0     0
    478 scsi_eh_13       0.0     0
    479 scsi_tmf_13      0.0     0
    480 scsi_eh_14       0.0     0
    481 scsi_tmf_14      0.0     0
    482 scsi_eh_15       0.0     0
    483 scsi_tmf_15      0.0     0
    484 scsi_eh_16       0.0     0
    485 scsi_tmf_16      0.0     0
    486 scsi_eh_17       0.0     0
    487 scsi_tmf_17      0.0     0
    488 scsi_eh_18       0.0     0
    489 scsi_tmf_18      0.0     0
    490 scsi_eh_19       0.0     0
    491 scsi_tmf_19      0.0     0
    492 scsi_eh_20       0.0     0
    493 scsi_tmf_20      0.0     0
    494 scsi_eh_21       0.0     0
    495 scsi_tmf_21      0.0     0
    496 scsi_eh_22       0.0     0
    497 scsi_tmf_22      0.0     0
    498 scsi_eh_23       0.0     0
    499 scsi_tmf_23      0.0     0
    500 scsi_eh_24       0.0     0
    501 scsi_tmf_24      0.0     0
    502 scsi_eh_25       0.0     0
    503 scsi_tmf_25      0.0     0
    504 scsi_eh_26       0.0     0
    505 scsi_tmf_26      0.0     0
    506 scsi_eh_27       0.0     0
    507 scsi_tmf_27      0.0     0
    508 scsi_eh_28       0.0     0
    509 scsi_tmf_28      0.0     0
    510 scsi_eh_29       0.0     0
    511 scsi_tmf_29      0.0     0
    512 scsi_eh_30       0.0     0
    513 scsi_tmf_30      0.0     0
    514 scsi_eh_31       0.0     0
    515 scsi_tmf_31      0.0     0
    516 scsi_eh_32       0.0     0
    517 scsi_tmf_32      0.0     0
    547 irq/16-vmwgfx    0.0     0
    548 ttm              0.0     0
    617 kdmflush/253:0   0.0     0
    624 kdmflush/253:1   0.0     0
    642 xfsalloc         0.0     0
    643 xfs_mru_cache    0.0     0
    644 xfs-buf/dm-0     0.0     0
    645 xfs-conv/dm-0    0.0     0
    646 xfs-reclaim/dm-  0.0     0
    647 xfs-blockgc/dm-  0.0     0
    648 xfs-inodegc/dm-  0.0     0
    649 xfs-log/dm-0     0.0     0
    650 xfs-cil/dm-0     0.0     0
    651 xfsaild/dm-0     0.0     0
    930 irq/61-vmw_vmci  0.0     0
    931 irq/62-vmw_vmci  0.0     0
    955 kdmflush/253:2   0.0     0
    958 nfit             0.0     0
    972 xfs-buf/sda2     0.0     0
    973 xfs-conv/sda2    0.0     0
    974 xfs-reclaim/sda  0.0     0
    975 xfs-blockgc/sda  0.0     0
    976 xfs-inodegc/sda  0.0     0
    977 xfs-log/sda2     0.0     0
    978 xfs-cil/sda2     0.0     0
    979 xfsaild/sda2     0.0     0
    980 xfs-buf/dm-2     0.0     0
    981 xfs-conv/dm-2    0.0     0
    982 xfs-reclaim/dm-  0.0     0
    983 xfs-blockgc/dm-  0.0     0
    984 xfs-inodegc/dm-  0.0     0
    985 xfs-log/dm-2     0.0     0
    986 xfs-cil/dm-2     0.0     0
    987 xfsaild/dm-2     0.0     0
   1014 rpciod           0.0     0
   1015 xprtiod          0.0     0
 709045 kworker/u4:0-ev  0.0     0
 715538 kworker/u4:3-xf  0.0     0
 718481 kworker/u4:1-fl  0.0     0
 725929 kworker/1:3-eve  0.0     0
 727643 kworker/1:1-mm_  0.0     0
 727658 kworker/0:2-xfs  0.0     0
 727771 kworker/0:3-xfs  0.0     0
 728577 kworker/1:0-xfs  0.0     0
 728822 kworker/1:2-eve  0.0     0
 728931 kworker/0:0-xfs  0.0     0
 728947 kworker/0:1-eve  0.0     0
1277181 kworker/0:2H-kb  0.0     0

---
```

# description

- `ps` 명령을 통해 WAS 관련 프로세스의 CPU/메모리 사용률 혹은 기동 상태를 점검하여 서비스 정상 동작 여부를 확인합니다.

- **양호**: 대상 프로세스의 상태가 정상이고 사용률이 임계치 이하로 유지됨 (기동 상태의 경우 프로세스 존재)
- **경고**: 자원 사용률이 임계치를 초과하거나 좀비(Z)/비정상 상태, 프로세스가 기동되지 않음
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds

[
    {id: null, key: "max_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'ps -eo pid,comm,%mem,rss --sort=-%mem'
COMMAND_TIMEOUT = 20
TOP_PROCESS_LIMIT = 10


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _run_command(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='Apache Tomcat 메모리 사용률 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def _parse_rows(self, stdout):
        rows = []
        header_found = False
        for line in stdout.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if 'PID' in parts and 'COMMAND' in parts and '%MEM' in parts and 'RSS' in parts:
                header_found = True
                continue
            if not header_found or len(parts) < 4:
                continue
            try:
                pid = int(parts[0])
                mem_percent = float(parts[-2])
                rss_kib = int(parts[-1])
            except ValueError:
                continue
            command = ' '.join(parts[1:-2]).strip()
            if command:
                rows.append({
                    'pid': pid,
                    'command': command,
                    'mem_percent': mem_percent,
                    'rss_kib': rss_kib,
                })
        return rows

    def run(self):
        stdout, _stderr, error = self._run_command()
        if error:
            return error

        threshold = self.get_threshold_var('max_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_usage_percent': threshold}
        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='ps 출력에서 프로세스 메모리 사용률 정보를 해석할 수 없습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        max_row = max(rows, key=lambda row: row['mem_percent'])
        over_rows = [row for row in rows if row['mem_percent'] > threshold]
        metrics = {
            'process_count': len(rows),
            'max_usage_percent': max_row['mem_percent'],
            'max_usage_pid': max_row['pid'],
            'max_usage_command': max_row['command'],
            'max_usage_rss_kib': max_row['rss_kib'],
            'over_threshold_count': len(over_rows),
            'over_threshold_processes': over_rows,
            'top_processes': rows[:TOP_PROCESS_LIMIT],
        }
        if over_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 사용률이 기준을 초과한 프로세스가 있습니다.',
                message='Apache Tomcat 프로세스 메모리 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (
                    max_row['mem_percent'],
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='프로세스 메모리 사용률이 기준 이하입니다.',
            message='Apache Tomcat 프로세스 메모리 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (
                max_row['mem_percent'],
                threshold,
            ),
        )


CHECK_CLASS = Check
