# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _list_threshold(self, key, default=''):
        raw = self.get_threshold_var(key, default, 'str')
        return [
            item.strip()
            for item in str(raw or '').replace('\r', '\n').replace('\n', ',').split(',')
            if item.strip()
        ]

    def _thresholds(self):
        return {
            'required_agent_services': self._list_threshold('required_agent_services', 'hostd'),
            'require_vpxa_when_managed': self.get_threshold_var('require_vpxa_when_managed', True, 'bool'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        lines = [
            'ESXi HostServiceSystem Agent 서비스 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- host_name: %s' % metrics.get('host_name', ''),
            '- managed_by_vcenter: %s' % metrics.get('managed_by_vcenter', ''),
            '- management_server_ip: %s' % metrics.get('management_server_ip', ''),
            '- connection_state: %s' % metrics.get('connection_state', ''),
            '- services:',
        ]
        for service in metrics.get('services') or []:
            lines.append(
                '  - {key} ({label}): running={running}, policy={policy}'.format(
                    key=service.get('key', ''),
                    label=service.get('label', ''),
                    running=service.get('running', ''),
                    policy=service.get('policy', ''),
                )
            )
        lines.extend([
            '- missing_services: %s' % ', '.join(metrics.get('missing_services') or []),
            '- stopped_services: %s' % ', '.join(metrics.get('stopped_services') or []),
        ])
        return '\n'.join(lines)

    def _required_services(self, metrics, thresholds):
        required = list(thresholds['required_agent_services'])
        if metrics.get('managed_by_vcenter') and thresholds['require_vpxa_when_managed']:
            if not any(service.lower() == 'vpxa' for service in required):
                required.append('vpxa')
        return required

    def _build_message(self, metrics, thresholds, failed=None):
        services = metrics.get('services') or []
        required_services = self._required_services(metrics, thresholds)
        running_services = sorted(
            service.get('key', '')
            for service in services
            if service.get('running') and service.get('key')
        )
        current_state = ', '.join([
            'host=%s' % metrics.get('host_name', ''),
            'managed_by_vcenter=%s' % metrics.get('managed_by_vcenter', ''),
            '필수 서비스=%s' % (', '.join(required_services) or '없음'),
            '실행 중 서비스=%s' % (', '.join(running_services) or '없음'),
        ])
        if failed:
            return (
                'ESXi Agent 서비스 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi Agent 서비스 상태가 정상입니다. 현재 상태: %s. '
            '필수 Agent 서비스가 모두 존재하고 실행 중입니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        services = metrics.get('services') or []
        service_map = {
            str(service.get('key') or '').lower(): service
            for service in services
        }

        missing = []
        stopped = []
        for service_name in thresholds['required_agent_services']:
            service = service_map.get(service_name.lower())
            if service is None:
                missing.append(service_name)
            elif not service.get('running'):
                stopped.append(service_name)

        if metrics.get('managed_by_vcenter') and thresholds['require_vpxa_when_managed']:
            vpxa = service_map.get('vpxa')
            if vpxa is None and 'vpxa' not in missing:
                missing.append('vpxa')
            elif vpxa is not None and not vpxa.get('running') and 'vpxa' not in stopped:
                stopped.append('vpxa')

        metrics['service_count'] = len(services)
        metrics['missing_services'] = missing
        metrics['stopped_services'] = stopped

        failed = []
        if not services:
            failed.append('Agent service 목록이 비어 있습니다.')
        if missing:
            failed.append('필수 Agent 서비스 누락: %s' % ', '.join(missing))
        if stopped:
            failed.append('중지된 Agent 서비스: %s' % ', '.join(stopped))

        if failed:
            result = self.fail(
                'ESXi Agent 서비스 기준 미충족',
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
            reasons='필수 Agent 서비스가 존재하고 실행 중입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.agent_services_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi Agent 서비스 조회 실패',
                message='VMwareHelper 기반 ESXi Agent 서비스 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi Agent 서비스 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
