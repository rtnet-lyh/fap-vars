# 영역
네트워크

# 세부 점검항목
CPU사용률

# 점검 내용
Cisco 장비의 CPU사용률 점검

# 구분
필수

# 명령어
```bash
show processes cpu
```

# 출력 결과
```text
[OS: Cisco IOS] 추출된 결과입니다.
C2960X_Service#terminal length 0
C2960X_Service#show processes cpu
CPU utilization for five seconds: 23%/0%; one minute: 23%; five minutes: 23%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
   1          10         168         59  0.00%  0.00%  0.00%   0 Chunk Manager
   2       51673    31201722          1  0.00%  0.00%  0.00%   0 Load Meter
   3           0           1          0  0.00%  0.00%  0.00%   0 LICENSE AGENT
   4           0           1          0  0.00%  0.00%  0.00%   0 Retransmission o
   5           0           1          0  0.00%  0.00%  0.00%   0 IPC ISSU Dispatc
   6   278595236    29042454       9592  0.00%  0.15%  0.12%   0 Check heaps
   7       56023       16277       3441  0.00%  0.00%  0.00%   0 Pool Manager
   8           0           1          0  0.00%  0.00%  0.00%   0 DiscardQ Backgro
   9           0           2          0  0.00%  0.00%  0.00%   0 Timers
  10          30        3681          8  0.00%  0.00%  0.00%   0 WATCH_AFS
  11      194850   624009240          0  0.00%  0.00%  0.00%   0 HUSB Console
  12           0           1          0  0.00%  0.00%  0.00%   0 License Client N
  13    74351468     2598754      28610  0.47%  0.05%  0.00%   0 Licensing Auto U
  14           0           1          0  0.00%  0.00%  0.00%   0 Image License br
  15    26277075   171339271        153  0.00%  0.01%  0.00%   0 ARP Input
  16      105760   162520592          0  0.00%  0.00%  0.00%   0 ARP Background
  17           0           1          0  0.00%  0.00%  0.00%   0 AAA_SERVER_DEADT
  18           0           1          0  0.00%  0.00%  0.00%   0 Policy Manager
  19           4           3       1333  0.00%  0.00%  0.00%   0 Entity MIB API
  20           0           1          0  0.00%  0.00%  0.00%   0 IFS Agent Manage
  21     2175731    31140314         69  0.00%  0.00%  0.00%   0 IPC Event Notifi
  22       22889   152223198          0  0.00%  0.00%  0.00%   0 IPC Mcast Pendin
  23       49249     2598755         18  0.00%  0.00%  0.00%   0 IPC Dynamic Cach
  24           0           1          0  0.00%  0.00%  0.00%   0 IPC Session Serv
  25           0           1          0  0.00%  0.00%  0.00%   0 IPC Zone Manager
  26       25313   152223197          0  0.00%  0.00%  0.00%   0 IPC Periodic Tim
  27       19956   152223196          0  0.00%  0.00%  0.00%   0 IPC Deferred Por
  28           0           1          0  0.00%  0.00%  0.00%   0 IPC Process leve
  29           0           1          0  0.00%  0.00%  0.00%   0 IPC Seat Manager
  30        1313     8914032          0  0.00%  0.00%  0.00%   0 IPC Check Queue
  31           0           1          0  0.00%  0.00%  0.00%   0 IPC Seat RX Cont
  32           0           1          0  0.00%  0.00%  0.00%   0 IPC Seat TX Cont
  33        3699    15600871          0  0.00%  0.00%  0.00%   0 IPC Keep Alive M
  34       12223    31186788          0  0.00%  0.00%  0.00%   0 IPC Loadometer
  35           0           1          0  0.00%  0.00%  0.00%   0 IPC Session Deta
  36        1353          28      48321  0.00%  0.00%  0.00%   0 PrstVbl
  37           0           1          0  0.00%  0.00%  0.00%   0 Crash writer
  38           0           1          0  0.00%  0.00%  0.00%   0 Exception contro
  39         903         253       3569  0.00%  0.00%  0.00%   0 crypto sw pk pro
  40           0           1          0  0.00%  0.00%  0.00%   0 License IPC stat
  41           0           1          0  0.00%  0.00%  0.00%   0 License IPC serv
  42       35971   156008604          0  0.00%  0.00%  0.00%   0 GraphIt
  43           0           1          0  0.00%  0.00%  0.00%   0 client_entity_se
  44           0           2          0  0.00%  0.00%  0.00%   0 SMART
  45           0           2          0  0.00%  0.00%  0.00%   0 XML Proxy Client
  46           0           1          0  0.00%  0.00%  0.00%   0 ARP Snoop
  47           0           1          0  0.00%  0.00%  0.00%   0 Critical Bkgnd
  48     1469212   172535812          8  0.00%  0.00%  0.00%   0 Net Background
  49           0          10          0  0.00%  0.00%  0.00%   0 IDB Work
  50        6475       35080        184  0.00%  0.00%  0.00%   0 Logger
  51       35822   155607959          0  0.00%  0.00%  0.00%   0 TTY Background
  52          26         149        174  0.00%  0.00%  0.00%   0 SXP CORE
  53           0           1          0  0.00%  0.00%  0.00%   0 Cat6k NTI ICC pr
  54           3           5        600  0.00%  0.00%  0.00%   0 IF-MGR control p
  55          37       11487          3  0.00%  0.00%  0.00%   0 IF-MGR event pro
  56           0           1          0  0.00%  0.00%  0.00%   0 ICC Nego
  57      123405     5025047         24  0.00%  0.00%  0.00%   0 Net Input
  58      111490    31201723          3  0.00%  0.00%  0.00%   0 Compute load avg
  59    27219219     2617005      10400  0.00%  0.00%  0.00%   0 Per-minute Jobs
  60      326259   156008696          2  0.00%  0.00%  0.00%   0 Per-Second Jobs
  61           0           1          0  0.00%  0.00%  0.00%   0 Inode Table Dest
  62           0           2          0  0.00%  0.00%  0.00%   0 ACT2 Crypto Engi
  63           0           1          0  0.00%  0.00%  0.00%   0 AggMgr Process
  64         680      353392          1  0.00%  0.00%  0.00%   0 Transport Port A
  65           0           1          0  0.00%  0.00%  0.00%   0 Token Daemon
  66           0           1          0  0.00%  0.00%  0.00%   0 HRPC pppoeia req
  67    18256907    46385684        393  0.00%  0.00%  0.00%   0 HC Counter Timer
  68           0           1          0  0.00%  0.00%  0.00%   0 SFF8472
  69           7           4       1750  0.00%  0.00%  0.00%   0 EEM ED Identity
  70           3           4        750  0.00%  0.00%  0.00%   0 EEM ED MAT
  71        2612       23172        112  0.00%  0.00%  0.00%   0 EEM ED ND
  72          66          11       6000  0.00%  0.00%  0.00%   0 USB Startup
  73           0           2          0  0.00%  0.00%  0.00%   0 APM 86392 RTC
  74      161044  2965516427          0  0.00%  0.00%  0.00%   0 DownWhenLooped
  75           0           1          0  0.00%  0.00%  0.00%   0 HRPC power_mgmt
  76           0           2          0  0.00%  0.00%  0.00%   0 Porter Power Man
  77           0           1          0  0.00%  0.00%  0.00%   0 HRPC lpip reques
  78           0           2          0  0.00%  0.00%  0.00%   0 HLPIP Sync Proce
  79           0           1          0  0.00%  0.00%  0.00%   0 HRPC Multi-FS Sy
  80           0          69          0  0.00%  0.00%  0.00%   0 HULC multifs pro
  81           0           1          0  0.00%  0.00%  0.00%   0 HRPC hnetwpol re
  82           0           1          0  0.00%  0.00%  0.00%   0 HPM FEC LOAD SHA
  83           3           1       3000  0.00%  0.00%  0.00%   0 HRPC EnergyWise
  84           0           1          0  0.00%  0.00%  0.00%   0 HRPC actual powe
  85           0           1          0  0.00%  0.00%  0.00%   0 Notify process
  86           0           1          0  0.00%  0.00%  0.00%   0 HRPC xcvr reques
  87       53821     5197513         10  0.00%  0.00%  0.00%   0 PSP Timer
  88     3700939  2961553016          1  0.00%  0.00%  0.00%   0 RedEarth Tx Mana
  89     7930600  2961627821          2  0.00%  0.00%  0.00%   0 RedEarth Rx Mana
  90        9787    31201722          0  0.00%  0.00%  0.00%   0 HULC Thermal Pro
  91          20       43337          0  0.00%  0.00%  0.00%   0 SSH Event handle
  92           0           1          0  0.00%  0.00%  0.00%   0 HRPC asic-stats
  93           0           1          0  0.00%  0.00%  0.00%   0 HRPC hsm request
  94           0           7          0  0.00%  0.00%  0.00%   0 Stack Mgr
  95          91          13       7000  0.00%  0.00%  0.00%   0 Stack Mgr Notifi
  96         154       75013          2  0.00%  0.00%  0.00%   0 Adjust Regions
  97      134907    77920907          1  0.00%  0.00%  0.00%   0 hrpc -> response
  98           4          61         65  0.00%  0.00%  0.00%   0 hrpc -> request
  99      489567    25987573         18  0.00%  0.00%  0.00%   0 hrpc <- response
 100           0           1          0  0.00%  0.00%  0.00%   0 HRPC hcomp reque
 101     1272800   780038708          1  0.00%  0.00%  0.00%   0 apm86xxx_enet_pr
 102           3          10        300  0.00%  0.00%  0.00%   0 HULC Device Mana
 103           0           3          0  0.00%  0.00%  0.00%   0 HRPC hdm non blo
 104           0           2          0  0.00%  0.00%  0.00%   0 HRPC hdm blockin
 105     2596654    31140297         83  0.00%  0.00%  0.00%   0 HIPC bkgrd proce
 106           0           1          0  0.00%  0.00%  0.00%   0 RTTYS Process
 107           0           1          0  0.00%  0.00%  0.00%   0 HRPC hautosecure
 108         442       23154         19  0.00%  0.00%  0.00%   0 Hulc Port-Securi
 109           0           1          0  0.00%  0.00%  0.00%   0 HRPC hpsecure re
 110           0           1          0  0.00%  0.00%  0.00%   0 HRPC hrcmd reque
 111           7          66        106  0.00%  0.00%  0.00%   0 HRPC emac reques
 112          36          20       1800  0.00%  0.00%  0.00%   0 HULC EMAC Proces
 113           0           3          0  0.00%  0.00%  0.00%   0 HRPC hulc misc r
 114       25738    51947067          0  0.00%  0.00%  0.00%   0 HVLAN main bkgrd
 115           0           2          0  0.00%  0.00%  0.00%   0 HVLAN Mapped Vla
 116           0           2          0  0.00%  0.00%  0.00%   0 Vlan shutdown Pr
 117           0           3          0  0.00%  0.00%  0.00%   0 HRPC vlan reques
 118           0           1          0  0.00%  0.00%  0.00%   0 HULC VLAN REF Ba
 119           0           1          0  0.00%  0.00%  0.00%   0 HRPC ilp request
 120     1485445    10395009        142  0.00%  0.00%  0.00%   0 Strider Tcam Mem
 121           0           1          0  0.00%  0.00%  0.00%   0 HRPC hlfm reques
 122     3258612   152886545         21  0.00%  0.00%  0.00%   0 HLFM address lea
 123       25484   155607963          0  0.00%  0.00%  0.00%   0 HLFM aging proce
 124        9085    39012533          0  0.00%  0.00%  0.00%   0 HLFM address ret
 125           0           1          0  0.00%  0.00%  0.00%   0 HULC PM Vector P
 126           0           1          0  0.00%  0.00%  0.00%   0 HPM Msg Retry Pr
 127        2771       15360        180  0.00%  0.00%  0.00%   0 SpanTree Helper
 128     1401709  1240125616          1  0.00%  0.00%  0.00%   0 hpm main process
 129          35       19298          1  0.00%  0.00%  0.00%   0 HPM Stack Sync P
 130           0           1          0  0.00%  0.00%  0.00%   0 HRPC pm request
 131     2468915   156008602         15  0.00%  0.00%  0.00%   0 hpm counter proc
 132           0           1          0  0.00%  0.00%  0.00%   0 HRPC pm-counters
 133           0           1          0  0.00%  0.00%  0.00%   0 hpm vp events ca
 134          35       74292          0  0.00%  0.00%  0.00%   0 HCEF ADJ Refresh
 135           0           1          0  0.00%  0.00%  0.00%   0 HACL Queue Proce
 136           0           1          0  0.00%  0.00%  0.00%   0 HRPC acl request
 137          15          85        176  0.00%  0.00%  0.00%   0 HACL Acl Manager
 138           0           1          0  0.00%  0.00%  0.00%   0 HRPC aim request
 139           0           1          0  0.00%  0.00%  0.00%   0 HRPC cdp request
 140           0           1          0  0.00%  0.00%  0.00%   0 HULC CISP Proces
 141           0           1          0  0.00%  0.00%  0.00%   0 HRPC dot1x reque
 142           0           1          0  0.00%  0.00%  0.00%   0 Dot1X Msg Retry
 143           0           3          0  0.00%  0.00%  0.00%   0 HULC DOT1X Proce
 144           0           1          0  0.00%  0.00%  0.00%   0 HRPC epm vlan pl
 145           0           1          0  0.00%  0.00%  0.00%   0 HRPC lldp reques
 146           0           1          0  0.00%  0.00%  0.00%   0 HRPC system mtu
 147           0           1          0  0.00%  0.00%  0.00%   0 HRPC rep request
 148           4           3       1333  0.00%  0.00%  0.00%   0 REP Helper Proc
 149           0           1          0  0.00%  0.00%  0.00%   0 HULC REP monitor
 150           0           1          0  0.00%  0.00%  0.00%   0 HRPC sdm request
 151      914045   770904497          1  0.00%  0.00%  0.00%   0 Hulc Storm Contr
 152           0           2          0  0.00%  0.00%  0.00%   0 HSTP Sync Proces
 153           0           1          0  0.00%  0.00%  0.00%   0 HRPC stp_cli req
 154           0           1          0  0.00%  0.00%  0.00%   0 HRPC stp_state_s
 155           0           2          0  0.00%  0.00%  0.00%   0 S/W Bridge Proce
 156           0           1          0  0.00%  0.00%  0.00%   0 HRPC hudld reque
 157           0           1          0  0.00%  0.00%  0.00%   0 HRPC vqpc reques
 158           0           1          0  0.00%  0.00%  0.00%   0 HRPC hled reques
 159   404904742  3875654324        104  7.55%  7.47%  7.48%   0 Hulc LED Process
 160      152980   114332770          1  0.00%  0.00%  0.00%   0 HL3U bkgrd proce
 161           0           1          0  0.00%  0.00%  0.00%   0 HRPC hl3u reques
 162        1108         561       1975  0.53%  0.16%  0.16%   1 SSH Process
 163           0           1          0  0.00%  0.00%  0.00%   0 HRPC dtp request
 164           0           1          0  0.00%  0.00%  0.00%   0 HRPC show_forwar
 165           0           1          0  0.00%  0.00%  0.00%   0 HRPC snmp reques
 166           0           1          0  0.00%  0.00%  0.00%   0 HULC SNMP Proces
 167   220395719    31140308       7077  0.17%  0.12%  0.12%   0 HQM Stack Proces
 168    60215104    62280596        966  0.00%  0.03%  0.01%   0 HRPC qos request
 169           0           1          0  0.00%  0.00%  0.00%   0 HRPC span reques
 170           0           3          0  0.00%  0.00%  0.00%   0 HRPC system post
 171           0           1          0  0.00%  0.00%  0.00%   0 Hulc Reload Mana
 172           0           1          0  0.00%  0.00%  0.00%   0 Hulc Blue Beacon
 173           0           1          0  0.00%  0.00%  0.00%   0 HRPC hrcli-event
 174        9145      520120         17  0.00%  0.00%  0.00%   0 OBFL TEMP obfl0
 175           0           2          0  0.00%  0.00%  0.00%   0 image mgr
 176           0           1          0  0.00%  0.00%  0.00%   0 HRFS OIR Proc
 177       23267    52002869          0  0.00%  0.00%  0.00%   0 Power RPS Proces
 178           3           5        600  0.00%  0.00%  0.00%   0 HL2MCM
 179           0           5          0  0.00%  0.00%  0.00%   0 HL2MCM
 181           0         266          0  0.00%  0.00%  0.00%   0 AAA Server
 182           0           1          0  0.00%  0.00%  0.00%   0 AAA ACCT Proc
 183           0           1          0  0.00%  0.00%  0.00%   0 ACCT Periodic Pr
 184           0           1          0  0.00%  0.00%  0.00%   0 Webauth client
 185           0           1          0  0.00%  0.00%  0.00%   0 Auth-proxy HTTP
 186           0           1          0  0.00%  0.00%  0.00%   0 IP Admin SM Proc
 187           0           1          0  0.00%  0.00%  0.00%   0 hci usb process
 188          28           3       9333  0.00%  0.00%  0.00%   0 OBFL MSG obfl0
 189          35           5       7000  0.00%  0.00%  0.00%   0 OBFL ENV obfl0
 190           0           1          0  0.00%  0.00%  0.00%   0 HRPC hl2mcm igmp
 191           0           2          0  0.00%  0.00%  0.00%   0 AAA Dictionary R
 192         842     1300072          0  0.00%  0.00%  0.00%   0 DHCP Snooping
 193           0           1          0  0.00%  0.00%  0.00%   0 DHCP Snooping db
 194           0           2          0  0.00%  0.00%  0.00%   0 Dot1x Mgr Proces
 195           0           1          0  0.00%  0.00%  0.00%   0 EAP Framework
 196           0           1          0  0.00%  0.00%  0.00%   0 EAP Test
 197           4           1       4000  0.00%  0.00%  0.00%   0 TRACK Main threa
 198           0           1          0  0.00%  0.00%  0.00%   0 TRACK Client thr
 199           0           2          0  0.00%  0.00%  0.00%   0 CEF switching ba
 200         525         668        785  0.00%  0.00%  0.00%   0 IP ARP Adjacency
 201     1484417   152886611          9  0.00%  0.00%  0.00%   0 IP ARP Retry Age
 202    32207738   308382727        104  0.17%  0.05%  0.01%   0 IP Input
 203           0           1          0  0.00%  0.00%  0.00%   0 ICMP event handl
 204       50455   303022973          0  0.00%  0.00%  0.00%   0 IP ARP Track
 205           0           1          0  0.00%  0.00%  0.00%   0 ADJ NSF process
 206           0           1          0  0.00%  0.00%  0.00%   0 IPv6 ping proces
 207        9546   155612227          0  0.00%  0.00%  0.00%   0 loopdetect
 209           0           2          0  0.00%  0.00%  0.00%   0 REP Topology cha
 210           0           2          0  0.00%  0.00%  0.00%   0 RIB LM VALIDATE
 211    27346529   233608780        117  0.00%  0.00%  0.00%   0 Spanning Tree
 212          20        7667          2  0.00%  0.00%  0.00%   0 SpanTree Msg
 213         757     2600057          0  0.00%  0.00%  0.00%   0 Spanning Tree St
 214         100       11576          8  0.00%  0.00%  0.00%   0 802.1x switch
 215       28850      216026        133  0.00%  0.00%  0.00%   0 DTP Protocol
 216           0           1          0  0.00%  0.00%  0.00%   0 HRPC power down
 217           3           1       3000  0.00%  0.00%  0.00%   0 HRPC ip device t
 218       35801   155607968          0  0.00%  0.00%  0.00%   0 HULC Open flow S
 219           0           1          0  0.00%  0.00%  0.00%   0 HRPC ofsdn reque
 220      188817    10395628         18  0.00%  0.00%  0.00%   0 OBFL I/O Buffer
 221       63105   155607962          0  0.00%  0.00%  0.00%   0 PI MATM Aging Pr
 222      334408  1559984392          0  0.00%  0.00%  0.00%   0 UDLD
 223        1100     5200287          0  0.00%  0.00%  0.00%   0 Port-Security
 224           0           2          0  0.00%  0.00%  0.00%   0 IP Host Track Pr
 225       24383     2598754          9  0.00%  0.00%  0.00%   0 MMN bkgrd proces
 226       26607    15592516          1  0.00%  0.00%  0.00%   0 Ethchnl
 227         428       13514         31  0.00%  0.00%  0.00%   0 VMATM Callback
 228           0           1          0  0.00%  0.00%  0.00%   0 XDR background p
 229      104296     2598754         40  0.00%  0.00%  0.00%   0 XDR mcast
 230           0           1          0  0.00%  0.00%  0.00%   0 XDR RP Ping Back
 231           0           1          0  0.00%  0.00%  0.00%   0 XDR receive
 232           0           1          0  0.00%  0.00%  0.00%   0 IPC LC Message H
 233           0           1          0  0.00%  0.00%  0.00%   0 XDR RP Test Back
 234       29181     2598754         11  0.00%  0.00%  0.00%   0 FRR Background P
 235      516339    11489362         44  0.00%  0.00%  0.00%   0 CEF background p
 236           0           1          0  0.00%  0.00%  0.00%   0 fib_fib_bfd_sb e
 237           0           1          0  0.00%  0.00%  0.00%   0 IP IRDP
 238           0           1          0  0.00%  0.00%  0.00%   0 CEF RF HULC Conv
 239           0           1          0  0.00%  0.00%  0.00%   0 Tunnel FIB
 240       50367    77869574          0  0.00%  0.00%  0.00%   0 CEF: IPv4 proces
 241      164240   155452024          1  0.00%  0.00%  0.00%   0 ADJ background
 242           0           1          0  0.00%  0.00%  0.00%   0 AAA System Acct
 243           0           2          0  0.00%  0.00%  0.00%   0 Routing Topology
 244           0           2          0  0.00%  0.00%  0.00%   0 IP RIB Update
 245    15311067       86661     176679  0.00%  0.00%  0.00%   0 NIST rng proc
 246       56865   303022973          0  0.00%  0.00%  0.00%   0 Timer Library
 247           0           1          0  0.00%  0.00%  0.00%   0 IPv6 RIB Event H
 248        1387       11577        119  0.00%  0.00%  0.00%   0 Auth Manager
 249           0           1          0  0.00%  0.00%  0.00%   0 EPM MAIN PROCESS
 250           0           1          0  0.00%  0.00%  0.00%   0 Critical Auth
 251      115952   310988821          0  0.00%  0.00%  0.00%   0 SVM UT Process
 252           0           1          0  0.00%  0.00%  0.00%   0 CMD HANDLER
 253           0           1          0  0.00%  0.00%  0.00%   0 Socket Timers
 254           0           2          0  0.00%  0.00%  0.00%   0 Dot1x Supplicant
 255           0           2          0  0.00%  0.00%  0.00%   0 Dot1x Supplicant
 256           0           2          0  0.00%  0.00%  0.00%   0 Dot1x Supplicant
 257           0           1          0  0.00%  0.00%  0.00%   0 DSensor HTTP
 258           0           1          0  0.00%  0.00%  0.00%   0 EPM Downlad Mana
 259     2623624    31140317         84  0.00%  0.00%  0.00%   0 EPM ACL PLUG-IN
 261           0           1          0  0.00%  0.00%  0.00%   0 Timer Handler Pr
 262           0           1          0  0.00%  0.00%  0.00%   0 HTTP EPM Redirec
 263           0           1          0  0.00%  0.00%  0.00%   0 CEF RP Backgroun
 264          14        1239         11  0.00%  0.00%  0.00%   0 TCP Timer
 265       33154      392513         84  0.00%  0.00%  0.00%   0 TCP Protocols
 266         169      520030          0  0.00%  0.00%  0.00%   0 HTTP CORE
 267           0           1          0  0.00%  0.00%  0.00%   0 DCT Bkgd Process
 268           0           2          0  0.00%  0.00%  0.00%   0 Tunnel
 269           0           1          0  0.00%  0.00%  0.00%   0 RARP Input
 270           0           3          0  0.00%  0.00%  0.00%   0 static
 271           0           2          0  0.00%  0.00%  0.00%   0 ADJ resolve proc
 272           0           1          0  0.00%  0.00%  0.00%   0 IPv6 Static Hand
 273           0           1          0  0.00%  0.00%  0.00%   0 MAB Framework
 274      199757    15592511         12  0.00%  0.00%  0.00%   0 QoS stats proces
 276           0           2          0  0.00%  0.00%  0.00%   0 REP LSL Proc
 277           0           2          0  0.00%  0.00%  0.00%   0 REP BPA/EPA Proc
 278           0           5          0  0.00%  0.00%  0.00%   0 SNMP Timers
 279           0           1          0  0.00%  0.00%  0.00%   0 HRPC dhcp snoopi
 280           0           4          0  0.00%  0.00%  0.00%   0 HULC DHCP Snoopi
 281        1851       24121         76  0.00%  0.00%  0.00%   0 IGMPSN L2MCM
 282           0           1          0  0.00%  0.00%  0.00%   0 IGMPSN MRD
 283           0          15          0  0.00%  0.00%  0.00%   0 IGMPSN
 284           0           1          0  0.00%  0.00%  0.00%   0 IGMPQR
 285           0           2          0  0.00%  0.00%  0.00%   0 AUTO LAG Protoco
 286        1548       24120         64  0.00%  0.00%  0.00%   0 MLDSN L2MCM
 287           0           1          0  0.00%  0.00%  0.00%   0 MRD
 288           0           1          0  0.00%  0.00%  0.00%   0 MLD_SNOOP
 289           0           2          0  0.00%  0.00%  0.00%   0 AAA Cached Serve
 290           0           1          0  0.00%  0.00%  0.00%   0 HRPC hl2mcm mlds
 291           0           2          0  0.00%  0.00%  0.00%   0 ENABLE AAA
 292           0           3          0  0.00%  0.00%  0.00%   0 LDAP process
 293           0           2          0  0.00%  0.00%  0.00%   0 Crypto Support
 294           0           1          0  0.00%  0.00%  0.00%   0 IPSECv6 PS Proc
 295           0           2          0  0.00%  0.00%  0.00%   0 LINE AAA
 296          36         267        134  0.00%  0.00%  0.00%   0 LOCAL AAA
 298           0           2          0  0.00%  0.00%  0.00%   0 TPLUS
 299           3           3       1000  0.00%  0.00%  0.00%   0 Collection proce
 300           0           1          0  0.00%  0.00%  0.00%   0 hulc cfg mgr mas
 301          59          14       4214  0.00%  0.00%  0.00%   0 crypto engine pr
 302           0           1          0  0.00%  0.00%  0.00%   0 RSA background p
 303         164       27167          6  0.00%  0.00%  0.00%   0 Crypto CA
 304           0           3          0  0.00%  0.00%  0.00%   0 Crypto PKI-CRL
 305           0           1          0  0.00%  0.00%  0.00%   0 Crypto PKI-Rev-P
 306           0           1          0  0.00%  0.00%  0.00%   0 PKI OCSP
 307           0           1          0  0.00%  0.00%  0.00%   0 PKI Revocation
 308      103891   162284830          0  0.00%  0.00%  0.00%   0 Crypto IKEv2
 309           0           1          0  0.00%  0.00%  0.00%   0 IKEv2 AAA handle
 310           0           1          0  0.00%  0.00%  0.00%   0 tHUB
 311           0           1          0  0.00%  0.00%  0.00%   0 encrypt proc
 312           0           3          0  0.00%  0.00%  0.00%   0 CRYPTO MAP FREE
 313           0           1          0  0.00%  0.00%  0.00%   0 Crypto INT
 314           0           3          0  0.00%  0.00%  0.00%   0 Crypto IKE Dispa
 315           0           3          0  0.00%  0.00%  0.00%   0 Crypto IKMP
 316           0           1          0  0.00%  0.00%  0.00%   0 IPSEC manual key
 317       53291     7796260          6  0.00%  0.00%  0.00%   0 IPSEC key engine
 318           0           1          0  0.00%  0.00%  0.00%   0 Crypto ACL
 319           0           1          0  0.00%  0.00%  0.00%   0 Crypto PAS Proc
 320           0           1          0  0.00%  0.00%  0.00%   0 IPSec background
 321           0           1          0  0.00%  0.00%  0.00%   0 HRPC x_setup req
 322           0           2          0  0.00%  0.00%  0.00%   0 REP Switch Helpe
 323           0           1          0  0.00%  0.00%  0.00%   0 Licensing MIB pr
 324           0          10          0  0.00%  0.00%  0.00%   0 VTP Trap Process
 326        1151       11803         97  0.00%  0.00%  0.00%   0 ASP Process Crea
 327          12         117        102  0.00%  0.00%  0.00%   0 AAA SEND STOP EV
 328           0           1          0  0.00%  0.00%  0.00%   0 Test AAA Client
 329           0           7          0  0.00%  0.00%  0.00%   0 DCM Core Thread
 330           0           1          0  0.00%  0.00%  0.00%   0 dcm_cli_engine
 331           0           3          0  0.00%  0.00%  0.00%   0 dcm_cli_provider
 332           0           4          0  0.00%  0.00%  0.00%   0 EEM ED Routing
 333         207       25964          7  0.00%  0.00%  0.00%   0 EEM ED Syslog
 334       10635       11596        917  0.00%  0.00%  0.00%   0 Syslog Traps
 335          90       17640          5  0.00%  0.00%  0.00%   0 FEX Logger Proce
 336           0           1          0  0.00%  0.00%  0.00%   0 HCD Process
 337           0           1          0  0.00%  0.00%  0.00%   0 HRPC cable diagn
 338           0           1          0  0.00%  0.00%  0.00%   0 HRPC archive_dnl
 339           0           2          0  0.00%  0.00%  0.00%   0 DiagCard1/-1
 340       53901   128546014          0  0.00%  0.00%  0.00%   0 PM Callback
 341           0          48          0  0.00%  0.00%  0.00%   0 hulc running con
 342        6574    12477335          0  0.00%  0.00%  0.00%   0 dhcp snooping sw
 343           0           1          0  0.00%  0.00%  0.00%   0 ONEP_DPSS_SERVIC
 344           0           1          0  0.00%  0.00%  0.00%   0 HRPC onep reques
 346           7          18        388  0.00%  0.00%  0.00%   0 EEM Server
 347      113998    15592556          7  0.00%  0.00%  0.00%   0 Bulkstat-Client
 348           4           6        666  0.00%  0.00%  0.00%   0 DCM snmp dp Thre
 349           0           3          0  0.00%  0.00%  0.00%   0 snmp dcm ma shim
 350           4           3       1333  0.00%  0.00%  0.00%   0 EEM Policy Direc
 352           6           4       1500  0.00%  0.00%  0.00%   0 EEM ED OIR
 353        3063     2601924          1  0.00%  0.00%  0.00%   0 EEM ED Timer
 354        5503       16092        341  0.00%  0.00%  0.00%   0 Syslog
 355           7          68        102  0.00%  0.00%  0.00%   0 PnP-Monitor
 357           3           4        750  0.00%  0.00%  0.00%   0 RBM CORE
 358           0           1          0  0.00%  0.00%  0.00%   0 HRPC eee request
 359      104230     2598754         40  0.00%  0.00%  0.00%   0 hulc_eee_monitor
 360           0           2          0  0.00%  0.00%  0.00%   0 STP FAST TRANSIT
 361           0           2          0  0.00%  0.00%  0.00%   0 CSRT RAPID TRANS
 362          11           3       3666  0.00%  0.00%  0.00%   0 VLAN Manager
 363           0           5          0  0.00%  0.00%  0.00%   0 EEM Helper Threa
 365       35455      659680         53  0.00%  0.00%  0.00%   0 IP SNMP
 366       31270      318285         98  0.00%  0.00%  0.00%   0 PDU DISPATCHER
 367       46531      318285        146  0.00%  0.00%  0.00%   0 SNMP ENGINE
 368           0           2          0  0.00%  0.00%  0.00%   0 IP SNMPV6
 369  2817674368    51056179      55188  0.00%  1.03%  1.44%   0 Snmp Flash Cache
 370           0           1          0  0.00%  0.00%  0.00%   0 SNMP ConfCopyPro
 371      192869      329761        584  0.00%  0.00%  0.00%   0 SNMP Traps
 373      268818   157239005          1  0.00%  0.00%  0.00%   0 NTP
```

# 설명
- `show processes cpu` 명령을 통해 장비의 CPU 사용률을 확인하여 비정상적인 과부하가 없는지 점검합니다.

# 임계치
CPU 사용률 80% 미만

# 판단기준
- **양호**: 최근 5분, 1분 간의 CPU 사용률이 임계치 미만으로 안정적임
- **경고**: CPU 사용률이 임계치를 초과하여 패킷 처리 지연 및 서비스 장애 우려
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태
