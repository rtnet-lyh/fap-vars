#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_RAW_ROOT = Path('inspection_cases_bundle/raw_data')
DEFAULT_CASE_ROOT = Path('inspection_cases_bundle/inspection_cases')
DEFAULT_OUTPUT_ROOT = Path('inspection_cases_bundle/api_data/os')
DEFAULT_REPORT_ROOT = Path('inspection_cases_bundle/api_data/_reports')
DEFAULT_TYPE_NAME = '일상점검'
DEFAULT_CATEGORY_NAME = '상태점검'

EXCLUDED_PATH_PARTS = {'참고'}
RAW_HEADINGS = {
    '영역',
    '세부 점검항목',
    '점검 내용',
    '구분',
    '명령어',
    '출력 결과',
    '설명',
    '임계치',
    '판단기준',
}


@dataclass
class SkipEntry:
    raw_path: str
    reason: str
    detail: str = ''
    expected_script: str = ''
    output_path: str = ''


@dataclass
class WarningEntry:
    raw_path: str
    reason: str
    detail: str = ''


@dataclass
class GeneratedEntry:
    raw_path: str
    script_path: str
    output_path: str
    dry_run: bool
    match_strategy: str = 'exact'


@dataclass
class ConversionSummary:
    dry_run: bool
    raw_root: str
    case_root: str
    output_root: str
    report_root: str
    total_raw_md: int = 0
    excluded_agents: int = 0
    excluded_reference: int = 0
    generated_count: int = 0
    skipped_count: int = 0
    warning_count: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    warning_reasons: dict[str, int] = field(default_factory=dict)
    generated: list[GeneratedEntry] = field(default_factory=list)
    skipped: list[SkipEntry] = field(default_factory=list)
    warnings: list[WarningEntry] = field(default_factory=list)

    def add_skip(self, entry: SkipEntry) -> None:
        self.skipped.append(entry)
        self.skipped_count += 1
        self.skip_reasons[entry.reason] = self.skip_reasons.get(entry.reason, 0) + 1

    def add_warning(self, entry: WarningEntry) -> None:
        self.warnings.append(entry)
        self.warning_count += 1
        self.warning_reasons[entry.reason] = self.warning_reasons.get(entry.reason, 0) + 1

    def add_generated(self, entry: GeneratedEntry) -> None:
        self.generated.append(entry)
        self.generated_count += 1


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def to_posix(path: Path) -> str:
    return path.as_posix()


def parse_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            heading = stripped[2:].strip()
            if heading in RAW_HEADINGS:
                current_heading = heading
                sections.setdefault(current_heading, [])
                continue
            current_heading = None
            continue

        if current_heading is not None:
            sections[current_heading].append(line)

    return {heading: '\n'.join(lines).strip() for heading, lines in sections.items()}


def strip_outer_fence(value: str) -> str:
    lines = (value or '').strip().splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith('```') and lines[-1].strip() == '```':
        return '\n'.join(lines[1:-1]).strip()
    return (value or '').strip()


def load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(read_text(path))
    if isinstance(data, dict):
        return data
    return None


def first_item(case_data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(case_data, dict):
        return {}

    item = case_data.get('item')
    if isinstance(item, dict):
        return item

    items = case_data.get('items')
    if isinstance(items, list):
        for candidate in items:
            if isinstance(candidate, dict):
                return candidate

    return {}


def extract_inspection_code(case_data: dict[str, Any] | None) -> str:
    item = first_item(case_data)
    for source in (item, case_data or {}):
        value = source.get('inspection_code') if isinstance(source, dict) else None
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def extract_threshold_entries(case_data: dict[str, Any] | None) -> list[dict[str, str]]:
    item = first_item(case_data)
    threshold_list = item.get('threshold_list') if isinstance(item, dict) else None
    if not isinstance(threshold_list, list):
        return []

    entries: list[dict[str, str]] = []
    for threshold in threshold_list:
        if not isinstance(threshold, dict):
            continue
        key = str(threshold.get('name') or threshold.get('key') or '').strip()
        if not key:
            continue
        value = threshold.get('value1')
        if value is None:
            value = threshold.get('value')
        if value is None:
            value = ''
        entries.append({'key': key, 'value': str(value)})
    return entries


def raw_threshold_entries(raw_thresholds: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in (raw_thresholds or '').splitlines():
        stripped = line.strip().strip('-').strip()
        if not stripped or stripped.startswith('```'):
            continue
        entries.append({'key': stripped, 'value': ''})
    return entries


def escape_js_string(value: str) -> str:
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def format_thresholds(entries: list[dict[str, str]]) -> str:
    if not entries:
        return '[]'

    lines = ['[']
    for idx, entry in enumerate(entries):
        prefix = '    ' if idx == 0 else ''
        if idx > 0:
            lines.append(',')
        key = escape_js_string(entry.get('key', ''))
        value = escape_js_string(entry.get('value', ''))
        lines.append(f'{prefix}{{id: null, key: "{key}", value: "{value}", sortOrder: {idx}}}')
    lines.append(']')
    return '\n'.join(lines)


def render_markdown(
    rel_path: Path,
    sections: dict[str, str],
    case_data: dict[str, Any] | None,
    script_text: str,
    *,
    type_name: str = DEFAULT_TYPE_NAME,
    category_name: str = DEFAULT_CATEGORY_NAME,
) -> str:
    area_name, application_type, application = rel_path.parts[:3]
    case_thresholds = extract_threshold_entries(case_data)
    threshold_entries = case_thresholds or raw_threshold_entries(sections.get('임계치', ''))
    description_parts = [sections.get('설명', '').strip(), sections.get('판단기준', '').strip()]
    description = '\n\n'.join(part for part in description_parts if part)

    field_values = [
        ('type_name', type_name),
        ('area_name', area_name),
        ('category_name', category_name),
        ('application_type', application_type),
        ('application', application),
        ('inspection_code', extract_inspection_code(case_data)),
        ('is_required', sections.get('구분', '').strip()),
        ('inspection_name', sections.get('세부 점검항목', '').strip()),
        ('inspection_content', sections.get('점검 내용', '').strip()),
    ]

    chunks: list[str] = []
    for heading, value in field_values:
        chunks.append(f'# {heading}\n\n{value}'.rstrip())

    command = strip_outer_fence(sections.get('명령어', ''))
    output = strip_outer_fence(sections.get('출력 결과', ''))
    chunks.append(f'# inspection_command\n\n```bash\n{command}\n```')
    chunks.append(f'# inspection_output\n\n```text\n{output}\n```')
    chunks.append(f'# description\n\n{description}'.rstrip())
    chunks.append(f'# thresholds\n\n{format_thresholds(threshold_entries)}')
    chunks.append(f'# inspection_script\n\n{script_text.rstrip()}')

    return '\n\n'.join(chunks).rstrip() + '\n'


def classify_raw_path(raw_path: Path, raw_root: Path) -> tuple[str, Path | None]:
    rel_path = raw_path.relative_to(raw_root)
    if raw_path.name == 'AGENTS.md':
        return 'agents', rel_path
    if any(part in EXCLUDED_PATH_PARTS for part in rel_path.parts):
        return 'reference', rel_path
    if len(rel_path.parts) != 4:
        return 'invalid_depth', rel_path
    return 'candidate', rel_path


def extract_number_key(case_name: str) -> str:
    match = re.search(r'(?<!\d)(\d+(?:_\d+)+)(?!\d)', case_name)
    if not match:
        return ''
    return match.group(1)


def case_parent_candidates(case_root: Path, rel_path: Path) -> list[tuple[str, Path]]:
    rel_parent = rel_path.with_suffix('').parent
    candidates = [('same_parent', case_root / rel_parent)]

    if len(rel_path.parts) >= 4:
        area_name, _application_type, application = rel_path.parts[:3]
        collapsed_parent = case_root / area_name / application
        if collapsed_parent != candidates[0][1]:
            candidates.append(('collapsed_application_type_parent', collapsed_parent))

    return candidates


def find_number_key_case_dir(parent: Path, number_key: str) -> Path | None:
    if not number_key or not parent.is_dir():
        return None

    matches = [
        child
        for child in sorted(parent.iterdir())
        if child.is_dir()
        and extract_number_key(child.name) == number_key
        and (child / 'script.py').exists()
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_case_dir(case_root: Path, rel_path: Path) -> tuple[Path | None, str, list[Path]]:
    base_case_dir = case_root / rel_path.with_suffix('')
    number_key = extract_number_key(base_case_dir.name)
    tried = []

    for parent_strategy, parent in case_parent_candidates(case_root, rel_path):
        exact_dir = parent / base_case_dir.name
        suffix_dir = parent / f'{base_case_dir.name}_check'
        direct_candidates = [
            (f'{parent_strategy}:exact', exact_dir),
            (f'{parent_strategy}:suffix_check', suffix_dir),
        ]

        for strategy, case_dir in direct_candidates:
            tried.append(case_dir / 'script.py')
            if (case_dir / 'script.py').exists():
                return case_dir, strategy, tried

        number_key_case_dir = find_number_key_case_dir(parent, number_key)
        if number_key_case_dir is not None:
            tried.append(number_key_case_dir / 'script.py')
            return number_key_case_dir, f'{parent_strategy}:number_key', tried

        if number_key and parent.is_dir():
            tried.extend(
                child / 'script.py'
                for child in sorted(parent.iterdir())
                if child.is_dir() and extract_number_key(child.name) == number_key
            )

    return None, 'missing_script', tried


def convert_all(
    raw_root: Path,
    case_root: Path,
    output_root: Path,
    report_root: Path,
    dry_run: bool,
    overwrite: bool,
    *,
    type_name: str = DEFAULT_TYPE_NAME,
    category_name: str = DEFAULT_CATEGORY_NAME,
) -> ConversionSummary:
    summary = ConversionSummary(
        dry_run=dry_run,
        raw_root=to_posix(raw_root),
        case_root=to_posix(case_root),
        output_root=to_posix(output_root),
        report_root=to_posix(report_root),
    )

    for raw_path in sorted(raw_root.rglob('*.md')):
        summary.total_raw_md += 1
        status, rel_path = classify_raw_path(raw_path, raw_root)
        rel_path = rel_path or raw_path.relative_to(raw_root)

        if status == 'agents':
            summary.excluded_agents += 1
            continue
        if status == 'reference':
            summary.excluded_reference += 1
            continue
        if status == 'invalid_depth':
            summary.add_skip(SkipEntry(
                raw_path=to_posix(raw_path),
                reason='invalid_path_depth',
                detail='expected <area_name>/<application_type>/<application>/<case>.md',
            ))
            continue

        case_dir, match_strategy, tried_scripts = resolve_case_dir(case_root, rel_path)
        output_path = output_root / rel_path

        if case_dir is None:
            summary.add_skip(SkipEntry(
                raw_path=to_posix(raw_path),
                reason='missing_script',
                expected_script=', '.join(to_posix(path) for path in tried_scripts),
                output_path=to_posix(output_path),
            ))
            continue

        script_path = case_dir / 'script.py'

        if output_path.exists() and not overwrite:
            summary.add_skip(SkipEntry(
                raw_path=to_posix(raw_path),
                reason='output_exists',
                expected_script=to_posix(script_path),
                output_path=to_posix(output_path),
            ))
            continue

        case_json_path = case_dir / 'case.json'
        case_data = load_json_object(case_json_path)
        if case_data is None:
            summary.add_warning(WarningEntry(
                raw_path=to_posix(raw_path),
                reason='missing_or_invalid_case_json',
                detail=to_posix(case_json_path),
            ))

        sections = parse_markdown_sections(read_text(raw_path))
        script_text = read_text(script_path)
        rendered = render_markdown(rel_path, sections, case_data, script_text, type_name=type_name, category_name=category_name)

        if not dry_run:
            write_text(output_path, rendered)

        summary.add_generated(GeneratedEntry(
            raw_path=to_posix(raw_path),
            script_path=to_posix(script_path),
            output_path=to_posix(output_path),
            dry_run=dry_run,
            match_strategy=match_strategy,
        ))

    return summary


def entry_to_dict(entry: GeneratedEntry | SkipEntry | WarningEntry) -> dict[str, Any]:
    return {key: value for key, value in entry.__dict__.items() if value not in ('', None)}


def summary_to_dict(summary: ConversionSummary) -> dict[str, Any]:
    return {
        'dry_run': summary.dry_run,
        'raw_root': summary.raw_root,
        'case_root': summary.case_root,
        'output_root': summary.output_root,
        'report_root': summary.report_root,
        'total_raw_md': summary.total_raw_md,
        'excluded_agents': summary.excluded_agents,
        'excluded_reference': summary.excluded_reference,
        'generated_count': summary.generated_count,
        'skipped_count': summary.skipped_count,
        'warning_count': summary.warning_count,
        'skip_reasons': summary.skip_reasons,
        'warning_reasons': summary.warning_reasons,
        'generated': [entry_to_dict(entry) for entry in summary.generated],
        'skipped': [entry_to_dict(entry) for entry in summary.skipped],
        'warnings': [entry_to_dict(entry) for entry in summary.warnings],
    }


def render_report(summary: ConversionSummary) -> str:
    lines = [
        '# generate_os_md_from_cases report',
        '',
        '## Summary',
        '',
        f'- dry_run: `{str(summary.dry_run).lower()}`',
        f'- raw_root: `{summary.raw_root}`',
        f'- case_root: `{summary.case_root}`',
        f'- output_root: `{summary.output_root}`',
        f'- total_raw_md: `{summary.total_raw_md}`',
        f'- excluded_agents: `{summary.excluded_agents}`',
        f'- excluded_reference: `{summary.excluded_reference}`',
        f'- generated_count: `{summary.generated_count}`',
        f'- skipped_count: `{summary.skipped_count}`',
        f'- warning_count: `{summary.warning_count}`',
        '',
        '## Skip reasons',
        '',
    ]

    if summary.skip_reasons:
        for reason, count in sorted(summary.skip_reasons.items()):
            lines.append(f'- `{reason}`: `{count}`')
    else:
        lines.append('- 없음')

    lines.extend(['', '## Warning reasons', ''])
    if summary.warning_reasons:
        for reason, count in sorted(summary.warning_reasons.items()):
            lines.append(f'- `{reason}`: `{count}`')
    else:
        lines.append('- 없음')

    lines.extend(['', '## Generated outputs', ''])
    if summary.generated:
        for entry in summary.generated:
            label = 'would_create' if entry.dry_run else 'created'
            lines.append(f'- `{label}` `{entry.output_path}`')
            lines.append(f'  - raw: `{entry.raw_path}`')
            lines.append(f'  - script: `{entry.script_path}`')
            lines.append(f'  - match_strategy: `{entry.match_strategy}`')
    else:
        lines.append('- 없음')

    lines.extend(['', '## Skipped files', ''])
    if summary.skipped:
        for entry in summary.skipped:
            lines.append(f'- `{entry.reason}` `{entry.raw_path}`')
            if entry.detail:
                lines.append(f'  - detail: `{entry.detail}`')
            if entry.expected_script:
                lines.append(f'  - expected_script: `{entry.expected_script}`')
            if entry.output_path:
                lines.append(f'  - output_path: `{entry.output_path}`')
    else:
        lines.append('- 없음')

    lines.extend(['', '## Warnings', ''])
    if summary.warnings:
        for entry in summary.warnings:
            lines.append(f'- `{entry.reason}` `{entry.raw_path}`')
            if entry.detail:
                lines.append(f'  - detail: `{entry.detail}`')
    else:
        lines.append('- 없음')

    return '\n'.join(lines).rstrip() + '\n'


def write_reports(summary: ConversionSummary, report_root: Path) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    write_text(report_root / 'skip_report.md', render_report(summary))
    write_text(
        report_root / 'summary.json',
        json.dumps(summary_to_dict(summary), ensure_ascii=False, indent=2) + '\n',
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate api_data/os Markdown from raw_data Markdown and inspection case scripts.',
    )
    parser.add_argument('--raw-root', default=str(DEFAULT_RAW_ROOT), help='raw_data root directory')
    parser.add_argument('--case-root', default=str(DEFAULT_CASE_ROOT), help='inspection_cases root directory')
    parser.add_argument('--output-root', default=str(DEFAULT_OUTPUT_ROOT), help='api_data/os output root')
    parser.add_argument('--report-root', default=str(DEFAULT_REPORT_ROOT), help='report output root')
    parser.add_argument('--dry-run', action='store_true', help='do not create api_data/os Markdown files')
    parser.add_argument('--overwrite', action='store_true', help='overwrite existing generated Markdown files')
    parser.add_argument('--type-name', default=DEFAULT_TYPE_NAME, help='type_name value for generated Markdown')
    parser.add_argument('--category-name', default=DEFAULT_CATEGORY_NAME, help='category_name value for generated Markdown')
    parser.add_argument('--area-name', dest='legacy_area_name', help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_root = Path(args.raw_root)
    case_root = Path(args.case_root)
    output_root = Path(args.output_root)
    report_root = Path(args.report_root)

    category_name = args.legacy_area_name or args.category_name

    summary = convert_all(
        raw_root=raw_root,
        case_root=case_root,
        output_root=output_root,
        report_root=report_root,
        dry_run=bool(args.dry_run),
        overwrite=bool(args.overwrite),
        type_name=args.type_name,
        category_name=category_name,
    )
    write_reports(summary, report_root)

    print(json.dumps({
        'dry_run': summary.dry_run,
        'total_raw_md': summary.total_raw_md,
        'excluded_agents': summary.excluded_agents,
        'excluded_reference': summary.excluded_reference,
        'generated_count': summary.generated_count,
        'skipped_count': summary.skipped_count,
        'warning_count': summary.warning_count,
        'skip_reasons': summary.skip_reasons,
        'warning_reasons': summary.warning_reasons,
        'report': to_posix(report_root / 'skip_report.md'),
        'summary': to_posix(report_root / 'summary.json'),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
