# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


IOSCAN_COMMAND = 'ioscan -m dsf'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_int(self, value, default=0):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def _parse_ioscan_disks(self, text):
        disks = []
        current = None

        for raw_line in (text or '').splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith('Persistent DSF') or stripped.startswith('='):
                continue

            match = re.match(r'^(/dev/rdisk/\S+)\s+(.+)$', line)
            if match:
                current = {
                    'persistent_dsf': match.group(1),
                    'legacy_dsfs': re.findall(r'/dev/rdsk/\S+', match.group(2)),
                }
                disks.append(current)
                continue

            if current and line.startswith(' '):
                current['legacy_dsfs'].extend(re.findall(r'/dev/rdsk/\S+', stripped))

        return disks

    def _parse_scsimgr(self, text):
        status_match = re.search(r'Generic Status:\s*(\S+)', text or '', re.IGNORECASE)
        paths_match = re.search(r'Number of Paths:\s*(\d+)', text or '', re.IGNORECASE)
        return {
            'lun_status': status_match.group(1).upper() if status_match else '',
            'path_count': self._parse_int(paths_match.group(1), 0) if paths_match else 0,
        }

    def run(self):
        expected_path_count = self.get_threshold_var('expected_path_count', default=2, value_type='int')
        required_lun_status = str(
            self.get_threshold_var('required_lun_status', default='OPTIMAL', value_type='str')
        ).strip().upper()

        rc, out, err = self._ssh(IOSCAN_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='ioscan -m dsf 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        disks = self._parse_ioscan_disks(out)
        if not disks:
            return self.fail(
                'Path 매핑 정보 없음',
                message='ioscan -m dsf 결과에서 /dev/rdisk persistent DSF를 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        disk_results = []
        failed_disks = []
        for disk in disks:
            device = disk['persistent_dsf']
            command = f'scsimgr get_info -D {device}'
            rc, scsi_out, scsi_err = self._ssh(command)

            if self._is_connection_error(rc, scsi_err):
                return self.fail(
                    '호스트 연결 실패',
                    message=(scsi_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                    stderr=(scsi_err or '').strip(),
                )
            if rc != 0:
                return self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 실행에 실패했습니다.',
                    stdout=(scsi_out or '').strip(),
                    stderr=(scsi_err or '').strip(),
                )

            parsed = self._parse_scsimgr(scsi_out)
            legacy_path_count = len(disk['legacy_dsfs'])
            result = {
                'persistent_dsf': device,
                'legacy_dsfs': disk['legacy_dsfs'],
                'legacy_path_count': legacy_path_count,
                'scsimgr_path_count': parsed['path_count'],
                'lun_status': parsed['lun_status'],
            }
            disk_results.append(result)

            if (
                legacy_path_count < expected_path_count
                or parsed['path_count'] < expected_path_count
                or parsed['lun_status'] != required_lun_status
            ):
                failed_disks.append(result)

        thresholds = {
            'expected_path_count': expected_path_count,
            'required_lun_status': required_lun_status,
        }
        metrics = {
            'disk_count': len(disk_results),
            'failed_disk_count': len(failed_disks),
            'disks': disk_results,
            'failed_disks': failed_disks,
        }

        if failed_disks:
            return self.fail(
                'Path 이중화 상태 비정상',
                message=(
                    '경로 수 부족 또는 LUN 상태 비정상 디스크가 확인되었습니다: '
                    + ', '.join(
                        f"{item['persistent_dsf']}(legacy_paths={item['legacy_path_count']}, "
                        f"scsimgr_paths={item['scsimgr_path_count']}, status={item['lun_status'] or 'unknown'})"
                        for item in failed_disks
                    )
                ),
                stdout='',
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='모든 persistent DSF의 legacy path 수, scsimgr path 수, LUN 상태가 기준을 만족합니다.',
            message='ioscan/scsimgr 기준 Path 이중화 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
