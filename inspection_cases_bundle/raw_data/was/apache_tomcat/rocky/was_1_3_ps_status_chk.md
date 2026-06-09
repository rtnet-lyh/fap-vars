# 영역
프로세스

# 세부 점검항목
프로세스 사용 상태 점검

# 점검 내용
점유 리소스 사용률 점검

# 구분
필수

# 명령어
```bash
ps -eo pid,stat,comm
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL ~]# ps -eo pid,stat,comm
    PID STAT COMMAND
      1 Ss   systemd
      2 S    kthreadd
      3 I<   rcu_gp
      4 I<   rcu_par_gp
      5 I<   slub_flushwq
      6 I<   netns
      8 I<   kworker/0:0H-events_highpri
     10 I<   mm_percpu_wq
     12 I    rcu_tasks_kthre
     13 I    rcu_tasks_rude_
     14 I    rcu_tasks_trace
     15 S    ksoftirqd/0
     16 S    pr/tty0
     17 I    rcu_preempt
     18 S    migration/0
     19 S    idle_inject/0
     21 S    cpuhp/0
     22 S    cpuhp/1
     23 S    idle_inject/1
     24 S    migration/1
     25 S    ksoftirqd/1
     27 I<   kworker/1:0H-events_highpri
     29 S    kdevtmpfs
     30 I<   inet_frag_wq
     31 S    kauditd
     32 S    khungtaskd
     33 S    oom_reaper
     35 I<   writeback
     36 S    kcompactd0
     37 SN   ksmd
     38 SN   khugepaged
     39 I<   cryptd
     40 I<   kintegrityd
     41 I<   kblockd
     42 I<   blkcg_punt_bio
     43 I<   tpm_dev_wq
     44 I<   md
     45 I<   md_bitmap
     46 I<   edac-poller
     47 S    watchdogd
     49 S    kswapd0
     55 I<   kthrotld
     62 S    irq/24-pciehp
     63 S    irq/25-pciehp
     64 S    irq/26-pciehp
     65 S    irq/27-pciehp
     66 S    irq/28-pciehp
     67 S    irq/29-pciehp
     68 S    irq/30-pciehp
     69 S    irq/31-pciehp
     70 S    irq/32-pciehp
     71 S    irq/33-pciehp
     72 S    irq/34-pciehp
     73 S    irq/35-pciehp
     74 S    irq/36-pciehp
     75 S    irq/37-pciehp
     76 S    irq/38-pciehp
     77 S    irq/39-pciehp
     78 S    irq/40-pciehp
     79 S    irq/41-pciehp
     80 S    irq/42-pciehp
     81 S    irq/43-pciehp
     82 S    irq/44-pciehp
     83 S    irq/45-pciehp
     84 S    irq/46-pciehp
     85 S    irq/47-pciehp
     86 S    irq/48-pciehp
     87 S    irq/49-pciehp
     88 S    irq/50-pciehp
     89 S    irq/51-pciehp
     90 S    irq/52-pciehp
     91 S    irq/53-pciehp
     92 S    irq/54-pciehp
     93 S    irq/55-pciehp
     94 I<   acpi_thermal_pm
     95 I<   kmpath_rdacd
     96 I<   kaluad
     97 I<   mld
     98 I<   ipv6_addrconf
    108 I<   kstrp
    113 I<   zswap-shrink
    114 I<   kworker/u5:0
    262 I<   kworker/1:1H-kblockd
    427 S    scsi_eh_0
    428 I<   scsi_tmf_0
    429 I<   vmw_pvscsi_wq_0
    446 I<   ata_sff
    450 S    scsi_eh_1
    451 I<   scsi_tmf_1
    453 S    scsi_eh_2
    454 I<   scsi_tmf_2
    457 S    scsi_eh_3
    459 I<   scsi_tmf_3
    460 S    scsi_eh_4
    461 I<   scsi_tmf_4
    462 S    scsi_eh_5
    463 I<   scsi_tmf_5
    464 S    scsi_eh_6
    465 I<   scsi_tmf_6
    466 S    scsi_eh_7
    467 I<   scsi_tmf_7
    468 S    scsi_eh_8
    469 I<   scsi_tmf_8
    470 S    scsi_eh_9
    471 I<   scsi_tmf_9
    472 S    scsi_eh_10
    473 I<   scsi_tmf_10
    474 S    scsi_eh_11
    475 I<   scsi_tmf_11
    476 S    scsi_eh_12
    477 I<   scsi_tmf_12
    478 S    scsi_eh_13
    479 I<   scsi_tmf_13
    480 S    scsi_eh_14
    481 I<   scsi_tmf_14
    482 S    scsi_eh_15
    483 I<   scsi_tmf_15
    484 S    scsi_eh_16
    485 I<   scsi_tmf_16
    486 S    scsi_eh_17
    487 I<   scsi_tmf_17
    488 S    scsi_eh_18
    489 I<   scsi_tmf_18
    490 S    scsi_eh_19
    491 I<   scsi_tmf_19
    492 S    scsi_eh_20
    493 I<   scsi_tmf_20
    494 S    scsi_eh_21
    495 I<   scsi_tmf_21
    496 S    scsi_eh_22
    497 I<   scsi_tmf_22
    498 S    scsi_eh_23
    499 I<   scsi_tmf_23
    500 S    scsi_eh_24
    501 I<   scsi_tmf_24
    502 S    scsi_eh_25
    503 I<   scsi_tmf_25
    504 S    scsi_eh_26
    505 I<   scsi_tmf_26
    506 S    scsi_eh_27
    507 I<   scsi_tmf_27
    508 S    scsi_eh_28
    509 I<   scsi_tmf_28
    510 S    scsi_eh_29
    511 I<   scsi_tmf_29
    512 S    scsi_eh_30
    513 I<   scsi_tmf_30
    514 S    scsi_eh_31
    515 I<   scsi_tmf_31
    516 S    scsi_eh_32
    517 I<   scsi_tmf_32
    547 S    irq/16-vmwgfx
    548 I<   ttm
    617 I<   kdmflush/253:0
    624 I<   kdmflush/253:1
    642 I<   xfsalloc
    643 I<   xfs_mru_cache
    644 I<   xfs-buf/dm-0
    645 I<   xfs-conv/dm-0
    646 I<   xfs-reclaim/dm-
    647 I<   xfs-blockgc/dm-
    648 I<   xfs-inodegc/dm-
    649 I<   xfs-log/dm-0
    650 I<   xfs-cil/dm-0
    651 S    xfsaild/dm-0
    728 Ss   systemd-journal
    747 Ss   systemd-udevd
    930 S    irq/61-vmw_vmci
    931 S    irq/62-vmw_vmci
    955 I<   kdmflush/253:2
    958 I<   nfit
    972 I<   xfs-buf/sda2
    973 I<   xfs-conv/sda2
    974 I<   xfs-reclaim/sda
    975 I<   xfs-blockgc/sda
    976 I<   xfs-inodegc/sda
    977 I<   xfs-log/sda2
    978 I<   xfs-cil/sda2
    979 S    xfsaild/sda2
    980 I<   xfs-buf/dm-2
    981 I<   xfs-conv/dm-2
    982 I<   xfs-reclaim/dm-
    983 I<   xfs-blockgc/dm-
    984 I<   xfs-inodegc/dm-
    985 I<   xfs-log/dm-2
    986 I<   xfs-cil/dm-2
    987 S    xfsaild/dm-2
   1001 Ss   rpcbind
   1002 S<sl auditd
   1004 S<   sedispatch
   1014 I<   rpciod
   1015 I<   xprtiod
   1028 Ss   dbus-broker-lau
   1029 S    dbus-broker
   1030 Ss   avahi-daemon
   1033 Ssl  irqbalance
   1034 Ss   lsmd
   1036 Ss   mcelog
   1037 Ssl  polkitd
   1039 Ssl  power-profiles-
   1040 SNsl rtkit-daemon
   1043 Ssl  accounts-daemon
   1044 Ssl  switcheroo-cont
   1046 Ss   systemd-logind
   1047 Ssl  udisksd
   1051 Ssl  upowerd
   1053 Ss   VGAuthService
   1055 Ssl  vmtoolsd
   1058 S    chronyd
   1071 S    avahi-daemon
   1103 Ssl  ModemManager
   1107 Ssl  firewalld
   1241 Ssl  NetworkManager
   1266 Ss   cupsd
   1274 Ss   sshd
   1284 Ssl  gssproxy
   1293 Ss   atd
   1294 Ss   crond
   1295 Ssl  gdm
   1459 Ss   wpa_supplicant
   1714 Ssl  colord
   1788 Ssl  rsyslogd
   2303 Ss   pmcd
   2307 S    pmdaroot
   2308 S    pmdaproc
   2310 S    pmdaxfs
   2311 S    pmdalinux
   2312 S    python3
   2316 S    pmdakvm
   2317 S    pmdadm
   2318 S    python3
   2850 S    pmie
   2859 Ss   pmpause
   2952 S    pmlogger
  10505 Ss   pmpause
 709045 I    kworker/u4:0-events_unbound
 715538 I    kworker/u4:3-xfs-cil/sda2
 718481 I    kworker/u4:1-writeback
 725929 I    kworker/1:3-mm_percpu_wq
 727658 I    kworker/0:2-xfs-sync/dm-2
 727771 I    kworker/0:3-xfs-sync/sda2
 728816 Ss   sshd
 728822 I    kworker/1:2-events
 728825 Ss   systemd
 728827 S    (sd-pam)
 728841 S    sshd
 728842 Ss   bash
 728877 S    su
 728881 S    bash
 728931 I    kworker/0:0-xfs-sync/dm-2
 728947 I    kworker/0:1-mm_percpu_wq
 728996 R+   ps
1276593 Sl   gdm-session-wor
1276602 Ss   systemd
1276607 S    (sd-pam)
1276635 Sl   gnome-keyring-d
1276641 Ssl+ gdm-wayland-ses
1276643 Ss   dbus-broker-lau
1276644 S    dbus-broker
1276648 Sl+  gnome-session-b
1276717 Ssl  gnome-session-c
1276721 Ssl  gnome-session-b
1276745 Ssl  gnome-shell
1276771 Ssl  gvfsd
1276780 Sl   gvfsd-fuse
1276790 Ssl  at-spi-bus-laun
1276795 S    dbus-broker-lau
1276796 S    dbus-broker
1276810 Ssl  xdg-permission-
1276817 Ssl  gnome-shell-cal
1276830 Ssl  evolution-sourc
1276843 Ssl  gvfs-udisks2-vo
1276849 Ssl  goa-daemon
1276853 Ssl  gvfs-goa-volume
1276863 Ssl  goa-identity-se
1276865 Ssl  gvfs-gphoto2-vo
1276871 Ssl  evolution-calen
1276876 Ssl  gvfs-mtp-volume
1276882 Ss   sssd_kcm
1276893 Ssl  dconf-service
1276898 Ssl  evolution-addre
1276910 Ssl  gjs
1276912 Ssl  at-spi2-registr
1276919 Ssl  gsd-a11y-settin
1276920 Ssl  gsd-color
1276929 Ssl  gsd-datetime
1276933 Ssl  gsd-housekeepin
1276934 Ssl  gsd-keyboard
1276935 Ssl  gsd-media-keys
1276941 Ssl  gsd-power
1276943 Ssl  gsd-print-notif
1276946 Ssl  gsd-rfkill
1276951 Ssl  gsd-screensaver
1276957 Ssl  gsd-sharing
1276959 Ssl  gsd-smartcard
1276963 Sl   gsd-disk-utilit
1276964 Ssl  gsd-sound
1276968 Ssl  gsd-usb-protect
1276970 Ssl  gsd-wacom
1277000 Sl   evolution-alarm
1277005 Sl   vmtoolsd
1277021 Sl   gnome-software
1277058 Ssl  gjs
1277086 S    Xwayland
1277088 Sl   gsd-printer
1277147 Ssl  fwupd
1277158 Sl   ibus-daemon
1277161 Ssl  gsd-xsettings
1277167 Sl   ibus-dconf
1277168 Sl   ibus-extension-
1277175 Sl   ibus-x11
1277176 Ssl  ibus-portal
1277181 I<   kworker/0:2H-xfs-log/dm-0
1277241 Sl   ibus-engine-sim
1277399 Ssl  gnome-terminal-
1277440 Ss+  bash
1277556 Ssl  gvfsd-metadata
1277821 Sl   java
1277850 Sl   firefox
1277938 Sl   Socket Process
1277949 Ssl  xdg-desktop-por
1277953 Ssl  xdg-document-po
1277957 Ss   fusermount
1277963 Ssl  xdg-desktop-por
1277973 Ssl  xdg-desktop-por
1277980 S<sl pipewire
1277981 S<sl wireplumber
1278047 Sl   WebExtensions
1278068 Sl   Isolated Web Co
1278123 Sl   Isolated Web Co
1278140 Sl   Privileged Cont
1278187 Sl   Isolated Web Co
1278350 Sl   Web Content
1278378 Sl   Web Content
1278401 Sl   Web Content

---
```

# 설명
- `ps` 명령을 통해 WAS 관련 프로세스의 CPU/메모리 사용률 혹은 기동 상태를 점검하여 서비스 정상 동작 여부를 확인합니다.

# 임계치
max_usage_percent: 최대 허용 자원 사용률

# 판단기준
- **양호**: 대상 프로세스의 상태가 정상이고 사용률이 임계치 이하로 유지됨 (기동 상태의 경우 프로세스 존재)
- **경고**: 자원 사용률이 임계치를 초과하거나 좀비(Z)/비정상 상태, 프로세스가 기동되지 않음
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태
