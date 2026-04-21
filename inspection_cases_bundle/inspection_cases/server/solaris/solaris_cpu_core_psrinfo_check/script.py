# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PSRINFO_VERBOSE_COMMAND = 'psrinfo -v'
PSRINFO_PHYSICAL_COMMAND = 'psrinfo -pv'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _join_stderr(self, err_v, err_p):
        return '\n'.join(part for part in ((err_v or '').strip(), (err_p or '').strip()) if part)

    def _build_processor_summary(self, processors, limit=4):
        if not processors:
            return '가상 프로세서 정보 없음'

        summary_items = [
            f'{item["processor_id"]}:{item["state"]}'
            for item in processors[:limit]
        ]
        if len(processors) > limit:
            summary_items.append(f'외 {len(processors) - limit}개')
        return ', '.join(summary_items)

    def _parse_virtual_processors(self, text):
        processors = []
        raw_blocks = re.finditer(
            r'Status of virtual processor\s+(\d+)\s+as of.*?(?=Status of virtual processor\s+\d+\s+as of|\Z)',
            text or '',
            re.DOTALL,
        )

        for match in raw_blocks:
            processor_id = match.group(1)
            block_text = match.group(0)
            state_match = re.search(
                r'Processor has been\s+([A-Za-z-]+)',
                block_text,
                re.IGNORECASE,
            )
            state = state_match.group(1).lower() if state_match else 'unknown'
            processors.append({
                'processor_id': processor_id,
                'state': state,
            })

        return processors

    def _parse_physical_processors(self, text):
        physical_matches = re.findall(
            r'^The physical processor has\s+(\d+)\s+virtual processors?\s+\(([^)]+)\)',
            text or '',
            re.MULTILINE,
        )
        return [
            {
                'virtual_processor_count': int(virtual_count),
                'processor_range': processor_range.strip(),
            }
            for virtual_count, processor_range in physical_matches
        ]

    def run(self):
        max_offline_processor_count = self.get_threshold_var('max_offline_processor_count', default=0, value_type='int')
        min_physical_processor_count = self.get_threshold_var('min_physical_processor_count', default=1, value_type='int')
        expected_virtual_processor_count = self.get_threshold_var('expected_virtual_processor_count', default=0, value_type='int')
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found',
                value_type='str',
            )
        )

        rc_v, out_v, err_v = self._ssh(PSRINFO_VERBOSE_COMMAND)
        if self._is_connection_error(rc_v, err_v):
            return self.fail(
                '호스트 연결 실패',
                message=(err_v or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err_v or '').strip(),
            )
        if rc_v != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -v 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out_v or '').strip(),
                stderr=(err_v or '').strip(),
            )
        command_error = self._detect_command_error(
            out_v,
            err_v,
            extra_patterns=['permission denied', 'not supported', 'illegal option', 'invalid option'] + failure_keywords,
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -v 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out_v or '').strip(),
                stderr=(err_v or '').strip(),
            )
        rc_p, out_p, err_p = self._ssh(PSRINFO_PHYSICAL_COMMAND)
        if self._is_connection_error(rc_p, err_p):
            return self.fail(
                '호스트 연결 실패',
                message=(err_p or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err_p or '').strip(),
            )
        if rc_p != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -pv 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out_p or '').strip(),
                stderr=(err_p or '').strip(),
            )
        command_error = self._detect_command_error(
            out_p,
            err_p,
            extra_patterns=['permission denied', 'not supported', 'illegal option', 'invalid option'] + failure_keywords,
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -pv 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out_p or '').strip(),
                stderr=(err_p or '').strip(),
            )

        combined_output = '\n'.join(part for part in ((out_v or '').strip(), (out_p or '').strip()) if part)
        combined_stderr = self._join_stderr(err_v, err_p)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in '\n'.join(part for part in (combined_output, combined_stderr) if part).lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'CPU 코어 상태 실패 키워드 감지',
                message=f'Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.',
                stdout=combined_output,
                stderr=combined_stderr,
            )
        if combined_stderr:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: stderr 출력이 확인되었습니다: {combined_stderr}',
                stdout=combined_output,
                stderr=combined_stderr,
            )

        virtual_processors = self._parse_virtual_processors(out_v)
        if not virtual_processors:
            return self.fail(
                'CPU 코어 상태 파싱 실패',
                message='Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -v 출력에서 가상 프로세서 상태를 해석하지 못했습니다.',
                stdout=(out_v or '').strip(),
                stderr=(err_v or '').strip(),
            )
        offline_processors = [item['processor_id'] for item in virtual_processors if item['state'] != 'on-line']

        physical_processors = self._parse_physical_processors(out_p)
        physical_processor_count = len(physical_processors)
        if physical_processor_count == 0:
            return self.fail(
                '물리 CPU 파싱 실패',
                message='Solaris CPU 코어별 상태 점검에 실패했습니다. 현재 상태: psrinfo -pv 출력에서 물리 CPU 구성을 해석하지 못했습니다.',
                stdout=(out_p or '').strip(),
                stderr=(err_p or '').strip(),
            )

        total_physical_virtual_count = sum(item['virtual_processor_count'] for item in physical_processors)
        if total_physical_virtual_count < len(virtual_processors):
            return self.fail(
                'CPU 구성 불일치',
                message=(
                    'Solaris CPU 코어별 상태 점검에 실패했습니다. '
                    f'현재 상태: psrinfo -v 기준 가상 프로세서 {len(virtual_processors)}개, '
                    f'psrinfo -pv 기준 가상 프로세서 합계 {total_physical_virtual_count}개로 집계되어 구성 정보가 서로 일치하지 않습니다.'
                ),
                stdout=combined_output,
                stderr=combined_stderr,
            )

        if expected_virtual_processor_count and len(virtual_processors) < expected_virtual_processor_count:
            return self.fail(
                '가상 프로세서 수 부족',
                message=(
                    'Solaris CPU 코어별 상태 점검에 실패했습니다. '
                    f'현재 상태: 가상 프로세서 {len(virtual_processors)}개로 집계되어 기대값 {expected_virtual_processor_count}개보다 적습니다. '
                    f'물리 CPU {physical_processor_count}개, psrinfo -pv 기준 가상 프로세서 합계 {total_physical_virtual_count}개입니다.'
                ),
                stdout=combined_output,
                stderr=combined_stderr,
            )
        if physical_processor_count < min_physical_processor_count:
            return self.fail(
                '물리 CPU 수 부족',
                message=(
                    'Solaris CPU 코어별 상태 점검에 실패했습니다. '
                    f'현재 상태: 물리 CPU {physical_processor_count}개로 집계되어 기준 {min_physical_processor_count}개 이상을 만족하지 못했습니다. '
                    f'psrinfo -pv 기준 가상 프로세서 합계 {total_physical_virtual_count}개입니다.'
                ),
                stdout=combined_output,
                stderr=combined_stderr,
            )
        if len(offline_processors) > max_offline_processor_count:
            return self.fail(
                '오프라인 CPU 코어 감지',
                message=(
                    'Solaris CPU 코어별 상태 점검에 실패했습니다. '
                    f'현재 상태: off-line 프로세서 {len(offline_processors)}개({", ".join(offline_processors)})로 집계되어 '
                    f'기준 {max_offline_processor_count}개 이하를 초과했습니다. 물리 CPU {physical_processor_count}개, '
                    f'psrinfo -pv 기준 가상 프로세서 합계 {total_physical_virtual_count}개입니다.'
                ),
                stdout=combined_output,
                stderr=combined_stderr,
            )

        physical_summary = ', '.join(
            f'{index + 1}번 물리 CPU {item["virtual_processor_count"]}개({item["processor_range"]})'
            for index, item in enumerate(physical_processors)
        )
        return self.ok(
            metrics={
                'virtual_processor_count': len(virtual_processors),
                'physical_processor_count': physical_processor_count,
                'online_processor_count': len(virtual_processors) - len(offline_processors),
                'offline_processor_count': len(offline_processors),
                'offline_processor_ids': offline_processors,
                'physical_processors': physical_processors,
                'total_physical_virtual_count': total_physical_virtual_count,
                'matched_failure_keywords': matched_failure_keywords,
                'processor_states': virtual_processors,
                'processor_state_summary': self._build_processor_summary(virtual_processors),
            },
            thresholds={
                'max_offline_processor_count': max_offline_processor_count,
                'min_physical_processor_count': min_physical_processor_count,
                'expected_virtual_processor_count': expected_virtual_processor_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'가상 프로세서 {len(virtual_processors)}개가 모두 on-line이며 '
                f'물리 CPU {physical_processor_count}개와 물리 CPU별 가상 프로세서 구성이 정상 인식되었습니다.'
            ),
            message=(
                'Solaris CPU 코어별 상태 점검이 정상입니다. '
                f'현재 상태: 가상 프로세서 {len(virtual_processors)}개 중 on-line {len(virtual_processors) - len(offline_processors)}개, '
                f'off-line {len(offline_processors)}개 (기준 {max_offline_processor_count}개 이하), '
                f'물리 CPU {physical_processor_count}개 (기준 {min_physical_processor_count}개 이상), '
                f'psrinfo -pv 기준 가상 프로세서 합계 {total_physical_virtual_count}개, 구성 {physical_summary}.'
            ),
        )


CHECK_CLASS = Check
