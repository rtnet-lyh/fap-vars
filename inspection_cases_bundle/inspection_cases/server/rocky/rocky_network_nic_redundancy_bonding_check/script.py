# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


BONDING_COMMAND = '\n'.join([
    'if ls /proc/net/bonding/* >/dev/null 2>&1; then',
    '  for b in /proc/net/bonding/*; do',
    '    echo "===== $(basename "$b") ====="',
    '    cat "$b"',
    '  done',
    'else',
    '  echo "NIC BONDING NOT CONFIGURED"',
    'fi',
])
NOT_CONFIGURED_MARKER = 'NIC BONDING NOT CONFIGURED'
SECTION_PATTERN = re.compile(r'^=====\s*(.+?)\s*=====$')
ACTIVE_SLAVE_PATTERN = re.compile(r'^Currently Active Slave:\s*(.+)$', re.IGNORECASE)
SLAVE_PATTERN = re.compile(r'^Slave Interface:\s*(.+)$', re.IGNORECASE)
MII_STATUS_PATTERN = re.compile(r'^MII Status:\s*(.+)$', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _normalize_status(self, value):
        text = str(value or '').strip()
        if not text:
            return ''
        return text.split()[0].lower()

    def _parse_bond_block(self, bond_name, block_lines):
        bond_mii_status = ''
        active_slave = ''
        slaves = []
        current_slave = None

        for raw_line in block_lines:
            line = raw_line.strip()
            if not line:
                continue

            active_match = ACTIVE_SLAVE_PATTERN.match(line)
            if active_match and not active_slave:
                active_slave = active_match.group(1).strip()
                continue

            slave_match = SLAVE_PATTERN.match(line)
            if slave_match:
                current_slave = {
                    'name': slave_match.group(1).strip(),
                    'mii_status': '',
                }
                slaves.append(current_slave)
                continue

            mii_status_match = MII_STATUS_PATTERN.match(line)
            if mii_status_match:
                normalized_status = self._normalize_status(mii_status_match.group(1))
                if current_slave is None and not bond_mii_status:
                    bond_mii_status = normalized_status
                elif current_slave is not None and not current_slave.get('mii_status'):
                    current_slave['mii_status'] = normalized_status

        if not bond_mii_status:
            raise ValueError(f'{bond_name} bonding 레벨 MII Status를 찾지 못했습니다.')

        for slave in slaves:
            slave['mii_status'] = self._normalize_status(slave.get('mii_status')) or 'unknown'
            slave['is_active'] = bool(active_slave and slave['name'] == active_slave)

        down_slave_names = [
            slave.get('name')
            for slave in slaves
            if slave.get('mii_status') != 'up'
        ]
        if bond_mii_status == 'down':
            status = 'fail'
            status_reason = 'bond_mii_down'
        elif slaves and not down_slave_names:
            status = 'ok'
            status_reason = 'all_slaves_up'
        else:
            status = 'warn'
            status_reason = 'slave_down_or_missing'

        return {
            'name': bond_name,
            'bond_mii_status': bond_mii_status,
            'active_slave': active_slave,
            'slave_count': len(slaves),
            'down_slave_count': len(down_slave_names),
            'down_slave_names': down_slave_names,
            'status': status,
            'status_reason': status_reason,
            'slaves': slaves,
            'raw_lines': [line for line in block_lines if line.strip()],
        }

    def _parse_output(self, stdout):
        stripped = (stdout or '').strip()
        if not stripped:
            raise ValueError('bonding 상태 점검 출력이 비어 있습니다.')

        if stripped == NOT_CONFIGURED_MARKER:
            return {
                'bonding_configured': False,
                'bonds': [],
            }

        lines = [line.rstrip() for line in stripped.splitlines()]
        bonds = []
        current_bond_name = ''
        current_lines = []

        for line in lines:
            section_match = SECTION_PATTERN.match(line.strip())
            if section_match:
                if current_bond_name:
                    bonds.append(self._parse_bond_block(current_bond_name, current_lines))
                current_bond_name = section_match.group(1).strip()
                current_lines = []
                continue

            if current_bond_name:
                current_lines.append(line)

        if current_bond_name:
            bonds.append(self._parse_bond_block(current_bond_name, current_lines))

        if not bonds:
            raise ValueError('bonding 인터페이스 섹션을 찾지 못했습니다.')

        return {
            'bonding_configured': True,
            'bonds': bonds,
        }

    def _build_metrics(self, parsed):
        bonds = parsed.get('bonds') or []
        return {
            'bonding_configured': bool(parsed.get('bonding_configured')),
            'bond_count': len(bonds),
            'bond_ok_count': sum(1 for bond in bonds if bond.get('status') == 'ok'),
            'bond_warn_count': sum(1 for bond in bonds if bond.get('status') == 'warn'),
            'bond_fail_count': sum(1 for bond in bonds if bond.get('status') == 'fail'),
            'bonds': bonds,
        }

    def _format_bond_statuses(self, bonds):
        return ', '.join(
            f"{bond.get('name')}={bond.get('status')}"
            for bond in bonds
        )

    def _format_down_slaves(self, bonds):
        details = []
        for bond in bonds:
            down_slaves = bond.get('down_slave_names') or []
            if down_slaves:
                details.append(f"{bond.get('name')}({','.join(down_slaves)})")
            elif bond.get('status') == 'warn':
                details.append(f"{bond.get('name')}(slave 상태 미확인)")
        return ', '.join(details)

    def run(self):
        rc, out, err = self._ssh(BONDING_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='NIC bonding 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            parsed = self._parse_output(out)
        except ValueError as exc:
            return self.fail(
                'bonding 상태 파싱 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        metrics = self._build_metrics(parsed)
        bonds = metrics.get('bonds') or []

        if not parsed.get('bonding_configured'):
            result = self.fail(
                'NIC Bonding 미구성',
                message='시스템에 NIC bonding이 구성되어 있지 않습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = '명령 결과가 NIC BONDING NOT CONFIGURED로 출력되어 NIC bonding이 미구성 상태로 확인되었습니다.'
            return result

        failed_bonds = [
            bond
            for bond in bonds
            if bond.get('status') == 'fail'
        ]
        if failed_bonds:
            result = self.fail(
                'NIC Bonding 인터페이스 Down',
                message='bonding 레벨 MII Status가 down인 인터페이스가 확인되었습니다: ' + ', '.join(
                    bond.get('name') or ''
                    for bond in failed_bonds
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = 'bonding 레벨 MII Status가 down인 인터페이스가 있습니다. 본드별 상태: ' + self._format_bond_statuses(bonds)
            return result

        warning_bonds = [
            bond
            for bond in bonds
            if bond.get('status') == 'warn'
        ]
        if warning_bonds:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='bonding 인터페이스는 up이지만 구성원 NIC 상태에 추가 확인이 필요합니다: ' + self._format_down_slaves(warning_bonds),
                message='NIC Bonding 구성원 상태 추가 확인 필요',
            )

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='모든 bonding 인터페이스와 구성원 NIC가 up 상태입니다. 본드별 상태: ' + self._format_bond_statuses(bonds),
            message='NIC 이중화 점검 정상',
        )


CHECK_CLASS = Check
