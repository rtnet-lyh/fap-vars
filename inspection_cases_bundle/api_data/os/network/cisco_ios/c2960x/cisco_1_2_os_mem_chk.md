# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

cisco_ios

# application

c2960x

# inspection_code

NETWORK-CISCO-IOS-C2960X-MEMORY-01

# is_required

필수

# inspection_name

메모리 사용률

# inspection_content

Cisco 장비의 메모리 사용률 점검

# inspection_command

```bash
show processes memory
```

# inspection_output

```text
[OS: Cisco IOS] 추출된 결과입니다.
C2960X_Service#terminal length 0
C2960X_Service#show processes memory
Processor Pool Total:   97691252 Used:   40244996 Free:   57446256
      I/O Pool Total:   33554432 Used:    6897976 Free:   26656456
Driver te Pool Total:    1048576 Used:         40 Free:    1048536

 PID TTY  Allocated      Freed    Holding    Getbufs    Retbufs Process
   0   0   65060500   25123900   36119084          0          0 *Init*
   0   0      12112    7935676      12112          0          0 *Sched*
   0   0  742780776  739897496    2991468    7349151     949166 *Dead*
   0   0          0          0     394800          0          0 *MallocLite*
   1   0     405188     137244     275112          0          0 Chunk Manager
   2   0        232        232       4168          0          0 Load Meter
   3   0      19068          0      44108          0          0 LICENSE AGENT
   4   0          0          0       7168          0          0 Retransmission o
   5   0          0          0       7168          0          0 IPC ISSU Dispatc
   6   0       4652       4288      11640          0          0 Check heaps
   7   0  418005040  419823768      33104  375820908  376556859 Pool Manager
   8   0          0          0       7168          0          0 DiscardQ Backgro
   9   0        232        232       7168          0          0 Timers
  10   0          0          0       4168          0          0 WATCH_AFS
  11   0          0          0       7168          0          0 HUSB Console
  12   0          0          0       7168          0          0 License Client N
  13   0 1695420092 1695421152       7168          0          0 Licensing Auto U
  14   0          0          0       7168          0          0 Image License br
  15   0 2481780364 2481760320      27212          0          0 ARP Input
  16   0      25184      25184       7168          0          0 ARP Background
  17   0          0          0       7168          0          0 AAA_SERVER_DEADT
  18   0          0          0      13168          0          0 Policy Manager
  19   0      23456       5696      24928          0          0 Entity MIB API
  20   0          0          0       7168          0          0 IFS Agent Manage
  21   0          0          0       7168          0          0 IPC Event Notifi
  22   0          0          0       7168          0          0 IPC Mcast Pendin
  23   0          0          0       7168          0          0 IPC Dynamic Cach
  24   0          0          0       7168          0          0 IPC Session Serv
  25   0          0          0       7168          0          0 IPC Zone Manager
  26   0          0          0       7168          0          0 IPC Periodic Tim
  27   0          0          0       7168          0          0 IPC Deferred Por
  28   0          0          0       7168          0          0 IPC Process leve
  29   0       2088          0       9256          0          0 IPC Seat Manager
  30   0          0          0       7168          0          0 IPC Check Queue
  31   0          0          0       7168          0          0 IPC Seat RX Cont
  32   0          0          0       7168          0          0 IPC Seat TX Cont
  33   0          0          0       7168          0          0 IPC Keep Alive M
  34   0          0          0       7168          0          0 IPC Loadometer
  35   0          0          0       7168          0          0 IPC Session Deta
  36   0     533492     533492       7168          0          0 PrstVbl
  37   0          0          0      25168          0          0 Crash writer
  38   0        340          0       7508          0          0 Exception contro
  39   0     361468     469592       7704          0          0 crypto sw pk pro
  40   0          0          0      13168          0          0 License IPC stat
  41   0          0          0      13168          0          0 License IPC serv
  42   0        232        232       7168          0          0 GraphIt
  43   0          0          0       7168          0          0 client_entity_se
  44   0        232        232       7168          0          0 SMART
  45   0        232        232      13168          0          0 XML Proxy Client
  46   0          0          0       7168          0          0 ARP Snoop
  47   0          0          0       7168          0          0 Critical Bkgnd
  48   0   46105580    4602972      23392          0          0 Net Background
  49   0       2092       2092      13168          0          0 IDB Work
  50   0    2873316    2730276      13168      81216          0 Logger
  51   0      76544       2900       7168          0          0 TTY Background
  52   0        788      27664      13724          0          0 SXP CORE
  53   0          0          0       7168          0          0 Cat6k NTI ICC pr
  54   0     106820      84592      69440          0          0 IF-MGR control p
  55   0          0          0       7168          0          0 IF-MGR event pro
  56   0          0          0       7168          0          0 ICC Nego
  57   0          0          0       7168          0          0 Net Input
  58   0        232        232       7208          0          0 Compute load avg
  59   0          0        572       7168          0          0 Per-minute Jobs
  60   0      48460      28704      27028          0          0 Per-Second Jobs
  61   0          0          0       4168          0          0 Inode Table Dest
  62   0          0          0      13168          0          0 ACT2 Crypto Engi
  63   0          0          0       7168          0          0 AggMgr Process
  64   0          0    9509436       7168          0          0 Transport Port A
  65   0          0          0       7168          0          0 Token Daemon
  66   0          0          0       7168          0          0 HRPC pppoeia req
  67   0          0          0       7168          0          0 HC Counter Timer
  68   0          0          0       7168          0          0 SFF8472
  69   0     369796       6964     372904          0          0 EEM ED Identity
  70   0      12180       5164      17184          0          0 EEM ED MAT
  71   0      44124   28060200      48728          0          0 EEM ED ND
  72   0     224352        232     206120          0          0 USB Startup
  73   0        232        232       7168          0          0 APM 86392 RTC
  74   0        232        232       7168          0          0 DownWhenLooped
  75   0          0          0       7168          0          0 HRPC power_mgmt
  76   0       5276        232      12212          0          0 Porter Power Man
  77   0          0          0       7168          0          0 HRPC lpip reques
  78   0        232        232       7168          0          0 HLPIP Sync Proce
  79   0          0          0       7168          0          0 HRPC Multi-FS Sy
  80   0          0          0       7168          0          0 HULC multifs pro
  81   0          0          0       7168          0          0 HRPC hnetwpol re
  82   0          0          0       7168          0          0 HPM FEC LOAD SHA
  83   0          0          0       7168          0          0 HRPC EnergyWise
  84   0          0          0       7168          0          0 HRPC actual powe
  85   0          0          0      13168          0          0 Notify process
  86   0          0          0       7168          0          0 HRPC xcvr reques
  87   0          0          0       7168          0          0 PSP Timer
  88   0     342732     341208       7168          0          0 RedEarth Tx Mana
  89   0     252284     342760       7168          0          0 RedEarth Rx Mana
  90   0      66044        232       7168          0          0 HULC Thermal Pro
  91   0       8500         76      15460          0          0 SSH Event handle
  92   0          0          0       7168          0          0 HRPC asic-stats
  93   0          0          0       4168          0          0 HRPC hsm request
  94   0       5044          0      18212          0          0 Stack Mgr
  95   0     521108     142020     341872          0          0 Stack Mgr Notifi
  96   0      29356      29356      10168          0          0 Adjust Regions
  97   0          0          0       7168          0          0 hrpc -> response
  98   0          0          0       7168          0          0 hrpc -> request
  99   0       6192  818068004      12212          0          0 hrpc <- response
 100   0          0          0       7168          0          0 HRPC hcomp reque
 101   0        232        232       7168          0          0 apm86xxx_enet_pr
 102   0        768        232       7168          0          0 HULC Device Mana
 103   0         72         72       7168          0          0 HRPC hdm non blo
 104   0        176        176       7168          0          0 HRPC hdm blockin
 105   0          0          0      13168          0          0 HIPC bkgrd proce
 106   0          0          0       7168          0          0 RTTYS Process
 107   0          0          0       7168          0          0 HRPC hautosecure
 108   0        232        232       7168          0          0 Hulc Port-Securi
 109   0          0          0       7168          0          0 HRPC hpsecure re
 110   0          0          0      13168          0          0 HRPC hrcmd reque
 111   0          0          0       7168          0          0 HRPC emac reques
 112   0     127108          0     102956      53760          0 HULC EMAC Proces
 113   0          0          0       7168          0          0 HRPC hulc misc r
 114   0          0          0      13168          0          0 HVLAN main bkgrd
 115   0        232        232       7168          0          0 HVLAN Mapped Vla
 116   0        232        232       7168          0          0 Vlan shutdown Pr
 117   0          0          0      13168          0          0 HRPC vlan reques
 118   0          0          0       7168          0          0 HULC VLAN REF Ba
 119   0          0          0       7168          0          0 HRPC ilp request
 120   0          0          0       7168          0          0 Strider Tcam Mem
 121   0          0          0       7168          0          0 HRPC hlfm reques
 122   0        232        232       7168          0          0 HLFM address lea
 123   0        232        232       7168          0          0 HLFM aging proce
 124   0        232        232       7168          0          0 HLFM address ret
 125   0          0          0       7168          0          0 HULC PM Vector P
 126   0          0          0       7168          0          0 HPM Msg Retry Pr
 127   0   16254400   19412524      25488          0          0 SpanTree Helper
 128   0  119147100   97107656     157808          0          0 hpm main process
 129   0        232        232       7168          0          0 HPM Stack Sync P
 130   0          0          0      25168          0          0 HRPC pm request
 131   0        232        232       7168          0          0 hpm counter proc
 132   0          0          0       7216          0          0 HRPC pm-counters
 133   0          0          0       7168          0          0 hpm vp events ca
 134   0          0          0      13168          0          0 HCEF ADJ Refresh
 135   0          0          0       7168          0          0 HACL Queue Proce
 136   0          0          0       7168          0          0 HRPC acl request
 137   0        232      13356      61168          0          0 HACL Acl Manager
 138   0          0          0       7168          0          0 HRPC aim request
 139   0          0          0       7168          0          0 HRPC cdp request
 140   0          0          0       7168          0          0 HULC CISP Proces
 141   0          0          0       7168          0          0 HRPC dot1x reque
 142   0          0          0       7168          0          0 Dot1X Msg Retry
 143   0          0          0      13168          0          0 HULC DOT1X Proce
 144   0          0          0       7168          0          0 HRPC epm vlan pl
 145   0          0          0       7168          0          0 HRPC lldp reques
 146   0          0          0       4168          0          0 HRPC system mtu
 147   0          0          0       7168          0          0 HRPC rep request
 148   0      65812        232      72748          0          0 REP Helper Proc
 149   0          0          0       7168          0          0 HULC REP monitor
 150   0          0          0       7168          0          0 HRPC sdm request
 151   0        232        232       7168          0          0 Hulc Storm Contr
 152   0        232        232       7168          0          0 HSTP Sync Proces
 153   0          0          0       7168          0          0 HRPC stp_cli req
 154   0          0          0       7168          0          0 HRPC stp_state_s
 155   0        232        232       7168          0          0 S/W Bridge Proce
 156   0          0          0       7168          0          0 HRPC hudld reque
 157   0          0          0       7168          0          0 HRPC vqpc reques
 158   0          0          0       7168          0          0 HRPC hled reques
 159   0        232        232      10168          0          0 Hulc LED Process
 160   0          0          0      13168          0          0 HL3U bkgrd proce
 161   0          0          0       7212          0          0 HRPC hl3u reques
 162   1    4424644    4329548     107200       4536          0 SSH Process
 163   0          0          0       7168          0          0 HRPC dtp request
 164   0          0          0       7168          0          0 HRPC show_forwar
 165   0          0          0       7168          0          0 HRPC snmp reques
 166   0          0          0       7168          0          0 HULC SNMP Proces
 167   0 2734270376 1916141432      20220      35532          0 HQM Stack Proces
 168   0 4105675728 4105657848      61168      10152          0 HRPC qos request
 169   0          0          0       7168          0          0 HRPC span reques
 170   0        540        540       7168          0          0 HRPC system post
 171   0          0          0       7168          0          0 Hulc Reload Mana
 172   0          0          0       7168          0          0 Hulc Blue Beacon
 173   0          0          0       7168          0          0 HRPC hrcli-event
 174   0   41186592   41176644      15948          0          0 OBFL TEMP obfl0
 175   0        232        232      10168          0          0 image mgr
 176   0          0          0       7168          0          0 HRFS OIR Proc
 177   0        232        232       7168          0          0 Power RPS Proces
 178   0       8184       5776       8184          0          0 HL2MCM
 179   0      13024       5740      13024          0          0 HL2MCM
 181   0      16816        232      23752          0          0 AAA Server
 182   0          0          0       7168          0          0 AAA ACCT Proc
 183   0      49352          0      56520          0          0 ACCT Periodic Pr
 184   0          0          0       7168          0          0 Webauth client
 185   0        888          0       8056          0          0 Auth-proxy HTTP
 186   0          0          0       7168          0          0 IP Admin SM Proc
 187   0       5044          0      12212          0          0 hci usb process
 188   0      14200      12380      14860          0          0 OBFL MSG obfl0
 189   0      10600        392      20248          0          0 OBFL ENV obfl0
 190   0          0          0       7168          0          0 HRPC hl2mcm igmp
 191   0        232        232       7168          0          0 AAA Dictionary R
 192   0          0          0       7168          0          0 DHCP Snooping
 193   0          0          0       7168          0          0 DHCP Snooping db
 194   0        232        232       7168          0          0 Dot1x Mgr Proces
 195   0          0          0       7168          0          0 EAP Framework
 196   0          0          0       7168          0          0 EAP Test
 197   0       1896          0       9064          0          0 TRACK Main threa
 198   0       1680          0       8848          0          0 TRACK Client thr
 199   0        216          0      13384          0          0 CEF switching ba
 200   0       2720          0      15888          0          0 IP ARP Adjacency
 201   0      33012          0      40180          0          0 IP ARP Retry Age
 202   0 1093181784     315588      15020       1560          0 IP Input
 203   0          0          0       7168          0          0 ICMP event handl
 204   0        232        232      10168          0          0 IP ARP Track
 205   0        216          0       4384          0          0 ADJ NSF process
 206   0          0          0       7168          0          0 IPv6 ping proces
 207   0        448        232       7384          0          0 loopdetect
 209   0        232        232       7168          0          0 REP Topology cha
 210   0          0          0       7168          0          0 RIB LM VALIDATE
 211   0   11779088        232       7384          0          0 Spanning Tree
 212   0        232        232       7168          0          0 SpanTree Msg
 213   0          0          0       7168          0          0 Spanning Tree St
 214   0          0          0       7168          0          0 802.1x switch
 215   0        928        232       7864          0          0 DTP Protocol
 216   0          0          0       7168          0          0 HRPC power down
 217   0          0          0       7168          0          0 HRPC ip device t
 218   0          0          0       7168          0          0 HULC Open flow S
 219   0          0          0       7168          0          0 HRPC ofsdn reque
 220   0          0          0       7040          0          0 OBFL I/O Buffer
 221   0        232        232       7168          0          0 PI MATM Aging Pr
 222   0        532        232       7468          0          0 UDLD
 223   0        216          0       7384          0          0 Port-Security
 224   0        232        232      10168          0          0 IP Host Track Pr
 225   0          0          0       7168          0          0 MMN bkgrd proces
 226   0        232        232       7168          0          0 Ethchnl
 227   0          0     727908       7168          0          0 VMATM Callback
 228   0        216          0       7384          0          0 XDR background p
 229   0          0          0       7168          0          0 XDR mcast
 230   0          0          0       7168          0          0 XDR RP Ping Back
 231   0          0          0      13168          0          0 XDR receive
 232   0          0          0       7168          0          0 IPC LC Message H
 233   0          0          0       7168          0          0 XDR RP Test Back
 234   0          0          0       7168          0          0 FRR Background P
 235   0        316       1420      13384          0          0 CEF background p
 236   0        216          0      13428          0          0 fib_fib_bfd_sb e
 237   0          0          0      10168          0          0 IP IRDP
 238   0          0          0       7168          0          0 CEF RF HULC Conv
 239   0        216          0      10384          0          0 Tunnel FIB
 240   0      34080       4040      29952          0          0 CEF: IPv4 proces
 241   0        216          0      13384          0          0 ADJ background
 242   0       7168          0      14336          0          0 AAA System Acct
 243   0          0          0      13168          0          0 Routing Topology
 244   0        216          0      13384          0          0 IP RIB Update
 245   0 1222539556 1222539556       7184          0          0 NIST rng proc
 246   0      49584        232      56520          0          0 Timer Library
 247   0          0          0      10168          0          0 IPv6 RIB Event H
 248   0        232        232      13168          0          0 Auth Manager
 249   0          0          0      13168          0          0 EPM MAIN PROCESS
 250   0          0          0       7168          0          0 Critical Auth
 251   0          0          0       7168          0          0 SVM UT Process
 252   0          0          0       7168          0          0 CMD HANDLER
 253   0          0          0       7168          0          0 Socket Timers
 254   0        448        232       7384          0          0 Dot1x Supplicant
 255   0        448        232       7384          0          0 Dot1x Supplicant
 256   0        448        232       7384          0          0 Dot1x Supplicant
 257   0          0          0       7168          0          0 DSensor HTTP
 258   0          0          0       7168          0          0 EPM Downlad Mana
 259   0       2888        612      16056          0          0 EPM ACL PLUG-IN
 261   0          0          0       7168          0          0 Timer Handler Pr
 262   0        888          0      14056          0          0 HTTP EPM Redirec
 263   0        216          0       7384          0          0 CEF RP Backgroun
 264   0          0      44448      13168          0          0 TCP Timer
 265   0    8675860 1082592156      15184          0          0 TCP Protocols
 266   0      13668      12352      11148          0          0 HTTP CORE
 267   0          0          0       7168          0          0 DCT Bkgd Process
 268   0        232        232      13168          0          0 Tunnel
 269   0          0          0       7168          0          0 RARP Input
 270   0        232        232      10168          0          0 static
 271   0        216          0      13384          0          0 ADJ resolve proc
 272   0          0          0      10168          0          0 IPv6 Static Hand
 273   0          0          0       7168          0          0 MAB Framework
 274   0 1493198340 1493198340      10168          0          0 QoS stats proces
 276   0        232        232       7168          0          0 REP LSL Proc
 277   0       7804        232      14740          0          0 REP BPA/EPA Proc
 278   0          0          0       7196          0          0 SNMP Timers
 279   0          0          0       7168          0          0 HRPC dhcp snoopi
 280   0          0          0       7168          0          0 HULC DHCP Snoopi
 281   0    6579152   20474452      11468          0          0 IGMPSN L2MCM
 282   0          0          0       7168          0          0 IGMPSN MRD
 283   0          0          0      10168          0          0 IGMPSN
 284   0          0          0       7168          0          0 IGMPQR
 285   0        448        232      10384          0          0 AUTO LAG Protoco
 286   0    6516004   20574700      11704          0          0 MLDSN L2MCM
 287   0          0          0       7168          0          0 MRD
 288   0          0          0      10168          0          0 MLD_SNOOP
 289   0        232        232       7168          0          0 AAA Cached Serve
 290   0          0          0       7168          0          0 HRPC hl2mcm mlds
 291   0        232        232       7168          0          0 ENABLE AAA
 292   0        788        232      13724          0          0 LDAP process
 293   0      10320        232      17292          0          0 Crypto Support
 294   0          0          0       7168          0          0 IPSECv6 PS Proc
 295   0        232        232       7168          0          0 LINE AAA
 296   0      36808      36808      13168          0          0 LOCAL AAA
 298   0        788        232      13724          0          0 TPLUS
 299   0        216          0      13404          0          0 Collection proce
 300   0          0          0      13096          0          0 hulc cfg mgr mas
 301   0     212608     211836       7940          0          0 crypto engine pr
 302   0          0          0      13168          0          0 RSA background p
 303   0     596908     522716      96800          0          0 Crypto CA
 304   0        232        232      13168          0          0 Crypto PKI-CRL
 305   0          0          0      13168          0          0 Crypto PKI-Rev-P
 306   0        888          0      14056          0          0 PKI OCSP
 307   0          0          0      13168          0          0 PKI Revocation
 308   0     149520        248     156308       2268          0 Crypto IKEv2
 309   0          0          0       7168          0          0 IKEv2 AAA handle
 310   0        232          0      25400          0          0 tHUB
 311   0          0          0      13168          0          0 encrypt proc
 312   0        232        568       7168          0          0 CRYPTO MAP FREE
 313   0          0          0      13168          0          0 Crypto INT
 314   0        232        400      13168          0          0 Crypto IKE Dispa
 315   0      65856        232      78792          0          0 Crypto IKMP
 316   0          0          0      10168          0          0 IPSEC manual key
 317   0     204324       5972      13472          0          0 IPSEC key engine
 318   0          0          0      25168          0          0 Crypto ACL
 319   0          0          0       7168          0          0 Crypto PAS Proc
 320   0          0          0      13168          0          0 IPSec background
 321   0          0          0       7168          0          0 HRPC x_setup req
 322   0        232        232       7168          0          0 REP Switch Helpe
 323   0          0          0      10168          0          0 Licensing MIB pr
 324   0      11208        232      18144          0          0 VTP Trap Process
 326   0        232        232      25168          0          0 ASP Process Crea
 327   0        232      46180       7168          0          0 AAA SEND STOP EV
 328   0          0          0      13168          0          0 Test AAA Client
 329   0      18468       4308      21636          0          0 DCM Core Thread
 330   0       2412          0       9580          0          0 dcm_cli_engine
 331   0       4300        240      11216          0          0 dcm_cli_provider
 332   0      11780       5124      16984          0          0 EEM ED Routing
 333   0     283700       4964     288920     100548          0 EEM ED Syslog
 334   0   32886284   32885944       7508          0          0 Syslog Traps
 335   0        232        232       7168          0          0 FEX Logger Proce
 336   0          0          0       7168          0          0 HCD Process
 337   0          0          0       7168          0          0 HRPC cable diagn
 338   0          0          0       7168          0          0 HRPC archive_dnl
 339   0      65748        356       7168          0          0 DiagCard1/-1
 340   0   12905328   28185496       7168          0          0 PM Callback
 341   0          0          0       7040          0          0 hulc running con
 342   0        232        232       7168          0          0 dhcp snooping sw
 343   0      10088          0      17256          0          0 ONEP_DPSS_SERVIC
 344   0          0          0       7168          0          0 HRPC onep reques
 346   0    1016892       8088    1018972          0          0 EEM Server
 347   0       8556      13148      13456          0          0 Bulkstat-Client
 348   0       9244       1772      14536          0          0 DCM snmp dp Thre
 349   0       3320        240      10176          0          0 snmp dcm ma shim
 350   0      20372       1136      22236          0          0 EEM Policy Direc
 352   0      11376       4964      16580          0          0 EEM ED OIR
 353   0      11492       4964      16696          0          0 EEM ED Timer
 354   0    5753960    5752136      14992          0          0 Syslog
 355   0          0          0      33092          0          0 PnP-Monitor
 357   0      11812        464      24516          0          0 RBM CORE
 358   0          0          0       7168          0          0 HRPC eee request
 359   0        188          0       7356          0          0 hulc_eee_monitor
 360   0        232        232       4172          0          0 STP FAST TRANSIT
 361   0        232        232       4168          0          0 CSRT RAPID TRANS
 362   0     204756     176984      22728       2340          0 VLAN Manager
 363   0       6864        432      13600          0          0 EEM Helper Threa
 365   0   71297672        668      14212          0          0 IP SNMP
 366   0  665843852  665845068      13192          0          0 PDU DISPATCHER
 367   0       2092   71296860      13192          0          0 SNMP ENGINE
 368   0       1268        232      14212          0          0 IP SNMPV6
 369   0    3562680    3088324     481852          0          0 Snmp Flash Cache
 370   0          0          0      13192          0          0 SNMP ConfCopyPro
 371   0  861464208  861446368      31032          0          0 SNMP Traps
 373   0    1117716    1097164      33720          0          0 NTP
                                 47137532 Total

---
```

# description

- `show processes memory` 명령을 통해 장비의 메모리(Processor/IO Pool) 여유 공간을 점검합니다.

- **양호**: 메모리 사용량이 임계치 미만이며 여유(Free) 메모리가 충분함
- **경고**: 메모리 사용량이 임계치를 초과하여 메모리 누수 또는 고갈 위험
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds

[
    {id: null, key: "max_memory_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show processes memory'
POOL_RE = re.compile(
    r'^\s*(?P<pool>.+?)\s+Pool Total:\s*(?P<total>\d+)\s+'
    r'Used:\s*(?P<used>\d+)\s+Free:\s*(?P<free>\d+)',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _parse_pools(self, text):
        pools = []
        for line in (text or '').splitlines():
            match = POOL_RE.match(line)
            if not match:
                continue
            total = int(match.group('total'))
            used = int(match.group('used'))
            free = int(match.group('free'))
            pools.append({
                'pool': match.group('pool').strip(),
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': free,
                'usage_percent': round((used / total) * 100, 2) if total else 0.0,
            })
        return pools

    def run(self):
        max_usage = self.get_threshold_var(
            'max_memory_usage_percent',
            default=80.0,
            value_type='float',
        )
        thresholds = {'max_memory_usage_percent': max_usage}
        stdout, error = self._run_command()
        if error:
            return error

        pools = self._parse_pools(stdout)
        if not pools:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='show processes memory 출력에서 Pool 사용량을 찾지 못했습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        max_pool = max(pools, key=lambda item: item['usage_percent'])
        over = [item for item in pools if item['usage_percent'] > max_usage]
        metrics = {
            'pool_count': len(pools),
            'max_memory_usage_percent': max_pool['usage_percent'],
            'max_memory_pool': max_pool['pool'],
            'over_threshold_pools': over,
            'pools': pools,
        }
        if over:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 사용률이 기준을 초과한 Pool이 있습니다.',
                message=f'메모리 사용률 경고: 최대 {max_pool["usage_percent"]}%, 기준 {max_usage}%.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='메모리 사용률이 기준 이하입니다.',
            message=f'메모리 사용률 점검 정상: 최대 {max_pool["usage_percent"]}%, 기준 {max_usage}%.',
        )


CHECK_CLASS = Check
