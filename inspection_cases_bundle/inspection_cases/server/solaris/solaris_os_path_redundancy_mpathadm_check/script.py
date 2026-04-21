# -*- coding: utf-8 -*-

from .common._base import BaseCheck


MPATHADM_SHOW_LU_COMMAND = 'mpathadm show lu'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _normalize(self, value):
        return str(value or '').strip().lower()

    def _parse_logical_units(self, text):
        logical_units = []
        current = None

        for raw_line in (text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith('Logical Unit:'):
                if current:
                    logical_units.append(current)
                current = {
                    'logical_unit': line.split(':', 1)[1].strip(),
                    'stms_state': '',
                    'current_path': '',
                    'path_status': '',
                    'paths': [],
                }
                continue

            if not current or ':' not in line:
                continue

            if line.startswith('Path '):
                path_name, status = line.split(':', 1)
                current['paths'].append({
                    'path': path_name.replace('Path ', '', 1).strip(),
                    'status': status.strip(),
                })
                continue

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if key == 'Stms State':
                current['stms_state'] = value
            elif key == 'Current Path':
                current['current_path'] = value
            elif key == 'Path Status':
                current['path_status'] = value

        if current:
            logical_units.append(current)

        if not logical_units:
            return None

        for lu in logical_units:
            lu['path_count'] = len(lu['paths'])
            lu['connected_path_count'] = sum(
                1 for path in lu['paths']
                if self._normalize(path['status']) == 'connected'
            )

        return logical_units

    def run(self):
        expected_stms_state = self.get_threshold_var('expected_stms_state', default='ENABLED', value_type='str')
        expected_path_status = self.get_threshold_var('expected_path_status', default='CONNECTED', value_type='str')
        expected_path_state = self.get_threshold_var('expected_path_state', default='CONNECTED', value_type='str')
        disallowed_path_states_raw = self.get_threshold_var('disallowed_path_states', default='DISABLED', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(MPATHADM_SHOW_LU_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris Multipath 이중화 점검에 실패했습니다. 현재 상태: mpathadm 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=[
                'permission denied',
                'not supported',
                'unknown userland error',
                'no such file or directory',
                'cannot find',
                'not found',
                'device not found',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Multipath 이중화 점검에 실패했습니다. '
                    f'현재 상태: mpathadm 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in (out or '').lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'Multipath 실패 키워드 감지',
                message=(
                    'Solaris Multipath 이중화 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        logical_units = self._parse_logical_units(out)
        if not logical_units:
            return self.fail(
                'Multipath 파싱 실패',
                message='Solaris Multipath 이중화 점검에 실패했습니다. 현재 상태: mpathadm 출력에서 Logical Unit 정보를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        expected_stms_norm = self._normalize(expected_stms_state)
        expected_path_status_norm = self._normalize(expected_path_status)
        expected_path_state_norm = self._normalize(expected_path_state)
        disallowed_path_states = [
            item.strip() for item in disallowed_path_states_raw.split(',') if item.strip()
        ]
        disallowed_norm = [self._normalize(item) for item in disallowed_path_states]

        stms_issue_units = []
        path_status_issue_units = []
        abnormal_paths = []
        disallowed_paths = []
        stms_enabled_count = 0
        connected_path_status_count = 0
        connected_path_count = 0

        for lu in logical_units:
            if self._normalize(lu['stms_state']) == expected_stms_norm:
                stms_enabled_count += 1
            else:
                stms_issue_units.append(lu['logical_unit'])

            if self._normalize(lu['path_status']) == expected_path_status_norm:
                connected_path_status_count += 1
            else:
                path_status_issue_units.append(lu['logical_unit'])

            for path in lu['paths']:
                status_norm = self._normalize(path['status'])
                if status_norm == expected_path_state_norm:
                    connected_path_count += 1
                else:
                    abnormal_paths.append({
                        'logical_unit': lu['logical_unit'],
                        'path': path['path'],
                        'status': path['status'],
                    })
                if status_norm in disallowed_norm:
                    disallowed_paths.append({
                        'logical_unit': lu['logical_unit'],
                        'path': path['path'],
                        'status': path['status'],
                    })

        metrics = {
            'logical_unit_count': len(logical_units),
            'stms_enabled_count': stms_enabled_count,
            'connected_path_status_count': connected_path_status_count,
            'connected_path_count': connected_path_count,
            'abnormal_path_count': len(abnormal_paths),
            'logical_units': logical_units,
            'stms_issue_units': stms_issue_units,
            'path_status_issue_units': path_status_issue_units,
            'abnormal_paths': abnormal_paths,
            'disallowed_paths': disallowed_paths,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'expected_stms_state': expected_stms_state,
            'expected_path_status': expected_path_status,
            'expected_path_state': expected_path_state,
            'disallowed_path_states': disallowed_path_states,
            'failure_keywords': failure_keywords,
        }

        if stms_issue_units or path_status_issue_units or abnormal_paths:
            problem_parts = []
            if stms_issue_units:
                problem_parts.append(f'Stms State 비정상 LU={stms_issue_units}')
            if path_status_issue_units:
                problem_parts.append(f'Path Status 비정상 LU={path_status_issue_units}')
            if abnormal_paths:
                abnormal_text = [
                    f"{item['path']}={item['status']}"
                    for item in abnormal_paths
                ]
                problem_parts.append(f'비정상 경로={abnormal_text}')
            return self.fail(
                'Multipath 상태 비정상',
                metrics=metrics,
                thresholds=thresholds,
                reasons='STMS 또는 Path Status 또는 개별 경로 상태가 기준과 다릅니다.',
                message=(
                    'Solaris Multipath 이중화 점검에 실패했습니다. '
                    '현재 상태: ' + ', '.join(problem_parts) + '. '
                    f'기준 Stms State={expected_stms_state}, Path Status={expected_path_status}, '
                    f'개별 경로 상태={expected_path_state}, 금지 상태={disallowed_path_states}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'모든 Logical Unit의 Stms State가 {expected_stms_state}이고 Path Status와 개별 경로 상태가 '
                f'{expected_path_status}/{expected_path_state} 기준을 충족합니다.'
            ),
            message=(
                'Solaris Multipath 이중화 상태가 정상입니다. '
                f'현재 상태: LU {len(logical_units)}개, Stms State 정상 {stms_enabled_count}개, '
                f'Path Status 정상 {connected_path_status_count}개, CONNECTED 경로 {connected_path_count}개, '
                '비정상 경로 0개입니다.'
            ),
        )


CHECK_CLASS = Check
