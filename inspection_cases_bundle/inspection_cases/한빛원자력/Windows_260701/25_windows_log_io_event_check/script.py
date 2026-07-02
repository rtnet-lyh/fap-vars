# -*- coding: utf-8 -*-

import json
import re

from items.common._base import BaseCheck


CHECK_COMMAND = "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match 'disk|storport|stornvme|nvme|ntfs|partmgr|iaStor|storahci|mpio' -or $_.Message -match '(?i)i/o error|timeout|timed out|transport failed|media error|reset to device|bad block|fc packet|dropped request|corrupt' }; if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No I/O timeout/transport/media-like warning or error events found in the last 30 days.'}"
CASE_ID = '25_windows_log_io_event_check'
CHECK_NAME = 'Windows I/O 로그'
THRESHOLD_DEFS = [('max_io_event_count', 0, 'int'), ('failure_keywords', '', 'str')]
THRESHOLD_LABELS = {'min_socket_count': '물리 CPU 소켓 수 최소 기준', 'min_total_core_count': '전체 물리 CPU 코어 수 최소 기준', 'min_total_logical_processor_count': '전체 논리 CPU 수 최소 기준', 'max_memory_usage_percent': '물리 메모리 사용률 최대 기준', 'min_memory_free_percent': '가용 메모리 비율 최소 기준', 'max_swap_usage_percent': 'PageFile 사용률 최대 기준', 'min_installed_memory_gib': '설치 메모리 총량 최소 기준', 'max_usage_percent': '디스크 사용률 최대 기준', 'min_available_percent': '디스크 가용률 최소 기준', 'require_spare_device': 'spare 디스크 최소 기준', 'min_disk_count': '디스크 수 최소 기준', 'min_partition_count': '파티션 수 최소 기준', 'max_busy_percent': '디스크 Busy 최대 기준', 'min_idle_percent': 'Idle 비율 최소 기준', 'max_wait_ms': '대기시간 최대 기준(ms)', 'max_queue_length': '큐 길이 최대 기준', 'max_iuse_percent': 'inode 유사 사용률 최대 기준', 'expected_ip_forward': 'IPEnableRouter 기대값', 'disallowed_accept_source_route_values': 'Source Route 차단 값', 'max_critical_error_count': 'Critical/Error 이벤트 최대 기준', 'max_warning_count': 'Warning 이벤트 최대 기준', 'max_down_node_count': 'Down 노드 최대 기준', 'max_offline_resource_count': 'Offline 리소스 최대 기준', 'expected_mount_path': '공유 볼륨 기대 경로', 'expected_mode': '공유 볼륨 기대 모드', 'min_up_physical_nic_count': 'Up 물리 NIC 최소 기준', 'max_down_or_degraded_team_count': 'Down/Degraded 팀 최대 기준', 'max_failed_member_count': '비정상 멤버 최대 기준', 'max_loss_percent': 'Ping 손실률 최대 기준', 'max_average_time_ms': '평균 응답시간 최대 기준(ms)', 'expected_policy_keyword': 'MPIO 정책 기대 키워드', 'max_non_online_port_count': 'Non-Online HBA 포트 최대 기준', 'max_cluster_event_count': '클러스터 이벤트 최대 기준', 'max_cpu_ecc_event_count': 'CPU/ECC 이벤트 최대 기준', 'max_fan_event_count': 'FAN 이벤트 최대 기준', 'max_hba_event_count': 'HBA 이벤트 최대 기준', 'max_io_event_count': 'I/O 이벤트 최대 기준', 'max_panic_like_event_count': '장애성 커널 이벤트 최대 기준', 'max_memory_error_event_count': '메모리 오류 이벤트 최대 기준', 'min_up_nic_count': 'Up 서비스 NIC 최소 기준', 'max_nic_event_count': 'NIC 부정 이벤트 최대 기준', 'max_power_event_count': 'POWER 이벤트 최대 기준', 'failure_keywords': '실패 키워드'}


NEGATIVE_NIC_EVENT_PATTERNS = (
    'link down',
    'media disconnected',
    'disconnected from the network',
    'status down',
    'adapter reset',
    'failover',
)


def _split_keywords(value):
    if isinstance(value, (list, tuple)):
        raw_values = value
    else:
        raw_values = str(value or '').split(',')
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _format_value(value):
    if isinstance(value, list):
        return ', '.join(str(item) for item in value) if value else '없음'
    if value in (None, ''):
        return '없음'
    return str(value)


def _format_percent(value):
    try:
        return '{0:.2f}%'.format(float(value))
    except (TypeError, ValueError):
        return 'N/A'


def _format_count(value, unit='건'):
    if value in (None, ''):
        return '0{0}'.format(unit)
    return '{0}{1}'.format(value, unit)


def _to_float(value, default=0.0):
    if value in (None, ''):
        return default
    match = re.search(r'-?\d+(?:\.\d+)?', str(value).replace(',', ''))
    if not match:
        return default
    try:
        return float(match.group(0))
    except ValueError:
        return default


def _to_int(value, default=0):
    try:
        return int(round(_to_float(value, default)))
    except (TypeError, ValueError):
        return default


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


def _parse_json(text):
    try:
        return json.loads((text or '').strip())
    except (TypeError, ValueError):
        return None


def _parse_colon_map(text):
    parsed = {}
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        key, value = line.split(':', 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _parse_colon_blocks(text):
    blocks = []
    current = {}
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                blocks.append(current)
                current = {}
            continue
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def _event_entries_from_output(text, json_keys=None, no_event_markers=None):
    json_keys = json_keys or ()
    no_event_markers = no_event_markers or ()
    lowered = (text or '').lower()
    for marker in no_event_markers:
        if marker.lower() in lowered:
            return []

    parsed = _parse_json(text)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in json_keys:
            value = parsed.get(key)
            if isinstance(value, list):
                return value
        return [parsed]

    rows = [line.strip() for line in (text or '').splitlines() if line.strip()]
    return rows


def _contains_any(text, patterns):
    lowered = str(text or '').lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _message_of_entry(entry):
    if isinstance(entry, dict):
        return str(entry.get('Message') or entry.get('message') or '')
    return str(entry or '')


def _level_of_entry(entry):
    if not isinstance(entry, dict):
        return ''
    return str(entry.get('LevelDisplayName') or entry.get('level') or '').strip()


def _is_bad_port_state(state):
    normalized = str(state or '').strip().lower()
    return normalized not in ('online', 'operational', 'ok')


def _init_metrics(text):
    return {
        '_raw_output': (text or '').strip(),
        '_parse_error': '',
        '_excluded_reason': '',
    }


def _parse_cpu_core(text):
    metrics = _init_metrics(text)
    processors = _parse_colon_blocks(text)
    if not processors:
        metrics['_parse_error'] = 'CPU 프로세서 정보를 찾지 못했습니다.'
        return metrics

    parsed = []
    for item in processors:
        cores = _to_int(item.get('NumberOfCores'))
        logical = _to_int(item.get('NumberOfLogicalProcessors'))
        if cores <= 0 and logical <= 0:
            continue
        parsed.append({
            'name': item.get('Name', ''),
            'socket_designation': item.get('SocketDesignation', ''),
            'manufacturer': item.get('Manufacturer', ''),
            'max_clock_speed_mhz': _to_int(item.get('MaxClockSpeed')),
            'number_of_cores': cores,
            'number_of_logical_processors': logical,
            'threads_per_core': round(float(logical) / cores, 2) if cores > 0 else 0.0,
        })
    if not parsed:
        metrics['_parse_error'] = 'CPU 코어 수 또는 논리 프로세서 수를 해석하지 못했습니다.'
        return metrics

    metrics.update({
        'socket_count': len(parsed),
        'total_core_count': sum(item['number_of_cores'] for item in parsed),
        'total_logical_processor_count': sum(item['number_of_logical_processors'] for item in parsed),
        'threads_per_core': parsed[0]['threads_per_core'],
        'processor_name': parsed[0]['name'],
        'processors': parsed,
    })
    return metrics


def _parse_memory_usage(text):
    metrics = _init_metrics(text)
    pattern = (
        r'MEM\s+total=([0-9.,]+)GiB\s+used=([0-9.,]+)GiB\s+'
        r'free=([0-9.,]+)GiB\s+usage=([0-9.,]+)%\s+\|\s+'
        r'SWAP\s+total=([0-9.,]+)GiB\s+used=([0-9.,]+)GiB\s+free=([0-9.,]+)GiB'
    )
    match = re.search(pattern, text or '', re.IGNORECASE)
    if not match:
        metrics['_parse_error'] = '메모리 사용률 출력 형식을 해석하지 못했습니다.'
        return metrics
    total, used, free, usage, swap_total, swap_used, swap_free = [_to_float(v) for v in match.groups()]
    metrics.update({
        'memory_total_gib': total,
        'memory_used_gib': used,
        'memory_free_gib': free,
        'memory_usage_percent': usage,
        'memory_free_percent': round((free / total) * 100, 2) if total > 0 else 0.0,
        'swap_total_gib': swap_total,
        'swap_used_gib': swap_used,
        'swap_free_gib': swap_free,
        'swap_usage_percent': round((swap_used / swap_total) * 100, 2) if swap_total > 0 else 0.0,
    })
    return metrics


def _parse_memory_recognition(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    if not isinstance(parsed, dict):
        metrics['_parse_error'] = '메모리 인식 상태 JSON을 해석하지 못했습니다.'
        return metrics
    modules = _as_list(parsed.get('Modules'))
    array = parsed.get('Array') if isinstance(parsed.get('Array'), dict) else {}
    installed = round(sum(_to_float(module.get('SizeGiB')) for module in modules if isinstance(module, dict)), 2)
    metrics.update({
        'installed_memory_gib': installed,
        'memory_module_count': len(modules),
        'memory_slot_count': _to_int(array.get('Slots')),
        'max_capacity_gib': _to_float(array.get('MaxCapacityGiB')),
        'modules': modules,
    })
    if installed <= 0:
        metrics['_parse_error'] = '설치된 메모리 용량을 찾지 못했습니다.'
    return metrics


def _parse_pagefile(text):
    metrics = _init_metrics(text)
    entries = []
    for block in _parse_colon_blocks(text):
        usage = _to_float(block.get('Usage(%)'))
        size_mb = _to_float(block.get('Size(MB)'))
        used_mb = _to_float(block.get('Used(MB)'))
        if usage == 0.0 and size_mb > 0:
            usage = round((used_mb / size_mb) * 100, 2) if size_mb > 0 else 0.0
        entries.append({
            'filename': block.get('Filename') or block.get('Name') or '',
            'type': block.get('Type', ''),
            'size_mb': size_mb,
            'used_mb': used_mb,
            'usage_percent': usage,
            'peak_mb': _to_float(block.get('Peak(MB)')),
        })
    if not entries:
        metrics['_parse_error'] = 'PageFile 사용률 결과를 해석하지 못했습니다.'
        return metrics
    max_entry = max(entries, key=lambda item: item['usage_percent'])
    metrics.update({
        'pagefile_count': len(entries),
        'pagefiles': entries,
        'swap_total_gib': round(sum(item['size_mb'] for item in entries) / 1024, 2),
        'swap_used_gib': round(sum(item['used_mb'] for item in entries) / 1024, 2),
        'max_swap_usage_percent': max_entry['usage_percent'],
        'max_swap_usage_file': max_entry['filename'],
    })
    return metrics


def _parse_disk_usage(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    volumes = []
    for item in _as_list(parsed):
        if not isinstance(item, dict):
            continue
        size = _to_float(item.get('Size(GB)'))
        used = _to_float(item.get('Used(GB)'))
        available = _to_float(item.get('Avail(GB)'))
        usage = _to_float(item.get('Use%'))
        if usage == 0.0 and size > 0:
            usage = round((used / size) * 100, 2)
        available_percent = round((available / size) * 100, 2) if size > 0 else 0.0
        volumes.append({
            'mount_point': item.get('Filesystem') or item.get('Mounted on') or '',
            'size_gib': size,
            'used_gib': used,
            'available_gib': available,
            'usage_percent': usage,
            'available_percent': available_percent,
        })
    if not volumes:
        metrics['_parse_error'] = '디스크 사용률 JSON을 해석하지 못했습니다.'
        return metrics
    max_usage = max(volumes, key=lambda item: item['usage_percent'])
    min_available = min(volumes, key=lambda item: item['available_percent'])
    metrics.update({
        'volume_count': len(volumes),
        'volumes': volumes,
        'max_usage_percent': max_usage['usage_percent'],
        'max_usage_mount': max_usage['mount_point'],
        'min_available_percent': min_available['available_percent'],
        'min_available_mount': min_available['mount_point'],
    })
    return metrics


def _parse_disk_ha(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'does not appear to be a storage spaces raid device' in lowered or 'not_applicable' in lowered:
        metrics['_excluded_reason'] = 'Storage Spaces 또는 가상 디스크 구성이 없어 점검 대상이 아닙니다.'
        metrics.update({'virtual_disk_count': 0, 'spare_count': 0, 'failed_device_count': 0, 'degraded_count': 0})
        return metrics
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    if not lines:
        metrics['_parse_error'] = '디스크 HA 상태 결과가 비어 있습니다.'
        return metrics
    entries = []
    for line in lines:
        entries.append({
            'line': line,
            'failed_devices': _to_int(re.search(r'FailedDevices=([^/]+)', line).group(1)) if re.search(r'FailedDevices=([^/]+)', line) else 0,
            'spare_devices': _to_int(re.search(r'SpareDevices=([^/]+)', line).group(1)) if re.search(r'SpareDevices=([^/]+)', line) else 0,
            'health': re.search(r'Health=([^/]+)', line).group(1).strip() if re.search(r'Health=([^/]+)', line) else '',
            'state': re.search(r'State=([^/]+)', line).group(1).strip() if re.search(r'State=([^/]+)', line) else '',
        })
    failed_count = sum(item['failed_devices'] for item in entries)
    degraded = [item for item in entries if item['failed_devices'] > 0 or item['health'].lower() not in ('', 'healthy', 'ok')]
    metrics.update({
        'virtual_disk_count': len(entries),
        'spare_count': sum(item['spare_devices'] for item in entries),
        'failed_device_count': failed_count,
        'degraded_count': len(degraded),
        'entries': entries,
    })
    return metrics


def _parse_disk_recognition(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    entries = [item for item in _as_list(parsed) if isinstance(item, dict)]
    if not entries:
        metrics['_parse_error'] = '디스크/파티션 인식 상태 JSON을 해석하지 못했습니다.'
        return metrics
    disks = [item for item in entries if str(item.get('TYPE', '')).lower() == 'disk']
    partitions = [item for item in entries if str(item.get('TYPE', '')).lower() == 'part']
    metrics.update({
        'disk_count': len(disks),
        'partition_count': len(partitions),
        'removable_count': len([item for item in entries if _to_int(item.get('RM')) == 1]),
        'entries': entries,
    })
    return metrics


def _parse_disk_io(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    entries = []
    for item in _as_list(parsed):
        if not isinstance(item, dict):
            continue
        entries.append({
            'device': item.get('device', ''),
            'read_per_sec': _to_float(item.get('r/s')),
            'write_per_sec': _to_float(item.get('w/s')),
            'read_kib_per_sec': _to_float(item.get('kr/s')),
            'write_kib_per_sec': _to_float(item.get('kw/s')),
            'wait_ms': _to_float(item.get('wait(ms)')),
            'queue_length': _to_float(item.get('actv')),
            'busy_percent': _to_float(item.get('%b')),
            'idle_percent': _to_float(item.get('idle%')),
        })
    if not entries:
        metrics['_parse_error'] = '디스크 I/O JSON을 해석하지 못했습니다.'
        return metrics
    metrics.update({
        'disk_count': len(entries),
        'devices': entries,
        'max_busy_percent': max(item['busy_percent'] for item in entries),
        'min_idle_percent': min(item['idle_percent'] for item in entries),
        'max_wait_ms': max(item['wait_ms'] for item in entries),
        'max_queue_length': max(item['queue_length'] for item in entries),
    })
    return metrics


def _parse_inode(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    entries = []
    for item in _as_list(parsed):
        if not isinstance(item, dict):
            continue
        entries.append({
            'filesystem': item.get('Filesystem', ''),
            'mount_point': item.get('Mounted on', ''),
            'inode_total': _to_float(item.get('Inodes(approx)')),
            'inode_used': _to_float(item.get('IUsed(approx)')),
            'inode_free': _to_float(item.get('IFree(approx)')),
            'iuse_percent': _to_float(item.get('IUse%(approx)')),
        })
    if not entries:
        metrics['_parse_error'] = 'NTFS inode 유사 사용률 JSON을 해석하지 못했습니다.'
        return metrics
    max_entry = max(entries, key=lambda item: item['iuse_percent'])
    metrics.update({
        'volume_count': len(entries),
        'volumes': entries,
        'max_iuse_percent': max_entry['iuse_percent'],
        'max_iuse_mount': max_entry['mount_point'],
    })
    return metrics


def _parse_kernel(text):
    metrics = _init_metrics(text)
    data = _parse_colon_map(text)
    if not data:
        metrics['_parse_error'] = '커널 파라미터 출력 형식을 해석하지 못했습니다.'
        return metrics
    metrics.update({
        'kernel.osrelease': data.get('kernel.osrelease', ''),
        'kernel.ostype': data.get('kernel.ostype', ''),
        'kernel.hostname': data.get('kernel.hostname', ''),
        'net.ipv4.ip_forward': data.get('net.ipv4.ip_forward', ''),
        'net.ipv4.conf.all.accept_source_route': data.get('net.ipv4.conf.all.accept_source_route', ''),
        'fs.file-max': data.get('fs.file-max', ''),
    })
    return metrics


def _parse_system_log(text):
    metrics = _init_metrics(text)
    entries = _event_entries_from_output(text)
    critical_error = [entry for entry in entries if _level_of_entry(entry).lower() in ('critical', 'error')]
    warnings = [entry for entry in entries if _level_of_entry(entry).lower() == 'warning']
    metrics.update({
        'event_count': len(entries),
        'critical_error_count': len(critical_error),
        'warning_count': len(warnings),
        'entries': entries[:20],
    })
    return metrics


def _parse_cluster_daemon(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'failoverclusters module not installed' in lowered or 'failover cluster not found' in lowered:
        metrics['_excluded_reason'] = 'WSFC 미구성 또는 FailoverClusters 모듈 미설치로 점검 대상이 아닙니다.'
        return metrics
    parsed = _parse_json(text)
    if not isinstance(parsed, dict):
        metrics['_parse_error'] = '클러스터 상태 JSON을 해석하지 못했습니다.'
        return metrics
    summary = parsed.get('Summary') if isinstance(parsed.get('Summary'), dict) else {}
    nodes_configured = _to_int(summary.get('NodesConfigured'))
    nodes_online = _to_int(summary.get('NodesOnline'))
    resources_configured = _to_int(summary.get('ResourceInstancesConfigured'))
    resources_online = _to_int(summary.get('ResourcesOnline'))
    metrics.update({
        'cluster_name': summary.get('Cluster', ''),
        'nodes_configured': nodes_configured,
        'nodes_online': nodes_online,
        'down_node_count': max(nodes_configured - nodes_online, 0),
        'resources_configured': resources_configured,
        'resources_online': resources_online,
        'offline_resource_count': max(resources_configured - resources_online, 0),
        'nodes': _as_list(parsed.get('Nodes')),
        'resources': _as_list(parsed.get('Resources')),
    })
    return metrics


def _parse_cluster_shared_volume(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'mount point not found' in lowered or 'not_applicable' in lowered:
        metrics['_excluded_reason'] = '클러스터 공유 볼륨 또는 기대 마운트 지점이 없어 점검 대상이 아닙니다.'
        metrics.update({'csv_count': 0})
        return metrics
    data = _parse_colon_map(text)
    if not data:
        metrics['_parse_error'] = '공유 볼륨 상태 출력 형식을 해석하지 못했습니다.'
        return metrics
    metrics.update({
        'csv_count': 1,
        'device': data.get('Device', ''),
        'mounted_on': data.get('MountedOn', ''),
        'filesystem': data.get('FileSystem', ''),
        'mode': data.get('Mode', ''),
        'status': data.get('Status', ''),
        'health': data.get('Health', ''),
    })
    return metrics


def _parse_network_link(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    adapters = [item for item in _as_list(parsed) if isinstance(item, dict)]
    if not adapters:
        metrics['_parse_error'] = '네트워크 어댑터 JSON을 해석하지 못했습니다.'
        return metrics
    up_adapters = [item for item in adapters if str(item.get('Status', '')).strip().lower() == 'up']
    metrics.update({
        'physical_nic_count': len(adapters),
        'up_physical_nic_count': len(up_adapters),
        'down_physical_nic_count': len(adapters) - len(up_adapters),
        'adapters': adapters,
    })
    return metrics


def _parse_nic_teaming(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if '미구성' in lowered or '미지원' in lowered or 'cmdlet 없음' in lowered or 'not_applicable' in lowered:
        metrics['_excluded_reason'] = 'NIC Teaming 구성이 없거나 관련 cmdlet이 없어 점검 대상이 아닙니다.'
        metrics.update({'team_count': 0, 'down_or_degraded_team_count': 0, 'failed_member_count': 0})
        return metrics
    parsed = _parse_json(text)
    entries = [item for item in _as_list(parsed) if isinstance(item, dict)]
    if not entries:
        metrics['_parse_error'] = 'NIC Teaming JSON을 해석하지 못했습니다.'
        return metrics
    teams = sorted(set(str(item.get('GROUPNAME', '')) for item in entries if item.get('GROUPNAME')))
    bad_teams = sorted(set(str(item.get('GROUPNAME', '')) for item in entries if str(item.get('TEAMSTATE', '')).lower() not in ('up', 'ok', 'active')))
    failed_members = [item for item in entries if str(item.get('STATE', '')).lower() not in ('active', 'standby', 'up', 'ok')]
    metrics.update({
        'team_count': len(teams),
        'down_or_degraded_team_count': len(bad_teams),
        'failed_member_count': len(failed_members),
        'teams': entries,
    })
    return metrics


def _parse_ping(text):
    metrics = _init_metrics(text)
    packet_match = re.search(r'(?:보냄|Sent)\s*=\s*(\d+).*?(?:받음|Received)\s*=\s*(\d+).*?(?:손실|Lost)\s*=\s*(\d+)\s*\((\d+)%', text or '', re.S | re.I)
    rtt_match = re.search(r'(?:최소|Minimum)\s*=\s*<?(\d+)ms.*?(?:최대|Maximum)\s*=\s*<?(\d+)ms.*?(?:평균|Average)\s*=\s*<?(\d+)ms', text or '', re.S | re.I)
    target_match = re.search(r'Ping\s+([^\s]+)', text or '', re.I)
    if not packet_match:
        metrics['_parse_error'] = 'Ping 패킷 통계를 해석하지 못했습니다.'
        return metrics
    metrics.update({
        'target_gateway': target_match.group(1) if target_match else '',
        'sent': _to_int(packet_match.group(1)),
        'received': _to_int(packet_match.group(2)),
        'lost': _to_int(packet_match.group(3)),
        'loss_percent': _to_int(packet_match.group(4)),
        'min_rtt_ms': _to_int(rtt_match.group(1)) if rtt_match else 0,
        'max_rtt_ms': _to_int(rtt_match.group(2)) if rtt_match else 0,
        'avg_rtt_ms': _to_int(rtt_match.group(3)) if rtt_match else 0,
    })
    return metrics


def _parse_mpio(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'mpio 미설치' in lowered or '미지원' in lowered:
        metrics['_excluded_reason'] = 'MPIO가 설치되어 있지 않거나 지원되지 않아 점검 대상이 아닙니다.'
        metrics.update({'failed_path_count': 0, 'active_path_like_count': 0, 'enabled_path_like_count': 0, 'load_balance_policy': ''})
        return metrics
    data = _parse_colon_map(text)
    failed_path_count = len(re.findall(r'\bfailed\b|\bfaulty\b|\boffline\b', lowered))
    active_path_like_count = len(re.findall(r'\bactive\b|\brunning\b', lowered))
    enabled_path_like_count = len(re.findall(r'\benabled\b|\bstandby\b', lowered))
    metrics.update({
        'load_balance_policy': data.get('LoadBalancePolicy', ''),
        'failed_path_count': failed_path_count,
        'active_path_like_count': active_path_like_count,
        'enabled_path_like_count': enabled_path_like_count,
    })
    return metrics


def _parse_hba_ports(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'not found' in lowered or 'not_applicable' in lowered:
        metrics['_excluded_reason'] = 'FC HBA 포트 정보를 확인할 수 없어 점검 대상이 아닙니다.'
        return metrics
    parsed = _parse_json(text)
    ports = [item for item in _as_list(parsed) if isinstance(item, dict)]
    if not ports:
        metrics['_parse_error'] = 'FC HBA 포트 JSON을 해석하지 못했습니다.'
        return metrics
    non_online = [item for item in ports if _is_bad_port_state(item.get('fc_state'))]
    metrics.update({
        'port_count': len(ports),
        'non_online_port_count': len(non_online),
        'ports': ports,
    })
    return metrics


def _parse_log_cluster(text):
    metrics = _init_metrics(text)
    lowered = (text or '').lower()
    if 'log not present' in lowered or 'not a local wsfc node' in lowered:
        metrics['_excluded_reason'] = 'Failover Clustering 로그 채널이 없어 점검 대상이 아닙니다.'
        metrics.update({'event_count': 0, 'entries': []})
        return metrics
    entries = _event_entries_from_output(text)
    metrics.update({'event_count': len(entries), 'entries': entries[:20]})
    return metrics


def _parse_simple_log(text, no_event_markers, json_keys=None):
    metrics = _init_metrics(text)
    entries = _event_entries_from_output(text, json_keys=json_keys, no_event_markers=no_event_markers)
    metrics.update({'event_count': len(entries), 'entries': entries[:20]})
    return metrics


def _parse_fan_log(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    if not isinstance(parsed, dict):
        return _parse_simple_log(text, ('no fan', 'no cooling'))
    fans = _as_list(parsed.get('Fans'))
    events = _as_list(parsed.get('Events'))
    bad_fans = [fan for fan in fans if isinstance(fan, dict) and str(fan.get('Status', '')).lower() not in ('ok', 'healthy')]
    metrics.update({
        'fan_data_exposed': bool(parsed.get('FanDataExposed')),
        'event_data_exposed': bool(parsed.get('EventDataExposed')),
        'fan_count': len(fans),
        'bad_fan_count': len(bad_fans),
        'event_count': len(events),
        'fans': fans,
        'entries': events[:20],
    })
    return metrics


def _parse_hba_log(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    if not isinstance(parsed, dict):
        return _parse_simple_log(text, ('no hba', 'no fibre'))
    ports = _as_list(parsed.get('FcPorts'))
    events = _as_list(parsed.get('Events'))
    bad_ports = [port for port in ports if isinstance(port, dict) and _is_bad_port_state(port.get('PortState'))]
    metrics.update({
        'initiator_ports_exposed': bool(parsed.get('InitiatorPortsExposed')),
        'fc_port_state_exposed': bool(parsed.get('FcPortStateExposed')),
        'port_count': len(ports),
        'bad_port_count': len(bad_ports),
        'event_count': len(events),
        'ports': ports,
        'entries': events[:20],
    })
    return metrics


def _parse_nic_log(text):
    metrics = _init_metrics(text)
    parsed = _parse_json(text)
    if isinstance(parsed, dict):
        adapters = _as_list(parsed.get('NicStatus'))
        events = _as_list(parsed.get('RecentEvents'))
    else:
        adapters = []
        events = _event_entries_from_output(text, no_event_markers=('no nic link',))
    service_adapters = [item for item in adapters if isinstance(item, dict)]
    up_adapters = [item for item in service_adapters if str(item.get('Status', '')).lower() == 'up']
    negative_events = [entry for entry in events if _contains_any(_message_of_entry(entry), NEGATIVE_NIC_EVENT_PATTERNS)]
    metrics.update({
        'service_nic_count': len(service_adapters),
        'up_nic_count': len(up_adapters),
        'nic_event_count': len(events),
        'negative_event_count': len(negative_events),
        'adapters': service_adapters,
        'entries': events[:20],
    })
    return metrics


def parse_by_case(case_id, text):
    if case_id == '02_windows_cpu_core_cim_check':
        return _parse_cpu_core(text)
    if case_id == '03_windows_memory_usage_cim_check':
        return _parse_memory_usage(text)
    if case_id == '04_windows_memory_recognition_cim_check':
        return _parse_memory_recognition(text)
    if case_id in ('05_windows_memory_pagefile_usage_cim_check', '07_windows_disk_swap_usage_check'):
        return _parse_pagefile(text)
    if case_id == '06_windows_disk_filesystem_usage_cim_check':
        return _parse_disk_usage(text)
    if case_id == '08_windows_disk_redundancy_health_check':
        return _parse_disk_ha(text)
    if case_id == '09_windows_disk_recognition_cim_check':
        return _parse_disk_recognition(text)
    if case_id == '10_windows_disk_io_counter_check':
        return _parse_disk_io(text)
    if case_id == '11_windows_disk_inode_not_applicable_check':
        return _parse_inode(text)
    if case_id == '12_windows_kernel_parameter_nettcp_check':
        return _parse_kernel(text)
    if case_id == '13_windows_log_system_event_check':
        return _parse_system_log(text)
    if case_id == '14_windows_cluster_daemon_check':
        return _parse_cluster_daemon(text)
    if case_id == '15_windows_cluster_shared_volume_check':
        return _parse_cluster_shared_volume(text)
    if case_id == '16_windows_network_link_status_check':
        return _parse_network_link(text)
    if case_id == '17_windows_network_nic_teaming_check':
        return _parse_nic_teaming(text)
    if case_id == '18_windows_network_ping_loss_check':
        return _parse_ping(text)
    if case_id == '19_windows_os_mpio_path_check':
        return _parse_mpio(text)
    if case_id == '20_windows_os_hba_connection_manual_check':
        return _parse_hba_ports(text)
    if case_id == '21_windows_log_cluster_event_check':
        return _parse_log_cluster(text)
    if case_id == '22_windows_log_cpu_event_check':
        return _parse_simple_log(text, ('no cpu/ecc/offline-like events found',))
    if case_id == '23_windows_log_fan_manual_check':
        return _parse_fan_log(text)
    if case_id == '24_windows_log_hba_manual_check':
        return _parse_hba_log(text)
    if case_id == '25_windows_log_io_event_check':
        return _parse_simple_log(text, ('no i/o timeout/transport/media-like warning or error events found',))
    if case_id == '26_windows_log_kernel_event_check':
        return _parse_simple_log(text, ('no panic-like kernel events found',))
    if case_id == '27_windows_log_memory_event_check':
        return _parse_simple_log(text, ('no ecc/memory-error-like events found',))
    if case_id == '28_windows_log_nic_event_check':
        return _parse_nic_log(text)
    if case_id == '29_windows_log_power_event_check':
        return _parse_simple_log(text, ('no psu/power-failure-like warning or error events found',))

    metrics = _init_metrics(text)
    metrics['_parse_error'] = '지원하지 않는 점검 케이스입니다.'
    return metrics


def _failure_keyword_matches(metrics, thresholds):
    keywords = thresholds.get('failure_keywords') or []
    raw_output = metrics.get('_raw_output', '')
    return [keyword for keyword in keywords if keyword.lower() in raw_output.lower()]


def _evaluation_reasons(case_id, metrics, thresholds):
    reasons = []
    if case_id == '02_windows_cpu_core_cim_check':
        if metrics.get('socket_count', 0) < thresholds['min_socket_count']:
            reasons.append('물리 CPU 소켓 수 기준 미충족')
        if metrics.get('total_core_count', 0) < thresholds['min_total_core_count']:
            reasons.append('전체 물리 CPU 코어 수 기준 미충족')
        if metrics.get('total_logical_processor_count', 0) < thresholds['min_total_logical_processor_count']:
            reasons.append('전체 논리 CPU 수 기준 미충족')
    elif case_id == '03_windows_memory_usage_cim_check':
        if metrics.get('memory_usage_percent', 0.0) >= thresholds['max_memory_usage_percent']:
            reasons.append('물리 메모리 사용률 기준 미충족')
        if metrics.get('memory_free_percent', 0.0) <= thresholds['min_memory_free_percent']:
            reasons.append('가용 메모리 비율 기준 미충족')
        if metrics.get('swap_usage_percent', 0.0) >= thresholds['max_swap_usage_percent']:
            reasons.append('PageFile 사용률 기준 미충족')
    elif case_id == '04_windows_memory_recognition_cim_check':
        if metrics.get('installed_memory_gib', 0.0) < thresholds['min_installed_memory_gib']:
            reasons.append('설치 메모리 용량 기준 미충족')
    elif case_id in ('05_windows_memory_pagefile_usage_cim_check', '07_windows_disk_swap_usage_check'):
        if metrics.get('max_swap_usage_percent', 0.0) >= thresholds['max_swap_usage_percent']:
            reasons.append('PageFile 사용률 기준 미충족')
    elif case_id == '06_windows_disk_filesystem_usage_cim_check':
        if metrics.get('max_usage_percent', 0.0) >= thresholds['max_usage_percent']:
            reasons.append('디스크 사용률 기준 미충족')
        if metrics.get('min_available_percent', 100.0) <= thresholds['min_available_percent']:
            reasons.append('디스크 가용률 기준 미충족')
    elif case_id == '08_windows_disk_redundancy_health_check':
        if metrics.get('failed_device_count', 0) > 0 or metrics.get('degraded_count', 0) > 0:
            reasons.append('디스크 HA 상태 이상 감지')
        if thresholds.get('require_spare_device', 0) and metrics.get('spare_count', 0) < thresholds['require_spare_device']:
            reasons.append('spare 디스크 수 기준 미충족')
    elif case_id == '09_windows_disk_recognition_cim_check':
        if metrics.get('disk_count', 0) < thresholds['min_disk_count']:
            reasons.append('디스크 수 기준 미충족')
        if metrics.get('partition_count', 0) < thresholds['min_partition_count']:
            reasons.append('파티션 수 기준 미충족')
    elif case_id == '10_windows_disk_io_counter_check':
        if metrics.get('max_busy_percent', 0.0) >= thresholds['max_busy_percent']:
            reasons.append('디스크 Busy 비율 기준 미충족')
        if metrics.get('min_idle_percent', 100.0) <= thresholds['min_idle_percent']:
            reasons.append('디스크 Idle 비율 기준 미충족')
        if metrics.get('max_wait_ms', 0.0) > thresholds['max_wait_ms']:
            reasons.append('디스크 대기시간 기준 미충족')
        if metrics.get('max_queue_length', 0.0) > thresholds['max_queue_length']:
            reasons.append('디스크 큐 길이 기준 미충족')
    elif case_id == '11_windows_disk_inode_not_applicable_check':
        if metrics.get('max_iuse_percent', 0.0) > thresholds['max_iuse_percent']:
            reasons.append('inode 유사 사용률 기준 미충족')
    elif case_id == '12_windows_kernel_parameter_nettcp_check':
        if str(metrics.get('net.ipv4.ip_forward', '')).strip() != str(thresholds['expected_ip_forward']).strip():
            reasons.append('IPEnableRouter 기대값 불일치')
        disallowed = _split_keywords(thresholds.get('disallowed_accept_source_route_values'))
        if str(metrics.get('net.ipv4.conf.all.accept_source_route', '')).strip() in disallowed:
            reasons.append('Source Route 허용 값 감지')
    elif case_id == '13_windows_log_system_event_check':
        if metrics.get('critical_error_count', 0) > thresholds['max_critical_error_count']:
            reasons.append('Critical/Error 이벤트 수 기준 미충족')
        if metrics.get('warning_count', 0) > thresholds['max_warning_count']:
            reasons.append('Warning 이벤트 수 기준 미충족')
    elif case_id == '14_windows_cluster_daemon_check':
        if metrics.get('down_node_count', 0) > thresholds['max_down_node_count']:
            reasons.append('Down 노드 수 기준 미충족')
        if metrics.get('offline_resource_count', 0) > thresholds['max_offline_resource_count']:
            reasons.append('Offline 리소스 수 기준 미충족')
    elif case_id == '15_windows_cluster_shared_volume_check':
        mount_path = str(metrics.get('mounted_on', '')).lower()
        if thresholds.get('expected_mount_path') and str(thresholds['expected_mount_path']).strip().rstrip('\\').lower() not in mount_path.rstrip('\\'):
            reasons.append('공유 볼륨 경로 기준 미충족')
        if thresholds.get('expected_mode') and str(metrics.get('mode', '')).lower() != str(thresholds['expected_mode']).lower():
            reasons.append('공유 볼륨 모드 기준 미충족')
        if str(metrics.get('status', '')).lower() not in ('online', 'ok', 'healthy'):
            reasons.append('공유 볼륨 상태 이상')
    elif case_id == '16_windows_network_link_status_check':
        if metrics.get('up_physical_nic_count', 0) < thresholds['min_up_physical_nic_count']:
            reasons.append('Up 물리 NIC 수 기준 미충족')
    elif case_id == '17_windows_network_nic_teaming_check':
        if metrics.get('down_or_degraded_team_count', 0) > thresholds['max_down_or_degraded_team_count']:
            reasons.append('Down/Degraded 팀 수 기준 미충족')
        if metrics.get('failed_member_count', 0) > thresholds['max_failed_member_count']:
            reasons.append('비정상 멤버 수 기준 미충족')
    elif case_id == '18_windows_network_ping_loss_check':
        if metrics.get('loss_percent', 0) > thresholds['max_loss_percent']:
            reasons.append('Ping 손실률 기준 미충족')
        if metrics.get('avg_rtt_ms', 0) > thresholds['max_average_time_ms']:
            reasons.append('Ping 평균 응답시간 기준 미충족')
    elif case_id == '19_windows_os_mpio_path_check':
        if metrics.get('failed_path_count', 0) > 0:
            reasons.append('MPIO 비정상 경로 감지')
        policy = str(metrics.get('load_balance_policy', '')).lower()
        expected = str(thresholds.get('expected_policy_keyword', '')).lower()
        if expected and expected not in policy:
            reasons.append('MPIO 부하분산 정책 기준 미충족')
    elif case_id == '20_windows_os_hba_connection_manual_check':
        if metrics.get('non_online_port_count', 0) > thresholds['max_non_online_port_count']:
            reasons.append('Non-Online HBA 포트 수 기준 미충족')
    elif case_id == '21_windows_log_cluster_event_check':
        if metrics.get('event_count', 0) > thresholds['max_cluster_event_count']:
            reasons.append('클러스터 로그 이벤트 수 기준 미충족')
    elif case_id == '22_windows_log_cpu_event_check':
        if metrics.get('event_count', 0) > thresholds['max_cpu_ecc_event_count']:
            reasons.append('CPU/ECC 이벤트 수 기준 미충족')
    elif case_id == '23_windows_log_fan_manual_check':
        if metrics.get('bad_fan_count', 0) > 0:
            reasons.append('팬 상태 이상 감지')
        if metrics.get('event_count', 0) > thresholds['max_fan_event_count']:
            reasons.append('FAN 이벤트 수 기준 미충족')
    elif case_id == '24_windows_log_hba_manual_check':
        if metrics.get('bad_port_count', 0) > 0:
            reasons.append('HBA 포트 상태 이상 감지')
        if metrics.get('event_count', 0) > thresholds['max_hba_event_count']:
            reasons.append('HBA 이벤트 수 기준 미충족')
    elif case_id == '25_windows_log_io_event_check':
        if metrics.get('event_count', 0) > thresholds['max_io_event_count']:
            reasons.append('I/O 이벤트 수 기준 미충족')
    elif case_id == '26_windows_log_kernel_event_check':
        if metrics.get('event_count', 0) > thresholds['max_panic_like_event_count']:
            reasons.append('장애성 커널 이벤트 수 기준 미충족')
    elif case_id == '27_windows_log_memory_event_check':
        if metrics.get('event_count', 0) > thresholds['max_memory_error_event_count']:
            reasons.append('메모리 오류 이벤트 수 기준 미충족')
    elif case_id == '28_windows_log_nic_event_check':
        if metrics.get('up_nic_count', 0) < thresholds['min_up_nic_count']:
            reasons.append('Up 서비스 NIC 수 기준 미충족')
        if metrics.get('negative_event_count', 0) > thresholds['max_nic_event_count']:
            reasons.append('NIC 부정 이벤트 수 기준 미충족')
    elif case_id == '29_windows_log_power_event_check':
        if metrics.get('event_count', 0) > thresholds['max_power_event_count']:
            reasons.append('POWER 이벤트 수 기준 미충족')
    return reasons


def _warn_case(case_id, reasons):
    if not reasons:
        return False
    return case_id in (
        '02_windows_cpu_core_cim_check',
        '08_windows_disk_redundancy_health_check',
    )


def _summary_lines(case_id, metrics):
    if case_id == '02_windows_cpu_core_cim_check':
        return [
            '프로세서: {0}'.format(metrics.get('processor_name') or 'unknown'),
            '물리 CPU 소켓 수: {0}'.format(metrics.get('socket_count', 0)),
            '전체 물리 CPU 코어 수: {0}'.format(metrics.get('total_core_count', 0)),
            '전체 논리 CPU 수: {0}'.format(metrics.get('total_logical_processor_count', 0)),
        ]
    if case_id == '03_windows_memory_usage_cim_check':
        return [
            '물리 메모리 총량: {0:.2f}GiB'.format(metrics.get('memory_total_gib', 0.0)),
            '물리 메모리 사용률: {0}'.format(_format_percent(metrics.get('memory_usage_percent'))),
            '가용 메모리 비율: {0}'.format(_format_percent(metrics.get('memory_free_percent'))),
            'PageFile 사용률: {0}'.format(_format_percent(metrics.get('swap_usage_percent'))),
        ]
    if case_id == '04_windows_memory_recognition_cim_check':
        return [
            '설치 메모리 총량: {0:.2f}GiB'.format(metrics.get('installed_memory_gib', 0.0)),
            '메모리 모듈 수: {0}'.format(metrics.get('memory_module_count', 0)),
            '메모리 슬롯 수: {0}'.format(metrics.get('memory_slot_count', 0)),
        ]
    if case_id in ('05_windows_memory_pagefile_usage_cim_check', '07_windows_disk_swap_usage_check'):
        return [
            'PageFile 수: {0}'.format(metrics.get('pagefile_count', 0)),
            'PageFile 총량: {0:.2f}GiB'.format(metrics.get('swap_total_gib', 0.0)),
            'PageFile 사용량: {0:.2f}GiB'.format(metrics.get('swap_used_gib', 0.0)),
            '최대 PageFile 사용률: {0}'.format(_format_percent(metrics.get('max_swap_usage_percent'))),
        ]
    if case_id == '06_windows_disk_filesystem_usage_cim_check':
        return [
            '볼륨 수: {0}'.format(metrics.get('volume_count', 0)),
            '최대 디스크 사용률: {0} ({1})'.format(_format_percent(metrics.get('max_usage_percent')), metrics.get('max_usage_mount') or 'unknown'),
            '최소 디스크 가용률: {0} ({1})'.format(_format_percent(metrics.get('min_available_percent')), metrics.get('min_available_mount') or 'unknown'),
        ]
    if case_id == '08_windows_disk_redundancy_health_check':
        return [
            '가상 디스크 수: {0}'.format(metrics.get('virtual_disk_count', 0)),
            'spare 디스크 수: {0}'.format(metrics.get('spare_count', 0)),
            '실패 디스크 수: {0}'.format(metrics.get('failed_device_count', 0)),
            '상태 이상 항목 수: {0}'.format(metrics.get('degraded_count', 0)),
        ]
    if case_id == '09_windows_disk_recognition_cim_check':
        return [
            '디스크 수: {0}'.format(metrics.get('disk_count', 0)),
            '파티션 수: {0}'.format(metrics.get('partition_count', 0)),
            '이동식/ROM 항목 수: {0}'.format(metrics.get('removable_count', 0)),
        ]
    if case_id == '10_windows_disk_io_counter_check':
        return [
            '디스크 수: {0}'.format(metrics.get('disk_count', 0)),
            '최대 Busy: {0}'.format(_format_percent(metrics.get('max_busy_percent'))),
            '최소 Idle: {0}'.format(_format_percent(metrics.get('min_idle_percent'))),
            '최대 대기시간: {0:.2f}ms'.format(metrics.get('max_wait_ms', 0.0)),
            '최대 큐 길이: {0:.2f}'.format(metrics.get('max_queue_length', 0.0)),
        ]
    if case_id == '11_windows_disk_inode_not_applicable_check':
        return [
            '볼륨 수: {0}'.format(metrics.get('volume_count', 0)),
            '최대 inode 유사 사용률: {0} ({1})'.format(_format_percent(metrics.get('max_iuse_percent')), metrics.get('max_iuse_mount') or 'unknown'),
        ]
    if case_id == '12_windows_kernel_parameter_nettcp_check':
        return [
            '호스트명: {0}'.format(metrics.get('kernel.hostname') or 'unknown'),
            'IPEnableRouter: {0}'.format(metrics.get('net.ipv4.ip_forward') or 'N/A'),
            'accept_source_route: {0}'.format(metrics.get('net.ipv4.conf.all.accept_source_route') or 'N/A'),
        ]
    if case_id == '13_windows_log_system_event_check':
        return [
            '이벤트 수: {0}'.format(metrics.get('event_count', 0)),
            'Critical/Error 이벤트 수: {0}'.format(metrics.get('critical_error_count', 0)),
            'Warning 이벤트 수: {0}'.format(metrics.get('warning_count', 0)),
        ]
    if case_id == '14_windows_cluster_daemon_check':
        return [
            '클러스터: {0}'.format(metrics.get('cluster_name') or 'unknown'),
            '노드 Online/Configured: {0}/{1}'.format(metrics.get('nodes_online', 0), metrics.get('nodes_configured', 0)),
            '리소스 Online/Configured: {0}/{1}'.format(metrics.get('resources_online', 0), metrics.get('resources_configured', 0)),
            'Down 노드 수: {0}'.format(metrics.get('down_node_count', 0)),
            'Offline 리소스 수: {0}'.format(metrics.get('offline_resource_count', 0)),
        ]
    if case_id == '15_windows_cluster_shared_volume_check':
        return [
            '공유 볼륨 수: {0}'.format(metrics.get('csv_count', 0)),
            '마운트 경로: {0}'.format(metrics.get('mounted_on') or 'N/A'),
            '모드: {0}'.format(metrics.get('mode') or 'N/A'),
            '상태: {0}'.format(metrics.get('status') or 'N/A'),
        ]
    if case_id == '16_windows_network_link_status_check':
        return [
            '물리 NIC 수: {0}'.format(metrics.get('physical_nic_count', 0)),
            'Up 물리 NIC 수: {0}'.format(metrics.get('up_physical_nic_count', 0)),
            'Down 물리 NIC 수: {0}'.format(metrics.get('down_physical_nic_count', 0)),
        ]
    if case_id == '17_windows_network_nic_teaming_check':
        return [
            'NIC Team 수: {0}'.format(metrics.get('team_count', 0)),
            'Down/Degraded 팀 수: {0}'.format(metrics.get('down_or_degraded_team_count', 0)),
            '비정상 멤버 수: {0}'.format(metrics.get('failed_member_count', 0)),
        ]
    if case_id == '18_windows_network_ping_loss_check':
        return [
            '대상 게이트웨이: {0}'.format(metrics.get('target_gateway') or 'unknown'),
            '패킷 송신/수신/손실: {0}/{1}/{2}'.format(metrics.get('sent', 0), metrics.get('received', 0), metrics.get('lost', 0)),
            '손실률: {0}'.format(_format_percent(metrics.get('loss_percent'))),
            '평균 응답시간: {0}ms'.format(metrics.get('avg_rtt_ms', 0)),
        ]
    if case_id == '19_windows_os_mpio_path_check':
        return [
            '부하분산 정책: {0}'.format(metrics.get('load_balance_policy') or 'N/A'),
            '비정상 경로 수: {0}'.format(metrics.get('failed_path_count', 0)),
            'Active 유사 경로 수: {0}'.format(metrics.get('active_path_like_count', 0)),
            'Enabled/Standby 유사 경로 수: {0}'.format(metrics.get('enabled_path_like_count', 0)),
        ]
    if case_id == '20_windows_os_hba_connection_manual_check':
        return [
            'FC HBA 포트 수: {0}'.format(metrics.get('port_count', 0)),
            'Online이 아닌 포트 수: {0}'.format(metrics.get('non_online_port_count', 0)),
        ]
    if case_id == '23_windows_log_fan_manual_check':
        return [
            '팬 정보 노출 여부: {0}'.format(metrics.get('fan_data_exposed', False)),
            '팬 수: {0}'.format(metrics.get('fan_count', 0)),
            '상태 이상 팬 수: {0}'.format(metrics.get('bad_fan_count', 0)),
            '팬/냉각 이벤트 수: {0}'.format(metrics.get('event_count', 0)),
        ]
    if case_id == '24_windows_log_hba_manual_check':
        return [
            'FC 포트 상태 노출 여부: {0}'.format(metrics.get('fc_port_state_exposed', False)),
            'FC 포트 수: {0}'.format(metrics.get('port_count', 0)),
            '상태 이상 포트 수: {0}'.format(metrics.get('bad_port_count', 0)),
            'HBA 이벤트 수: {0}'.format(metrics.get('event_count', 0)),
        ]
    if case_id == '28_windows_log_nic_event_check':
        return [
            '서비스 NIC 수: {0}'.format(metrics.get('service_nic_count', 0)),
            'Up 서비스 NIC 수: {0}'.format(metrics.get('up_nic_count', 0)),
            'NIC 이벤트 수: {0}'.format(metrics.get('nic_event_count', 0)),
            'NIC 부정 이벤트 수: {0}'.format(metrics.get('negative_event_count', 0)),
        ]
    if case_id in (
        '21_windows_log_cluster_event_check',
        '22_windows_log_cpu_event_check',
        '25_windows_log_io_event_check',
        '26_windows_log_kernel_event_check',
        '27_windows_log_memory_event_check',
        '29_windows_log_power_event_check',
    ):
        return ['이벤트 수: {0}'.format(metrics.get('event_count', 0))]
    return ['원문 라인 수: {0}'.format(len((metrics.get('_raw_output') or '').splitlines()))]


def _clean_metrics(metrics, matched_keywords):
    clean = {}
    for key, value in metrics.items():
        if key.startswith('_'):
            continue
        clean[key] = value
    clean['matched_failure_keywords'] = matched_keywords
    return clean


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def parse_output(self, output):
        text = (output or '').strip()
        metrics = parse_by_case(CASE_ID, text)
        if not text and not metrics.get('_parse_error'):
            metrics['_parse_error'] = '점검 명령 출력이 비어 있습니다.'
        return metrics

    def evaluate(self, metrics, thresholds):
        if metrics.get('_excluded_reason'):
            return 'excluded'
        if metrics.get('_parse_error'):
            return 'fail'
        if _failure_keyword_matches(metrics, thresholds):
            return 'fail'
        reasons = _evaluation_reasons(CASE_ID, metrics, thresholds)
        if reasons:
            return 'warn' if _warn_case(CASE_ID, reasons) else 'fail'
        return 'ok'

    def build_result(self, metrics, thresholds, status):
        matched_keywords = _failure_keyword_matches(metrics, thresholds)
        clean_metrics = _clean_metrics(metrics, matched_keywords)
        criteria = '\n'.join(
            '{0}: {1}'.format(THRESHOLD_LABELS.get(name, name), _format_value(value))
            for name, value in thresholds.items()
        )

        if status == 'excluded':
            message = '\n'.join([
                '{0} 점검 결과: 제외'.format(CHECK_NAME),
                metrics.get('_excluded_reason') or '점검 대상 조건에 해당하지 않습니다.',
            ])
            results = '\n'.join(['점검 제외 사유: {0}'.format(metrics.get('_excluded_reason') or '대상 미해당')] + _summary_lines(CASE_ID, clean_metrics))
            return {'message': message, 'results': results, 'criteria': criteria, 'metrics': clean_metrics}

        if metrics.get('_parse_error'):
            message = '\n'.join([
                '{0} 점검 결과: 실패'.format(CHECK_NAME),
                metrics['_parse_error'],
            ])
            results = '\n'.join([
                '파싱 상태: 실패',
                '원문 라인 수: {0}'.format(len((metrics.get('_raw_output') or '').splitlines())),
            ])
            return {'message': message, 'results': results, 'criteria': criteria, 'metrics': clean_metrics}

        reasons = []
        if matched_keywords:
            reasons.append('실패 키워드 감지: {0}'.format(_format_value(matched_keywords)))
        reasons.extend(_evaluation_reasons(CASE_ID, metrics, thresholds))

        status_label = {'ok': '정상', 'warn': '주의', 'fail': '기준 미충족'}.get(status, status)
        detail = '모든 점검 기준을 만족합니다.' if not reasons else '\n'.join(reasons)
        message = '\n'.join([
            '{0} 점검 결과: {1}'.format(CHECK_NAME, status_label),
            detail,
        ])
        results = '\n'.join(_summary_lines(CASE_ID, clean_metrics) + [
            '감지된 실패 키워드: {0}'.format(_format_value(matched_keywords)),
        ])
        return {'message': message, 'results': results, 'criteria': criteria, 'metrics': clean_metrics}

    def run(self):
        thresholds = {}
        for name, default, value_type in THRESHOLD_DEFS:
            value = self.get_threshold_var(name, default=default, value_type=value_type)
            if name == 'failure_keywords':
                value = _split_keywords(value)
            thresholds[name] = value

        _rc, out, _err = self._run_ps(CHECK_COMMAND)
        metrics = self.parse_output(out)
        status = self.evaluate(metrics, thresholds)
        result = self.build_result(metrics, thresholds, status)
        return self.result(
            status,
            message=result['message'],
            results=result['results'],
            criteria=result['criteria'],
            metrics=result['metrics'],
        )


CHECK_CLASS = Check
