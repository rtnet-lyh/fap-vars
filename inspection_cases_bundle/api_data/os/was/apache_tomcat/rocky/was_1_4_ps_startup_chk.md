# type_name

일상점검

# area_name

상태점검

# category_name

was

# application_type

apache_tomcat

# application

rocky

# inspection_code

WAS-APACHE-TOMCAT-ROCKY-REPLAY-004

# is_required

필수

# inspection_name

프로세스 기동 점검

# inspection_content

서비스 컨테이너별 WAS 프로세스 확인(컨테이너 구동 시 실행되는 프로세스 점검)

# inspection_command

```bash
ps -ef | grep tomcat | grep -v grep
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL logs]# ps -ef | grep tomcat | grep -v grep
root      729184       1  4 10:40 pts/1    00:00:17 /usr/bin/java -Djava.util.logging.config.file=/home/koem01/apache-tomcat-8.0.32/conf/logging.properties -Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager -Djava.awt.headless=true -Dfile.encoding=UTF-8 -server -Xms8192m -Xmx8192m -XX:NewRatio=2 -XX:PermSize=512m -XX:MaxPermSize=512m -Xloggc:/home/koem01/apache-tomcat-8.0.32/logs/gc_%t.log -verbose:gc -XX:+PrintGC -XX:+PrintGCDateStamps -XX:+PrintGCTimeStamps -XX:+PrintGCDetails -XX:+UseGCLogFileRotation -XX:NumberOfGCLogFiles=15 -XX:GCLogFileSize=10m -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/home/koem01/apache-tomcat-8.0.32/dump -Djava.endorsed.dirs=/home/koem01/apache-tomcat-8.0.32/endorsed -classpath /home/koem01/apache-tomcat-8.0.32/bin/bootstrap.jar:/home/koem01/apache-tomcat-8.0.32/bin/tomcat-juli.jar -Dcatalina.base=/home/koem01/apache-tomcat-8.0.32 -Dcatalina.home=/home/koem01/apache-tomcat-8.0.32 -Djava.io.tmpdir=/home/koem01/apache-tomcat-8.0.32/temp org.apache.catalina.startup.Bootstrap start


---
```

# description

- `ps` 명령을 통해 WAS 관련 프로세스의 CPU/메모리 사용률 혹은 기동 상태를 점검하여 서비스 정상 동작 여부를 확인합니다.

- **양호**: 대상 프로세스의 상태가 정상이고 사용률이 임계치 이하로 유지됨 (기동 상태의 경우 프로세스 존재)
- **경고**: 자원 사용률이 임계치를 초과하거나 좀비(Z)/비정상 상태, 프로세스가 기동되지 않음
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds

[
    {id: null, key: "max_usage_percent: 최대 허용 자원 사용률", value: "", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'ps -ef | grep tomcat | grep -v grep'
COMMAND_TIMEOUT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

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
                message='Apache Tomcat 기동 프로세스 확인 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        tomcat_lines = [
            line for line in lines
            if 'tomcat' in line.lower() and 'grep' not in line.lower()
        ]
        metrics = {
            'tomcat_process_count': len(tomcat_lines),
            'processes': tomcat_lines,
        }
        if not tomcat_lines:
            return self.warn(
                metrics=metrics,
                reasons='Apache Tomcat 기동 프로세스가 확인되지 않습니다.',
                message='Apache Tomcat 프로세스 기동 경고: 프로세스 없음',
            )
        return self.ok(
            metrics=metrics,
            reasons='Apache Tomcat 기동 프로세스가 확인되었습니다.',
            message='Apache Tomcat 프로세스 기동 정상: process_count=%s' % len(tomcat_lines),
        )


CHECK_CLASS = Check
