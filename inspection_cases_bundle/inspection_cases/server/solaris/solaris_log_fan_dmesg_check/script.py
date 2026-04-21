# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "dmesg | grep -i 'fan|fail'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _find_bad_lines(self, lines, bad_keywords):
        bad_lines = []
        for line in lines:
            lowered = line.lower()
            if any(keyword.lower() in lowered for keyword in bad_keywords):
                bad_lines.append(line)
        return bad_lines

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return 'FAN 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def run(self):
        bad_log_keywords = self._split_keywords(self.get_threshold_var('bad_log_keywords', default='failed,not spinning,over-temperature,fail', value_type='str'))
        failure_keywords = self._split_keywords(self.get_threshold_var('failure_keywords', default='', value_type='str'))

        rc, out, err = self._ssh(LOG_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris FAN 로그 점검에 실패했습니다. '
                    "현재 상태: dmesg | grep -i 'fan|fail' 명령을 정상적으로 실행하지 못했습니다."
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join([value for value in (text, stderr_text) if value])
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail(
                'FAN 로그 실패 키워드 감지',
                message=(
                    'Solaris FAN 로그 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )
        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris FAN 로그 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        bad_lines = self._find_bad_lines(lines, bad_log_keywords)
        if bad_lines:
            return self.fail(
                'FAN 이상 로그 감지',
                message=(
                    'Solaris FAN 로그 점검에 실패했습니다. '
                    f'현재 상태: FAN 관련 로그 {len(lines)}건 중 비정상 로그 {len(bad_lines)}건이 확인되었습니다. '
                    f'첫 로그: {bad_lines[0]}. 로그 요약: {self._build_log_summary(bad_lines)}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics={
                'matched_log_count': len(lines),
                'abnormal_log_count': len(bad_lines),
                'matched_logs': lines,
                'abnormal_logs': bad_lines,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'bad_log_keywords': bad_log_keywords,
                'failure_keywords': failure_keywords,
            },
            reasons='FAN 관련 비정상 로그가 검출되지 않았고 stderr도 없습니다.',
            message=(
                f'Solaris FAN 로그가 정상입니다. 현재 상태: FAN 관련 로그 {len(lines)}건 조회, '
                f'비정상 로그 0건, stderr 0건으로 집계되었습니다.'
            ),
        )


CHECK_CLASS = Check
