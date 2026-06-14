# type_name

일상점검

# area_name

web

# category_name

상태점검

# application_type

webtob

# application

rocky

# inspection_code

WEBTOB-ROCKY-REPLAY-002

# is_required

필수

# inspection_name

WEB 어플리케이션 설치 파일시스템 점검

# inspection_content

WEB 소스가 설치되어 있는 파일시스템 FULL로 인한 서비스 불가 확인을 위한 파일시스템 점검

# inspection_command

```bash
- web_app_fs_path 변수
```bash
df -h "{{ web_app_fs_path }}" # web_app_fs_path: /home/exTMS/tmax/webtob/docs
```
```

# inspection_output

```text
[root@sd_tipswebwas ~]# df -h /home/exTMS/tmax/webtob/docs
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   30G   28G  2.6G  92% /
```

# description

- Use% (60%): 사용량이 과도하여 용량 부족 시 증설 필요. 
- Avail (20G): 남은 용량이 부족할 경우 증설 필요. ※ 기본 경로로 나타냈으며, 사용자가 임의로 경로를 변경했을 경우 수정되어야 함.

- **양호**: 파일시스템 사용률이 `max_use_percent`를 초과하지 않고, 여유공간이 `min_avail_gb`이상인 상태
- **경고**: 파일시스템 사용률이 `max_use_percent`를 초과하고, 여유공간이 `min_avail_gb`미만인 상태
- **확인 필요**: 출력이 비어 있거나 명령 실행 불가/권한/미지원 등의 사유로 점검 불가한 상태

# thresholds

[
    {id: null, key: "web_app_fs_path", value: "/home/exTMS/tmax/webtob/docs", sortOrder: 0}
,
{id: null, key: "max_use_percent", value: "80", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_PATH = '/home/exTMS/tmax/webtob/docs'
    DEFAULT_MAX_USE_PERCENT = 80
    COMMAND_TIMEOUT = 10

    def _target_path(self):
        host_path = str(self.get_host_var('web_app_fs_path', '') or '').strip()
        if host_path:
            return host_path, 'host_vars'

        threshold_path = str(
            self.get_threshold_var('web_app_fs_path', default='', value_type='str') or ''
        ).strip()
        if threshold_path:
            return threshold_path, 'threshold_list'

        return self.DEFAULT_PATH, 'default'

    def _parse_df(self, stdout):
        for line in str(stdout or '').splitlines():
            if not line.strip() or 'Filesystem' in line:
                continue

            parts = re.split(r'\s+', line.strip())
            use_index = next(
                (idx for idx, token in enumerate(parts) if re.match(r'^\d+%$', token)),
                -1,
            )
            if use_index < 1:
                continue

            return {
                'filesystem': parts[0],
                'use_percent': int(parts[use_index].rstrip('%')),
                'mounted_on': ' '.join(parts[use_index + 1:]).strip(),
            }
        return None

    def run(self):
        target_path, path_source = self._target_path()
        max_use_percent = self.get_threshold_var(
            'max_use_percent',
            default=self.DEFAULT_MAX_USE_PERCENT,
            value_type='int',
        )
        command = 'df -h %s' % shlex.quote(target_path)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'df 명령 실행 실패',
                message='WEB 어플리케이션 파일시스템 사용률을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        parsed = self._parse_df(stdout)
        if not parsed:
            return self.fail(
                'df 출력 파싱 실패',
                message='df -h 출력에서 파일시스템 사용률을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        metrics = {
            'web_app_fs_path': target_path,
            'web_app_fs_path_source': path_source,
            'filesystem': parsed['filesystem'],
            'mounted_on': parsed['mounted_on'],
            'use_percent': parsed['use_percent'],
            'max_use_percent': max_use_percent,
        }
        thresholds = {
            'web_app_fs_path': target_path,
            'web_app_fs_path_source': path_source,
            'max_use_percent': max_use_percent,
        }

        if parsed['use_percent'] > max_use_percent:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='파일시스템 사용률 %s%%가 기준 %s%%를 초과했습니다.' % (
                    parsed['use_percent'],
                    max_use_percent,
                ),
                message='WEB 어플리케이션 파일시스템 사용률 경고: %s 사용률 %s%%, 기준 %s%%' % (
                    target_path,
                    parsed['use_percent'],
                    max_use_percent,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='파일시스템 사용률이 기준 이하입니다.',
            message='WEB 어플리케이션 파일시스템 사용률 정상: %s 사용률 %s%%, 기준 %s%%' % (
                target_path,
                parsed['use_percent'],
                max_use_percent,
            ),
        )


CHECK_CLASS = Check
