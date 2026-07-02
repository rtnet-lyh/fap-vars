# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'for md in $(ls /dev/md* 2>/dev/null | grep -v mdp); do mdadm --detail $md; done'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# raid_device_match_type = prefix
# raid_device_values = /dev/md
# raid_state = clean|active
# active_devices = raid_devices
# working_devices = raid_devices
# failed_devices = 0
# member_state = active sync
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def parse_output(self, output):
        text = output or ''
        if not text.strip():
            return {'not_applicable': True, 'reason': 'mdadm RAID 장치를 찾을 수 없어 점검 대상에서 제외합니다.'}

        arrays = []
        current = None
        in_member_table = False

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('/dev/md') and stripped.endswith(':'):
                if current:
                    arrays.append(current)
                current = {
                    'name': stripped[:-1],
                    'state': '',
                    'raid_devices': None,
                    'active_devices': None,
                    'working_devices': None,
                    'failed_devices': None,
                    'members': [],
                }
                in_member_table = False
                continue

            if current is None:
                continue

            field = re.match(r'^(State|Raid Devices|Active Devices|Working Devices|Failed Devices)\s*:\s*(.+)$', stripped)
            if field:
                key = field.group(1).lower().replace(' ', '_')
                value = field.group(2).strip()
                if key == 'state':
                    current[key] = value
                    continue
                try:
                    current[key] = int(value.split()[0])
                except (IndexError, ValueError):
                    return {'failure_type': 'parse_failure', 'reason': 'mdadm 숫자 필드 파싱 실패: %s' % stripped}
                continue

            if stripped.startswith('Number') and 'RaidDevice' in stripped and 'State' in stripped:
                in_member_table = True
                continue

            if in_member_table and re.match(r'^\d+\s+', stripped):
                parts = stripped.split()
                if len(parts) >= 5:
                    device = parts[-1] if parts[-1].startswith('/dev/') else ''
                    state_parts = parts[4:-1] if device else parts[4:]
                    current['members'].append({'device': device, 'state': ' '.join(state_parts)})

        if current:
            arrays.append(current)

        if not arrays:
            return {'failure_type': 'parse_failure', 'reason': 'mdadm 출력에서 /dev/md 배열을 찾을 수 없습니다.'}

        required = ('state', 'raid_devices', 'active_devices', 'working_devices', 'failed_devices')
        for array in arrays:
            missing = [key for key in required if array.get(key) in (None, '')]
            if missing:
                return {'failure_type': 'parse_failure', 'reason': '%s 필수 필드 누락: %s' % (array['name'], ', '.join(missing))}

        return {'arrays': arrays, 'array_count': len(arrays)}

    def _split_values(self, value):
        return [item.strip().lower() for item in re.split(r'[|,\n]+', str(value or '')) if item.strip()]

    def _select_arrays(self, arrays, match_type, values):
        targets = self._split_values(values)
        if not targets:
            return arrays
        if str(match_type or '').strip().lower() == 'prefix':
            return [array for array in arrays if any(array['name'].lower().startswith(target) for target in targets)]
        return [array for array in arrays if array['name'].lower() in targets]

    def _meets_device_rule(self, actual, expected, raid_devices):
        if str(expected).strip().lower() == 'raid_devices':
            return actual >= raid_devices
        try:
            return actual >= int(expected)
        except (TypeError, ValueError):
            return False

    def evaluate(self, metrics, criteria):
        if metrics.get('not_applicable'):
            return 'excluded'
        if metrics.get('failure_type'):
            return 'fail'

        selected = self._select_arrays(
            metrics['arrays'],
            criteria['raid_device_match_type'],
            criteria['raid_device_values'],
        )
        metrics['checked_arrays'] = selected

        if not selected:
            metrics['not_applicable'] = True
            metrics['reason'] = '기준에 해당하는 mdadm RAID 배열을 찾을 수 없어 점검 대상에서 제외합니다.'
            return 'excluded'

        allowed_states = self._split_values(criteria['raid_state'])
        allowed_member_states = self._split_values(criteria['member_state'])
        bad_state_tokens = ('degraded', 'failed', 'faulty', 'inactive')
        detail_lines = []
        failed_lines = []

        for array in selected:
            name = array['name']
            state = array['state'].lower()
            detail_lines.append(
                '%s 상태=%s 활성=%s 동작=%s 실패=%s 멤버=%s' % (
                    name,
                    array['state'],
                    array['active_devices'],
                    array['working_devices'],
                    array['failed_devices'],
                    len(array['members']),
                )
            )

            if any(token in state for token in bad_state_tokens) or not any(token in state for token in allowed_states):
                failed_lines.append('%s RAID 상태 비정상: %s' % (name, array['state']))
            if not self._meets_device_rule(array['active_devices'], criteria['active_devices'], array['raid_devices']):
                failed_lines.append('%s 활성 디스크 수 부족: 활성=%s, RAID 디스크=%s' % (name, array['active_devices'], array['raid_devices']))
            if not self._meets_device_rule(array['working_devices'], criteria['working_devices'], array['raid_devices']):
                failed_lines.append('%s 동작 디스크 수 부족: 동작=%s, RAID 디스크=%s' % (name, array['working_devices'], array['raid_devices']))
            if array['failed_devices'] > criteria['failed_devices']:
                failed_lines.append('%s 실패 디스크 수 기준 초과: 실패=%s' % (name, array['failed_devices']))

            for member in array['members']:
                member_state = member['state'].lower()
                if allowed_member_states and member_state not in allowed_member_states:
                    failed_lines.append('%s 멤버 %s 상태 비정상: %s' % (name, member.get('device') or '-', member['state']))

        metrics['detail_lines'] = detail_lines
        metrics['policy_violations'] = failed_lines
        if failed_lines:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, criteria_vars, status):
        criteria = f"""대상 {criteria_vars['raid_device_match_type']}={criteria_vars['raid_device_values']}
            상태는 {criteria_vars['raid_state']} 중 하나
            활성 디스크 기준={criteria_vars['active_devices']}
            동작 디스크 기준={criteria_vars['working_devices']}
            실패 디스크 수 <= {criteria_vars['failed_devices']}
            멤버 상태={criteria_vars['member_state']}"""

        if metrics.get('not_applicable'):
            return {'message': 'mdadm RAID 점검 대상이 아닙니다.', 'results': metrics.get('reason', ''), 'criteria': criteria}
        if metrics.get('failure_type'):
            message = 'mdadm 명령 실행에 실패했습니다.' if metrics['failure_type'] == 'command_failure' else 'mdadm 출력 파싱에 실패했습니다.'
            return {'message': message, 'results': metrics.get('reason', ''), 'criteria': criteria}

        lines = metrics.get('policy_violations') or metrics.get('detail_lines', [])
        results = '\n'.join(lines)
        message = 'mdadm RAID 점검 양호' if status == 'ok' else 'mdadm RAID 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        criteria = {
            'raid_device_match_type': self.get_threshold_var('raid_device_match_type', default='prefix', value_type='str'),
            'raid_device_values': self.get_threshold_var('raid_device_values', default='/dev/md', value_type='str'),
            'raid_state': self.get_threshold_var('raid_state', default='clean|active', value_type='str'),
            'active_devices': self.get_threshold_var('active_devices', default='raid_devices', value_type='str'),
            'working_devices': self.get_threshold_var('working_devices', default='raid_devices', value_type='str'),
            'failed_devices': self.get_threshold_var('failed_devices', default=0, value_type='int'),
            'member_state': self.get_threshold_var('member_state', default='active sync', value_type='str'),
        }

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, criteria)
        result = self.build_result(metrics, criteria, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check