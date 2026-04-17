# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


MEMORY_STATUS_COMMAND = (
    '$a=Get-CimInstance Win32_PhysicalMemoryArray;'
    '$m=Get-CimInstance Win32_PhysicalMemory;'
    '"ARRAY slots=$((($a|Measure-Object -Property MemoryDevices -Sum).Sum)) max={0:N2}GiB" -f '
    '((((($a|Measure-Object -Property MaxCapacityEx -Sum).Sum)*1KB)/1GB));'
    '$m|Select-Object DeviceLocator,BankLabel,@{N=\'SizeGiB\';E={[math]::Round($_.Capacity/1GB,2)}},Manufacturer,PartNumber,SerialNumber,ConfiguredClockSpeed,Speed,SMBIOSMemoryType,FormFactor | '
    'Format-Table -AutoSize'
)


def _parse_float(value):
    return round(float(value), 2)


def _parse_int(value):
    return int(str(value).strip())


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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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
                message='메모리 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        array_match = re.search(r'ARRAY slots=(\d+) max=([0-9]+(?:\.[0-9]+)?)GiB', text)
        if not array_match:
            return self.fail(
                '메모리 배열 정보 파싱 실패',
                message='메모리 슬롯 수 또는 최대 용량을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        array_slot_count = _parse_int(array_match.group(1))
        array_max_capacity_gib = _parse_float(array_match.group(2))

        lines = [line.rstrip() for line in text.splitlines()]
        separator_index = -1
        for idx, line in enumerate(lines):
            if line.strip().startswith('---'):
                separator_index = idx
                break

        if separator_index < 0:
            return self.fail(
                '메모리 모듈 정보 파싱 실패',
                message='메모리 모듈 표 헤더를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        module_rows = []
        for line in lines[separator_index + 1:]:
            if not line.strip():
                continue

            tokens = line.split()
            numeric_tokens = [token for token in tokens if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', token)]
            if len(numeric_tokens) < 5:
                continue

            try:
                size_gib = _parse_float(numeric_tokens[0])
                configured_clock_speed_mhz = _parse_int(numeric_tokens[-4])
                speed_mhz = _parse_int(numeric_tokens[-3])
                smbios_memory_type = _parse_int(numeric_tokens[-2])
                form_factor = _parse_int(numeric_tokens[-1])
            except ValueError:
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
            message='Windows 메모리 상태 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
