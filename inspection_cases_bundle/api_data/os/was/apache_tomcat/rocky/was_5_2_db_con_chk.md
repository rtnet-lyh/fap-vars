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

WAS-APACHE-TOMCAT-ROCKY-REPLAY-013

# is_required

필수

# inspection_name

DB연결 상태 점검

# inspection_content

DB에 연결된 객체 저장공간인 DB Connection Pool 확인(각 컨테이너별 Enable상태 확인)

# inspection_command

```bash
netstat -ntp | grep '3306' | awk '{print $6}' | sort | uniq -c
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
- 선행작업 필요
- ps -ef | grep tomcat 해서 피드 확인해서 {피드} 부분에 입력 필요

[root@re-test-POTAL logs]# /home/koem01/elasticsearch-7.6.2/jdk/bin/jstat -gcutil {피드}
  S0     S1     E      O      M     CCS    YGC     YGCT    FGC    FGCT    CGC    CGCT     GCT
  0.00   0.00  17.44   2.75  98.51  96.42      5    0.282     3    0.529     -        -    0.811

---
```

# description

- `netstat -ntp` 명령어를 사용하여 WAS 서비스 포트(8080/8009) 혹은 DB 포트(3306)에 연결된 네트워크 세션의 상태(ESTABLISHED, CLOSE_WAIT 등) 통계를 확인합니다. 이를 통해 워커 스레드나 커넥션 풀의 고갈 여부를 파악합니다.

- **양호**: 활성화된 연결(ESTABLISHED) 수가 임계치 내에서 안정적으로 관리됨
- **경고**: 연결 수가 한계치에 도달하거나, 반환되지 않는 `CLOSE_WAIT` 상태가 다수 누적됨
- **확인 필요**: 명령어 오류 또는 수집된 네트워크 통계 결과와 포맷이 달라 점검이 불가한 상태

# thresholds

[
    {id: null, key: "max_established_conn", value: "1000", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "netstat -ntp | grep '3306' | awk '{print $6}' | sort | uniq -c"
COMMAND_TIMEOUT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _parse_state_counts(self, stdout):
        counts = {}
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            try:
                count = int(parts[0])
            except ValueError:
                continue
            counts[parts[1].upper()] = count
        return counts

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
                message='Apache Tomcat DB 연결 상태 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        state_counts = self._parse_state_counts(stdout)
        threshold = self.get_threshold_var('max_established_conn', default=1000, value_type='int')
        established_count = state_counts.get('ESTABLISHED', 0)
        close_wait_count = state_counts.get('CLOSE_WAIT', 0)
        metrics = {
            'state_counts': state_counts,
            'established_count': established_count,
            'close_wait_count': close_wait_count,
        }
        thresholds = {'max_established_conn': threshold, 'max_close_wait_count': 0}
        if established_count > threshold or close_wait_count > 0:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='DB 연결 수가 기준을 초과했거나 CLOSE_WAIT 상태가 확인되었습니다.',
                message='Apache Tomcat DB 연결 상태 경고: ESTABLISHED=%s, CLOSE_WAIT=%s, 기준=%s' % (
                    established_count,
                    close_wait_count,
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='DB 활성 연결 수와 CLOSE_WAIT 상태가 기준 이내입니다.',
            message='Apache Tomcat DB 연결 상태 정상: ESTABLISHED=%s, 기준=%s' % (
                established_count,
                threshold,
            ),
        )


CHECK_CLASS = Check
