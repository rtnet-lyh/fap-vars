# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "dmesg | grep -i 'ecc error|singlebit|multibit|uncorrectable'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return '메모리 이상 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def run(self):
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

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
                    'Solaris 메모리 로그 점검에 실패했습니다. '
                    "현재 상태: dmesg | grep -i 'ecc error|singlebit|multibit|uncorrectable' 명령을 정상적으로 실행하지 못했습니다."
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_text = '\n'.join([value for value in (text, stderr_text) if value])
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail(
                '메모리 로그 실패 키워드 감지',
                message=(
                    'Solaris 메모리 로그 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )
        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 메모리 로그 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return self.fail(
                '메모리 오류 로그 감지',
                message=(
                    'Solaris 메모리 로그 점검에 실패했습니다. '
                    f'현재 상태: 메모리 ECC/uncorrectable 관련 로그 {len(lines)}건이 확인되었습니다. '
                    f'첫 로그: {lines[0]}. 로그 요약: {self._build_log_summary(lines)}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics={
                'matched_log_count': len(lines),
                'matched_logs': lines,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'failure_keywords': failure_keywords,
            },
            reasons='메모리 ECC 및 정정 불가 오류 로그가 검출되지 않았고 stderr도 없습니다.',
            message='Solaris 메모리 로그가 정상입니다. 현재 상태: 메모리 ECC/uncorrectable 관련 로그 0건, stderr 0건으로 집계되었습니다.',
        )


CHECK_CLASS = Check
