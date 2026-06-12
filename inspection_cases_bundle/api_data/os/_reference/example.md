# type_name 

일상점검(상태점검)

# area_name

서버 

# category_name

NETWORK

# application_type

UNIX

# application

solaris

# inspection_code

SVR 7-2

# is_required

필수

# inspection_name

NIC 이중화 점검


# inspection_content

NIC 이중화(IPMP) 및 Daemon 상태 점검


# inspection_command

```bash
ipmpstat -i
```

# inspection_output

```text
INTERFACE ACTIVE GROUP FLAGS  LINK STATE
net0      yes    ipmp0 ------ up   ok
net1      yes    ipmp0 ------ up   ok
```

# description

- `ipmpstat -i`는 IPMP 인터페이스별 ACTIVE, GROUP, LINK, STATE 값을 확인할 때 사용합니다.
- 같은 IPMP 그룹 내 인터페이스가 2개 이상이고, 각 인터페이스의 `ACTIVE=yes`, `LINK=up`, `STATE=ok`이면 정상으로 판단합니다.
- `off-line`, `failed`, `down`, `unknown` 등 비정상 상태가 있거나 그룹 내 인터페이스 수가 부족하면 실패로 처리합니다.
- `ipmpstat` 명령이 없거나 출력 형식을 해석할 수 없으면 실패로 처리합니다.
- **정상**: 각 IPMP 그룹에 인터페이스가 2개 이상 존재하고 모든 인터페이스가 `ACTIVE=yes`, `LINK=up`, `STATE=ok`인 경우
- **실패**: 그룹 내 인터페이스 수가 부족하거나, `ACTIVE`, `LINK`, `STATE` 중 하나라도 기준과 다른 경우
- **실패**: `ipmpstat` 명령 실행 실패, 명령 미설치, 출력 파싱 실패, 오류 로그 확인 시


# thresholds

[
    {id: null, key: "min_group_interface_count", value: "2", sortOrder: 0}
,
{id: null, key: "expected_active_value", value: "yes", sortOrder: 1}
]


# inspection_script

# -*- coding: utf-8 -*-

import re
from collections import defaultdict

from .common._base import BaseCheck


IPMPSTAT_INTERFACE_COMMAND = 'ipmpstat -i'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _normalize(self, value):
        return str(value or '').strip().lower()

    def _parse_ipmp_interfaces(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        header = None
        rows = []

        for line in lines:
            tokens = re.split(r'\s+', line.strip())
            lowered = [token.lower() for token in tokens]
            if 'interface' in lowered and 'active' in lowered and 'group' in lowered and 'link' in lowered and 'state' in lowered:
                header = lowered
                continue

            if not header:
                continue

            if len(tokens) < len(header):
                continue

            row = {header[idx]: tokens[idx] for idx in range(len(header))}
            interface = row.get('interface', '')
            group_name = row.get('group', '')
            if not interface or not group_name:
                continue

            rows.append({
                'interface': interface,
                'active': row.get('active', ''),
                'group': group_name,
                'flags': row.get('flags', ''),
                'link': row.get('link', ''),
                'state': row.get('state', ''),
            })

        if not rows:
            return None

        groups = defaultdict(list)
        for row in rows:
            groups[row['group']].append(row)

        group_summaries = []
        for group_name in sorted(groups.keys()):
            members = groups[group_name]
            group_summaries.append({
                'group': group_name,
                'interface_count': len(members),
                'interfaces': [member['interface'] for member in members],
            })

        return {
            'rows': rows,
            'group_count': len(groups),
            'group_summaries': group_summaries,
        }

    def run(self):
        min_group_interface_count = self.get_threshold_var('min_group_interface_count', default=2, value_type='int')
        expected_active_value = self.get_threshold_var('expected_active_value', default='yes', value_type='str')
        expected_link_value = self.get_threshold_var('expected_link_value', default='up', value_type='str')
        expected_state_value = self.get_threshold_var('expected_state_value', default='ok', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(IPMPSTAT_INTERFACE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris NIC 이중화(IPMP) 점검에 실패했습니다. 현재 상태: ipmpstat 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=[
                'permission denied',
                'not supported',
                'unknown userland error',
                'no such file or directory',
                'cannot find',
                'not found',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris NIC 이중화(IPMP) 점검에 실패했습니다. '
                    f'현재 상태: ipmpstat 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in (out or '').lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'NIC 이중화 실패 키워드 감지',
                message=(
                    'Solaris NIC 이중화(IPMP) 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = self._parse_ipmp_interfaces(out)
        if not parsed:
            return self.fail(
                'NIC 이중화 파싱 실패',
                message='Solaris NIC 이중화(IPMP) 점검에 실패했습니다. 현재 상태: ipmpstat 출력에서 인터페이스 상태를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        expected_active_norm = self._normalize(expected_active_value)
        expected_link_norm = self._normalize(expected_link_value)
        expected_state_norm = self._normalize(expected_state_value)

        inactive_interfaces = []
        link_issue_interfaces = []
        state_issue_interfaces = []
        insufficient_groups = []
        active_interface_count = 0

        for row in parsed['rows']:
            if self._normalize(row['active']) == expected_active_norm:
                active_interface_count += 1
            else:
                inactive_interfaces.append(row['interface'])

            if self._normalize(row['link']) != expected_link_norm:
                link_issue_interfaces.append(row['interface'])

            if self._normalize(row['state']) != expected_state_norm:
                state_issue_interfaces.append(row['interface'])

        for summary in parsed['group_summaries']:
            if summary['interface_count'] < min_group_interface_count:
                insufficient_groups.append(summary)

        metrics = {
            'group_count': parsed['group_count'],
            'interface_count': len(parsed['rows']),
            'active_interface_count': active_interface_count,
            'group_summaries': parsed['group_summaries'],
            'inactive_interfaces': inactive_interfaces,
            'link_issue_interfaces': link_issue_interfaces,
            'state_issue_interfaces': state_issue_interfaces,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'min_group_interface_count': min_group_interface_count,
            'expected_active_value': expected_active_value,
            'expected_link_value': expected_link_value,
            'expected_state_value': expected_state_value,
            'failure_keywords': failure_keywords,
        }

        if insufficient_groups:
            group_text = ', '.join(
                f"{item['group']}={item['interface_count']}개"
                for item in insufficient_groups
            )
            return self.fail(
                'IPMP 그룹 인터페이스 수 부족',
                message=(
                    'Solaris NIC 이중화(IPMP) 점검에 실패했습니다. '
                    f'현재 상태: 같은 IPMP 그룹 내 인터페이스 수가 부족합니다. {group_text} '
                    f'(기준 그룹당 {min_group_interface_count}개 이상).'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if inactive_interfaces or link_issue_interfaces or state_issue_interfaces:
            problem_parts = []
            if inactive_interfaces:
                problem_parts.append(f'ACTIVE 비정상={inactive_interfaces}')
            if link_issue_interfaces:
                problem_parts.append(f'LINK 비정상={link_issue_interfaces}')
            if state_issue_interfaces:
                problem_parts.append(f'STATE 비정상={state_issue_interfaces}')
            return self.fail(
                'NIC 이중화 상태 비정상',
                message=(
                    'Solaris NIC 이중화(IPMP) 점검에 실패했습니다. '
                    '현재 상태: ' + ', '.join(problem_parts) + '. '
                    f"기준 ACTIVE={expected_active_value}, LINK={expected_link_value}, STATE={expected_state_value}."
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        group_names = ', '.join(summary['group'] for summary in parsed['group_summaries'])
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'모든 인터페이스가 ACTIVE={expected_active_value}, LINK={expected_link_value}, '
                f'STATE={expected_state_value}이며 각 IPMP 그룹이 {min_group_interface_count}개 이상 인터페이스를 가집니다.'
            ),
            message=(
                'Solaris NIC 이중화(IPMP) 상태가 정상입니다. '
                f'현재 상태: 그룹 {group_names}, 총 인터페이스 {len(parsed["rows"])}개, '
                f'ACTIVE 정상 {active_interface_count}개, '
                f'LINK={expected_link_value} / STATE={expected_state_value} 확인, '
                f'그룹당 인터페이스 수 기준 {min_group_interface_count}개 이상 충족.'
            ),
        )


CHECK_CLASS = Check


