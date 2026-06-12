# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

unix

# application

solaris

# inspection_code

SOL-REPLAY-OS-01

# is_required

# inspection_name

# inspection_content

# inspection_command

```bash

```

# inspection_output

```text

```

# description

# thresholds

[
    {id: null, key: "expected_stms_state", value: "ENABLED", sortOrder: 0}
,
{id: null, key: "expected_path_status", value: "CONNECTED", sortOrder: 1}
,
{id: null, key: "expected_path_state", value: "CONNECTED", sortOrder: 2}
,
{id: null, key: "disallowed_path_states", value: "DISABLED", sortOrder: 3}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 4}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

MPATHADM_SHOW_LU_COMMAND = 'mpathadm show lu'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False
    
    def _parse_logical_units(self, output: str, min_path_count: int, ok_state: str, ok_disabled: str):
        results = []
    #     Logical Unit:  /dev/rdsk/c0t5000CCA02F653D5Cd0s2
    #         mpath-support:  libmpscsi_vhci.so
    #         Vendor:  HGST
    #         Product:  H101860SFSUN600G
    #         Revision:  A990
    #         Name Type:  unknown type
    #         Name:  5000cca02f653d5c
    #         Asymmetric:  no
    #         Current Load Balance:  shortest-path
    #         Logical Unit Group ID:  NA
    #         Auto Failback:  on
    #         Auto Probing:  NA

    #         Paths:
    #                 Initiator Port Name:  500605b00e77b830
    #                 Target Port Name:  5000cca02f653d5d
    #                 Override Path:  NA
    #                 Path State:  OK
    #                 Disabled:  no

    #         Target Ports:
    #                 Name:  5000cca02f653d5d
    #                 Relative ID:  0

    # Logical Unit:  /dev/rdsk/c0t5000CCA07D594A30d0s2
    #         mpath-support:  libmpscsi_vhci.so
    #         Vendor:  HGST
    #         Product:  H101860SFSUN600G
    #         Revision:  A990
    #         Name Type:  unknown type
    #         Name:  5000cca07d594a30
    #         Asymmetric:  no
    #         Current Load Balance:  shortest-path
    #         Logical Unit Group ID:  NA
    #         Auto Failback:  on
    #         Auto Probing:  NA

    #         Paths:
    #                 Initiator Port Name:  500605b00e77b830
    #                 Target Port Name:  5000cca07d594a31
    #                 Override Path:  NA
    #                 Path State:  OK
    #                 Disabled:  no

    #         Target Ports:
    #                 Name:  5000cca07d594a31
    #                 Relative ID:  0

    # Logical Unit:  /dev/rdsk/c0t5000CCA02F6569A0d0s2
    #         mpath-support:  libmpscsi_vhci.so
    #         Vendor:  HGST
    #         Product:  H101860SFSUN600G
    #         Revision:  A990
    #         Name Type:  unknown type
    #         Name:  5000cca02f6569a0
    #         Asymmetric:  no
    #         Current Load Balance:  shortest-path
    #         Logical Unit Group ID:  NA
    #         Auto Failback:  on
    #         Auto Probing:  NA

    #         Paths:
    #                 Initiator Port Name:  500605b00e77b830
    #                 Target Port Name:  5000cca02f6569a1
    #                 Override Path:  NA
    #                 Path State:  OK
    #                 Disabled:  no

    #         Target Ports:
    #                 Name:  5000cca02f6569a1
    #                 Relative ID:  0

    # Logical Unit:  /dev/rdsk/c0t5000CCA07D598CA4d0s2
    #         mpath-support:  libmpscsi_vhci.so
    #         Vendor:  HGST
    #         Product:  H101860SFSUN600G
    #         Revision:  A990
    #         Name Type:  unknown type
    #         Name:  5000cca07d598ca4
    #         Asymmetric:  no
    #         Current Load Balance:  shortest-path
    #         Logical Unit Group ID:  NA
    #         Auto Failback:  on
    #         Auto Probing:  NA

    #         Paths:
    #                 Initiator Port Name:  500605b00e77b830
    #                 Target Port Name:  5000cca07d598ca5
    #                 Override Path:  NA
    #                 Path State:  OK
    #                 Disabled:  no

    #         Target Ports:
    #                 Name:  5000cca07d598ca5
    #                 Relative ID:  0

        blocks = re.split(r'(?=^Logical Unit:\s+)', output, flags=re.MULTILINE)

        for block in blocks:
            if not block.strip():
                continue

            lu_match = re.search('^Logical Unit:\s+(\S+)', block, re.MULTILINE)
            if not lu_match:
                continue

            lu_name = lu_match.group(1)

            path_blocks = re.findall(
                r'Initiator Port Name:\s+(\S+).*?'
                r'Target Port Name:\s+(\S+).*?'
                r'Path State:\s+(\S+).*?'
                r'Disabled:\s+(\S+)',
                block,
                flags=re.DOTALL
            )

            paths = []
            for idx, (initiator, target, state, disabled) in enumerate(path_blocks, start=1):
                paths.append({
                    "path_no": idx,
                    "initiator_port_name": initiator,
                    "target_port_name": target,
                    "path_state": state,
                    "disabled": disabled,
                    "is_ok": state == ok_state and disabled == ok_disabled
                })

            path_count = len(paths)

            results.append({
                "logical_unit": lu_name,
                "path_count": path_count,
                "is_multipath": path_count >= min_path_count,
                "is_ok": path_count >= min_path_count and all(p["is_ok"] for p in paths),
                "paths": paths
            })

        return results
            

    def run(self):
        min_path_count = self.get_threshold_var('min_path_count', default=1, value_type='int')
        ok_state = self.get_threshold_var('ok_state', default='OK', value_type='str')
        ok_disabled = self.get_threshold_var('ok_disabled', default='no', value_type='str')

        result = self._run_solaris_commands([
            {'command': MPATHADM_SHOW_LU_COMMAND, 'timeout': 5},
        ], become_required=True)[0]

        rc = result['rc']
        out = result['stdout']
        err = result['stderr']

        text = (out or '').strip()
       
        logical_units = self._parse_logical_units(text, min_path_count, ok_state, ok_disabled)

        ok_items = [item for item in logical_units if item.get("is_ok")]
        fail_items = [item for item in logical_units if not item.get("is_ok")]

        is_pass = True if ok_items and not fail_items else False

        metrics = logical_units
        thresholds = {
            'min_path_count': min_path_count,
            'ok_state': ok_state,
            'ok_disabled': ok_disabled,          
        }

        if is_pass:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=f"MultiPath 이중화 점검 성공. {ok_items}",
                message=f"MultiPath 이중화 점검 성공. {ok_items}",
            )

        else:
            return self.fail(
                error='Multipath 파싱 실패',
                metrics=metrics,
                thresholds=thresholds,
                reasons=f"MultiPath 이중화 점검 실패. {ok_items}",
                message=f"MultiPath 이중화 점검 실패. {fail_items}",
            )


       
       
        

CHECK_CLASS = Check
