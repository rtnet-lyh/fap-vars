# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


MOUNT_COMMAND_TEMPLATE = 'mount | grep -- {mount_point}'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _quote_for_shell(self, value):
        text = str(value or '')
        return "'" + text.replace("'", "'\"'\"'") + "'"

    def _parse_mount_lines(self, text):
        rows = []
        for line_number, raw_line in enumerate((text or '').splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue

            match = re.match(
                r'^(?P<device>\S+)\s+on\s+(?P<mount_point>\S+)\s+type\s+'
                r'(?P<filesystem_type>\S+)\s+\((?P<options>[^)]*)\)\s*$',
                line,
            )
            if not match:
                continue

            options = [option.strip() for option in match.group('options').split(',') if option.strip()]
            rows.append({
                'line_number': line_number,
                'raw_line': line,
                'device': match.group('device'),
                'mount_point': match.group('mount_point'),
                'filesystem_type': match.group('filesystem_type'),
                'mount_options': options,
            })

        return rows

    def _detect_access_mode(self, mount_options):
        lowered = [option.lower() for option in (mount_options or [])]
        if 'rw' in lowered:
            return 'rw'
        if 'ro' in lowered:
            return 'ro'
        return 'unknown'

    def _build_mount_summary(self, rows, limit=3):
        if not rows:
            return '감지된 mount 정보 없음'

        parts = []
        for row in rows[:limit]:
            access_mode = self._detect_access_mode(row['mount_options'])
            parts.append(
                f"{row['mount_point']} {row['filesystem_type']} {access_mode} ({', '.join(row['mount_options'])})"
            )
        if len(rows) > limit:
            parts.append(f'외 {len(rows) - limit}건')
        return ', '.join(parts)

    def run(self):
        mount_point = self.get_threshold_var('mount_point', default='/mnt/shared', value_type='str').strip()
        expected_access_mode = self.get_threshold_var('expected_access_mode', default='rw', value_type='str').strip().lower()
        expected_filesystem_types = [
            token.lower()
            for token in self._split_keywords(
                self.get_threshold_var('expected_filesystem_types', default='', value_type='str')
            )
        ]
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file',
                value_type='str',
            )
        )

        if not mount_point:
            return self.fail(
                '점검 설정 오류',
                message='Solaris 공유 볼륨 상태 점검에 실패했습니다. 현재 상태: mount_point 임계치가 비어 있어 점검 대상을 결정할 수 없습니다.',
            )

        command = MOUNT_COMMAND_TEMPLATE.format(mount_point=self._quote_for_shell(mount_point))
        rc, out, err = self._ssh(command)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(part for part in (text, stderr_text) if part)

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=failure_keywords + [
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
                'not supported',
                'unknown userland error',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount 점검 명령 종료코드가 rc={rc}로 반환되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '공유 볼륨 실패 키워드 감지',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc == 1 or not text:
            return self.fail(
                '공유 볼륨 미마운트',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount point {mount_point}가 mount 출력에서 확인되지 않아 공유 볼륨이 마운트되지 않았습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        parsed_rows = self._parse_mount_lines(text)
        if not parsed_rows:
            return self.fail(
                '공유 볼륨 파싱 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    '현재 상태: mount 출력에서 장치, mount point, 파일시스템, 옵션 정보를 정상적으로 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        matched_rows = [row for row in parsed_rows if row['mount_point'] == mount_point]
        if not matched_rows:
            return self.fail(
                '공유 볼륨 파싱 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount 출력은 존재하지만 요청한 mount point {mount_point}와 정확히 일치하는 항목을 찾지 못했습니다. '
                    f'감지된 mount 요약: {self._build_mount_summary(parsed_rows)}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        target_row = matched_rows[0]
        access_mode = self._detect_access_mode(target_row['mount_options'])
        metrics = {
            'command_rc': rc,
            'mount_point': target_row['mount_point'],
            'device': target_row['device'],
            'filesystem_type': target_row['filesystem_type'],
            'access_mode': access_mode,
            'mount_options': target_row['mount_options'],
            'parsed_mount_count': len(parsed_rows),
            'matched_mount_count': len(matched_rows),
            'matched_failure_keywords': matched_failure_keywords,
            'parsed_mounts': parsed_rows,
        }
        thresholds = {
            'mount_point': mount_point,
            'expected_access_mode': expected_access_mode,
            'expected_filesystem_types': expected_filesystem_types,
            'failure_keywords': failure_keywords,
        }

        if access_mode == 'unknown':
            return self.fail(
                '공유 볼륨 접근 상태 확인 실패',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount point {mount_point}의 옵션 {target_row["mount_options"]}에서 rw/ro 상태를 확인하지 못했습니다.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        if expected_access_mode and access_mode != expected_access_mode:
            return self.fail(
                '공유 볼륨 접근 상태 이상',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount point {mount_point}가 {access_mode} 상태이며 기준은 {expected_access_mode}입니다. '
                    f'device {target_row["device"]}, filesystem {target_row["filesystem_type"]}, '
                    f'options {", ".join(target_row["mount_options"])}.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        if expected_filesystem_types and target_row['filesystem_type'].lower() not in expected_filesystem_types:
            return self.fail(
                '공유 볼륨 파일시스템 유형 이상',
                message=(
                    'Solaris 공유 볼륨 상태 점검에 실패했습니다. '
                    f'현재 상태: mount point {mount_point}의 파일시스템 유형이 {target_row["filesystem_type"]}이며 '
                    f'허용 기준은 {expected_filesystem_types}입니다.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'공유 볼륨 {mount_point}가 정상 마운트되어 있고 '
                f'접근 상태 {access_mode}, 파일시스템 {target_row["filesystem_type"]}가 기준과 일치합니다.'
            ),
            message=(
                'Solaris 공유 볼륨 상태가 정상입니다. '
                f'현재 상태: mount point {mount_point}, device {target_row["device"]}, '
                f'filesystem {target_row["filesystem_type"]}, access {access_mode} '
                f'(기준 {expected_access_mode}), options {", ".join(target_row["mount_options"])}.'
            ),
        )


CHECK_CLASS = Check
