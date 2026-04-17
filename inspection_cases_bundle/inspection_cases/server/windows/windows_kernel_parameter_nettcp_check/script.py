# -*- coding: utf-8 -*-

from .common._base import BaseCheck


KERNAL_PARAMETER_COMMAND = (
    "$os=Get-CimInstance Win32_OperatingSystem; "
    "$tcp=Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' -ErrorAction SilentlyContinue; "
    "$if4=Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue; "
    "[pscustomobject]@{'kernel.osrelease'=\"$($os.Version) (Build $($os.BuildNumber))\";"
    "'kernel.ostype'=$os.Caption;"
    "'kernel.hostname'=$os.CSName;"
    "'kernel.shmmax'='N/A';"
    "'kernel.shmall'='N/A';"
    "'net.ipv4.ip_forward'=$(if($tcp.PSObject.Properties.Name -contains 'IPEnableRouter'){$tcp.IPEnableRouter}else{(@($if4.Forwarding|Select-Object -Unique)-join ',')});"
    "'net.ipv4.conf.all.rp_filter'='N/A';"
    "'net.ipv4.conf.all.accept_source_route'=$(if($tcp.PSObject.Properties.Name -contains 'DisableIPSourceRouting'){$tcp.DisableIPSourceRouting}else{'NotConfigured'});"
    "'net.core.somaxconn'='N/A';"
    "'vm.swappiness'='N/A';"
    "'vm.dirty_ratio'='N/A';"
    "'fs.file-max'=$(if($tcp.PSObject.Properties.Name -contains 'TcpNumConnections'){$tcp.TcpNumConnections}else{'N/A'});"
    "'fs.aio-max-nr'='N/A'} | Format-List"
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        expected_ip_forward = self.get_threshold_var('expected_ip_forward', default='0', value_type='str')
        disallowed_accept_source_route_values_raw = self.get_threshold_var(
            'disallowed_accept_source_route_values',
            default='0',
            value_type='str',
        )
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(KERNAL_PARAMETER_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 커널 파라미터 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '커널 파라미터 정보 없음',
                message='커널 파라미터 결과가 비어 있습니다.',
                stdout='',
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
                '커널 파라미터 실패 키워드 감지',
                message='커널 파라미터 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        result_map = {}
        for line in text.splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            result_map[key.strip()] = value.strip()

        required_keys = [
            'kernel.osrelease',
            'kernel.ostype',
            'kernel.hostname',
            'net.ipv4.ip_forward',
            'net.ipv4.conf.all.accept_source_route',
        ]
        if any(key not in result_map for key in required_keys):
            return self.fail(
                '커널 파라미터 파싱 실패',
                message='핵심 커널 파라미터 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        disallowed_accept_source_route_values = [
            value.strip()
            for value in disallowed_accept_source_route_values_raw.split(',')
            if value.strip()
        ]

        ip_forward_value = result_map.get('net.ipv4.ip_forward', '')
        accept_source_route_value = result_map.get('net.ipv4.conf.all.accept_source_route', '')

        if ip_forward_value != expected_ip_forward:
            return self.fail(
                'IP 포워딩 설정 기준 불일치',
                message='IP 포워딩 설정값이 기준과 다릅니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if accept_source_route_value in disallowed_accept_source_route_values:
            return self.fail(
                '소스 라우팅 설정 기준 불일치',
                message='소스 라우팅 관련 설정값이 허용되지 않는 값입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'kernel_osrelease': result_map.get('kernel.osrelease', ''),
                'kernel_ostype': result_map.get('kernel.ostype', ''),
                'kernel_hostname': result_map.get('kernel.hostname', ''),
                'kernel_shmmax': result_map.get('kernel.shmmax', ''),
                'kernel_shmall': result_map.get('kernel.shmall', ''),
                'net_ipv4_ip_forward': ip_forward_value,
                'net_ipv4_conf_all_rp_filter': result_map.get('net.ipv4.conf.all.rp_filter', ''),
                'net_ipv4_conf_all_accept_source_route': accept_source_route_value,
                'net_core_somaxconn': result_map.get('net.core.somaxconn', ''),
                'vm_swappiness': result_map.get('vm.swappiness', ''),
                'vm_dirty_ratio': result_map.get('vm.dirty_ratio', ''),
                'fs_file_max': result_map.get('fs.file-max', ''),
                'fs_aio_max_nr': result_map.get('fs.aio-max-nr', ''),
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'expected_ip_forward': expected_ip_forward,
                'disallowed_accept_source_route_values': disallowed_accept_source_route_values,
                'failure_keywords': failure_keywords,
            },
            reasons='Windows에서 직접 확인 가능한 커널 파라미터 설정값이 기준 범위 내입니다.',
            message='Windows 커널 파라미터 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
