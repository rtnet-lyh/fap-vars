# type_name

일상점검(상태점검)

# area_name

서버

# category_name

KERNAL

# application_type

UNIX

# application

solaris

# inspection_code

SVR-4-1

# is_required

권고

# inspection_name

Kernel Parameter Check

# inspection_content

Solaris 서버의 기본 커널 파라미터가 섹션별로 조회되는지와 핵심 파라미터 존재 여부를 점검합니다.

# inspection_command

```bash
sysdef
```

# inspection_output

```text
*Tunable Parameters*
shmmax: 4294967295
shminfo_shmmin: 1
seminfo_semmsl: 256
seminfo_semmns: 32000
seminfo_semopm: 32

*File System Parameters*
maxfiles: 8192
maxuproc: 512

*Memory Management Parameters*
maxpgio: 8192
minfree: 200
desfree: 400
lotsfree: 1024

*IPC Parameters*
msginfo_msgmax: 8192
msginfo_msgmnb: 16384
msginfo_msgtql: 40
msginfo_msgseg: 2048
```

# description

- 시스템 운영자가 커널 파라미터를 조정할 때 기준값 확인용으로 사용.
  - 예시에서는 공유 메모리 최대 크기 `shmmax=4294967295`를 확인.
  - File System, Memory, IPC 관련 파라미터를 함께 점검 가능.

# thresholds

[
    {id: null, key: "required_parameters", value: "shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax", sortOrder: 0}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


SYSDEF_COMMAND = 'sysdef'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_parameters(self, text):
        parameter_map = {}
        section_names = []
        current_section = ''

        for line in text.splitlines():
            stripped = line.strip()
            section_match = stripped.startswith('*') and stripped.endswith('*')
            if section_match:
                current_section = stripped.strip('*').strip()
                if current_section:
                    section_names.append(current_section)
                continue

            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if not key or not value or key.startswith('*'):
                continue
            parameter_map[key] = {
                'value': value,
                'section': current_section,
            }
        return {
            'parameter_map': parameter_map,
            'section_names': section_names,
        }

    def run(self):
        required_parameters_raw = self.get_threshold_var('required_parameters', default='shmmax,seminfo_semmsl,maxfiles,maxuproc,minfree,msginfo_msgmax', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(SYSDEF_COMMAND)
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
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    '현재 상태: sysdef 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: sysdef 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_output = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '커널 파라미터 실패 키워드 감지',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_parameters(text)
        parameter_map = parsed['parameter_map']
        section_names = parsed['section_names']
        if not parameter_map:
            return self.fail(
                '커널 파라미터 파싱 실패',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    '현재 상태: sysdef 출력에서 파라미터 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        required_sections = [
            'Tunable Parameters',
            'File System Parameters',
            'Memory Management Parameters',
            'IPC Parameters',
        ]
        missing_sections = [section for section in required_sections if section not in section_names]
        if missing_sections:
            return self.fail(
                '커널 파라미터 섹션 누락',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: sysdef 출력에서 핵심 섹션 {missing_sections}를 확인하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        required_parameters = [token.strip() for token in required_parameters_raw.split(',') if token.strip()]
        missing_parameters = [name for name in required_parameters if name not in parameter_map]
        if missing_parameters:
            return self.fail(
                '커널 파라미터 누락',
                message=(
                    'Solaris 커널 파라미터 점검에 실패했습니다. '
                    f'현재 상태: 핵심 파라미터 {missing_parameters}를 sysdef 출력에서 확인하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        summary = ', '.join(
            f'{name}={parameter_map[name]["value"]}'
            for name in required_parameters
        )
        return self.ok(
            metrics={
                'parameter_count': len(parameter_map),
                'section_count': len(section_names),
                'section_names': section_names,
                'required_parameter_count': len(required_parameters),
                'required_parameters': {
                    name: {
                        'value': parameter_map[name]['value'],
                        'section': parameter_map[name]['section'],
                    }
                    for name in required_parameters
                },
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'required_parameters': required_parameters,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'핵심 커널 파라미터 {len(required_parameters)}개와 주요 섹션 {len(required_sections)}개가 모두 조회되었습니다.'
            ),
            message=(
                'Solaris 커널 파라미터가 정상입니다. '
                f'현재 상태: 섹션 {len(section_names)}개, 파라미터 {len(parameter_map)}개, '
                f'핵심 파라미터 {len(required_parameters)}개가 모두 확인되었습니다. {summary}.'
            ),
        )


CHECK_CLASS = Check
