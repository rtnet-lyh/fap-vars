# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


MEMORY_STATUS_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    '$a=Get-CimInstance Win32_PhysicalMemoryArray;'
    '$m=Get-CimInstance Win32_PhysicalMemory;'
    '$result = [ordered]@{'
    '  Array = [ordered]@{'
    '    Slots = (($a | Measure-Object -Property MemoryDevices -Sum).Sum);'
    '    MaxCapacityGiB = [math]::Round((((($a | Measure-Object -Property MaxCapacityEx -Sum).Sum) * 1KB) / 1GB), 2)'
    '  };'
    '  Modules = @($m | Select-Object '
    '    DeviceLocator,'
    '    BankLabel,'
    '    @{N=\'SizeGiB\';E={[math]::Round($_.Capacity/1GB,2)}},'
    '    Manufacturer,'
    '    PartNumber,'
    '    SerialNumber,'
    '    ConfiguredClockSpeed,'
    '    Speed,'
    '    SMBIOSMemoryType,'
    '    FormFactor'
    '  )'
    '};'
    '$result | ConvertTo-Json -Depth 4'
)


def _parse_float(value):
    return round(float(value), 2)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        min_installed_memory_gib = self.get_threshold_var('min_installed_memory_gib', default=8.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(MEMORY_STATUS_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 메모리 인식 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 메모리 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').rstrip()
        if not text:
            return self.fail(
                '메모리 상태 정보 없음',
                message='메모리 상태 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '메모리 점검 실패 키워드 감지',
                message=f'메모리 상태 결과에서 실패 키워드가 확인되었습니다.: 실패 키워드: {", ".join(matched_failure_keywords)}',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '메모리 상태 파싱 실패',
                message='메모리 상태 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        array_info = parsed.get('Array', {}) if isinstance(parsed, dict) else {}
        module_entries = _as_list(parsed.get('Modules', [])) if isinstance(parsed, dict) else []

        try:
            array_slot_count = _parse_int(array_info.get('Slots', 0))
            array_max_capacity_gib = _parse_float(array_info.get('MaxCapacityGiB', 0))
        except (TypeError, ValueError):
            return self.fail(
                '메모리 배열 정보 파싱 실패',
                message='메모리 슬롯 수 또는 최대 용량을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        module_rows = []
        for entry in module_entries:
            try:
                size_gib = _parse_float(entry.get('SizeGiB', 0))
                configured_clock_speed_value = entry.get('ConfiguredClockSpeed', '')
                speed_value = entry.get('Speed', '')
                smbios_memory_type_value = entry.get('SMBIOSMemoryType', '')
                form_factor_value = entry.get('FormFactor', '')
                configured_clock_speed_mhz = _parse_int(configured_clock_speed_value) if str(configured_clock_speed_value).strip() else 0
                speed_mhz = _parse_int(speed_value) if str(speed_value).strip() else 0
                smbios_memory_type = _parse_int(smbios_memory_type_value) if str(smbios_memory_type_value).strip() else 0
                form_factor = _parse_int(form_factor_value) if str(form_factor_value).strip() else 0
            except (TypeError, ValueError):
                continue

            module_rows.append({
                'size_gib': size_gib,
                'configured_clock_speed_mhz': configured_clock_speed_mhz,
                'speed_mhz': speed_mhz,
                'smbios_memory_type': smbios_memory_type,
                'form_factor': form_factor,
            })

        if not module_rows:
            return self.fail(
                '메모리 모듈 정보 파싱 실패',
                message='설치된 메모리 모듈 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        installed_module_count = len(module_rows)
        installed_memory_total_gib = round(sum(row['size_gib'] for row in module_rows), 2)
        configured_clock_speeds_mhz = [row['configured_clock_speed_mhz'] for row in module_rows]
        memory_speeds_mhz = [row['speed_mhz'] for row in module_rows]
        smbios_memory_types = [row['smbios_memory_type'] for row in module_rows]
        form_factors = [row['form_factor'] for row in module_rows]

        if installed_memory_total_gib < min_installed_memory_gib:
            return self.fail(
                '설치 메모리 용량 기준 미달',
                message='설치된 메모리 총 용량이 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'array_slot_count': array_slot_count,
                'array_max_capacity_gib': array_max_capacity_gib,
                'installed_module_count': installed_module_count,
                'installed_memory_total_gib': installed_memory_total_gib,
                'configured_clock_speeds_mhz': configured_clock_speeds_mhz,
                'memory_speeds_mhz': memory_speeds_mhz,
                'smbios_memory_types': smbios_memory_types,
                'form_factors': form_factors,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_installed_memory_gib': min_installed_memory_gib,
                'failure_keywords': failure_keywords,
            },
            reasons='메모리 슬롯 정보와 설치 메모리 용량이 기준 범위 내입니다.',
            message=(
                f'Windows 메모리 상태 점검이 정상입니다. 현재 상태: '
                f'메모리 슬롯 {array_slot_count}개, 최대 용량 {array_max_capacity_gib:.2f}GiB, '
                f'설치 모듈 {installed_module_count}개, 설치 용량 {installed_memory_total_gib:.2f}GiB '
                f'(기준 {min_installed_memory_gib:.2f}GiB 이상).'
            ),
        )


CHECK_CLASS = Check
