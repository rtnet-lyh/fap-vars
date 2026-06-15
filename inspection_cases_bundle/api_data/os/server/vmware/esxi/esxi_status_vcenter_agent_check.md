# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

vmware

# application

esxi

# inspection_code


SV-ESXI-004

# is_required

권고

# inspection_name

ESXi vCenter Agent 통신 상태 확인

# inspection_content

vCenter와 통신하는 Agent 상태 확인

# inspection_command

```bash
기본 점검은 `VMwareHelper.vcenter_agent_status_from_context()`를 사용한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostSystem.summary`와 `HostServiceSystem` 정보를 함께 확인하고, `password`가 없거나 `force_replay=true`이면 `outputs/vcenter_agent.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.vcenter_agent_status_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
```
```

# inspection_output

```text
{
  "host_name": "localhost.rtnet",
  "managed_by_vcenter": true,
  "management_server_ip": "192.168.1.10",
  "connection_state": "connected",
  "vpxa": {
    "exists": true,
    "running": true,
    "policy": "on"
  }
}
```

# description

- 이 항목은 ESXi가 vCenter에 등록되어 관리되는 환경에서 vCenter Agent 통신 상태를 확인한다.
- `vpxa`는 vCenter Agent이며 vCenter의 작업 전달, 인벤토리 갱신, 상태 보고에 사용된다.
- `summary.managementServerIp`가 있으면 해당 ESXi가 vCenter 관리 대상인지 확인할 수 있다.
- `summary.runtime.connectionState`가 `connected`이면 관리 연결 상태가 정상으로 해석된다.
- 단독 ESXi 운영 환경에서는 vCenter 관리 서버 정보가 없을 수 있으며, 기본 구현은 `require_vcenter_connection=false`로 두어 이 경우 대상미해당 성격의 `warn`으로 분류한다.
- vCenter 연결을 필수로 운영하는 환경에서는 `require_vcenter_connection=true`로 설정해 관리 서버 정보, 연결 상태, `vpxa` 상태를 모두 필수 기준으로 판정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connectionState`가 `connected`가 아니면 vCenter 연동 상태 점검이 필요하다.

- **양호**: vCenter 관리 대상 ESXi에서 `vpxa`가 실행 중이고 `connection_state`가 `connected`이며 관리 서버 정보가 확인되는 경우
- **경고**: vCenter 관리 대상인데 `vpxa`가 중지되어 있거나 `connection_state`가 `connected`가 아니거나 관리 서버 정보가 누락된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 `require_vcenter_connection=false`로 vCenter 연결을 요구하지 않는 경우
- **확인 필요**: ESXi API 인증, vCenter 관리 정보 조회, Agent 상태 확인이 불가능한 경우

# thresholds

[
    {id: null, key: "require_vcenter_connection", value: "false", sortOrder: 0}
,
{id: null, key: "expected_connection_state", value: "connected", sortOrder: 1}
,
{id: null, key: "force_replay", value: "false", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _thresholds(self):
        return {
            'require_vcenter_connection': self.get_threshold_var('require_vcenter_connection', True, 'bool'),
            'expected_connection_state': self.get_threshold_var('expected_connection_state', 'connected', 'str'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        vpxa = metrics.get('vpxa') or {}
        return '\n'.join([
            'ESXi vCenter Agent 통신 상태 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- host_name: %s' % metrics.get('host_name', ''),
            '- managed_by_vcenter: %s' % metrics.get('managed_by_vcenter', ''),
            '- management_server_ip: %s' % metrics.get('management_server_ip', ''),
            '- connection_state: %s' % metrics.get('connection_state', ''),
            '- vpxa.exists: %s' % vpxa.get('exists', ''),
            '- vpxa.running: %s' % vpxa.get('running', ''),
            '- vpxa.policy: %s' % vpxa.get('policy', ''),
        ])

    def _state_summary(self, metrics, thresholds):
        vpxa = metrics.get('vpxa') or {}
        return ', '.join([
            'host=%s' % metrics.get('host_name', ''),
            'managed_by_vcenter=%s' % metrics.get('managed_by_vcenter', ''),
            'management_server_ip=%s' % (metrics.get('management_server_ip') or '없음'),
            'connection_state=%s (기준 %s)' % (
                metrics.get('connection_state'),
                thresholds['expected_connection_state'],
            ),
            'vpxa.exists=%s' % vpxa.get('exists', ''),
            'vpxa.running=%s' % vpxa.get('running', ''),
        ])

    def _build_message(self, metrics, thresholds, failed=None):
        current_state = self._state_summary(metrics, thresholds)
        if failed:
            return (
                'ESXi vCenter Agent 통신 상태가 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi vCenter Agent 통신 상태가 정상입니다. 현재 상태: %s. '
            'vCenter 관리 정보와 vpxa 서비스 상태가 모두 기준을 충족했습니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        managed = bool(metrics.get('managed_by_vcenter'))
        vpxa = metrics.get('vpxa') or {}

        if not managed and not thresholds['require_vcenter_connection']:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='단독 ESXi 운영 정책으로 vCenter 연결 점검 대상이 아닙니다.',
                raw_output=self._raw_output(metrics),
                message=(
                    'ESXi가 vCenter 관리 대상으로 확인되지 않아 대상미해당으로 분류했습니다. '
                    '현재 상태: %s.'
                ) % self._state_summary(metrics, thresholds),
            )

        failed = []
        if not managed:
            failed.append('vCenter 관리 서버 정보가 확인되지 않습니다.')
        if managed and not metrics.get('management_server_ip'):
            failed.append('management_server_ip가 비어 있습니다.')
        if metrics.get('connection_state') != thresholds['expected_connection_state']:
            failed.append('Connection State %s != %s' % (
                metrics.get('connection_state'),
                thresholds['expected_connection_state'],
            ))
        if not vpxa.get('exists'):
            failed.append('vpxa 서비스가 존재하지 않습니다.')
        elif not vpxa.get('running'):
            failed.append('vpxa 서비스가 실행 중이 아닙니다.')

        if failed:
            result = self.fail(
                'ESXi vCenter Agent 기준 미충족',
                message=self._build_message(metrics, thresholds, failed),
                raw_output=self._raw_output(metrics),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = ', '.join(failed)
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='vCenter 관리 서버 정보가 확인되고 vpxa 및 관리 연결 상태가 정상입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.vcenter_agent_status_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi vCenter Agent 조회 실패',
                message='VMwareHelper 기반 ESXi vCenter Agent 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi vCenter Agent 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
