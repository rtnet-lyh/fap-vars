# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


DEFAULT_HBA_PORT_FAIL_KEYWORDS = (
    'offline due to error|port offline|link down|loop detected|loop failure|loop down'
)
DEFAULT_HBA_PORT_EXECPT_KEYWORDS = 'sata link down'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _build_dmesg_fail_command(self, keywords):
        grep_args = ' '.join(
            '-e ' + shlex.quote(keyword)
            for keyword in keywords
        )
        return 'dmesg | grep -Fi ' + grep_args

    def _find_matches(self, lines, keywords):
        matches = []

        for line in lines:
            lowered = line.lower()
            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower() in lowered
            ]
            if not matched_keywords:
                continue
            matches.append({
                'line': line,
                'matched_keywords': matched_keywords,
            })

        return matches

    def _filter_except_matches(self, matches, except_keywords):
        fail_matches = []
        except_matches = []

        for match in matches:
            line = match.get('line') or ''
            lowered = line.lower()
            matched_except_keywords = [
                keyword
                for keyword in except_keywords
                if keyword.lower() in lowered
            ]
            if matched_except_keywords:
                excluded_match = dict(match)
                excluded_match['matched_except_keywords'] = matched_except_keywords
                except_matches.append(excluded_match)
                continue

            fail_matches.append(match)

        return fail_matches, except_matches

    def _count_keywords(self, matches, keywords):
        counts = {keyword: 0 for keyword in keywords}

        for match in matches:
            for keyword in match.get('matched_keywords', []):
                if keyword in counts:
                    counts[keyword] += 1

        return counts

    def _format_keyword_counts(self, counts):
        return ', '.join(
            f'{keyword}={count}건'
            for keyword, count in counts.items()
        )

    def run(self):
        fail_keywords = self._split_keywords(
            self.get_threshold_var(
                'hba_port_fail_keywords',
                default=DEFAULT_HBA_PORT_FAIL_KEYWORDS,
                value_type='str',
            )
        )
        except_keywords = self._split_keywords(
            self.get_threshold_var(
                'hba_port_execpt_keywords',
                default=DEFAULT_HBA_PORT_EXECPT_KEYWORDS,
                value_type='str',
            )
        )
        if not fail_keywords:
            return self.fail(
                '임계치 미정의',
                message='hba_port_fail_keywords 가 정의되어 있지 않습니다.',
            )

        command = self._build_dmesg_fail_command(fail_keywords)
        rc, out, err = self._ssh(command)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg HBA 포트 장애 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        candidate_matches = self._find_matches(lines, fail_keywords)
        fail_matches, except_matches = self._filter_except_matches(candidate_matches, except_keywords)
        fail_keyword_counts = self._count_keywords(fail_matches, fail_keywords)
        candidate_keyword_counts = self._count_keywords(candidate_matches, fail_keywords)
        thresholds = {
            'hba_port_fail_keywords': '|'.join(fail_keywords),
            'hba_port_execpt_keywords': '|'.join(except_keywords),
        }
        metrics = {
            'grep_line_count': len(lines),
            'hba_port_fail_candidate_count': len(candidate_matches),
            'hba_port_fail_match_count': len(fail_matches),
            'hba_port_except_match_count': len(except_matches),
            'hba_port_fail_keyword_counts': fail_keyword_counts,
            'hba_port_fail_candidate_keyword_counts': candidate_keyword_counts,
            'hba_port_fail_matches': fail_matches,
            'hba_port_except_matches': except_matches,
            'grep_lines': lines,
        }
        threshold_summary = (
            'hba_port_fail_keywords=' + thresholds['hba_port_fail_keywords'] +
            '; hba_port_execpt_keywords=' + thresholds['hba_port_execpt_keywords']
        )

        if fail_matches:
            result = self.fail(
                'HBA 포트 장애 로그 감지',
                message=(
                    'HBA 포트 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                    f'. 제외 로그 {len(except_matches)}건. '
                    '임계치: ' + threshold_summary
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = (
                'HBA 포트 장애 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            )
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                'HBA 포트 장애 키워드가 검출되지 않았습니다. '
                '키워드별 검출 건수: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건.'
            ),
            message=(
                'HBA 포트 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(fail_keyword_counts) +
                f'. 제외 로그 {len(except_matches)}건. '
                '임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check