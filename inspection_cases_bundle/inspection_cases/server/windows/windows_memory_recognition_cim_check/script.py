# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


CHECK_KIND = 'memory_recognition'
ITEM_NAME = '메모리 상태 확인'
PS_COMMAND = "$ErrorActionPreference = 'Stop'; $mem = Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, DeviceLocator, Capacity, Speed, Manufacturer, PartNumber; $total = ($mem | Measure-Object -Property Capacity -Sum).Sum; [pscustomobject]@{ dimm_count = @($mem).Count; total_physical_memory_bytes = [int64]$total; modules = $mem } | ConvertTo-Json -Compress -Depth 6"
MANUAL_MESSAGE = ''


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def _thresholds(self):
        return {
            'max_cpu_usage_percent': self.get_threshold_var('max_cpu_usage_percent', 80.0, 'float'),
            'max_memory_usage_percent': self.get_threshold_var('max_memory_usage_percent', 80.0, 'float'),
            'max_pagefile_usage_percent': self.get_threshold_var('max_pagefile_usage_percent', 50.0, 'float'),
            'max_filesystem_usage_percent': self.get_threshold_var('max_filesystem_usage_percent', 80.0, 'float'),
            'max_avg_disk_sec': self.get_threshold_var('max_avg_disk_sec', 0.02, 'float'),
            'max_ping_loss_percent': self.get_threshold_var('max_ping_loss_percent', 0.0, 'float'),
            'max_event_count': self.get_threshold_var('max_event_count', 0, 'int'),
            'require_nic_team': self.get_threshold_var('require_nic_team', False, 'bool'),
        }

    def _load_json(self, text):
        parsed = json.loads(text or '{}')
        if isinstance(parsed, list):
            return {'items': parsed}
        return parsed

    def run(self):
        if MANUAL_MESSAGE:
            return self.not_applicable(MANUAL_MESSAGE, raw_output=MANUAL_MESSAGE)

        rc, out, err = self._run_ps(PS_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.not_applicable('WinRM 실행 환경을 사용할 수 없습니다.', raw_output=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{ITEM_NAME} PowerShell 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        try:
            metrics = self._load_json(out)
        except Exception:
            return self.fail('점검 결과 파싱 실패', message='PowerShell JSON 출력 형식을 해석할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        return self._evaluate(metrics)

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        kind = CHECK_KIND

        if kind == 'cpu_usage':
            value = float(metrics.get('cpu_usage_percent') or 0)
            if value > thresholds['max_cpu_usage_percent']:
                return self.fail('CPU 사용률 임계치 초과', message=f'CPU 사용률이 기준치를 초과했습니다: current={value}%, max={thresholds["max_cpu_usage_percent"]}%')
            return self.ok(metrics=metrics, thresholds={'max_cpu_usage_percent': thresholds['max_cpu_usage_percent']}, reasons='CPU 사용률이 임계치 이하입니다.', message=f'CPU 사용률 점검 정상: {value}%')

        if kind == 'memory_usage':
            value = float(metrics.get('memory_usage_percent') or 0)
            if value > thresholds['max_memory_usage_percent']:
                return self.fail('메모리 사용률 임계치 초과', message=f'메모리 사용률이 기준치를 초과했습니다: current={value}%, max={thresholds["max_memory_usage_percent"]}%')
            return self.ok(metrics=metrics, thresholds={'max_memory_usage_percent': thresholds['max_memory_usage_percent']}, reasons='메모리 사용률이 임계치 이하입니다.', message=f'메모리 사용률 점검 정상: {value}%')

        if kind in ('pagefile_usage', 'disk_swap'):
            value = float(metrics.get('pagefile_usage_percent') or 0)
            if int(metrics.get('pagefile_count') or 0) <= 0:
                return self.warn(metrics=metrics, thresholds={'max_pagefile_usage_percent': thresholds['max_pagefile_usage_percent']}, reasons='페이지 파일 항목이 확인되지 않아 운영 정책 확인이 필요합니다.', message='페이지 파일 항목이 확인되지 않습니다.')
            if value > thresholds['max_pagefile_usage_percent']:
                return self.fail('페이지 파일 사용률 임계치 초과', message=f'페이지 파일 사용률이 기준치를 초과했습니다: current={value}%, max={thresholds["max_pagefile_usage_percent"]}%')
            return self.ok(metrics=metrics, thresholds={'max_pagefile_usage_percent': thresholds['max_pagefile_usage_percent']}, reasons='페이지 파일 사용률이 임계치 이하입니다.', message=f'페이지 파일 점검 정상: {value}%')

        if kind == 'filesystem_usage':
            drives = metrics.get('drives') or []
            over = [d for d in drives if float(d.get('usage_percent') or 0) > thresholds['max_filesystem_usage_percent']]
            if not drives:
                return self.fail('파일시스템 정보 없음', message='고정 디스크 드라이브 정보를 찾지 못했습니다.')
            if over:
                return self.fail('파일시스템 사용률 임계치 초과', message='일부 드라이브 사용률이 기준치를 초과했습니다: ' + ', '.join(f"{d.get('device_id')}={d.get('usage_percent')}%" for d in over))
            return self.ok(metrics=metrics, thresholds={'max_filesystem_usage_percent': thresholds['max_filesystem_usage_percent']}, reasons='모든 드라이브 사용률이 임계치 이하입니다.', message='파일시스템 사용량 점검 정상')

        if kind == 'disk_io':
            read = float(metrics.get('avg_disk_sec_read') or 0)
            write = float(metrics.get('avg_disk_sec_write') or 0)
            if read > thresholds['max_avg_disk_sec'] or write > thresholds['max_avg_disk_sec']:
                return self.fail('Disk I/O 지연 임계치 초과', message=f'Disk I/O 지연이 기준치를 초과했습니다: read={read}, write={write}, max={thresholds["max_avg_disk_sec"]}')
            return self.ok(metrics=metrics, thresholds={'max_avg_disk_sec': thresholds['max_avg_disk_sec']}, reasons='Disk I/O 지연 값이 임계치 이하입니다.', message='Disk I/O 점검 정상')

        if kind.startswith('event_'):
            count = int(metrics.get('event_count') or 0)
            if count > thresholds['max_event_count']:
                return self.warn(metrics=metrics, thresholds={'max_event_count': thresholds['max_event_count']}, reasons=f'최근 이벤트 로그에서 관련 경고/오류 {count}건이 확인되었습니다.', message=f'이벤트 로그 추가 확인 필요: {count}건')
            return self.ok(metrics=metrics, thresholds={'max_event_count': thresholds['max_event_count']}, reasons='최근 이벤트 로그에서 기준 초과 오류가 확인되지 않았습니다.', message='이벤트 로그 점검 정상')

        if kind == 'disk_recognition':
            if int(metrics.get('disk_count') or 0) <= 0:
                return self.fail('디스크 미인식', message='Windows에서 인식된 디스크가 없습니다.')
            if int(metrics.get('abnormal_disk_count') or 0) > 0:
                return self.fail('디스크 상태 비정상', message='Status가 OK가 아닌 디스크가 확인되었습니다.')
            return self.ok(metrics=metrics, reasons='디스크가 정상 인식되었습니다.', message='디스크 인식 점검 정상')

        if kind == 'disk_redundancy':
            if not metrics.get('storage_module_available'):
                return self.not_applicable('Storage PowerShell 모듈 또는 지원 장치가 없어 디스크 이중화 상태는 수동 확인이 필요합니다.')
            bad = []
            for group in ('physical_disks', 'virtual_disks'):
                for item in metrics.get(group) or []:
                    if str(item.get('HealthStatus') or '').lower() not in ('healthy', 'ok'):
                        bad.append(item.get('FriendlyName') or group)
            if bad:
                return self.fail('디스크 이중화 상태 비정상', message='HealthStatus 비정상 디스크가 확인되었습니다: ' + ', '.join(bad))
            return self.ok(metrics=metrics, reasons='Storage 모듈 기준 디스크 HealthStatus가 정상입니다.', message='디스크 이중화 상태 점검 정상')

        if kind == 'cpu_core':
            if int(metrics.get('logical_processor_count') or 0) <= 0:
                return self.fail('CPU 코어 미인식', message='논리 CPU 수가 0으로 표시됩니다.')
            if int(metrics.get('abnormal_processor_count') or 0) > 0:
                return self.warn(metrics=metrics, reasons='Status가 OK가 아닌 프로세서 항목이 확인되었습니다.', message='CPU 코어 상태 추가 확인 필요')
            return self.ok(metrics=metrics, reasons='CPU 코어 정보가 정상 인식되었습니다.', message='코어별 상태 점검 정상')

        if kind == 'memory_recognition':
            if int(metrics.get('dimm_count') or 0) <= 0 or int(metrics.get('total_physical_memory_bytes') or 0) <= 0:
                return self.fail('물리 메모리 미인식', message='물리 메모리 모듈 또는 총 용량이 확인되지 않습니다.')
            return self.ok(metrics=metrics, reasons='물리 메모리 모듈과 총 용량이 확인되었습니다.', message='메모리 상태 확인 정상')

        if kind == 'kernel_parameter':
            if not metrics.get('get_net_tcp_setting_available'):
                return self.not_applicable('Get-NetTCPSetting을 사용할 수 없어 Windows TCP 파라미터는 수동 확인이 필요합니다.')
            return self.ok(metrics=metrics, reasons='Windows TCP 설정 조회가 정상 수행되었습니다.', message='Kernel Parameter 대체 점검 정상')

        if kind == 'network_link':
            if int(metrics.get('adapter_count') or 0) <= 0:
                return self.fail('네트워크 어댑터 미인식', message='네트워크 어댑터가 확인되지 않습니다.')
            if int(metrics.get('down_adapter_count') or 0) > 0:
                return self.warn(metrics=metrics, reasons='Down 상태 네트워크 어댑터가 확인되었습니다.', message='네트워크 링크 상태 추가 확인 필요')
            return self.ok(metrics=metrics, reasons='네트워크 어댑터 링크가 Up 상태입니다.', message='NW 링크 상태 점검 정상')

        if kind == 'nic_teaming':
            if not metrics.get('get_net_lbfo_team_available'):
                return self.not_applicable('NIC Teaming cmdlet을 사용할 수 없어 NIC 이중화는 수동 확인이 필요합니다.')
            if thresholds['require_nic_team'] and int(metrics.get('team_count') or 0) <= 0:
                return self.fail('NIC 이중화 미구성', message='NIC Team 구성이 확인되지 않습니다.')
            if int(metrics.get('team_count') or 0) <= 0:
                return self.warn(metrics=metrics, thresholds={'require_nic_team': thresholds['require_nic_team']}, reasons='NIC Team 구성이 없습니다. 단일 NIC 운영 정책이면 예외 처리 가능합니다.', message='NIC 이중화 구성 없음')
            return self.ok(metrics=metrics, thresholds={'require_nic_team': thresholds['require_nic_team']}, reasons='NIC Team 구성이 확인되었습니다.', message='NIC 이중화 점검 정상')

        if kind == 'ping_loss':
            value = float(metrics.get('loss_percent') or 0)
            if value > thresholds['max_ping_loss_percent']:
                return self.fail('Ping Loss 임계치 초과', message=f'Ping 손실률이 기준치를 초과했습니다: current={value}%, max={thresholds["max_ping_loss_percent"]}%')
            return self.ok(metrics=metrics, thresholds={'max_ping_loss_percent': thresholds['max_ping_loss_percent']}, reasons='Ping 손실률이 임계치 이하입니다.', message=f'Ping Loss 점검 정상: {value}%')

        if kind == 'cluster_service':
            if not metrics.get('service_exists'):
                return self.not_applicable('Failover Cluster 서비스가 없어 클러스터 데몬 점검은 대상미해당입니다.')
            if str(metrics.get('service_status') or '').lower() != 'running':
                return self.fail('Cluster 서비스 중지', message=f'ClusSvc 상태가 Running이 아닙니다: {metrics.get("service_status")}')
            return self.ok(metrics=metrics, reasons='ClusSvc 서비스가 Running 상태입니다.', message='Cluster 데몬 상태 점검 정상')

        if kind == 'shared_volume':
            if not metrics.get('cluster_shared_volume_available'):
                return self.not_applicable('Failover Cluster 모듈 또는 CSV 구성이 없어 공유 볼륨 점검은 대상미해당입니다.')
            return self.ok(metrics=metrics, reasons='Cluster Shared Volume 조회가 정상 수행되었습니다.', message='공유 볼륨 상태 점검 정상')

        if kind == 'mpio_path':
            if not metrics.get('mpio_installed'):
                return self.not_applicable('Multipath-IO 기능이 설치되어 있지 않아 Path 이중화 점검은 대상미해당입니다.')
            return self.ok(metrics=metrics, reasons='MPIO 기능과 mpclaim 조회가 수행되었습니다.', message='Path 이중화 점검 정상')

        return self.ok(metrics=metrics, reasons='Windows 예방점검 명령이 정상 수행되었습니다.', message=f'{ITEM_NAME} 점검 정상')


CHECK_CLASS = Check
