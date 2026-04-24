# 영역
클라우드

# 세부 점검항목
ESXi VM 리스트 확인

# 점검 내용
VM(가상서버) 리스트 확인

# 구분
권고

# 명령어
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper.vm_summaries_from_context()`를 사용해 ESXi에 등록된 VM 목록을 조회한다. 실제 접속 정보의 `password`가 있으면 pyVmomi로 VM 목록을 조회하고, `password`가 없거나 `force_replay=true`이면 `outputs/vm_list.json` fixture를 읽어 같은 metrics로 판정한다.

```python
helper = self.vmware_helper
metrics = helper.vm_summaries_from_context(source="pyvmomi")
```

# 출력 결과
```json
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

# 설명
- vCenter 데이터센터 경로 기준 VM 조회 항목은 ESXi 직접 점검에서는 해당 ESXi 호스트에 등록된 VM 목록 확인으로 바꾼다.
- `VMwareHelper.vm_summaries()`는 pyVmomi의 `vim.VirtualMachine` 목록에서 VM 이름, UUID, 전원 상태를 수집한다.
- VM 이름이 비어 있거나 중복되거나 운영 기준상 필요한 VM이 누락되었는지 확인한다.
- `required_vm_names`는 운영 정책이 있을 때만 지정한다. 기본 구현은 빈 값으로 두어 특정 VM 이름을 강제하지 않는다.
- VM 전원 상태는 운영 정책에 따라 해석한다. 기본 허용 상태는 `poweredOn,poweredOff,suspended`이며, 운영 중이어야 하는 VM만 강제하려면 `allowed_power_states` 또는 `required_vm_names` 기준을 조정한다.
- output fixture 처리는 공통 `VMwareHelper`가 담당하며 개별 `script.py`에서는 fixture 파일을 직접 읽지 않는다.
- 점검 대상 ESXi가 유지보수용이거나 VM이 없어야 하는 호스트라면 VM 수 0개가 정상일 수 있으므로 운영 정책과 함께 판단한다.

# 임계치
min_vm_count
required_vm_names
allowed_power_states
force_replay

# 판단기준
- **양호**: VM 목록 조회가 성공하고 VM 이름, UUID, 전원 상태가 확인되며 운영 정책상 필요한 VM이 모두 존재하고 전원 상태가 허용 기준에 포함되는 경우
- **경고**: VM 목록이 비어 있거나, 필수 VM이 누락되었거나, 운영 중이어야 하는 VM의 전원 상태가 기준과 다른 경우
- **확인 필요**: ESXi API 인증, VM 목록 조회, VM 상태 해석이 불가능한 경우
