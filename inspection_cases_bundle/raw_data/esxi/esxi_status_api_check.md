# 영역
클라우드

# 세부 점검항목
ESXi 상태 확인

# 점검 내용
하이퍼바이저 점검

# 구분
권고

# 명령어
```http
POST https://<esxi_host>/sdk
SOAPAction: urn:vim25
Request: RetrieveServiceContent

POST https://<esxi_host>/sdk
SOAPAction: urn:vim25/<api_version>
Request: Login(SessionManager)

POST https://<esxi_host>/sdk
SOAPAction: urn:vim25/<api_version>
Request: RetrievePropertiesEx(HostSystem:ha-host, pathSet=summary)
```

```sh
ESXI_HOST="https://<esxi_host>"
```

# 출력 결과
```json
{
  "name": "localhost.rtnet",
  "full_name": "VMware ESXi 8.0.3 build-24022510",
  "version": "8.0.3",
  "build": "24022510",
  "api_version": "8.0.3.0",
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
  "overall_status": "gray"
}
```

# 설명
- ESXi 호스트에 직접 HTTPS API로 접속해 하이퍼바이저 상태를 확인한다. 점검 대상은 vCenter가 아니라 ESXi이다.
- 대상 ESXi에서 VI JSON REST 경로가 지원되지 않을 수 있으므로, ESXi Host Client와 동일하게 `/sdk` SOAP API를 사용한다.
- `RetrieveServiceContent` 응답의 `about.apiVersion`을 사용해 이후 SOAPAction 값을 동적으로 구성한다.
- `Login` 요청으로 인증 세션 쿠키를 생성한 뒤 `RetrievePropertiesEx` 요청으로 `HostSystem.summary`를 조회한다.
- 단독 ESXi 접속 환경에서 호스트 관리 객체 ID는 일반적으로 `ha-host`이다.
- CPU Usage: CPU 사용률이 80% 이하인지 확인하며, 초과 시 성능 점검이 필요.
- Memory Usage: 메모리 사용률이 80% 이하인지 확인하며, 초과 시 메모리 추가 또는 최적화가 필요.
- Power State: 호스트가 "poweredOn" 상태인지 확인하며, 꺼져 있는 경우 전원 상태 점검이 필요.
- Connection State: 호스트가 관리 시스템과 정상적으로 연결되어 있는지 확인하며, 연결이 끊긴 경우 점검이 필요.
- `cpu_usage_percent`는 `summary.quickStats.overallCpuUsage / (summary.hardware.cpuMhz * summary.hardware.numCpuCores) * 100`으로 계산한다.
- `memory_usage_percent`는 `summary.quickStats.overallMemoryUsage / (summary.hardware.memorySize / 1024 / 1024) * 100`으로 계산한다.

# 임계치
max_cpu_usage_percent
max_memory_usage_percent
expected_power_state
expected_connection_state

# 판단기준
- **양호**: `cpu_usage_percent`와 `memory_usage_percent`가 각각 80% 이하이고, `power_state`가 `poweredOn`, `connection_state`가 `connected`인 경우
- **경고**: CPU 또는 메모리 사용률이 80%를 초과하거나, 전원 상태 또는 연결 상태가 정상 기준과 다른 경우
- **확인 필요**: ESXi API 인증, 세션 생성, 호스트 요약 조회 또는 결과 계산이 불가능한 경우
