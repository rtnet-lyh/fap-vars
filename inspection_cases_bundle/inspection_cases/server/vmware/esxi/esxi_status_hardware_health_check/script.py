# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _list_threshold(self, key, default=''):
        raw = self.get_threshold_var(key, default, 'str')
        return [
            item.strip().lower()
            for item in str(raw or '').replace('\r', '\n').replace('\n', ',').split(',')
            if item.strip()
        ]

    def _thresholds(self):
        return {
            'expected_overall_status': self.get_threshold_var('expected_overall_status', 'green', 'str'),
            'normal_health_states': self._list_threshold('normal_health_states', 'green,normal,ok'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        lines = [
            'ESXi 하드웨어 Health 상태 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- host_name: %s' % metrics.get('host_name', ''),
            '- overall_status: %s' % metrics.get('overall_status', ''),
            '- hardware_health:',
        ]
        for name in sorted((metrics.get('hardware_health') or {}).keys()):
            lines.append('  - %s: %s' % (name, metrics['hardware_health'][name]))
        lines.extend([
            '- warning_sensors: %s' % len(metrics.get('warning_sensors') or []),
            '- failed_sensors: %s' % len(metrics.get('failed_sensors') or []),
        ])
        for sensor in (metrics.get('warning_sensors') or []) + (metrics.get('failed_sensors') or []):
            lines.append(
                '  - {category}/{name}: {status}'.format(
                    category=sensor.get('category', ''),
                    name=sensor.get('name', ''),
                    status=sensor.get('status', ''),
                )
            )
        return '\n'.join(lines)

    def _build_message(self, metrics, thresholds, failed=None):
        abnormal_health = metrics.get('abnormal_health') or {}
        current_state = ', '.join([
            'host=%s' % metrics.get('host_name', ''),
            'overall_status=%s (기준 %s)' % (
                metrics.get('overall_status'),
                thresholds['expected_overall_status'],
            ),
            '비정상 Health=%s' % (
                ', '.join(
                    '%s=%s' % (name, status)
                    for name, status in sorted(abnormal_health.items())
                ) or '없음'
            ),
            'warning 센서=%s건' % len(metrics.get('warning_sensors') or []),
            'failed 센서=%s건' % len(metrics.get('failed_sensors') or []),
        ])
        if failed:
            return (
                'ESXi 하드웨어 Health 상태가 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi 하드웨어 Health 상태가 정상입니다. 현재 상태: %s. '
            'Host overall status와 주요 센서 상태가 모두 정상 범위입니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        normal_states = set(thresholds['normal_health_states'])
        failed = []

        if str(metrics.get('overall_status') or '').lower() != thresholds['expected_overall_status'].lower():
            failed.append('overall_status %s != %s' % (
                metrics.get('overall_status'),
                thresholds['expected_overall_status'],
            ))

        hardware_health = metrics.get('hardware_health') or {}
        abnormal_health = {}
        for name, status in hardware_health.items():
            if str(status or '').lower() not in normal_states:
                abnormal_health[name] = status

        if not hardware_health and not metrics.get('sensors'):
            failed.append('하드웨어 Health 센서 정보가 비어 있습니다.')
        if abnormal_health:
            failed.append('비정상 하드웨어 Health: %s' % ', '.join(
                '%s=%s' % (name, status) for name, status in sorted(abnormal_health.items())
            ))
        if metrics.get('warning_sensors'):
            failed.append('Warning 센서 %s개 확인' % len(metrics.get('warning_sensors') or []))
        if metrics.get('failed_sensors'):
            failed.append('Failed 센서 %s개 확인' % len(metrics.get('failed_sensors') or []))

        metrics['abnormal_health'] = abnormal_health

        if failed:
            result = self.fail(
                'ESXi 하드웨어 Health 기준 미충족',
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
            reasons='Host overall status와 주요 하드웨어 Health 상태가 정상 범위입니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.hardware_health_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi 하드웨어 Health 조회 실패',
                message='VMwareHelper 기반 ESXi 하드웨어 Health 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi 하드웨어 Health 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
