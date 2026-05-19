# 영역
프로세스

# 세부 점검항목
프로세스 기동 점검

# 점검 내용
WEB 서비스를 위한 WEB 프로세스가 정상적으로 기동 되었는지를 점검

# 구분
필수

# 명령어 - process_name 변수
```bash
 ps aux | egrep "PID|webtob" | grep -v grep
```

# 출력 결과
```text
[root@sd_tipswebwas ~]# ps aux | grep webtob | grep -v grep
exTMS    1476176  0.0  5.8 6052980 940596 ?      Sl    2025  93:32 /usr/lib/jvm/jdk-1.8.0_431-oracle-x64/bin/java -DadminServer -Xms1024m -Xmx1024m -XX:MetaspaceSize=128m -XX:MaxMetaspaceSize=512m -d64 -Djeus.vm.bits=64 -Djeus.io.buffer.size-per-pool=81920 -Djeus.cdi.enabled=false -Djeus.jms.server.manager.produce-wait-strategy-type=blocking -Djeus.servlet.sortWebinfLibraries=name_asc -server -Xbootclasspath/p:/home/exTMS/tmax/jeus/lib/system/extension.jar -classpath /home/exTMS/tmax/jeus/lib/jbext/jbext_v8500_202502_2_unified.jar:/home/exTMS/tmax/jeus/lib/system/bootstrap.jar -Djava.security.policy=/home/exTMS/tmax/jeus/domains/jeus_domain/config/security/policy -Djava.library.path=/home/exTMS/tmax/jeus/lib/system:/home/exTMS/tmax/webtob/lib: -Djava.endorsed.dirs=/home/exTMS/tmax/jeus/lib/endorsed -Djeus.properties.replicate=jeus,sun.rmi,java.util,java.net -Djeus.jvm.version=hotspot -Djava.util.logging.config.file=/home/exTMS/tmax/jeus/bin/logging.properties -Dsun.rmi.dgc.server.gcInterval=3600000 -Djava.util.logging.manager=jeus.util.logging.JeusLogManager -Djeus.home=/home/exTMS/tmax/jeus -Djeus.launcher.log.home=/home/exTMS/tmax/jeus/log/launcher -Djava.net.preferIPv4Stack=true -Djeus.tm.checkReg=true -Dsun.rmi.dgc.client.gcInterval=3600000 -Djeus.domain.name=jeus_domain -Djava.naming.factory.initial=jeus.jndi.JNSContextFactory -Djava.naming.factory.url.pkgs=jeus.jndi.jns.url -Djeus.server.protectmode=false -XX:+UnlockDiagnosticVMOptions -XX:+LogVMOutput -XX:LogFile=/home/exTMS/tmax/jeus/log/adminServer/jvm.log jeus.server.admin.DomainAdminServerBootstrapper -domain jeus_domain -u wasadmin -server adminServer
exTMS    1480138  0.0  0.0  19032  8728 ?        S     2025   8:27 wsm -l 0x2 -I webtob1_1480137 -b 1480137
exTMS    1480139  0.0  0.0  12588   900 ?        S     2025   2:40 htl -l 0x2 -I webtob1_1480137 -b 1480137
exTMS    1480140  0.0  3.6 1211928 596944 ?      Sl    2025   3:13 hth -l 0x2 -I webtob1_1480137 -b 1480137
```

# 설명
- PID: 프로세스의 고유 식별 번호를 나타내며, 정상적으로 기동된 경우 유효한 PID가 있어야 
하며, 비정상적인 PID 발견 시 점검이 필요. 해당 프로세스가 실행 중이지 않으면 PID가 
표시되지 않음. 
- COMMAND: 실행 중인 명령어와 경로를 나타내며, 명령어가 정확하게 실행되고 있는지 확인해야 함. ※ 프로세스 상태 ‘S’는 프로세스가 CPU를 사용하지 않고 대기 상태(Sleeping)임을 의미하고, ‘s’는 세션 리더 프로세스(자식 프로세스를 생성하고, 해당 세션의 제어를 담당하는 프로세스)임을 나타내므로, ‘Ss’는 해당 프로세스가 CPU 자원을 대기 중이면서 세션을 관리하고 있음을 의미함.

# 임계치
ps_status: WebtoB 프로세스 상태(S)

# 판단기준
- **양호**: 유효한 PID가 있고 비정상적인 상태 코드(Z, D, T)가 발견되지 않은 상태
- **경고**: 비정상적인 상태 코드(Z, D, T)가 발견된 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태
