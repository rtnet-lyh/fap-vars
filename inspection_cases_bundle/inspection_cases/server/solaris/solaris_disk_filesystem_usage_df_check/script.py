# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DF_COMMAND = 'df -h'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _to_bytes(self, value):
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([KMGTP]?)(?:i?B?)?$', str(value).strip(), re.IGNORECASE)
        if not match:
            return None
        number = float(match.group(1))
        unit = match.group(2).upper()
        multiplier = {'': 1, 'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4, 'P': 1024 ** 5}[unit]
        return number * multiplier

    def _parse_number(self, value):
        try:
            return float(str(value).strip().rstrip('%'))
        except (TypeError, ValueError):
            return None

    def _parse_df_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        if not lines:
            return {
                'header_found': False,
                'rows': [],
            }

        header_found = False
        rows = []
        for index, line in enumerate(lines):
            parts = re.split(r'\s+', line.strip())
            lowered = [part.lower() for part in parts]
            if not header_found:
                if 'filesystem' in lowered and ('use%' in lowered or 'capacity' in lowered):
                    header_found = True
                continue

            if len(parts) < 6:
                continue

            size_bytes = self._to_bytes(parts[1])
            used_bytes = self._to_bytes(parts[2])
            avail_bytes = self._to_bytes(parts[3])
            used_percent = self._parse_number(parts[4])

            if size_bytes is None or used_bytes is None or avail_bytes is None or used_percent is None:
                continue

            mount_point = ' '.join(parts[5:])
            avail_percent = round((avail_bytes / size_bytes) * 100, 2) if size_bytes > 0 else 0.0

            rows.append({
                'line_number': index + 1,
                'filesystem': parts[0],
                'size': parts[1],
                'used': parts[2],
                'avail': parts[3],
                'used_percent': round(used_percent, 2),
                'avail_percent': avail_percent,
                'mount_point': mount_point,
                'size_bytes': size_bytes,
                'used_bytes': used_bytes,
                'avail_bytes': avail_bytes,
            })

        return {
            'header_found': header_found,
            'rows': rows,
        }

    def _build_mount_summary(self, rows, limit=3):
        if not rows:
            return 'mount 요약 없음'

        summaries = []
        for row in rows[:limit]:
            summaries.append(
                f"{row['mount_point']} {row['used_percent']:.2f}% used, avail {row['avail_percent']:.2f}%"
            )
        if len(rows) > limit:
            summaries.append(f"외 {len(rows) - limit}개")
        return ', '.join(summaries)

    def run(self):
        used_max_percent = self.get_threshold_var('used_max_percent', default=80.0, value_type='float')
        avail_min_percent = self.get_threshold_var('avail_min_percent', default=20.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(DF_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    '현재 상태: df -h 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    f'현재 상태: df -h 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_output = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '파일시스템 실패 키워드 감지',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_df_rows(text)
        if not parsed['header_found']:
            return self.fail(
                '파일시스템 사용량 파싱 실패',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    '현재 상태: df -h 출력에서 Filesystem/Use% 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        rows = parsed['rows']
        if not rows:
            return self.fail(
                '파일시스템 사용량 파싱 실패',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    '현재 상태: df -h 출력에서 파일시스템 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        invalid_rows = [
            row for row in rows
            if row['size_bytes'] <= 0
            or row['used_bytes'] < 0
            or row['avail_bytes'] < 0
            or row['used_bytes'] > row['size_bytes']
            or row['avail_bytes'] > row['size_bytes']
        ]
        if invalid_rows:
            invalid_summary = ', '.join(
                f"{row['mount_point']} size {row['size']} used {row['used']} avail {row['avail']}"
                for row in invalid_rows[:3]
            )
            return self.fail(
                '파일시스템 데이터 불일치',
                message=(
                    'Solaris 파일시스템 사용량 점검에 실패했습니다. '
                    f'현재 상태: 파일시스템 용량 데이터가 비정상입니다: {invalid_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        threshold_rows = [
            row for row in rows
            if row['used_percent'] >= used_max_percent or row['avail_percent'] < avail_min_percent
        ]
        threshold_rows.sort(key=lambda row: (row['used_percent'], -row['avail_percent']), reverse=True)
        affected_summary = self._build_mount_summary(threshold_rows or sorted(rows, key=lambda row: row['used_percent'], reverse=True))
        if threshold_rows:
            top = threshold_rows[0]
            return self.fail(
                '파일시스템 사용률 임계치 초과',
                message=(
                    'Solaris 파일시스템 사용량이 기준치를 초과했습니다. '
                    f'현재 상태: {top["mount_point"]} 사용률 {top["used_percent"]:.2f}% (기준 {used_max_percent:.2f}% 미만), '
                    f'여유 {top["avail_percent"]:.2f}% (기준 {avail_min_percent:.2f}% 이상), '
                    f'Size {top["size"]}, Used {top["used"]}, Avail {top["avail"]}, 영향 mount 요약: {affected_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        max_row = max(rows, key=lambda item: item['used_percent'])
        min_avail_row = min(rows, key=lambda item: item['avail_percent'])
        return self.ok(
            metrics={
                'filesystem_count': len(rows),
                'max_usage_mount_point': max_row['mount_point'],
                'max_usage_percent': max_row['used_percent'],
                'lowest_avail_mount_point': min_avail_row['mount_point'],
                'lowest_avail_percent': min_avail_row['avail_percent'],
                'rows': rows,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'used_max_percent': used_max_percent,
                'avail_min_percent': avail_min_percent,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'모든 파일시스템 {len(rows)}개가 정상 해석되었고 최대 사용률 {max_row["used_percent"]:.2f}%와 '
                f'최소 여유율 {min_avail_row["avail_percent"]:.2f}%가 모두 기준 이내입니다.'
            ),
            message=(
                'Solaris 파일시스템 사용량이 정상입니다. '
                f'현재 상태: 파일시스템 {len(rows)}개, 최대 사용률 {max_row["mount_point"]} {max_row["used_percent"]:.2f}% '
                f'(기준 {used_max_percent:.2f}% 미만), 최소 여유율 {min_avail_row["mount_point"]} {min_avail_row["avail_percent"]:.2f}% '
                f'(기준 {avail_min_percent:.2f}% 이상), 영향 mount 요약: {affected_summary}.'
            ),
        )


CHECK_CLASS = Check
