# -*- coding: utf-8 -*-

from .common._base import BaseCheck


CLUSTER_MOUNT_COMMAND = (
    "$p='C:\\mnt\\shared\\'; "
    "$pt=Get-Partition | Where-Object { $_.AccessPaths -contains $p -or $_.AccessPaths -contains $p.TrimEnd('\\') }; "
    "if($pt){ $v=$pt | Get-Volume; "
    "[pscustomobject]@{Device=\"Disk$($pt.DiskNumber)\\Partition$($pt.PartitionNumber)\"; MountedOn=$p.TrimEnd('\\'); FileSystem=$v.FileSystem; Mode=$(if($pt.IsReadOnly){'ro'}else{'rw'}); Status=$pt.OperationalStatus; Health=$v.HealthStatus} | Format-List } "
    "else { \"Mount point not found: $p\" }"
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        expected_mount_path = self.get_threshold_var('expected_mount_path', default='C:\\mnt\\shared\\', value_type='str')
        expected_mode = self.get_threshold_var('expected_mode', default='rw', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(CLUSTER_MOUNT_COMMAND)

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
                message='Windows 클러스터 공유 볼륨 마운트 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '공유 볼륨 마운트 정보 없음',
                message='공유 볼륨 마운트 상태 결과가 비어 있습니다.',
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
                '공유 볼륨 마운트 실패 키워드 감지',
                message='공유 볼륨 마운트 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if text.startswith('Mount point not found:'):
            return self.fail(
                '공유 볼륨 마운트 지점 없음',
                message='지정된 공유 볼륨 마운트 경로를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        info = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ':' not in stripped:
                continue
            key, value = stripped.split(':', 1)
            info[key.strip()] = value.strip()

        if not info:
            return self.fail(
                '공유 볼륨 마운트 파싱 실패',
                message='공유 볼륨 마운트 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        mounted_on = info.get('MountedOn', '')
        filesystem = info.get('FileSystem', '')
        mode = info.get('Mode', '')
        status = info.get('Status', '')
        health = info.get('Health', '')
        device = info.get('Device', '')

        normalized_expected_mount = expected_mount_path.rstrip('\\')
        normalized_mounted_on = mounted_on.rstrip('\\')

        if normalized_mounted_on != normalized_expected_mount:
            return self.fail(
                '공유 볼륨 마운트 경로 불일치',
                message='공유 볼륨이 기대한 마운트 경로에 연결되어 있지 않습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if mode.lower() != expected_mode.lower():
            return self.fail(
                '공유 볼륨 읽기/쓰기 모드 이상',
                message='공유 볼륨이 기대한 읽기/쓰기 모드가 아닙니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if status.lower() not in ('online', 'ok'):
            return self.fail(
                '공유 볼륨 운영 상태 이상',
                message='공유 볼륨 파티션의 OperationalStatus가 정상 범위를 벗어났습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if health.lower() not in ('healthy', 'ok'):
            return self.fail(
                '공유 볼륨 헬스 상태 이상',
                message='공유 볼륨의 HealthStatus가 정상 범위를 벗어났습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'device': device,
                'mounted_on': mounted_on,
                'filesystem': filesystem,
                'mode': mode,
                'status': status,
                'health': health,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'expected_mount_path': expected_mount_path,
                'expected_mode': expected_mode,
                'failure_keywords': failure_keywords,
            },
            reasons='공유 볼륨이 기대한 경로에 연결되어 있고 읽기/쓰기 가능하며 볼륨 상태도 정상입니다.',
            message='Windows 클러스터 공유 볼륨 마운트 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
