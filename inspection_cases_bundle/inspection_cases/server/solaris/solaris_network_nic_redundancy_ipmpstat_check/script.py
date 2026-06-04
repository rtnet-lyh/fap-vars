# -*- coding: utf-8 -*-

import re
from collections import defaultdict

from .common._base import BaseCheck


IPMPSTAT_INTERFACE_COMMAND = 'ipmpstat -i'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _normalize(self, value):
        return str(value or '').strip().lower()

    def _parse_ipmp_interfaces(self, output:str, min_members: int=2, min_active_members: int=1):
        # root@ct-ttms-18:~# ipmpstat -i
        # INTERFACE   ACTIVE  GROUP       FLAGS     LINK      PROBE     STATE
        # net9        no      ipmp0       is-----   up        disabled  ok
        # net6        yes     ipmp0       --mbM--   up        disabled  ok

        results = []

        for line in output.splitlines():
            line = line.strip()

            if not line or line.startswith("INTERFACE"):
                continue
            
            parts = re.split(r"\s+", line)

            if len(parts) < 7:
                continue
            
            results.append({
                "interface": parts[0],
                "active": parts[1],
                "group": parts[2],
                "flags": parts[3],
                "link": parts[4],
                "probe": parts[5],
                "state": parts[6],                
            })

        groups = defaultdict(list)

        for item in results:
            groups[item["group"]].append(item)
        
        judgement = []

        for group, members in groups.items():
            ok_members = [
                m for m in members
                if m["link"] == "up" and m["state"] == "ok"
            ]

            active_members = [
                m for m in members
                if m["active"] == "yes"                
            ]

            is_pass = (
                len(members) >= min_members and
                len(ok_members) >= len(members) and
                len(active_members) >= min_active_members 
            )

            judgement.append({
                "group": group,
                "member_count": len(members),
                "active_count": len(active_members),
                "is_pass": is_pass,
                "members": members,
            })

        return judgement

    def run(self):
        min_members = self.get_threshold_var('min_members', default=2, value_type='int')
        min_active_members = self.get_threshold_var('min_active_members', default=1, value_type='int')        
        thresholds = {
            "min_members": min_members,
            "min_active_members": min_active_members,
        }

        result = self._run_solaris_commands([
            {'command': IPMPSTAT_INTERFACE_COMMAND, 'timeout': 10},
        ], become_required=True)[0]

        rc = result['rc']
        out = result['stdout']
        err = result['stderr']

        text = (out or '').strip()

        parsed = self._parse_ipmp_interfaces(text, min_members, min_active_members)
        metrics = parsed

        ok_items = [item for item in parsed if item.get("is_pass")] 
        fail_items = [item for item in parsed if not item.get("is_pass")] 

        is_pass = True if ok_items and not fail_items else False

        if is_pass:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=f"NIC 이중화 상태가 정상 입니다. {ok_items}",
                message=f"NIC 이중화 상태가 정상 입니다. {ok_items}",
            )
        else:
            return self.fail(
                error='NIC 이중화 상태 점검 필요',
                reasons=f"NIC 이중화 상태 점검이 필요 합니다. {fail_items}",
                message=f"NIC 이중화 상태 점검이 필요 합니다. {fail_items}",
            )

CHECK_CLASS = Check
