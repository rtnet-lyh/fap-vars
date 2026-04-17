# 영역
클라우드

# 세부 점검항목
데이터스토어 Path 확인

# 점검 내용
하이퍼바이저 연결된 데이터스토어 경로 확인

# 구분
권고

# 명령어
기본 점검은 `inspection_runtime/items/common/helpers/vmware.py`의 `VMwareHelper`를 사용해 ESXi에 연결된 Datastore 목록을 조회한다.

```python
helper = self.vmware_helper
service_instance, disconnect = helper.connect()
try:
    datastores = helper.datastore_summaries(service_instance)
finally:
    disconnect(service_instance)
```

# 출력 결과
```json
{
  "datastore_count": 2,
  "datastores": [
    {
      "name": "datastore1",
      "type": "VMFS",
      "url": "/vmfs/volumes/datastore1",
      "accessible": true,
      "capacity_bytes": 1099511627776,
      "free_space_bytes": 549755813888,
      "usage_percent": 50.0
    },
    {
      "name": "iso-nfs",
      "type": "NFS",
      "url": "/vmfs/volumes/iso-nfs",
      "accessible": true,
      "capacity_bytes": 214748364800,
      "free_space_bytes": 161061273600,
      "usage_percent": 25.0
    }
  ],
  "inaccessible_datastores": [],
  "overused_datastores": []
}
```

# 설명
- vCenter 기준의 datastore path 확인은 ESXi 직접 점검에서는 해당 ESXi 호스트에 연결된 Datastore 목록과 접근 가능 여부 확인으로 바꾼다.
- `VMwareHelper.datastore_summaries()`는 pyVmomi의 `vim.Datastore.summary`에서 이름, 타입, 경로 URL, 접근 가능 여부, 전체 용량, 여유 용량을 수집한다.
- `accessible`이 `false`인 Datastore는 마운트 또는 스토리지 연결 문제 가능성이 있으므로 점검이 필요하다.
- `url` 또는 datastore path가 운영 기준과 다르면 잘못된 마운트 또는 재구성 필요 여부를 확인한다.
- 사용률이 높거나 여유 공간이 부족한 Datastore는 VM 스냅샷, ISO, 로그, 템플릿 정리 또는 용량 증설을 검토한다.
- API에서 확인되는 Datastore `url`, `accessible`, `capacity`, `freeSpace` 값을 기준으로 경로와 용량 상태를 판단한다.

# 임계치
max_datastore_usage_percent
min_datastore_free_gib
required_datastore_names
require_accessible

# 판단기준
- **양호**: 모든 운영 대상 Datastore가 접근 가능하고 사용률과 여유 용량이 기준을 충족하며 필수 Datastore가 모두 확인되는 경우
- **경고**: 접근 불가 Datastore가 있거나, 사용률이 임계치를 초과하거나, 여유 용량이 부족하거나, 필수 Datastore가 누락된 경우
- **확인 필요**: ESXi API 인증, Datastore 목록 조회, 용량 계산 또는 경로 해석이 불가능한 경우
