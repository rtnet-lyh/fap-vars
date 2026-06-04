# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interface'
IFACE_RE = re.compile(r'^(\S+/\S+)\s+is\s+(\S+)')
RATE_RE = re.compile(r'5 minutes (input|output) rate (\d+) bits/sec')
SPEED_RE = re.compile(r'Speed is ([0-9.]+) Gbps')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _parse(self, text):
        rows = []
        current = None
        for line in (text or '').splitlines():
            iface = IFACE_RE.match(line.strip())
            if iface:
                if current:
                    rows.append(current)
                current = {'interface': iface.group(1)} if iface.group(2) == 'up' else None
                continue
            if not current:
                continue
            speed = SPEED_RE.search(line)
            rate = RATE_RE.search(line)
            if speed:
                current['speed_bps'] = float(speed.group(1)) * 1000000000
            if rate:
                current[rate.group(1) + '_bps'] = int(rate.group(2))
        if current:
            rows.append(current)

        parsed = []
        for row in rows:
            if not all(key in row for key in ('speed_bps', 'input_bps', 'output_bps')):
                continue
            row['input_usage_percent'] = round(row['input_bps'] / row['speed_bps'] * 100, 2)
            row['output_usage_percent'] = round(row['output_bps'] / row['speed_bps'] * 100, 2)
            parsed.append(row)
        return parsed

    def run(self):
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_interface_usage_percent': max_usage}
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        text = (out or '').strip()
        interfaces = self._parse(text)
        if not interfaces:
            return self.fail('인터페이스 사용률 파싱 실패', message='UP 인터페이스의 speed/input/output rate를 해석하지 못했습니다.', stdout=text, thresholds=thresholds)

        for row in interfaces:
            row['max_usage_percent'] = max(row['input_usage_percent'], row['output_usage_percent'])
        over = [row for row in interfaces if row['max_usage_percent'] > max_usage]
        max_row = max(interfaces, key=lambda row: row['max_usage_percent'])
        metrics = {
            'up_interface_count': len(interfaces),
            'max_interface_usage_percent': max_row['max_usage_percent'],
            'max_interface': max_row,
            'over_threshold_interfaces': over,
            'interfaces': interfaces,
        }
        if over:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(over)}개 인터페이스 사용률이 임계치를 초과했습니다.', message=f'인터페이스 사용률 기준 초과: max={max_row["max_usage_percent"]}%.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'UP 인터페이스 최대 사용률 {max_row["max_usage_percent"]}%가 임계치 이하입니다.', message=f'인터페이스 사용률 점검이 정상 수행되었습니다. max={max_row["max_usage_percent"]}%.')


CHECK_CLASS = Check
