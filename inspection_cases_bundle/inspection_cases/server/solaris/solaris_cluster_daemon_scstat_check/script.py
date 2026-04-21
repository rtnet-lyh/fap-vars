# -*- coding: utf-8 -*-

from .common._base import BaseCheck


SCSTAT_COMMAND = 'scstat'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _split_required_sections(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _parse_sections(self, text):
        sections = {}
        current = None

        for raw_line in (text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith('===') and line.endswith('==='):
                current = line.strip('=').strip()
                sections[current] = []
                continue

            if current is not None:
                sections[current].append(line)

        return sections

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return '클러스터 이상 상태 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def _detect_abnormal_lines(self, sections, bad_status_keywords):
        abnormal_lines = []
        for section_name, lines in sections.items():
            for line in lines:
                lowered = line.lower()
                if any(keyword.lower() in lowered for keyword in bad_status_keywords):
                    abnormal_lines.append(f'[{section_name}] {line}')
        return abnormal_lines

    def _count_keyword_hits(self, lines, keywords):
        counts = {}
        lowered_lines = [line.lower() for line in lines]
        for keyword in keywords:
            normalized = keyword.lower().replace(' ', '_')
            counts[normalized] = sum(1 for line in lowered_lines if keyword.lower() in line)
        return counts

    def run(self):
        bad_status_keywords = self._split_keywords(
            self.get_threshold_var(
                'bad_status_keywords',
                default='offline,maintenance,path down',
                value_type='str',
            )
        )
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found',
                value_type='str',
            )
        )
        required_sections = self._split_required_sections(
            self.get_threshold_var(
                'required_sections',
                default='Cluster Nodes,Cluster Transport Paths,Resource Groups,Network Interfaces',
                value_type='str',
            )
        )

        rc, out, err = self._ssh(SCSTAT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(value for value in (text, stderr_text) if value)

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=failure_keywords + [
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
                'not supported',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: scstat 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: scstat 명령 종료코드가 rc={rc}로 반환되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if not text:
            return self.fail(
                'Cluster 상태 파싱 실패',
                message='Solaris Cluster 정상 유무 점검에 실패했습니다. 현재 상태: scstat 출력이 비어 있어 Cluster 상태를 해석하지 못했습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'Cluster 상태 실패 키워드 감지',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        sections = self._parse_sections(text)
        missing_sections = [name for name in required_sections if name not in sections]
        if missing_sections:
            return self.fail(
                'Cluster 상태 파싱 실패',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: scstat 출력에서 필수 섹션 {missing_sections}을 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        section_line_counts = {
            'cluster_nodes_count': len(sections.get('Cluster Nodes', [])),
            'transport_paths_count': len(sections.get('Cluster Transport Paths', [])),
            'resource_groups_count': len(sections.get('Resource Groups', [])),
            'network_interfaces_count': len(sections.get('Network Interfaces', [])),
        }
        total_entries = sum(section_line_counts.values())
        if total_entries == 0:
            return self.fail(
                'Cluster 상태 파싱 실패',
                message='Solaris Cluster 정상 유무 점검에 실패했습니다. 현재 상태: 필수 섹션은 있으나 상태 항목이 없어 Cluster 상태를 집계하지 못했습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        all_lines = []
        for section_lines in sections.values():
            all_lines.extend(section_lines)

        abnormal_lines = self._detect_abnormal_lines(sections, bad_status_keywords)
        hit_counts = self._count_keyword_hits(all_lines, ('online', 'offline', 'maintenance', 'path down'))

        metrics = {
            'command_rc': rc,
            'section_count': len(sections),
            'total_entry_count': total_entries,
            'matched_failure_keywords': matched_failure_keywords,
            'abnormal_entry_count': len(abnormal_lines),
            'abnormal_entries': abnormal_lines,
            'cluster_nodes_count': section_line_counts['cluster_nodes_count'],
            'transport_paths_count': section_line_counts['transport_paths_count'],
            'resource_groups_count': section_line_counts['resource_groups_count'],
            'network_interfaces_count': section_line_counts['network_interfaces_count'],
            'online_count': hit_counts['online'],
            'offline_count': hit_counts['offline'],
            'maintenance_count': hit_counts['maintenance'],
            'path_down_count': hit_counts['path_down'],
            'stderr_line_count': len([line for line in stderr_text.splitlines() if line.strip()]),
        }

        if abnormal_lines:
            return self.fail(
                'Cluster 비정상 상태 감지',
                message=(
                    'Solaris Cluster 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: Cluster Nodes {section_line_counts["cluster_nodes_count"]}건, '
                    f'Transport Paths {section_line_counts["transport_paths_count"]}건, '
                    f'Resource Groups {section_line_counts["resource_groups_count"]}건, '
                    f'Network Interfaces {section_line_counts["network_interfaces_count"]}건을 확인했고, '
                    f'비정상 상태 {len(abnormal_lines)}건이 집계되었습니다. '
                    f'offline {hit_counts["offline"]}건, maintenance {hit_counts["maintenance"]}건, '
                    f'path down {hit_counts["path_down"]}건입니다. '
                    f'첫 비정상 상태: {abnormal_lines[0]}. 상태 요약: {self._build_log_summary(abnormal_lines)}.'
                ),
                metrics=metrics,
                thresholds={
                    'bad_status_keywords': bad_status_keywords,
                    'failure_keywords': failure_keywords,
                    'required_sections': required_sections,
                },
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds={
                'bad_status_keywords': bad_status_keywords,
                'failure_keywords': failure_keywords,
                'required_sections': required_sections,
            },
            reasons=(
                'Cluster Nodes, Cluster Transport Paths, Resource Groups, Network Interfaces 섹션이 모두 확인되었고 '
                'offline, maintenance, path down 같은 비정상 상태가 검출되지 않았습니다.'
            ),
            message=(
                'Solaris Cluster 정상 유무 점검이 정상입니다. '
                f'현재 상태: Cluster Nodes {section_line_counts["cluster_nodes_count"]}건, '
                f'Transport Paths {section_line_counts["transport_paths_count"]}건, '
                f'Resource Groups {section_line_counts["resource_groups_count"]}건, '
                f'Network Interfaces {section_line_counts["network_interfaces_count"]}건, '
                f'online {hit_counts["online"]}건, offline 0건, maintenance 0건, path down 0건으로 집계되었습니다.'
            ),
        )


CHECK_CLASS = Check
