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

SOL-REPLAY-NET-01

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
    {id: null, key: "required_state", value: "up", sortOrder: 0}
,
{id: null, key: "expected_speed_map", value: "e1000g0:1000,e1000g1:1000,e1000g2:1000", sortOrder: 1}
,
{id: null, key: "expected_duplex_map", value: "e1000g0:full,e1000g1:full,e1000g2:full", sortOrder: 2}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file", sortOrder: 3}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck


DLADM_SHOW_PHYS_COMMAND = 'dladm show-phys'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _split_csv_map(self, raw_value):
        mapping = {}
        for token in self._split_keywords(raw_value):
            if ':' not in token:
                continue
            key, value = token.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                mapping[key] = value
        return mapping

    def _parse_int(self, value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_show_phys_rows(self, output, ignore_link_pattern, required_state, min_speed_mb):
        # root@ct-ttms-18:~# dladm show-phys
        # LINK            MEDIA         STATE      SPEED  DUPLEX    DEVICE
        # net0            Ethernet      down       0      unknown   i40e0
        # net1            Ethernet      down       0      unknown   i40e1
        # net2            Ethernet      down       0      unknown   i40e2
        # net3            Ethernet      down       0      unknown   i40e3
        # net4            Ethernet      down       0      unknown   ixgbe0
        # net5            Ethernet      down       0      unknown   ixgbe1
        # net6            Ethernet      up         1000   full      igb0
        # net7            Ethernet      unknown    0      unknown   igb1
        # net8            Ethernet      unknown    0      unknown   igb2
        # net9            Ethernet      up         1000   full      igb3
        # net10           Ethernet      down       0      unknown   ixgbe2
        # net11           Ethernet      down       0      unknown   ixgbe3
        # sp-phys0        Ethernet      up         10     full      usbecm2
        ignore_link_pattern = rf"{ignore_link_pattern}"
        items = []

        for line in output.splitlines():
            line = line.strip()

            if not line or line.startswith("LINK"):
                continue

            parts = re.split(r"\s+", line)

            if len(parts) < 6:
                continue

            speed = int(parts[3])
            link = parts[0]
            is_ignore = True if re.search(ignore_link_pattern, link) else False
                
            if speed > 0:
                items.append({
                    "link": link,
                    "media": parts[1],
                    "state": parts[2],
                    "speed": speed,
                    "duplex": parts[4],
                    "device": parts[5],
                    "is_up": parts[2] == required_state,
                    "is_ignore": is_ignore,
                    "is_min_speed": speed >= min_speed_mb,
                })

        return items

    def _build_link_summary(self, rows, limit=3):
        if not rows:
            return '링크 요약 없음'

        parts = []
        for row in rows[:limit]:
            speed_value = row['speed_mbps'] if row['speed_mbps'] is not None else 'N/A'
            parts.append(
                f"{row['link_name']} state={row['state']}, speed={speed_value}, duplex={row['duplex']}"
            )
        if len(rows) > limit:
            parts.append(f'외 {len(rows) - limit}건')
        return ', '.join(parts)

    def run(self):
        required_state = self.get_threshold_var('required_state', default='up', value_type='str').strip().lower()
        min_speed_mb = self.get_threshold_var('min_speed_mb', default=1000, value_type='int')
        ignore_link_pattern = self.get_threshold_var('ignore_link_pattern', default='phys', value_type='raw')
        
        result = self._run_solaris_commands([
            {'command': DLADM_SHOW_PHYS_COMMAND, 'timeout': 10},
        ], become_required=True)[0]

        rc = result['rc']
        out = result['stdout']
        err = result['stderr']

        output = (out or '').strip()
        
        parsed = self._parse_show_phys_rows(output, ignore_link_pattern, required_state, min_speed_mb)
        metrics = parsed
        
        ok_items = []
        fail_items = []
        for item in parsed:
            if not item.get("is_ignore"):
                if item.get("is_up") and item.get("is_min_speed"):
                    ok_items.append(item)
                else: 
                    fail_items.append(item)

        is_pass = True if ok_items and not fail_items else False

        if is_pass:
            return self.ok(                
                metrics = metrics,
                reasons = f"네트워크 링크 상태 점검 성공. {ok_items}",
                message = f"네트워크 링크 상태 점검 성공. {ok_items}",
            )
        else:
            return self.fail(
                error = "네트워크 링크 상태 점검 실패",
                metrics = metrics,
                reasons = f"네트워크 링크 상태 점검 실패. {fail_items}",
                message = f"네트워크 링크 상태 점검 실패. {fail_items}",
            )

CHECK_CLASS = Check
