# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


NETWORK_NIC_HA_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "if (Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue) { "
    "$teams = Get-NetLbfoTeam -ErrorAction SilentlyContinue; "
    "if ($teams) { "
    "@($teams | ForEach-Object { $team = $_; "
    "Get-NetLbfoTeamMember -Team $team.Name | "
    "Select-Object @{N='GROUPNAME';E={$team.Name}}, @{N='TEAMSTATE';E={$team.Status}}, @{N='MODE';E={$team.TeamingMode}}, @{N='NIC';E={$_.Name}}, @{N='STATE';E={$_.OperationalMode}}, @{N='ACTIVE';E={if ($_.OperationalMode -eq 'Active') {'Yes'} else {'No'}}}, @{N='ROLE';E={$_.AdministrativeMode}} }) | "
    "ConvertTo-Json -Depth 3 } else { 'NIC Teaming(LBFO): 미구성 또는 미지원' } } else { 'NetLbfo cmdlet 없음' }"
)


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_down_or_degraded_team_count = self.get_threshold_var('max_down_or_degraded_team_count', default=0, value_type='int')
        max_failed_member_count = self.get_threshold_var('max_failed_member_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(NETWORK_NIC_HA_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows NIC 이중화 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows NIC 이중화 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'NIC Teaming 정보 없음',
                message=(
                    'Windows NIC 이중화 상태 점검에 실패했습니다. '
                    '현재 상태: NIC Teaming(LBFO) 정보를 확인할 수 없어 팀 0개, 멤버 0개로 집계했습니다.'
                ),
                stdout='',
                stderr=(err or '').strip(),
            )

        if text in ('NIC Teaming(LBFO): 미구성 또는 미지원', 'NetLbfo cmdlet 없음'):
            return self.fail(
                'NIC Teaming 미구성 또는 미지원',
                message=(
                    f'Windows NIC 이중화 상태 점검에 실패했습니다. 현재 상태: {text}, '
                    '팀 0개, 멤버 0개로 집계했습니다.'
                ),
                stdout=text,
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
                'NIC 이중화 실패 키워드 감지',
                message='NIC 이중화 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'NIC 이중화 파싱 실패',
                message='NIC Teaming 결과 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        for entry in _as_list(parsed):
            if not isinstance(entry, dict):
                continue
            entries.append({
                'groupname': str(entry.get('GROUPNAME', '')).strip(),
                'teamstate': str(entry.get('TEAMSTATE', '')).strip(),
                'mode': str(entry.get('MODE', '')).strip(),
                'nic': str(entry.get('NIC', '')).strip(),
                'state': str(entry.get('STATE', '')).strip(),
                'active': str(entry.get('ACTIVE', '')).strip(),
                'role': str(entry.get('ROLE', '')).strip(),
            })

        if not entries:
            return self.fail(
                'NIC 이중화 파싱 실패',
                message='NIC Teaming 결과 테이블을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        team_names = sorted({entry['groupname'] for entry in entries})
        down_or_degraded_teams = sorted({
            entry['groupname']
            for entry in entries
            if entry['teamstate'].lower() in ('down', 'degraded')
        })
        failed_members = [
            entry['nic']
            for entry in entries
            if entry['state'].lower() not in ('active', 'standby')
        ]
        active_members = [
            entry['nic']
            for entry in entries
            if entry['active'].lower() == 'yes'
        ]

        if len(down_or_degraded_teams) > max_down_or_degraded_team_count:
            return self.fail(
                'NIC 팀 상태 이상 감지',
                message='Down 또는 Degraded 상태의 NIC 팀이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(failed_members) > max_failed_member_count:
            return self.fail(
                'NIC 팀 멤버 상태 이상 감지',
                message='Active 또는 Standby가 아닌 NIC 팀 멤버가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        reasons = 'NIC Teaming 팀 상태와 멤버 상태를 점검한 결과 기준 범위 내입니다.'

        return self.ok(
            metrics={
                'lbfo_cmdlet_available': True,
                'team_count': len(team_names),
                'team_member_count': len(entries),
                'down_or_degraded_team_count': len(down_or_degraded_teams),
                'failed_member_count': len(failed_members),
                'team_names': team_names,
                'down_or_degraded_teams': down_or_degraded_teams,
                'failed_members': failed_members,
                'active_members': active_members,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_down_or_degraded_team_count': max_down_or_degraded_team_count,
                'max_failed_member_count': max_failed_member_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows NIC 이중화 상태 점검이 정상입니다. 현재 상태: '
                f'팀 {len(team_names)}개, 멤버 {len(entries)}개, '
                f'Down/Degraded 팀 {len(down_or_degraded_teams)}개 '
                f'(기준 {max_down_or_degraded_team_count}개 이하), '
                f'비정상 멤버 {len(failed_members)}개 '
                f'(기준 {max_failed_member_count}개 이하).'
            ),
        )


CHECK_CLASS = Check
