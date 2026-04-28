# type_name

일상점검(상태점검)

# area_name

서버

# category_name

MEMORY

# application_type

UNIX

# application

solaris

# inspection_code

SVR-2-2

# is_required

권고

# inspection_name

메모리 상태 확인

# inspection_content

시스템이 총 메모리 용량과 DIMM 모듈 정보를 정상적으로 인식하는지 점검합니다.

# inspection_command

```bash
prtdiag
```

# inspection_output

```text
System Configuration: Sun Microsystems sun4u
Memory size: 8192 Megabytes
Memory Module:
DIMM 0: 4096 MB, 64-bit, Error Correcting Code
DIMM 1: 4096 MB, 64-bit, Error Correcting Code
```

# description

- `Memory size`로 시스템이 인식한 총 메모리 용량을 확인.
  - 예시 기준 총 8GB가 정상 인식됨.
  - DIMM 단위 정보로 메모리 모듈 상태도 함께 점검 가능.

# thresholds

[
    {id: null, key: "expected_memory_mb", value: "8192", sortOrder: 0}
,
{id: null, key: "min_dimm_count", value: "1", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PRTDIAG_COMMAND = 'prtdiag'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _to_memory_mb(self, value, unit):
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None

        lowered_unit = str(unit or '').strip().lower()
        if lowered_unit.startswith('giga'):
            return round(number * 1024.0, 2)
        if lowered_unit.startswith('mega'):
            return round(number, 2)
        if lowered_unit.startswith('kilo'):
            return round(number / 1024.0, 2)
        return None

    def _parse_memory_size(self, text):
        match = re.search(r'Memory size:\s*([0-9]+(?:\.[0-9]+)?)\s*(Kilobytes|Megabytes|Gigabytes)', text or '', re.IGNORECASE)
        if not match:
            return None

        recognized_memory_mb = self._to_memory_mb(match.group(1), match.group(2))
        if recognized_memory_mb is None:
            return None

        return {
            'recognized_memory_mb': recognized_memory_mb,
            'recognized_memory_gib': round(recognized_memory_mb / 1024.0, 2),
            'memory_unit': match.group(2),
            'memory_value': match.group(1),
        }

    def _parse_dimm_entries(self, text):
        dimm_entries = []

        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or not re.match(r'^(DIMM|Memory Module)', stripped, re.IGNORECASE):
                continue

            if re.match(r'^DIMM\s+\d+:', stripped, re.IGNORECASE):
                slot_match = re.match(r'^(DIMM\s+\d+):\s*(.*)$', stripped, re.IGNORECASE)
                if not slot_match:
                    continue

                slot_name = slot_match.group(1)
                details = slot_match.group(2)
                size_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(KB|MB|GB)', details, re.IGNORECASE)
                size_mb = None
                if size_match:
                    size_value = size_match.group(1)
                    size_unit = size_match.group(2)
                    normalized_unit = {
                        'KB': 'Kilobytes',
                        'MB': 'Megabytes',
                        'GB': 'Gigabytes',
                    }.get(size_unit.upper(), size_unit)
                    size_mb = self._to_memory_mb(size_value, normalized_unit)

                dimm_entries.append({
                    'slot_name': slot_name,
                    'details': details,
                    'size_mb': size_mb,
                    'has_ecc': 'error correcting code' in details.lower() or 'ecc' in details.lower(),
                })

        return dimm_entries

    def run(self):
        expected_memory_mb = self.get_threshold_var('expected_memory_mb', default=0, value_type='int')
        min_dimm_count = self.get_threshold_var('min_dimm_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(PRTDIAG_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'SSH 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())

        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag 명령을 정상적으로 실행하지 못했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        command_error = self._detect_command_error(out, err, extra_patterns=['permission denied', 'not supported', 'unknown userland error'])
        if command_error:
            return self.fail('점검 명령 실행 실패', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag 출력에서 실행 오류가 확인되었습니다: {command_error}', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_text = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail('메모리 인식 실패 키워드 감지', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        parsed_memory = self._parse_memory_size(text)
        if not parsed_memory:
            return self.fail('메모리 인식 정보 없음', message='Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag 출력에서 Memory size 값을 찾지 못했습니다.', stdout=text, stderr=(err or '').strip())

        recognized_memory_mb = parsed_memory['recognized_memory_mb']
        recognized_memory_gib = parsed_memory['recognized_memory_gib']

        dimm_entries = self._parse_dimm_entries(text)
        dimm_count = len(dimm_entries)
        dimm_sized_entries = [entry for entry in dimm_entries if entry.get('size_mb') is not None]
        dimm_total_mb = round(sum(entry['size_mb'] for entry in dimm_sized_entries), 2) if dimm_sized_entries else 0.0
        ecc_dimm_count = len([entry for entry in dimm_entries if entry.get('has_ecc')])

        if expected_memory_mb and recognized_memory_mb < expected_memory_mb:
            return self.fail('인식 메모리 부족', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: 인식 메모리 {recognized_memory_mb:.2f}MB ({recognized_memory_gib:.2f}GiB)로 집계되어 기대값 {expected_memory_mb}MB보다 작습니다. DIMM {dimm_count}개, DIMM 합계 {dimm_total_mb:.2f}MB입니다.', stdout=text, stderr=(err or '').strip())

        if dimm_count < min_dimm_count:
            return self.fail('DIMM 정보 부족', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: DIMM {dimm_count}개만 확인되어 기준 {min_dimm_count}개 이상을 만족하지 못했습니다. 총 메모리 {recognized_memory_mb:.2f}MB ({recognized_memory_gib:.2f}GiB), DIMM 합계 {dimm_total_mb:.2f}MB입니다.', stdout=text, stderr=(err or '').strip())

        if dimm_sized_entries and dimm_total_mb + 0.01 < recognized_memory_mb:
            return self.fail('DIMM 합계와 총 메모리 불일치', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: Memory size {recognized_memory_mb:.2f}MB인데 DIMM 합계는 {dimm_total_mb:.2f}MB로 더 작습니다. DIMM {dimm_count}개, ECC 표기 DIMM {ecc_dimm_count}개입니다.', stdout=text, stderr=(err or '').strip())

        metrics = {
            'recognized_memory_mb': recognized_memory_mb,
            'recognized_memory_gib': recognized_memory_gib,
            'dimm_count': dimm_count,
            'dimm_total_mb': dimm_total_mb,
            'ecc_dimm_count': ecc_dimm_count,
            'dimm_entries': dimm_entries,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'expected_memory_mb': expected_memory_mb,
            'min_dimm_count': min_dimm_count,
            'failure_keywords': failure_keywords,
        }

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=f'총 메모리 {recognized_memory_mb:.2f}MB와 DIMM {dimm_count}개가 정상 인식되었고 DIMM 합계도 일치합니다.',
            message=f'Solaris 메모리 상태가 정상입니다. 현재 상태: 총 메모리 {recognized_memory_mb:.2f}MB ({recognized_memory_gib:.2f}GiB), DIMM {dimm_count}개 (기준 {min_dimm_count}개 이상), DIMM 합계 {dimm_total_mb:.2f}MB, ECC 표기 DIMM {ecc_dimm_count}개, 기대 메모리 {expected_memory_mb}MB 이상.',
        )


CHECK_CLASS = Check
