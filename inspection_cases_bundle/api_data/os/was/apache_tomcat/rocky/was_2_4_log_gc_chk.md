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


WAS-TOM-RKY-008

# is_required

필수

# inspection_name

메모리 로그 이상 유무 점검

# inspection_content

Full GC(Garbage Collection) 발생 빈도 점검(오래된 객체에 대한 삭제 등의 메모리 공간 확보 작업의 발생 빈도 체크, 일정기간 로그분석을 통해 GC 튜닝 여부 결정)

# inspection_command

```bash
tail -n 100 /home/koem01/apache-tomcat-8.0.32/logs/catalina.out
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL apache-tomcat-8.0.32]# tail -n 100 /home/koem01/apache-tomcat-8.0.32/logs/catalina.out
        at org.apache.catalina.core.ContainerBase.addChildInternal(ContainerBase.java:725)
        at org.apache.catalina.core.ContainerBase.addChild(ContainerBase.java:701)
        at org.apache.catalina.core.StandardHost.addChild(StandardHost.java:717)
        at org.apache.catalina.startup.HostConfig.deployDirectory(HostConfig.java:1091)
        at org.apache.catalina.startup.HostConfig$DeployDirectory.run(HostConfig.java:1830)
        at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
        at java.util.concurrent.FutureTask.run(FutureTask.java:266)
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
        at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
        at java.lang.Thread.run(Thread.java:750)

08-Apr-2026 14:47:57.017 SEVERE [localhost-startStop-1] org.apache.catalina.startup.ContextConfig.processAnnotationsJar Unable to process Jar entry [module-info.class] from Jar [jar:file:/home/koem01/apache-tomcat-8.0.32/webapps/koem/WEB-INF/lib/jaxb-api-2.3.1.jar!/] for annotations
 org.apache.tomcat.util.bcel.classfile.ClassFormatException: Invalid byte tag in constant pool: 19
        at org.apache.tomcat.util.bcel.classfile.Constant.readConstant(Constant.java:97)
        at org.apache.tomcat.util.bcel.classfile.ConstantPool.<init>(ConstantPool.java:55)
        at org.apache.tomcat.util.bcel.classfile.ClassParser.readConstantPool(ClassParser.java:176)
        at org.apache.tomcat.util.bcel.classfile.ClassParser.parse(ClassParser.java:85)
        at org.apache.catalina.startup.ContextConfig.processAnnotationsStream(ContextConfig.java:2045)
        at org.apache.catalina.startup.ContextConfig.processAnnotationsJar(ContextConfig.java:1991)
        at org.apache.catalina.startup.ContextConfig.processAnnotationsUrl(ContextConfig.java:1961)
        at org.apache.catalina.startup.ContextConfig.processAnnotations(ContextConfig.java:1915)
        at org.apache.catalina.startup.ContextConfig.webConfig(ContextConfig.java:1158)
        at org.apache.catalina.startup.ContextConfig.configureStart(ContextConfig.java:780)
        at org.apache.catalina.startup.ContextConfig.lifecycleEvent(ContextConfig.java:305)
        at org.apache.catalina.util.LifecycleSupport.fireLifecycleEvent(LifecycleSupport.java:95)
        at org.apache.catalina.util.LifecycleBase.fireLifecycleEvent(LifecycleBase.java:90)
        at org.apache.catalina.core.StandardContext.startInternal(StandardContext.java:5154)
        at org.apache.catalina.util.LifecycleBase.start(LifecycleBase.java:147)
        at org.apache.catalina.core.ContainerBase.addChildInternal(ContainerBase.java:725)
        at org.apache.catalina.core.ContainerBase.addChild(ContainerBase.java:701)
        at org.apache.catalina.core.StandardHost.addChild(StandardHost.java:717)
        at org.apache.catalina.startup.HostConfig.deployDirectory(HostConfig.java:1091)
        at org.apache.catalina.startup.HostConfig$DeployDirectory.run(HostConfig.java:1830)
        at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
        at java.util.concurrent.FutureTask.run(FutureTask.java:266)
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
        at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
        at java.lang.Thread.run(Thread.java:750)

08-Apr-2026 14:48:00.439 INFO [localhost-startStop-1] org.apache.jasper.servlet.TldScanner.scanJars At least one JAR was scanned for TLDs yet contained no TLDs. Enable debug logging for this logger for a complete list of JARs that were scanned but no TLDs were found in them. Skipping unneeded JARs during scanning can improve startup time and JSP compilation time.
=== multi company check start ===
=== IP CHECK === : true
=== Option String === : TTTTTTTT
=== version check start ===
*** /koem loading complete ***
08-Apr-2026 14:48:08.525 INFO [localhost-startStop-1] org.apache.catalina.startup.HostConfig.deployDirectory Deployment of web application directory /home/koem01/apache-tomcat-8.0.32/webapps/koem has finished in 13,795 ms
08-Apr-2026 14:48:08.530 INFO [main] org.apache.coyote.AbstractProtocol.start Starting ProtocolHandler ["http-nio-8443"]
08-Apr-2026 14:48:08.537 INFO [main] org.apache.coyote.AbstractProtocol.start Starting ProtocolHandler ["http-nio-8090"]
08-Apr-2026 14:48:08.537 INFO [main] org.apache.coyote.AbstractProtocol.start Starting ProtocolHandler ["ajp-nio-8009"]
08-Apr-2026 14:48:08.538 INFO [main] org.apache.catalina.startup.Catalina.start Server startup in 14053 ms
2026-04-08 16:17:04.334 ERROR [LogManager.java:errorHandler:49]  [] - [Error]No bean named 'attendanceOracleBO' available
org.springframework.beans.factory.NoSuchBeanDefinitionException: No bean named 'attendanceOracleBO' available
        at org.springframework.beans.factory.support.DefaultListableBeanFactory.getBeanDefinition(DefaultListableBeanFactory.java:687) ~[spring-beans-4.3.13.RELEASE.jar:4.3.13.RELEASE]
        at org.springframework.beans.factory.support.AbstractBeanFactory.getMergedLocalBeanDefinition(AbstractBeanFactory.java:1207) ~[spring-beans-4.3.13.RELEASE.jar:4.3.13.RELEASE]
        at org.springframework.beans.factory.support.AbstractBeanFactory.doGetBean(AbstractBeanFactory.java:284) ~[spring-beans-4.3.13.RELEASE.jar:4.3.13.RELEASE]
        at org.springframework.beans.factory.support.AbstractBeanFactory.getBean(AbstractBeanFactory.java:197) ~[spring-beans-4.3.13.RELEASE.jar:4.3.13.RELEASE]
        at org.springframework.context.support.AbstractApplicationContext.getBean(AbstractApplicationContext.java:1080) ~[spring-context-4.3.13.RELEASE.jar:4.3.13.RELEASE]
        at com.ontheit.bzr.framework.core.ControlCoreBase.getBean(ControlCoreBase.java:419) ~[bizrunner-core.jar:?]
        at com.ontheit.bzr.portlet.control.teamAttendance.Normal.preRenderAsPortlet(Normal.java:69) ~[bizrunner-km.jar:?]
        at com.ontheit.bzr.portlet.base.PortletNormalBase.preRenderAsBzR(PortletNormalBase.java:143) [bizrunner-framework.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:835) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ControlUiBase.preRender(ControlUiBase.java:842) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ServletUiBase.preRender(ServletUiBase.java:637) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ServletBase.preRender(ServletBase.java:924) [bizrunner-framework.jar:?]
        at com.ontheit.bzr.framework.core.ServletUiBase.doProcess(ServletUiBase.java:224) [bizrunner-core.jar:?]
        at com.ontheit.bzr.framework.core.ServletUiBase.doGet(ServletUiBase.java:137) [bizrunner-core.jar:?]
        at javax.servlet.http.HttpServlet.service(HttpServlet.java:622) [servlet-api.jar:?]
        at javax.servlet.http.HttpServlet.service(HttpServlet.java:729) [servlet-api.jar:?]
        at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:292) [catalina.jar:8.0.32]
        at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:207) [catalina.jar:8.0.32]
        at org.apache.tomcat.websocket.server.WsFilter.doFilter(WsFilter.java:52) [tomcat-websocket.jar:8.0.32]
        at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:240) [catalina.jar:8.0.32]
        at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:207) [catalina.jar:8.0.32]
        at com.ontheit.bzr.servlet.filter.HTMLTagFilter.doFilter(HTMLTagFilter.java:56) [bizrunner-portal.jar:?]
        at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:240) [catalina.jar:8.0.32]
        at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:207) [catalina.jar:8.0.32]
        at com.ontheit.bzr.web.SessionFilter.doFilter(SessionFilter.java:139) [classes/:?]
        at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:240) [catalina.jar:8.0.32]
        at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:207) [catalina.jar:8.0.32]
        at org.apache.catalina.core.StandardWrapperValve.invoke(StandardWrapperValve.java:212) [catalina.jar:8.0.32]
        at org.apache.catalina.core.StandardContextValve.invoke(StandardContextValve.java:106) [catalina.jar:8.0.32]
        at org.apache.catalina.authenticator.AuthenticatorBase.invoke(AuthenticatorBase.java:502) [catalina.jar:8.0.32]
        at org.apache.catalina.core.StandardHostValve.invoke(StandardHostValve.java:141) [catalina.jar:8.0.32]
        at org.apache.catalina.valves.ErrorReportValve.invoke(ErrorReportValve.java:79) [catalina.jar:8.0.32]
        at org.apache.catalina.valves.AbstractAccessLogValve.invoke(AbstractAccessLogValve.java:616) [catalina.jar:8.0.32]
        at org.apache.catalina.core.StandardEngineValve.invoke(StandardEngineValve.java:88) [catalina.jar:8.0.32]
        at org.apache.catalina.connector.CoyoteAdapter.service(CoyoteAdapter.java:522) [catalina.jar:8.0.32]
        at org.apache.coyote.http11.AbstractHttp11Processor.process(AbstractHttp11Processor.java:1095) [tomcat-coyote.jar:8.0.32]
        at org.apache.coyote.AbstractProtocol$AbstractConnectionHandler.process(AbstractProtocol.java:672) [tomcat-coyote.jar:8.0.32]
        at org.apache.tomcat.util.net.NioEndpoint$SocketProcessor.doRun(NioEndpoint.java:1500) [tomcat-coyote.jar:8.0.32]
        at org.apache.tomcat.util.net.NioEndpoint$SocketProcessor.run(NioEndpoint.java:1456) [tomcat-coyote.jar:8.0.32]
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149) [?:1.8.0_412]
        at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624) [?:1.8.0_412]
        at org.apache.tomcat.util.threads.TaskThread$WrappingRunnable.run(TaskThread.java:61) [tomcat-util.jar:8.0.32]
        at java.lang.Thread.run(Thread.java:750) [?:1.8.0_412]

---
```

# description

- `catalina.out` 등 WAS 메인 로그를 조회하여 서버의 관리, 서비스 구동, 클라이언트 접속, 가비지 컬렉션(GC), 커넥션풀 및 장기 수행 스레드 관련한 `SEVERE`, `Error`, `Exception` 발생 여부를 종합적으로 확인합니다.

- **양호**: 점검 대상 에러 및 지연 관련 로그(Exception, SEVERE 등)가 확인되지 않음
- **경고**: 애플리케이션 서비스 지장, 메모리 부족, DB 커넥션 풀 고갈을 암시하는 에러 로그가 발견됨
- **확인 필요**: 권한 문제 등으로 조회가 불가하거나 수집된 출력 결과 포맷과 일치하지 않아 점검이 불가한 상태

# thresholds

[
    {id: null, key: "max_error_count", value: "0", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'tail -n 100 /home/koem01/apache-tomcat-8.0.32/logs/catalina.out'
COMMAND_TIMEOUT = 20
CHECK_NAME = '메모리 로그'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _warning_words(self):
        raw_words = self.get_threshold_var(
            'warning_words',
            default='ERROR,WARN,FATAL,CRITICAL,EXCEPTION,SEVERE,OUTOFMEMORY,FULL GC',
            value_type='str',
        )
        return [word.strip().upper() for word in re.split(r'[,|]+', raw_words) if word.strip()]

    def run(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Apache Tomcat 로그 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return self.fail('로그 출력 없음', message='로그 출력이 비어 있습니다.', stdout=stdout)

        warning_words = self._warning_words()
        warning_lines = [
            line for line in lines
            if any(word in line.upper() for word in warning_words)
        ]
        threshold = self.get_threshold_var('max_error_count', default=0, value_type='int')
        metrics = {
            'inspected_line_count': len(lines),
            'error_count': len(warning_lines),
            'warning_lines': warning_lines[:20],
            'sample_lines': lines[:20],
        }
        thresholds = {
            'max_error_count': threshold,
            'warning_patterns': '|'.join(warning_words),
        }
        if len(warning_lines) > threshold:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='로그에서 메모리 또는 GC 이상 패턴이 발견되었습니다.',
                message='Apache Tomcat %s 점검 경고: error_count=%s, 기준=%s' % (
                    CHECK_NAME,
                    len(warning_lines),
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='로그에서 메모리 또는 GC 이상 패턴이 발견되지 않았습니다.',
            message='Apache Tomcat %s 점검 정상: inspected_line_count=%s' % (
                CHECK_NAME,
                len(lines),
            ),
        )


CHECK_CLASS = Check
