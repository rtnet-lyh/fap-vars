# type_name

일상점검

# area_name

상태점검

# category_name

network

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code

NETWORK-PIOLINK-PAS-K3200X-INTERFACE-USAGE-01

# is_required

필수

# inspection_name

네트워크 인터페이스 사용률

# inspection_content

네트워크 인터페이스 사용현황을 확인하여 네트워크 병목여부 확인

# inspection_command

```bash
show port-monitoring
```

# inspection_output

```text

```

# description

- RxRate(bps): 현재 수신 트래픽(bit/sec) 
- TxRate(bps): 현재 송신 트래픽(bit/sec) 
※ 각각 현재 포트가 사용 중인 네트워크 대역폭

- **양호**: RxRate(bps)값이 `rx_rate_warn_bps` 미만이고, TxRate(bps)값이 `tx_rate_warn_bps` 미만인 상태
- **경고**: RxRate(bps)값이 `rx_rate_warn_bps`를 이상이거나, TxRate(bps)값이 `tx_rate_warn_bps`를 이상인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "rx_rate_warn_bps", value: "700000000", sortOrder: 0}
,
{id: null, key: "tx_rate_warn_bps", value: "70000000", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show port-monitoring'
PORT_RATE_RE = re.compile(r'^\s*(?P<port>\S+)\s+(?P<rx_bps>\d+)\s+\d+\s+(?P<tx_bps>\d+)\s+\d+\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_ports(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = PORT_RATE_RE.match(line)
            if not match:
                continue
            rows.append({
                'port': match.group('port'),
                'rx_rate_bps': int(match.group('rx_bps')),
                'tx_rate_bps': int(match.group('tx_bps')),
            })
        return rows

    def run(self):
        rx_rate_warn_bps = self.get_threshold_var('rx_rate_warn_bps', default=700000000, value_type='int')
        tx_rate_warn_bps = self.get_threshold_var('tx_rate_warn_bps', default=700000000, value_type='int')
        thresholds = {'rx_rate_warn_bps': rx_rate_warn_bps, 'tx_rate_warn_bps': tx_rate_warn_bps}
        stdout, error = self._run_command()
        if error:
            return error

        ports = self._parse_ports(stdout)
        if not ports:
            return self.fail('포트 사용률 파싱 실패', message='show port-monitoring 출력에서 포트별 RxRate/TxRate 값을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        over_threshold = [
            item for item in ports
            if item['rx_rate_bps'] >= rx_rate_warn_bps or item['tx_rate_bps'] >= tx_rate_warn_bps
        ]
        max_rx = max(ports, key=lambda item: item['rx_rate_bps'])
        max_tx = max(ports, key=lambda item: item['tx_rate_bps'])
        metrics = {
            'port_count': len(ports),
            'max_rx_rate_bps': max_rx['rx_rate_bps'],
            'max_rx_port': max_rx['port'],
            'max_tx_rate_bps': max_tx['tx_rate_bps'],
            'max_tx_port': max_tx['port'],
            'over_threshold_ports': over_threshold,
            'ports': ports,
        }
        if over_threshold:
            return self.fail(error="일부 포트의 Rate가 임계치를 초과합니다", metrics=metrics, thresholds=thresholds, reasons='일부 포트의 RxRate 또는 TxRate가 임계치 이상입니다.', message=f'인터페이스 사용률 경고: 기준 초과 포트 {len(over_threshold)}개.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 포트의 RxRate/TxRate가 임계치 미만입니다.', message=f'인터페이스 사용률 점검 정상: Rx 최대 {max_rx["rx_rate_bps"]}bps, Tx 최대 {max_tx["tx_rate_bps"]}bps.')


CHECK_CLASS = Check
