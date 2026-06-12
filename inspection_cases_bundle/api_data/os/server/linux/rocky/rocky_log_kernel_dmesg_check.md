# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-DMESG-PANIC-01

# is_required

필수

# inspection_name

커널로그

# inspection_content

하드웨어 이상으로 인한 커널 패닉로그 점검(Kernel Panic, Panicking)

# inspection_command

```bash
dmesg | grep -i 'panic'
```

# inspection_output

```text
[  245.678901] Kernel panic - not syncing: Fatal hardware error!
[  245.679120] CPU: 3 PID: 1024 Comm: kworker/3:1 Not tainted 5.14.0-611.13.1.el9_7.x86_64
[  245.679845] Hardware name: ExampleServer R650/1.0, BIOS 2.8.4 11/15/2025
[  245.680512] Call Trace:
[  245.681033]  <TASK>
[  245.681420]  panic+0x110/0x2f0
[  245.681955]  machine_check_poll+0x1b4/0x220
[  245.682604]  do_machine_check+0x7d0/0x900
[  245.683210]  exc_machine_check+0x7a/0xd0
[  245.683834] Kernel Offset: disabled
```

# description

- (커널 패닉 메시지) Kernel panic 메시지가 확인되면, 커널 로그 분석과 시스템 재부팅 후 상태 점검 필요
- (CPU 및 프로세스 정보) CPU와 프로세스 정보를 확인하고, 상세 분석 권고
- (하드웨어 정보) 하드웨어 모델 정보를 확인하고, 하드웨어 상태 점검 권고
- (콜 트레이스) 호출 트레이스를 분석하여 패닉 원인을 파악하고, 커널 패치나 설정 변경 필요

- **양호**: `dmesg | grep -i 'panic'` 결과에서 임계치에 정의된 패닉 키워드가 존재하지 않는 상태
- **실패**: 패닉 키워드 존재

# thresholds

[
    {id: null, key: "panic_log_keywords", value: "kernel panic|panicking", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_PANIC_COMMAND = "dmesg | grep -i 'panic'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _count_keywords(self, lines, keywords):
        counts = {keyword: 0 for keyword in keywords}

        for line in lines:
            lowered = line.lower()
            for keyword in keywords:
                if keyword.lower() in lowered:
                    counts[keyword] += 1

        return counts

    def _format_keyword_counts(self, counts):
        return ', '.join(
            f'{keyword}={count}건'
            for keyword, count in counts.items()
        )

    def run(self):
        panic_keywords = self._split_keywords(
            self.get_threshold_var('panic_log_keywords', default='kernel panic|panicking', value_type='str')
        )
        if not panic_keywords:
            return self.fail(
                '임계치 미정의',
                message='panic_log_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_PANIC_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg panic 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        keyword_counts = self._count_keywords(lines, panic_keywords)
        threshold_summary = 'panic_log_keywords=' + '|'.join(panic_keywords)

        metrics = {
            'panic_line_count': len(lines),
            'panic_keyword_counts': keyword_counts,
            'panic_lines': lines,
        }
        thresholds = {
            'panic_log_keywords': '|'.join(panic_keywords),
        }

        if lines:
            return self.fail(
                '커널 패닉 로그 감지',
                message=(
                    '커널 패닉 관련 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='커널 패닉 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                '커널 패닉 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
