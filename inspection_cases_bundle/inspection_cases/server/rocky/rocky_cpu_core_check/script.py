# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_cpu_list(self, text):
        cpus = set()
        for token in str(text or '').split(','):
            token = token.strip()
            if not token:
                continue
            if '-' in token:
                start, end = token.split('-', 1)
                try:
                    start_no = int(start.strip())
                    end_no = int(end.strip())
                except ValueError:
                    continue
                if start_no <= end_no:
                    cpus.update(range(start_no, end_no + 1))
                else:
                    cpus.update(range(end_no, start_no + 1))
                continue
            try:
                cpus.add(int(token))
            except ValueError:
                continue
        return sorted(cpus)

    def _parse_fail_keywords(self, raw_value):
        return [
            keyword.strip().lower()
            for keyword in re.split(r'[,|\n]+', str(raw_value or ''))
            if keyword.strip()
        ]

    def _format_cpu_list(self, cpus):
        if not cpus:
            return '없음'
        return ','.join(str(cpu) for cpu in cpus)

    def _parse_lscpu(self, text):
        total_match = re.search(r'(?m)^\s*CPU\(s\):\s*([0-9]+)\s*$', text or '')
        online_match = re.search(r'(?m)^\s*On-line CPU\(s\) list:\s*(.+?)\s*$', text or '')
        offline_match = re.search(r'(?m)^\s*Off-line CPU\(s\) list:\s*(.+?)\s*$', text or '')

        total_cpu_count = int(total_match.group(1)) if total_match else 0
        online_cpus = self._parse_cpu_list(online_match.group(1) if online_match else '')
        offline_cpus = self._parse_cpu_list(offline_match.group(1) if offline_match else '')

        if total_cpu_count > 0 and online_cpus:
            expected_cpus = set(range(total_cpu_count))
            derived_offline = sorted(expected_cpus - set(online_cpus))
            if derived_offline:
                offline_cpus = sorted(set(offline_cpus) | set(derived_offline))

        return {
            'cpu_count': total_cpu_count,
            'online_cpus': online_cpus,
            'offline_cpus': offline_cpus,
        }

    def run(self):
        fail_keywords_raw = self.get_threshold_var('fail_keywords', default='offline')
        fail_keywords = self._parse_fail_keywords(fail_keywords_raw)
        rc, out, err = self._ssh("lscpu")

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='lscpu 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'CPU 정보 없음',
                message='lscpu 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        parsed = self._parse_lscpu(text)
        if parsed['cpu_count'] <= 0 or not parsed['online_cpus']:
            return self.fail(
                'CPU 정보 파싱 실패',
                message='lscpu 결과에서 CPU(s) 또는 On-line CPU(s) list를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        output_lower = text.lower()
        matched_fail_keywords = [
            keyword
            for keyword in fail_keywords
            if keyword and keyword in output_lower
        ]

        if parsed['offline_cpus']:
            return self.fail(
                'CPU 코어 상태 비정상',
                message=(
                    'offline CPU가 존재합니다. '
                    f"점검 근거: lscpu 결과 총 CPU {parsed['cpu_count']}개 중 "
                    f"online {len(parsed['online_cpus'])}개, "
                    f"offline {len(parsed['offline_cpus'])}개"
                    f"({self._format_cpu_list(parsed['offline_cpus'])})입니다. "
                    f'판단기준: offline CPU가 0개이고 '
                    f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                    '감지되지 않아야 합니다.'
                ),
                stdout=text,
            )

        if matched_fail_keywords:
            return self.fail(
                'CPU 코어 상태 비정상',
                message=(
                    f"실패 키워드가 감지되었습니다: {', '.join(matched_fail_keywords)}. "
                    f"점검 근거: lscpu 결과 총 CPU {parsed['cpu_count']}개 중 "
                    f"online {len(parsed['online_cpus'])}개, "
                    f"offline {len(parsed['offline_cpus'])}개이며 "
                    f"출력에서 실패 키워드 {', '.join(matched_fail_keywords)}가 감지되었습니다. "
                    f'판단기준: offline CPU가 0개이고 '
                    f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                    '감지되지 않아야 합니다.'
                ),
                stdout=text,
            )

        return self.ok(
            metrics={
                'cpu_count': parsed['cpu_count'],
                'online_cpu_count': len(parsed['online_cpus']),
                'offline_cpu_count': len(parsed['offline_cpus']),
                'online_cpus': parsed['online_cpus'],
                'offline_cpus': parsed['offline_cpus'],
                'matched_fail_keywords': matched_fail_keywords,
            },
            thresholds={
                'fail_keywords': fail_keywords_raw,
            },
            reasons=(
                f"총 CPU {parsed['cpu_count']}개 중 online {len(parsed['online_cpus'])}개, "
                'offline 0개이며 실패 키워드가 감지되지 않았습니다.'
            ),
            message=(
                'lscpu 기준 CPU 코어 상태 점검이 정상 수행되었습니다. '
                f"점검 근거: 총 CPU {parsed['cpu_count']}개 중 "
                f"online {len(parsed['online_cpus'])}개, "
                'offline 0개이며 실패 키워드가 감지되지 않았습니다. '
                f'판단기준: offline CPU가 0개이고 '
                f'실패 키워드(fail_keywords={fail_keywords_raw})가 '
                '감지되지 않아야 합니다.'
            ),
            raw_output=text,
        )


CHECK_CLASS = Check
