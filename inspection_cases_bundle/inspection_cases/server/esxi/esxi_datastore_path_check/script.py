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
            'max_datastore_usage_percent': self.get_threshold_var('max_datastore_usage_percent', 85.0, 'float'),
            'min_datastore_free_gib': self.get_threshold_var('min_datastore_free_gib', 10.0, 'float'),
            'required_datastore_names': self._list_threshold('required_datastore_names', ''),
            'require_accessible': self.get_threshold_var('require_accessible', True, 'bool'),
            'force_replay': self.get_threshold_var('force_replay', False, 'bool'),
        }

    def _free_gib(self, datastore):
        if datastore.get('free_space_gib') not in (None, ''):
            try:
                return float(datastore.get('free_space_gib'))
            except Exception:
                return 0.0
        try:
            return round(float(datastore.get('free_space_bytes') or 0) / 1024.0 / 1024.0 / 1024.0, 2)
        except Exception:
            return 0.0

    def _raw_output(self, metrics):
        lines = [
            'ESXi Datastore 목록 및 Path 조회 결과',
            '- source: %s' % metrics.get('source', ''),
            '- datastore_count: %s' % metrics.get('datastore_count', ''),
            '- datastores:',
        ]
        for datastore in metrics.get('datastores') or []:
            lines.append(
                '  - {name}: type={type}, accessible={accessible}, usage={usage_percent}%, free={free_space_gib} GiB, url={url}'.format(
                    name=datastore.get('name', ''),
                    type=datastore.get('type', ''),
                    accessible=datastore.get('accessible', ''),
                    usage_percent=datastore.get('usage_percent', ''),
                    free_space_gib=self._free_gib(datastore),
                    url=datastore.get('url', ''),
                )
            )
        lines.extend([
            '- missing_required_datastores: %s' % ', '.join(metrics.get('missing_required_datastores') or []),
            '- inaccessible_datastores: %s' % ', '.join(ds.get('name', '') for ds in metrics.get('inaccessible_datastores') or []),
            '- overused_datastores: %s' % ', '.join(ds.get('name', '') for ds in metrics.get('overused_datastores') or []),
            '- low_free_datastores: %s' % ', '.join(ds.get('name', '') for ds in metrics.get('low_free_datastores') or []),
        ])
        return '\n'.join(lines)

    def _format_names(self, values):
        names = []
        for value in values or []:
            if isinstance(value, dict):
                name = str(value.get('name') or '').strip()
            else:
                name = str(value or '').strip()
            if name:
                names.append(name)
        return ', '.join(names) or '없음'

    def _format_usage_details(self, datastores):
        details = []
        for datastore in datastores or []:
            details.append(
                '%s=%.2f%%' % (
                    datastore.get('name', ''),
                    float(datastore.get('usage_percent') or 0.0),
                )
            )
        return ', '.join(details) or '없음'

    def _format_free_details(self, datastores):
        details = []
        for datastore in datastores or []:
            details.append(
                '%s=%.2fGiB' % (
                    datastore.get('name', ''),
                    self._free_gib(datastore),
                )
            )
        return ', '.join(details) or '없음'

    def _build_message(self, metrics, thresholds, failed=None):
        current_state = ', '.join([
            'datastore_count=%s' % metrics.get('datastore_count', 0),
            '필수 Datastore=%s' % (', '.join(thresholds['required_datastore_names']) or '없음'),
            '누락 Datastore=%s' % self._format_names(metrics.get('missing_required_datastores')),
            '접근 불가=%s' % self._format_names(metrics.get('inaccessible_datastores')),
            '사용률 초과=%s' % self._format_usage_details(metrics.get('overused_datastores')),
            '여유 공간 부족=%s' % self._format_free_details(metrics.get('low_free_datastores')),
            '사용률 기준=%.2f%% 이하' % thresholds['max_datastore_usage_percent'],
            '여유 공간 기준=%.2fGiB 이상' % thresholds['min_datastore_free_gib'],
        ])
        if failed:
            return (
                'ESXi Datastore Path 상태가 기준을 충족하지 못했습니다. '
                '실패 사유: %s. 현재 상태: %s.'
            ) % (', '.join(failed), current_state)
        return (
            'ESXi Datastore Path 상태가 정상입니다. 현재 상태: %s. '
            '모든 Datastore가 접근 가능하고 사용률/여유 공간 기준을 충족했습니다.'
        ) % current_state

    def _evaluate(self, metrics):
        thresholds = self._thresholds()
        datastores = metrics.get('datastores') or []
        datastore_names = {str(ds.get('name') or '').strip() for ds in datastores if str(ds.get('name') or '').strip()}

        missing_required = [
            name for name in thresholds['required_datastore_names']
            if name not in datastore_names
        ]
        inaccessible = [
            ds for ds in datastores
            if thresholds['require_accessible'] and not bool(ds.get('accessible'))
        ]
        overused = [
            ds for ds in datastores
            if float(ds.get('usage_percent') or 0.0) > thresholds['max_datastore_usage_percent']
        ]
        low_free = [
            ds for ds in datastores
            if self._free_gib(ds) < thresholds['min_datastore_free_gib']
        ]

        metrics['datastore_count'] = len(datastores)
        metrics['missing_required_datastores'] = missing_required
        metrics['inaccessible_datastores'] = inaccessible
        metrics['overused_datastores'] = overused
        metrics['low_free_datastores'] = low_free

        failed = []
        if not datastores:
            failed.append('Datastore 목록이 비어 있습니다.')
        if missing_required:
            failed.append('필수 Datastore 누락: %s' % ', '.join(missing_required))
        if inaccessible:
            failed.append('접근 불가 Datastore: %s' % ', '.join(ds.get('name', '') for ds in inaccessible))
        if overused:
            failed.append('사용률 기준 초과 Datastore: %s' % ', '.join(
                '%s=%.2f%%' % (ds.get('name', ''), float(ds.get('usage_percent') or 0.0))
                for ds in overused
            ))
        if low_free:
            failed.append('여유 공간 기준 미달 Datastore: %s' % ', '.join(
                '%s=%.2fGiB' % (ds.get('name', ''), self._free_gib(ds))
                for ds in low_free
            ))

        if failed:
            result = self.fail(
                'ESXi Datastore 기준 미충족',
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
            reasons='Datastore가 접근 가능하고 사용률, 여유 공간, 필수 목록 기준을 충족합니다.',
            raw_output=self._raw_output(metrics),
            message=self._build_message(metrics, thresholds),
        )

    def run(self):
        try:
            metrics = self.vmware_helper.datastore_summaries_from_context(source='pyvmomi')
        except Exception as exc:
            return self.fail(
                'ESXi Datastore 목록 조회 실패',
                message='VMwareHelper 기반 ESXi Datastore 조회 중 예외가 발생했습니다: %s' % exc,
                raw_output='VMwareHelper 기반 ESXi Datastore Path 점검을 완료하지 못했습니다.',
            )

        return self._evaluate(metrics)


CHECK_CLASS = Check
