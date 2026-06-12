# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

vmware

# application

esxi

# inspection_code

ESXI-STATUS-AGENT-SERVICE-01

# is_required

권고

# inspection_name

ESXi Agent 상태 확인

# inspection_content

하이퍼바이저와 해당 가상시스템을 관리하고 구성하는 Agent 상태 확인

# inspection_command

```bash
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper.agent_services_from_context()`를 사용한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostServiceSystem` 서비스 목록을 조회하고, `password`가 없거나 `force_replay=true`이면 `outputs/agent_services.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.agent_services_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
```
```

# inspection_output

```text
{
  "host_name": "localhost.rtnet",
  "services": [
    {
      "key": "hostd",
      "label": "hostd",
      "running": true,
      "policy": "on"
    },
    {
      "key": "vpxa",
      "label": "vpxa",
      "running": true,
      "policy": "on"
    }
  ],
  "missing_services": [],
  "stopped_services": []
}
```

# description

- ESXi의 `hostd`는 Host Client, vSphere API, VM 관리 작업을 처리하는 핵심 Host Agent이다.
- `vpxa`는 vCenter Agent이며, ESXi가 vCenter에 등록되어 관리되는 환경에서 vCenter와 통신하는 데 사용된다.
- ESXi 단독 운영 환경에서는 `vpxa`가 없거나 중지되어 있어도 정책상 대상미해당일 수 있으므로 vCenter 관리 여부와 함께 해석한다.
- `HostServiceSystem.serviceInfo.service`에서 서비스 목록, 실행 여부, 시작 정책을 확인한다.
- 일부 ESXi API 응답에서 `hostd`가 서비스 목록에 직접 노출되지 않을 수 있다. 이 경우 vSphere API 세션 자체가 `hostd`를 통해 성립하므로 공통 `VMwareHelper`가 `hostd (vSphere API session)` 항목을 실행 중으로 보정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- API에서 서비스 정보가 충분히 노출되지 않는 환경은 서비스 상태를 확인할 수 없으므로 확인 필요로 분류한다.
- `hostd`가 중지되어 있으면 ESXi 관리 기능과 VM 관리 작업에 영향이 있으므로 즉시 확인이 필요하다.
- vCenter 관리 대상 ESXi에서 `vpxa`가 중지되어 있으면 vCenter 연동, 인벤토리 갱신, 작업 전달에 문제가 생길 수 있다.

- **양호**: 필수 Agent 서비스가 존재하고 `hostd`가 실행 중이며, vCenter 관리 대상인 경우 `vpxa`도 실행 중인 경우
- **경고**: `hostd`가 없거나 중지되어 있거나, vCenter 관리 대상인데 `vpxa`가 없거나 중지된 경우
- **대상미해당**: 단독 ESXi 운영 정책이고 `vpxa` 점검을 요구하지 않는 경우. 기본 구현에서는 vCenter 관리 대상이 아닐 때 `vpxa`를 요구하지 않는다.
- **확인 필요**: ESXi API 인증, 서비스 목록 조회, 서비스 상태 해석이 불가능한 경우

# thresholds

[
    {id: null, key: "required_agent_services", value: "hostd", sortOrder: 0}
,
{id: null, key: "require_vpxa_when_managed", value: "true", sortOrder: 1}
,
{id: null, key: "force_replay", value: "false", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _list_threshold(self, key, default=''):
        raw = self.get_threshold_var(key, default, 'str')
        return [
            item.strip()
            for item in str(raw or '').replace('\r', '\n').replace('\n', ',').split(',')
            if item.strip()
        ]

    def _thresholds(self):
        return {
            'required_agent_services': self._list_threshold('required_agent_services', 'hostd'),
            'require_vpxa_when_managed': self.get_threshold_var('require_vpxa_when_managed', True, 'bool'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        lines = [
            'ESXi HostServiceSystem Agent 서비스 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- host_name: %s' % metrics.get('host_name', ''),
            '- managed_by_vcenter: %s' % metrics.get('managed_by_vcenter', ''),
            '- management_server_ip: %s' % metrics.get('management_server_ip', ''),
            '- connection_state: %s' % metrics.get('connection_state', ''),
            '- services:',
        ]
        for service in metrics.get('services') or []:
            lines.append(
                '  - {key} ({label}): running={running}, policy={policy}'.format(
                    key=service.get('key', ''),
                    label=service.get('label', ''),
                    running=service.get('running', ''),
                    policy=service.get('policy', ''),
                )
            )
        lines.extend([
            '- missing_services: %s' % ', '.join(metrics.get('missing_services') or []),
            '- stopped_services: %s' % ', '.join(metrics.get('stopped_services') or []),
        ])
        return '\n'.join(lines)

    def _required_services(self, metrics, thresholds):
        required = list(thresholds['required_agent_services'])
        if metrics.get('managed_by_vcenter') and thresholds['require_vpxa_when_managed']:
            if not any(service.lower() == 'vpxa' for service in required):
                required.append('vpxa')
        return required

    def _build_message(self, metrics, thresholds, failed=None):
        services = metrics.get('services') or []
        required_services = self._required_services(metrics, thresholds)
        running_services = sorted(
            service.get('key', '')
            for service in services
            if service.get('running') and service.get('key')
        )
        current_state = ', '.join([
            'host=%s' % metrics.get('host_name', ''),
            'managed_by_vcenter=%s' % metrics.get('managed_by_vcenter', ''),
            '필수 서비스=%s' % (', '.join(required_services) or '없음'),
            '실행 중 서비스=%s' % (', '.join(running_services) or '없음'),
        ])
        if failed:
            return (
                'ESXi Agent 서비스 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi Agent 서비스 상태가 정상입니다. 현재 상태: %s. '
            '필수 Agent 서비스가 모두 존재하고 실행 중입니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        services = metrics.get('services') or []
        service_map = {
            str(service.get('key') or '').lower(): service
            for service in services
        }

        missing = []
        stopped = []
        for service_name in thresholds['required_agent_services']:
            service = service_map.get(service_name.lower())
            if service is None:
                missing.append(service_name)
            elif not service.get('running'):
                stopped.append(service_name)

        if metrics.get('managed_by_vcenter') and thresholds['require_vpxa_when_managed']:
            vpxa = service_map.get('vpxa')
            if vpxa is None and 'vpxa' not in missing:
                missing.append('vpxa')
            elif vpxa is not None and not vpxa.get('running') and 'vpxa' not in stopped:
                stopped.append('vpxa')

        metrics['service_count'] = len(services)
        metrics['missing_services'] = missing
        metrics['stopped_services'] = stopped

        failed = []
        if not services:
            failed.append('Agent service 목록이 비어 있습니다.')
        if missing:
            failed.append('필수 Agent 서비스 누락: %s' % ', '.join(missing))
        if stopped:
            failed.append('중지된 Agent 서비스: %s' % ', '.join(stopped))

        if failed:
            result = self.fail(
                'ESXi Agent 서비스 기준 미충족',
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
            reasons='필수 Agent 서비스가 존재하고 실행 중입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.agent_services_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi Agent 서비스 조회 실패',
                message='VMwareHelper 기반 ESXi Agent 서비스 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi Agent 서비스 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
