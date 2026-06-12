# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


OS_PATH_HA_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "if (Get-Command Get-MPIOSetting -ErrorAction SilentlyContinue) { "
    "Get-MPIOSetting | Select-Object PathVerificationState,PathVerificationPeriod,RetryCount,RetryInterval,DiskTimeoutValue,@{N='LoadBalancePolicy';E={Get-MSDSMGlobalDefaultLoadBalancePolicy 2>$null}} | Format-List; "
    "mpclaim.exe -s -d } else { 'MPIO 미설치 또는 미지원' }"
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        expected_policy_keyword = self.get_threshold_var('expected_policy_keyword', default='round', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(OS_PATH_HA_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows MPIO 경로 이중화 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows MPIO 경로 이중화 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or text == 'MPIO 미설치 또는 미지원':
            return self.fail(
                'MPIO 미설치 또는 미지원',
                message=(
                    'Windows MPIO 경로 이중화 점검에 실패했습니다. '
                    '현재 상태: MPIO가 설치되어 있지 않거나 지원되지 않아 '
                    'active 유사 경로 0개, failed 유사 경로 0개로 집계했습니다.'
                ),
                stdout=text,
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
                'MPIO 실패 키워드 감지',
                message='MPIO 경로 이중화 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        info = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ':' not in stripped:
                continue
            key, value = stripped.split(':', 1)
            info[key.strip()] = value.strip()

        lower_text = text.lower()
        active_path_like_count = len(re.findall(r'\bactive\b|\brunning\b', lower_text))
        enabled_path_like_count = len(re.findall(r'\benabled\b|\bstandby\b', lower_text))
        failed_path_like_count = len(re.findall(r'\bfailed\b|\bfaulty\b|\boffline\b', lower_text))
        load_balance_policy = str(info.get('LoadBalancePolicy', '')).strip()

        if failed_path_like_count > 0:
            return self.fail(
                'MPIO 경로 상태 이상 감지',
                message='failed, faulty 또는 offline 상태로 보이는 경로가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if expected_policy_keyword and load_balance_policy:
            if expected_policy_keyword.lower() not in load_balance_policy.lower():
                return self.fail(
                    'MPIO 부하분산 정책 불일치',
                    message='MPIO 부하분산 정책이 기대한 정책과 일치하지 않습니다.',
                    stdout=text,
                    stderr=(err or '').strip(),
                )

        reasons = 'MPIO 구성과 경로 상태를 점검한 결과 비정상 경로 징후가 확인되지 않았습니다.'

        return self.ok(
            metrics={
                'mpio_installed': True,
                'path_verification_state': info.get('PathVerificationState', ''),
                'path_verification_period': info.get('PathVerificationPeriod', ''),
                'retry_count': info.get('RetryCount', ''),
                'retry_interval': info.get('RetryInterval', ''),
                'disk_timeout_value': info.get('DiskTimeoutValue', ''),
                'load_balance_policy': load_balance_policy,
                'active_path_like_count': active_path_like_count,
                'enabled_path_like_count': enabled_path_like_count,
                'failed_path_like_count': failed_path_like_count,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'expected_policy_keyword': expected_policy_keyword,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows MPIO 경로 이중화 점검이 정상입니다. 현재 상태: '
                f'load_balance_policy={load_balance_policy or "N/A"}, '
                f'active 유사 경로 {active_path_like_count}개, enabled/standby 유사 경로 {enabled_path_like_count}개, '
                f'failed/faulty/offline 유사 경로 {failed_path_like_count}개.'
            ),
        )


CHECK_CLASS = Check
