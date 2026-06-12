# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _thresholds(self):
        return {
            'require_vcenter_connection': self.get_threshold_var('require_vcenter_connection', True, 'bool'),
            'expected_connection_state': self.get_threshold_var('expected_connection_state', 'connected', 'str'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        vpxa = metrics.get('vpxa') or {}
        return '\n'.join([
            'ESXi vCenter Agent 통신 상태 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- host_name: %s' % metrics.get('host_name', ''),
            '- managed_by_vcenter: %s' % metrics.get('managed_by_vcenter', ''),
            '- management_server_ip: %s' % metrics.get('management_server_ip', ''),
            '- connection_state: %s' % metrics.get('connection_state', ''),
            '- vpxa.exists: %s' % vpxa.get('exists', ''),
            '- vpxa.running: %s' % vpxa.get('running', ''),
            '- vpxa.policy: %s' % vpxa.get('policy', ''),
        ])

    def _state_summary(self, metrics, thresholds):
        vpxa = metrics.get('vpxa') or {}
        return ', '.join([
            'host=%s' % metrics.get('host_name', ''),
            'managed_by_vcenter=%s' % metrics.get('managed_by_vcenter', ''),
            'management_server_ip=%s' % (metrics.get('management_server_ip') or '없음'),
            'connection_state=%s (기준 %s)' % (
                metrics.get('connection_state'),
                thresholds['expected_connection_state'],
            ),
            'vpxa.exists=%s' % vpxa.get('exists', ''),
            'vpxa.running=%s' % vpxa.get('running', ''),
        ])

    def _build_message(self, metrics, thresholds, failed=None):
        current_state = self._state_summary(metrics, thresholds)
        if failed:
            return (
                'ESXi vCenter Agent 통신 상태가 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi vCenter Agent 통신 상태가 정상입니다. 현재 상태: %s. '
            'vCenter 관리 정보와 vpxa 서비스 상태가 모두 기준을 충족했습니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        managed = bool(metrics.get('managed_by_vcenter'))
        vpxa = metrics.get('vpxa') or {}

        if not managed and not thresholds['require_vcenter_connection']:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='단독 ESXi 운영 정책으로 vCenter 연결 점검 대상이 아닙니다.',
                raw_output=self._raw_output(metrics),
                message=(
                    'ESXi가 vCenter 관리 대상으로 확인되지 않아 대상미해당으로 분류했습니다. '
                    '현재 상태: %s.'
                ) % self._state_summary(metrics, thresholds),
            )

        failed = []
        if not managed:
            failed.append('vCenter 관리 서버 정보가 확인되지 않습니다.')
        if managed and not metrics.get('management_server_ip'):
            failed.append('management_server_ip가 비어 있습니다.')
        if metrics.get('connection_state') != thresholds['expected_connection_state']:
            failed.append('Connection State %s != %s' % (
                metrics.get('connection_state'),
                thresholds['expected_connection_state'],
            ))
        if not vpxa.get('exists'):
            failed.append('vpxa 서비스가 존재하지 않습니다.')
        elif not vpxa.get('running'):
            failed.append('vpxa 서비스가 실행 중이 아닙니다.')

        if failed:
            result = self.fail(
                'ESXi vCenter Agent 기준 미충족',
                message=self._build_message(metrics, thresholds, failed),
                raw_output=self._raw_output(metrics),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = ', '.join(failed)
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='vCenter 관리 서버 정보가 확인되고 vpxa 및 관리 연결 상태가 정상입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.vcenter_agent_status_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi vCenter Agent 조회 실패',
                message='VMwareHelper 기반 ESXi vCenter Agent 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi vCenter Agent 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
