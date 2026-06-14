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

ESXI-STATUS-API-01

# is_required

권고

# inspection_name

ESXi 상태 확인

# inspection_content

하이퍼바이저 점검

# inspection_command

```bash
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper`를 사용한다.

```python
helper = self.vmware_helper
metrics = helper.host_summary_metrics_from_context(
    default_host_moid="ha-host",
    source="pyvmomi",
)
```

output 데이터 테스트는 같은 헬퍼가 `HostSystem.summary` XML fixture를 읽어 처리한다.
```

# inspection_output

```text
{
  "name": "localhost.rtnet",
  "full_name": "VMware ESXi 8.0.3 build-24022510",
  "version": "8.0.3",
  "build": "24022510",
  "api_version": "8.0.3.0",
  "uuid": "63ca02ce-3610-11e6-bf03-749d8f88c836",
  "vendor": "Huawei",
  "model": "RH2288H V3",
  "cpu_model": "Intel(R) Xeon(R) CPU E5-2620 v3 @ 2.40GHz",
  "cpu_usage_mhz": 2297,
  "cpu_capacity_mhz": 28728,
  "cpu_usage_percent": 8.0,
  "memory_usage_mib": 14850,
  "memory_total_mib": 15981,
  "memory_usage_percent": 92.92,
  "power_state": "poweredOn",
  "connection_state": "connected",
  "overall_status": "gray",
  "source": "pyvmomi"
}
```

# description

- ESXi 호스트에 직접 API로 접속해 하이퍼바이저 상태를 확인한다. 점검 대상은 vCenter가 아니라 ESXi이다.
- 기본 점검 경로는 공통 `VMwareHelper`의 `host_summary_metrics_from_context()`이다.
- `VMwareHelper.connect()`는 `host`, `port`, `username`, `password`, `disable_ssl_verification` 값을 case 입력 또는 credential data에서 읽어 ESXi/vCenter API 세션을 생성한다.
- 실제 접속 정보의 `password`가 있으면 pyVmomi로 ESXi에 접속해 `HostSystem.summary`를 조회한다.
- 실제 접속 정보의 `password`가 없거나 `force_replay=true`이면 output XML fixture를 읽어 같은 metrics 변환과 판정 로직을 수행한다.
- output fixture 처리는 공통 `VMwareHelper`에서 담당하며, 개별 `script.py`에는 테스트 전용 XML 파싱 코드를 두지 않는다.
- pyVmomi 경로에서는 `HostSystem.summary`의 `hardware`, `runtime`, `quickStats`, `config.product` 값을 표준 metrics로 변환한다.
- 단독 ESXi 접속 환경에서 호스트 관리 객체 ID는 일반적으로 `ha-host`이다. 다른 관리 객체를 점검해야 하면 `host_moid` 또는 `host_name`으로 대상을 지정한다.
- CPU Usage: CPU 사용률이 80% 이하인지 확인하며, 초과 시 성능 점검이 필요.
- Memory Usage: 메모리 사용률이 80% 이하인지 확인하며, 초과 시 메모리 추가 또는 최적화가 필요.
- Power State: 호스트가 "poweredOn" 상태인지 확인하며, 꺼져 있는 경우 전원 상태 점검이 필요.
- Connection State: 호스트가 관리 시스템과 정상적으로 연결되어 있는지 확인하며, 연결이 끊긴 경우 점검이 필요.
- `cpu_usage_percent`는 `summary.quickStats.overallCpuUsage / (summary.hardware.cpuMhz * summary.hardware.numCpuCores) * 100`으로 계산한다.
- `memory_usage_percent`는 `summary.quickStats.overallMemoryUsage / (summary.hardware.memorySize / 1024 / 1024) * 100`으로 계산한다.

- **양호**: `cpu_usage_percent`와 `memory_usage_percent`가 각각 `max_cpu_usage_percent`, `max_memory_usage_percent` 이하이고, `power_state`가 `expected_power_state`, `connection_state`가 `expected_connection_state`와 일치하는 경우
- **경고**: CPU 또는 메모리 사용률이 기준을 초과하거나, 전원 상태 또는 연결 상태가 정상 기준과 다른 경우
- **확인 필요**: ESXi API 인증, pyVmomi 세션 생성, output fixture 로드, 호스트 요약 조회 또는 결과 계산이 불가능한 경우

# thresholds

[
    {id: null, key: "max_cpu_usage_percent", value: "80", sortOrder: 0}
,
{id: null, key: "max_memory_usage_percent", value: "80", sortOrder: 1}
,
{id: null, key: "expected_power_state", value: "poweredOn", sortOrder: 2}
,
{id: null, key: "expected_connection_state", value: "connected", sortOrder: 3}
,
{id: null, key: "force_replay", value: "false", sortOrder: 4}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _thresholds(self):
        return {
            'max_cpu_usage_percent': self.get_threshold_var('max_cpu_usage_percent', 80.0, 'float'),
            'max_memory_usage_percent': self.get_threshold_var('max_memory_usage_percent', 80.0, 'float'),
            'expected_power_state': self.get_threshold_var('expected_power_state', 'poweredOn', 'str'),
            'expected_connection_state': self.get_threshold_var('expected_connection_state', 'connected', 'str'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        return '\n'.join([
            'ESXi HostSystem.summary API 조회 결과',
            '- source: {source}',
            '- name: {name}',
            '- full_name: {full_name}',
            '- api_version: {api_version}',
            '- vendor/model: {vendor} / {model}',
            '- cpu_model: {cpu_model}',
            '- cpu_usage: {cpu_usage_percent}% ({cpu_usage_mhz}/{cpu_capacity_mhz} MHz)',
            '- memory_usage: {memory_usage_percent}% ({memory_usage_mib}/{memory_total_mib} MiB)',
            '- power_state: {power_state}',
            '- connection_state: {connection_state}',
            '- overall_status: {overall_status}',
        ]).format(**metrics)

    def _build_message(self, metrics, thresholds, failed=None):
        current_state = ', '.join([
            'host=%s' % metrics.get('name', ''),
            'CPU %.2f%% (기준 %.2f%% 이하)' % (
                metrics['cpu_usage_percent'],
                thresholds['max_cpu_usage_percent'],
            ),
            '메모리 %.2f%% (기준 %.2f%% 이하)' % (
                metrics['memory_usage_percent'],
                thresholds['max_memory_usage_percent'],
            ),
            '전원 상태 %s (기준 %s)' % (
                metrics['power_state'],
                thresholds['expected_power_state'],
            ),
            '연결 상태 %s (기준 %s)' % (
                metrics['connection_state'],
                thresholds['expected_connection_state'],
            ),
        ])
        if failed:
            return (
                'ESXi 상태 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi 상태 확인이 정상입니다. 현재 상태: %s. '
            'CPU/메모리 사용률과 전원/연결 상태가 모두 기준을 충족했습니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        failed = []

        if metrics['cpu_usage_percent'] > thresholds['max_cpu_usage_percent']:
            failed.append('CPU Usage %.2f%% > %.2f%%' % (
                metrics['cpu_usage_percent'],
                thresholds['max_cpu_usage_percent'],
            ))
        if metrics['memory_usage_percent'] > thresholds['max_memory_usage_percent']:
            failed.append('Memory Usage %.2f%% > %.2f%%' % (
                metrics['memory_usage_percent'],
                thresholds['max_memory_usage_percent'],
            ))
        if metrics['power_state'] != thresholds['expected_power_state']:
            failed.append('Power State %s != %s' % (
                metrics['power_state'],
                thresholds['expected_power_state'],
            ))
        if metrics['connection_state'] != thresholds['expected_connection_state']:
            failed.append('Connection State %s != %s' % (
                metrics['connection_state'],
                thresholds['expected_connection_state'],
            ))

        if failed:
            result = self.fail(
                'ESXi 상태 기준 미충족',
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
            reasons='CPU/Memory 사용률이 기준 이하이고 Power/Connection 상태가 정상입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.host_summary_metrics_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi API 점검 실패',
                message='VMwareHelper 기반 ESXi 상태 API 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi 상태 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
