# -*- coding: utf-8 -*-

from .common._base import BaseCheck


CPU_CORE_COMMAND = (
    'Get-CimInstance Win32_Processor | '
    'Select-Object Name,SocketDesignation,Manufacturer,MaxClockSpeed,NumberOfCores,NumberOfLogicalProcessors | '
    'Format-List'
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        min_socket_count = self.get_threshold_var('min_socket_count', default=1, value_type='int')
        min_total_core_count = self.get_threshold_var('min_total_core_count', default=4, value_type='int')
        min_total_logical_processor_count = self.get_threshold_var(
            'min_total_logical_processor_count',
            default=8,
            value_type='int',
        )
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(CPU_CORE_COMMAND)

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
                message='Windows CPU 코어 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'CPU 코어 정보 없음',
                message='CPU 코어 상태 결과가 비어 있습니다.',
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
                'CPU 점검 실패 키워드 감지',
                message='CPU 코어 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        processors = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                if current:
                    processors.append(current)
                    current = {}
                continue

            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            current[key.strip()] = value.strip()

        if current:
            processors.append(current)

        if not processors:
            return self.fail(
                'CPU 코어 정보 파싱 실패',
                message='CPU 코어 상태 결과를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed_processors = []
        for processor in processors:
            try:
                core_count = _parse_int(processor.get('NumberOfCores', ''))
                logical_processor_count = _parse_int(processor.get('NumberOfLogicalProcessors', ''))
                max_clock_speed_mhz = _parse_int(processor.get('MaxClockSpeed', ''))
            except ValueError:
                continue

            threads_per_core = round(
                logical_processor_count / core_count,
                2,
            ) if core_count > 0 else 0.0

            parsed_processors.append({
                'name': processor.get('Name', ''),
                'socket_designation': processor.get('SocketDesignation', ''),
                'manufacturer': processor.get('Manufacturer', ''),
                'max_clock_speed_mhz': max_clock_speed_mhz,
                'number_of_cores': core_count,
                'number_of_logical_processors': logical_processor_count,
                'threads_per_core': threads_per_core,
            })

        if not parsed_processors:
            return self.fail(
                'CPU 코어 정보 파싱 실패',
                message='CPU 코어 수 또는 논리 프로세서 수를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        socket_count = len(parsed_processors)
        total_core_count = sum(processor['number_of_cores'] for processor in parsed_processors)
        total_logical_processor_count = sum(
            processor['number_of_logical_processors']
            for processor in parsed_processors
        )
        max_clock_speed_mhz = max(
            (processor['max_clock_speed_mhz'] for processor in parsed_processors),
            default=0,
        )
        primary_processor = parsed_processors[0]

        if socket_count < min_socket_count:
            return self.fail(
                'CPU 소켓 수 기준 미달',
                message='확인된 물리 CPU 소켓 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if total_core_count < min_total_core_count:
            return self.fail(
                'CPU 코어 수 기준 미달',
                message='확인된 물리 CPU 코어 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if total_logical_processor_count < min_total_logical_processor_count:
            return self.fail(
                'CPU 논리 프로세서 수 기준 미달',
                message='확인된 논리 CPU 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'socket_count': socket_count,
                'total_core_count': total_core_count,
                'total_logical_processor_count': total_logical_processor_count,
                'threads_per_core': primary_processor['threads_per_core'],
                'processor_name': primary_processor['name'],
                'socket_designation': primary_processor['socket_designation'],
                'manufacturer': primary_processor['manufacturer'],
                'max_clock_speed_mhz': max_clock_speed_mhz,
                'processor_names': [processor['name'] for processor in parsed_processors],
                'socket_designations': [processor['socket_designation'] for processor in parsed_processors],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_socket_count': min_socket_count,
                'min_total_core_count': min_total_core_count,
                'min_total_logical_processor_count': min_total_logical_processor_count,
                'failure_keywords': failure_keywords,
            },
            reasons='물리 CPU 소켓 수, 물리 코어 수, 논리 프로세서 수가 모두 기준 범위 내입니다.',
            message='Windows CPU 코어 상태 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
