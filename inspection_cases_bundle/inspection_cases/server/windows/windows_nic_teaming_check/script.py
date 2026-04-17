# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


NETWORK_NIC_HA_COMMAND = (
    "if (Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue) { "
    "$teams = Get-NetLbfoTeam -ErrorAction SilentlyContinue; "
    "if ($teams) { "
    "$teams | ForEach-Object { $team = $_; "
    "Get-NetLbfoTeamMember -Team $team.Name | "
    "Select-Object @{N='GROUPNAME';E={$team.Name}}, @{N='TEAMSTATE';E={$team.Status}}, @{N='MODE';E={$team.TeamingMode}}, @{N='NIC';E={$_.Name}}, @{N='STATE';E={$_.OperationalMode}}, @{N='ACTIVE';E={if ($_.OperationalMode -eq 'Active') {'Yes'} else {'No'}}}, @{N='ROLE';E={$_.AdministrativeMode}} } | "
    "Format-Table -AutoSize } else { 'NIC Teaming(LBFO): 미구성 또는 미지원' } } else { 'NetLbfo cmdlet 없음' }"
)


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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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
            return self.ok(
                metrics={
                    'lbfo_cmdlet_available': False,
                    'team_count': 0,
                    'team_member_count': 0,
                    'down_or_degraded_team_count': 0,
                    'failed_member_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_down_or_degraded_team_count': max_down_or_degraded_team_count,
                    'max_failed_member_count': max_failed_member_count,
                    'failure_keywords': [],
                },
                reasons='NIC Teaming(LBFO) 정보를 확인할 수 없습니다.',
                message='Windows NIC 이중화 상태 점검이 정상 수행되었습니다.',
            )

        if text in ('NIC Teaming(LBFO): 미구성 또는 미지원', 'NetLbfo cmdlet 없음'):
            return self.ok(
                metrics={
                    'lbfo_cmdlet_available': text != 'NetLbfo cmdlet 없음',
                    'team_count': 0,
                    'team_member_count': 0,
                    'down_or_degraded_team_count': 0,
                    'failed_member_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_down_or_degraded_team_count': max_down_or_degraded_team_count,
                    'max_failed_member_count': max_failed_member_count,
                    'failure_keywords': [],
                },
                reasons='NIC Teaming(LBFO)이 미구성 또는 미지원 상태이며, 일반적인 Windows 11 환경에서는 LBFO 구성이 없을 수 있습니다.',
                message='Windows NIC 이중화 상태 점검이 정상 수행되었습니다.',
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

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        entries = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('GROUPNAME') and 'TEAMSTATE' in stripped:
                continue
            if stripped.startswith('----') or stripped.startswith('-----------'):
                continue

            parts = [part.strip() for part in re.split(r'\s{2,}', stripped) if part.strip()]
            if len(parts) < 7:
                continue

            entries.append({
                'groupname': parts[0],
                'teamstate': parts[1],
                'mode': parts[2],
                'nic': parts[3],
                'state': parts[4],
                'active': parts[5],
                'role': parts[6],
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
            message='Windows NIC 이중화 상태 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
