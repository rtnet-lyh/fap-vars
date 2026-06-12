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

ESXI-STATUS-VM-LIST-01

# is_required

권고

# inspection_name

ESXi VM 리스트 확인

# inspection_content

VM(가상서버) 리스트 확인

# inspection_command

```bash
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper.vm_summaries_from_context()`를 사용해 ESXi에 등록된 VM 목록을 조회한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 VM 목록을 조회하고, `password`가 없거나 `force_replay=true`이면 `outputs/vm_list.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.vm_summaries_from_context(source="pyvmomi")
```
```

# inspection_output

```text
{
  "vm_count": 3,
  "virtual_machines": [
    {
      "name": "app01",
      "uuid": "421a5a7d-0a1b-4c1d-9a10-000000000001",
      "power_state": "poweredOn"
    },
    {
      "name": "db01",
      "uuid": "421a5a7d-0a1b-4c1d-9a10-000000000002",
      "power_state": "poweredOn"
    },
    {
      "name": "test01",
      "uuid": "421a5a7d-0a1b-4c1d-9a10-000000000003",
      "power_state": "poweredOff"
    }
  ],
  "abnormal_vms": []
}
```

# description

- vCenter 데이터센터 경로 기준 VM 조회 항목은 ESXi 직접 점검에서는 해당 ESXi 호스트에 등록된 VM 목록 확인으로 바꾼다.
- `VMwareHelper.vm_summaries()`는 pyVmomi의 `vim.VirtualMachine` 목록에서 VM 이름, UUID, 전원 상태를 수집한다.
- VM 이름이 비어 있거나 중복되거나 운영 기준상 필요한 VM이 누락되었는지 확인한다.
- `required_vm_names`는 운영 정책이 있을 때만 지정한다. 기본 구현은 빈 값으로 두어 특정 VM 이름을 강제하지 않는다.
- VM 전원 상태는 운영 정책에 따라 해석한다. 기본 허용 상태는 `poweredOn,poweredOff,suspended`이며, 운영 중이어야 하는 VM만 강제하려면 `allowed_power_states` 또는 `required_vm_names` 기준을 조정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- 점검 대상 ESXi가 유지보수용이거나 VM이 없어야 하는 호스트라면 VM 수 0개가 정상일 수 있으므로 운영 정책과 함께 판단한다.

- **양호**: VM 목록 조회가 성공하고 VM 이름, UUID, 전원 상태가 확인되며 운영 정책상 필요한 VM이 모두 존재하고 전원 상태가 허용 기준에 포함되는 경우
- **경고**: VM 목록이 비어 있거나, 필수 VM이 누락되었거나, 운영 중이어야 하는 VM의 전원 상태가 기준과 다른 경우
- **확인 필요**: ESXi API 인증, VM 목록 조회, VM 상태 해석이 불가능한 경우

# thresholds

[
    {id: null, key: "min_vm_count", value: "1", sortOrder: 0}
,
{id: null, key: "required_vm_names", value: "", sortOrder: 1}
,
{id: null, key: "allowed_power_states", value: "poweredOn,poweredOff,suspended", sortOrder: 2}
,
{id: null, key: "force_replay", value: "false", sortOrder: 3}
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
            'min_vm_count': self.get_threshold_var('min_vm_count', 1, 'int'),
            'required_vm_names': self._list_threshold('required_vm_names', ''),
            'allowed_power_states': self._list_threshold('allowed_power_states', 'poweredOn,poweredOff,suspended'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        lines = [
            'ESXi VM 목록 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- vm_count: %s' % metrics.get('vm_count', ''),
            '- virtual_machines:',
        ]
        for vm in metrics.get('virtual_machines') or []:
            lines.append(
                '  - {name}: uuid={uuid}, power_state={power_state}'.format(
                    name=vm.get('name', ''),
                    uuid=vm.get('uuid', ''),
                    power_state=vm.get('power_state', ''),
                )
            )
        lines.extend([
            '- missing_required_vms: %s' % ', '.join(metrics.get('missing_required_vms') or []),
            '- abnormal_vms: %s' % ', '.join(vm.get('name', '') for vm in metrics.get('abnormal_vms') or []),
        ])
        return '\n'.join(lines)

    def _format_vm_states(self, vms):
        values = []
        for vm in vms or []:
            values.append(
                '%s=%s' % (
                    vm.get('name', '') or '(이름없음)',
                    vm.get('power_state', ''),
                )
            )
        return ', '.join(values) or '없음'

    def _build_message(self, metrics, thresholds, failed=None):
        current_state = ', '.join([
            'vm_count=%s (기준 %s 이상)' % (
                metrics.get('vm_count', 0),
                thresholds['min_vm_count'],
            ),
            '필수 VM=%s' % (', '.join(thresholds['required_vm_names']) or '없음'),
            '누락 VM=%s' % (', '.join(metrics.get('missing_required_vms') or []) or '없음'),
            '허용 전원 상태=%s' % (', '.join(thresholds['allowed_power_states']) or '없음'),
            '비정상 VM=%s' % self._format_vm_states(metrics.get('abnormal_vms')),
            '중복 VM=%s' % (', '.join(metrics.get('duplicate_names') or []) or '없음'),
            '이름 없는 VM=%s건' % metrics.get('empty_name_count', 0),
        ])
        if failed:
            return (
                'ESXi VM 목록 상태가 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi VM 목록 상태가 정상입니다. 현재 상태: %s. '
            'VM 수, 필수 VM 목록, 전원 상태 기준이 모두 충족되었습니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        vms = metrics.get('virtual_machines') or []
        names = [str(vm.get('name') or '').strip() for vm in vms]
        name_set = {name for name in names if name}
        allowed_states = {state.lower() for state in thresholds['allowed_power_states']}

        missing_required = [
            name for name in thresholds['required_vm_names']
            if name not in name_set
        ]
        abnormal_vms = [
            vm for vm in vms
            if str(vm.get('power_state') or '').lower() not in allowed_states
        ]
        empty_name_count = len([name for name in names if not name])
        duplicate_names = sorted({
            name for name in name_set
            if names.count(name) > 1
        })

        metrics['vm_count'] = len(vms)
        metrics['missing_required_vms'] = missing_required
        metrics['abnormal_vms'] = abnormal_vms
        metrics['empty_name_count'] = empty_name_count
        metrics['duplicate_names'] = duplicate_names

        failed = []
        if len(vms) < thresholds['min_vm_count']:
            failed.append('VM 수 %s < %s' % (len(vms), thresholds['min_vm_count']))
        if missing_required:
            failed.append('필수 VM 누락: %s' % ', '.join(missing_required))
        if abnormal_vms:
            failed.append('허용되지 않은 전원 상태 VM: %s' % ', '.join(
                '%s=%s' % (vm.get('name', ''), vm.get('power_state', ''))
                for vm in abnormal_vms
            ))
        if empty_name_count:
            failed.append('이름이 비어 있는 VM %s개 확인' % empty_name_count)
        if duplicate_names:
            failed.append('중복 VM 이름 확인: %s' % ', '.join(duplicate_names))

        if failed:
            result = self.fail(
                'ESXi VM 목록 기준 미충족',
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
            reasons='VM 목록 조회가 성공했고 필수 VM과 전원 상태 기준을 충족합니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.vm_summaries_from_context(source='pyvmomi')
        except Exception as exc:
            return self.fail(
                'ESXi VM 목록 조회 실패',
                message='VMwareHelper 기반 ESXi VM 목록 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi VM 리스트 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
