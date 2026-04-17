# 영역
클라우드

# 세부 점검항목
ESXi VM 리스트 확인

# 점검 내용
VM(가상서버) 리스트 확인

# 구분
권고

# 명령어
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper`를 사용해 ESXi에 등록된 VM 목록을 조회한다.

```python
helper = self.vmware_helper
service_instance, disconnect = helper.connect()
try:
    virtual_machines = helper.vm_summaries(service_instance)
finally:
    disconnect(service_instance)
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
- vCenter 기준의 `govc ls /dc1/vm/*` 항목은 ESXi 직접 점검에서는 해당 ESXi 호스트에 등록된 VM 목록 확인으로 바꾼다.
- `VMwareHelper.vm_summaries()`는 pyVmomi의 `vim.VirtualMachine` 목록에서 VM 이름, UUID, 전원 상태를 수집한다.
- VM 이름이 비어 있거나 중복되거나 운영 기준상 필요한 VM이 누락되었는지 확인한다.
- VM 전원 상태는 운영 정책에 따라 해석한다. 운영 중이어야 하는 VM이 `poweredOff`이면 경고로 본다.
- 점검 대상 ESXi가 유지보수용이거나 VM이 없어야 하는 호스트라면 VM 수 0개가 정상일 수 있으므로 운영 정책과 함께 판단한다.

# 임계치
min_vm_count
required_vm_names
allowed_power_states

# 판단기준
- **양호**: VM 목록 조회가 성공하고 VM 이름, UUID, 전원 상태가 확인되며 운영 정책상 필요한 VM이 모두 존재하는 경우
- **경고**: VM 목록이 비어 있거나, 필수 VM이 누락되었거나, 운영 중이어야 하는 VM의 전원 상태가 기준과 다른 경우
- **확인 필요**: ESXi API 인증, VM 목록 조회, VM 상태 해석이 불가능한 경우
