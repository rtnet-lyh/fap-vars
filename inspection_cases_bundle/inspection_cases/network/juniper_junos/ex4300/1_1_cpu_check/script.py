# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CONFIG = {'kind': 'cpu', 'commands': ['show chassis routing-engine']}
VALID_STP_COMBINATIONS = {('FWD', 'DESG'), ('FWD', 'ROOT'), ('BLK', 'ALT'), ('DSC', 'ALT')}
COMMAND_ERROR_RE = re.compile(r'(syntax error|unknown command|invalid command|unknown keyword|missing argument)', re.IGNORECASE)
MAC_RE = re.compile(r'^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$', re.IGNORECASE)
IP_RE = re.compile(r'^\d+(?:\.\d+){3}$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _split_list(self, value):
        return [item.strip() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _run_commands(self, commands):
        results = self._run_paramiko_commands(commands, profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        if len(results) < len(commands):
            return None, self.fail('점검 명령 실행 실패', message='일부 점검 명령 결과를 수신하지 못했습니다.')
        for result in results:
            stdout = (result.get('stdout') or '').strip()
            stderr = (result.get('stderr') or '').strip()
            command = result.get('display_command') or result.get('command')
            if result.get('rc') != 0:
                return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
            error_text = self._detect_cli_error(stdout, stderr)
            if error_text:
                return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return results, None

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                if stripped and COMMAND_ERROR_RE.search(stripped):
                    return stripped
        return ''

    def _combined_stdout(self, results):
        return '\n\n'.join((item.get('stdout') or '').strip() for item in results if (item.get('stdout') or '').strip()).strip()

    def _parse_cpu(self, text):
        idle_match = re.search(r'\bIdle\s+([0-9.]+)\s+percent', text, re.IGNORECASE)
        if idle_match:
            idle = float(idle_match.group(1))
            return {'idle_percent': round(idle, 2), 'cpu_usage_percent': round(max(0.0, 100.0 - idle), 2)}
        values = []
        for name in ('User', 'Background', 'Kernel', 'Interrupt'):
            match = re.search(r'\b' + name + r'\s+([0-9.]+)\s+percent', text, re.IGNORECASE)
            if match:
                values.append(float(match.group(1)))
        if not values:
            return None
        return {'cpu_usage_percent': round(sum(values), 2)}

    def _parse_memory(self, text):
        total_match = re.search(r'Total memory:\s*(\d+)\s+Kbytes\s*\(\s*100%\)', text, re.IGNORECASE)
        free_match = re.search(r'Free memory:\s*(\d+)\s+Kbytes\s*\(\s*([0-9.]+)%\s*\)', text, re.IGNORECASE)
        if not total_match or not free_match:
            return None
        total_kb = int(total_match.group(1))
        free_kb = int(free_match.group(1))
        free_percent = float(free_match.group(2))
        return {
            'memory_total_kb': total_kb,
            'memory_free_kb': free_kb,
            'memory_free_percent': round(free_percent, 2),
            'memory_usage_percent': round(max(0.0, 100.0 - free_percent), 2),
        }

    def _speed_to_bps(self, value, unit):
        number = float(value)
        normalized = str(unit or '').strip().lower()
        if normalized.startswith('g'):
            return number * 1000 * 1000 * 1000
        if normalized.startswith('m'):
            return number * 1000 * 1000
        if normalized.startswith('k'):
            return number * 1000
        return number

    def _parse_interface_usage(self, text, interface_name):
        speed_match = re.search(r'\bSpeed:\s*([0-9.]+)\s*([kmg]?bps)', text, re.IGNORECASE)
        input_match = re.search(r'Input rate\s*:\s*(\d+)\s+bps', text, re.IGNORECASE)
        output_match = re.search(r'Output rate\s*:\s*(\d+)\s+bps', text, re.IGNORECASE)
        if not speed_match or not input_match or not output_match:
            return None
        speed_bps = self._speed_to_bps(speed_match.group(1), speed_match.group(2))
        input_bps = int(input_match.group(1))
        output_bps = int(output_match.group(1))
        input_percent = round((input_bps / speed_bps) * 100, 4) if speed_bps else 0.0
        output_percent = round((output_bps / speed_bps) * 100, 4) if speed_bps else 0.0
        return {
            'interface_name': interface_name,
            'speed_bps': int(speed_bps),
            'input_rate_bps': input_bps,
            'output_rate_bps': output_bps,
            'input_usage_percent': input_percent,
            'output_usage_percent': output_percent,
            'max_usage_percent': max(input_percent, output_percent),
        }

    def _parse_interface_states(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = re.match(r'^(\S+)\s+(up|down)\s+(up|down)(?:\s|$)', line.strip(), re.IGNORECASE)
            if match:
                rows.append({'interface': match.group(1), 'admin': match.group(2).lower(), 'link': match.group(3).lower()})
        return rows

    def _parse_vlan_names(self, text):
        names = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 3 and re.match(r'^\d+$', parts[2]):
                names.append(parts[1])
        return names

    def _parse_arp_entries(self, text):
        entries = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 4 and MAC_RE.match(parts[0]) and IP_RE.match(parts[1]):
                entries.append({'mac_address': parts[0], 'ip_address': parts[1], 'name': parts[2], 'interface': parts[3]})
        return entries

    def _parse_stp_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 7 and re.match(r'^[a-z]+-\d+/\d+/\d+$', parts[0], re.IGNORECASE):
                rows.append({'interface': parts[0], 'state': parts[-2].upper(), 'role': parts[-1].upper()})
        return rows

    def _parse_environment_statuses(self, text):
        statuses = []
        for line in (text or '').splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.startswith('Class ') or set(stripped.strip()) <= {'-'}:
                continue
            match = re.match(r'^\s*(?P<item>.+?)\s{2,}(?P<status>[A-Za-z][A-Za-z_-]*)(?:\s{2,}.*)?$', stripped)
            if not match:
                continue
            status = match.group('status')
            if status.lower() not in ('status', 'measurement'):
                statuses.append({'item': match.group('item').strip(), 'status': status})
        return statuses

    def run(self):
        kind = CONFIG['kind']
        commands = list(CONFIG.get('commands') or [])
        thresholds = {}

        if kind == 'interface_usage':
            interface_name = str(self.get_threshold_var('interface_name', default='', value_type='str')).strip()
            max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
            thresholds = {'interface_name': interface_name, 'max_interface_usage_percent': max_usage}
            if not interface_name:
                return self.fail('임계치 미정의', message='interface_name threshold 값이 필요합니다.', thresholds=thresholds)
            commands = [CONFIG['template'].format(interface_name=interface_name)]
        elif kind == 'vlan':
            active_names = self._split_list(self.get_threshold_var('active_vlan_name', default='', value_type='str'))
            thresholds = {'active_vlan_name': active_names}
            if not active_names:
                return self.fail('임계치 미정의', message='active_vlan_name threshold 값이 필요합니다.', thresholds=thresholds)
        elif kind == 'ping':
            ping_ip = str(self.get_threshold_var('ping_ip', default='', value_type='str')).strip()
            thresholds = {'ping_ip': ping_ip}
            if not ping_ip:
                return self.fail('임계치 미정의', message='ping_ip threshold 값이 필요합니다.', thresholds=thresholds)
            commands = [CONFIG['template'].format(ping_ip=ping_ip)]
        elif kind == 'cpu':
            thresholds = {'max_cpu_usage_percent': self.get_threshold_var('max_cpu_usage_percent', default=80.0, value_type='float')}
        elif kind == 'memory':
            thresholds = {'max_mem_usage_percent': self.get_threshold_var('max_mem_usage_percent', default=80.0, value_type='float')}

        results, error = self._run_commands(commands)
        if error:
            return error
        stdout = self._combined_stdout(results)

        if kind == 'cpu':
            metrics = self._parse_cpu(stdout)
            if not metrics:
                return self.fail('CPU 사용률 파싱 실패', message='CPU 사용률 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
            if metrics['cpu_usage_percent'] > thresholds['max_cpu_usage_percent']:
                return self.fail('CPU 사용률 임계치 초과', message=f'CPU 사용률 {metrics["cpu_usage_percent"]}%가 기준 {thresholds["max_cpu_usage_percent"]}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='CPU 사용률이 임계치 이하입니다.', message=f'CPU 사용률 점검 정상: {metrics["cpu_usage_percent"]}%.')

        if kind == 'memory':
            metrics = self._parse_memory(stdout)
            if not metrics:
                return self.fail('메모리 사용률 파싱 실패', message='메모리 사용률 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
            if metrics['memory_usage_percent'] > thresholds['max_mem_usage_percent']:
                return self.fail('메모리 사용률 임계치 초과', message=f'메모리 사용률 {metrics["memory_usage_percent"]}%가 기준 {thresholds["max_mem_usage_percent"]}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='메모리 사용률이 임계치 이하입니다.', message=f'메모리 사용률 점검 정상: {metrics["memory_usage_percent"]}%.')

        if kind == 'interface_usage':
            metrics = self._parse_interface_usage(stdout, thresholds['interface_name'])
            if not metrics:
                return self.fail('인터페이스 사용률 파싱 실패', message='인터페이스 속도 또는 입출력 rate 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
            if metrics['max_usage_percent'] > thresholds['max_interface_usage_percent']:
                return self.fail('인터페이스 사용률 임계치 초과', message=f'인터페이스 사용률 최대값 {metrics["max_usage_percent"]}%가 기준 {thresholds["max_interface_usage_percent"]}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='인터페이스 입출력 사용률이 임계치 이하입니다.', message=f'인터페이스 사용률 점검 정상: 최대 {metrics["max_usage_percent"]}%.')

        if kind == 'inter_module':
            rows = self._parse_interface_states(stdout)
            if not rows:
                return self.fail('인터페이스 상태 파싱 실패', message='show interfaces terse 출력에서 인터페이스 상태 행을 찾지 못했습니다.', stdout=stdout)
            bad_rows = [row for row in rows if row['admin'] == 'up' and row['link'] != 'up']
            metrics = {'interface_count': len(rows), 'bad_interface_count': len(bad_rows), 'bad_interfaces': bad_rows, 'interfaces': rows}
            if bad_rows:
                return self.fail('인터페이스 상태 기준 미달', message=f'admin up/link down 인터페이스가 {len(bad_rows)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='admin up 인터페이스의 link가 모두 up입니다.', message='인터페이스/모듈 상태 점검 정상.')

        if kind == 'vlan':
            vlan_names = self._parse_vlan_names(stdout)
            if not vlan_names:
                return self.fail('VLAN 파싱 실패', message='show vlans 출력에서 VLAN name을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)
            missing = [name for name in thresholds['active_vlan_name'] if name not in vlan_names]
            metrics = {'vlan_names': vlan_names, 'missing_vlan_names': missing}
            if missing:
                return self.fail('VLAN 상태 기준 미달', message=f'운영대상 VLAN이 출력에 없습니다: {", ".join(missing)}', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 VLAN name이 출력에 존재합니다.', message='VLAN 상태 점검 정상.')

        if kind == 'lb':
            return self.fail('점검 불가', message='Junos EX4300에서 load-balancerpool 명령 점검이 지원되지 않아 점검 실패로 처리했습니다.', stdout=stdout, metrics={'output_line_count': len([line for line in stdout.splitlines() if line.strip()])}, thresholds=thresholds)

        if kind == 'mac_arp':
            entries = self._parse_arp_entries(stdout)
            metrics = {'arp_entry_count': len(entries), 'arp_entries': entries}
            if not entries:
                return self.fail('MAC/ARP 파싱 실패', message='show arp 출력에서 MAC/IP/interface 행을 찾지 못했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='MAC/IP/interface 행이 1개 이상 정상 파싱되었습니다.', message=f'MAC/ARP 테이블 점검 정상: {len(entries)}개 항목.')

        if kind == 'route':
            has_default_route = '0.0.0.0' in stdout
            metrics = {'has_default_route': has_default_route}
            if not has_default_route:
                return self.fail('라우팅 상태 기준 미달', message='출력에서 0.0.0.0 경로를 찾지 못했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='출력에서 0.0.0.0 경로가 확인되었습니다.', message='라우팅 Table 상태 점검 정상.')

        if kind == 'stp':
            rows = self._parse_stp_rows(stdout)
            if not rows:
                return self.fail('STP 파싱 실패', message='show spanning-tree interface 출력에서 STP 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)
            invalid = [row for row in rows if (row['state'], row['role']) not in VALID_STP_COMBINATIONS]
            metrics = {'stp_interface_count': len(rows), 'invalid_stp_interfaces': invalid, 'stp_interfaces': rows}
            if invalid:
                return self.fail('STP 상태 기준 미달', message=f'정상 State/Role 조합이 아닌 인터페이스가 {len(invalid)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 STP State/Role 조합이 정상 범위입니다.', message='STP 상태 점검 정상.')

        if kind == 'vrrp':
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            metrics = {'output_line_count': len(lines), 'output_lines': lines}
            if not lines:
                return self.fail('VRRP 상태 기준 미달', message='show vrrp summary 출력이 비어 있습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='VRRP 명령 결과가 존재합니다.', message='이중화 구성 상태 점검 정상.')

        if kind == 'ping':
            return self.fail('점검 불가', message='Junos EX4300 ping 명령 점검 결과가 명령 실패로 확인되어 실패 처리했습니다.', stdout=stdout, metrics={'ping_ip': thresholds['ping_ip']}, thresholds=thresholds)

        if kind == 'syslog':
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            metrics = {'matched_log_line_count': len(lines), 'matched_log_lines': lines}
            if lines:
                return self.fail('시스템 로그 기준 미달', message=f'HW 관련 오류 키워드 로그가 {len(lines)}건 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='HW 관련 오류 키워드 로그가 출력되지 않았습니다.', message='시스템 로그 점검 정상.')

        if kind == 'environment':
            statuses = self._parse_environment_statuses(stdout)
            if not statuses:
                return self.fail('환경 상태 파싱 실패', message='show chassis environment 출력에서 Status 값을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)
            bad = [item for item in statuses if item['status'].upper() != 'OK']
            metrics = {'status_count': len(statuses), 'bad_statuses': bad, 'statuses': statuses}
            if bad:
                return self.fail('환경 상태 기준 미달', message=f'OK가 아닌 하드웨어 Status가 {len(bad)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
            return self.ok(metrics=metrics, thresholds=thresholds, reasons='하드웨어 Status 값이 모두 OK입니다.', message='전원/FAN 등 환경 상태 점검 정상.')

        return self.fail('점검 스크립트 설정 오류', message=f'지원하지 않는 CHECK_KIND입니다: {kind}', thresholds=thresholds)


CHECK_CLASS = Check
