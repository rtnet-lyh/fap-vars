# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _thresholds(self):
        return {
            'max_cpu_usage_percent': self.get_threshold_var('max_cpu_usage_percent', 80.0, 'float'),
            'max_memory_usage_percent': self.get_threshold_var('max_memory_usage_percent', 80.0, 'float'),
            'expected_power_state': self.get_threshold_var('expected_power_state', 'poweredOn', 'str'),
            'expected_connection_state': self.get_threshold_var('expected_connection_state', 'connected', 'str'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _raw_output(self, metrics):
        return '\n'.join([
            'ESXi HostSystem.summary API 조회 결과',
            '- source: {source}',
            '- name: {name}',
            '- full_name: {full_name}',
            '- api_version: {api_version}',
            '- vendor/model: {vendor} / {model}',
            '- cpu_model: {cpu_model}',
            '- cpu_usage: {cpu_usage_percent}% ({cpu_usage_mhz}/{cpu_capacity_mhz} MHz)',
            '- memory_usage: {memory_usage_percent}% ({memory_usage_mib}/{memory_total_mib} MiB)',
            '- power_state: {power_state}',
            '- connection_state: {connection_state}',
            '- overall_status: {overall_status}',
        ]).format(**metrics)

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        failed = []

        if metrics['cpu_usage_percent'] > thresholds['max_cpu_usage_percent']:
            failed.append('CPU Usage %.2f%% > %.2f%%' % (
                metrics['cpu_usage_percent'],
                thresholds['max_cpu_usage_percent'],
            ))
        if metrics['memory_usage_percent'] > thresholds['max_memory_usage_percent']:
            failed.append('Memory Usage %.2f%% > %.2f%%' % (
                metrics['memory_usage_percent'],
                thresholds['max_memory_usage_percent'],
            ))
        if metrics['power_state'] != thresholds['expected_power_state']:
            failed.append('Power State %s != %s' % (
                metrics['power_state'],
                thresholds['expected_power_state'],
            ))
        if metrics['connection_state'] != thresholds['expected_connection_state']:
            failed.append('Connection State %s != %s' % (
                metrics['connection_state'],
                thresholds['expected_connection_state'],
            ))

        if failed:
            result = self.fail(
                'ESXi 상태 기준 미충족',
                message='ESXi 상태 기준을 충족하지 못했습니다: %s' % ', '.join(failed),
                raw_output=self._raw_output(metrics),
            )
            result['metrics'] = metrics
            result['thresholds'] = thresholds
            result['reasons'] = ', '.join(failed)
            return result

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='CPU/Memory 사용률이 기준 이하이고 Power/Connection 상태가 정상입니다.',
            raw_output=self._raw_output(metrics),
            message=(
                'ESXi 상태 확인 점검이 정상 수행되었습니다. '
                'CPU Usage %.2f%%, Memory Usage %.2f%%, Power State %s, Connection State %s.'
                % (
                    metrics['cpu_usage_percent'],
                    metrics['memory_usage_percent'],
                    metrics['power_state'],
                    metrics['connection_state'],
                )
            ),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.host_summary_metrics_from_context(
                default_host_moid='ha-host',
                source='pyvmomi',
            )
        except Exception as exc:
            return self.fail(
                'ESXi API 점검 실패',
                message=str(exc),
                raw_output='VMwareHelper 기반 ESXi 상태 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
