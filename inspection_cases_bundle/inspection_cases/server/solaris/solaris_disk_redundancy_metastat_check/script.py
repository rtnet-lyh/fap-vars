# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck


CHECK_COMMAND1 = 'zpool status'
CHECK_COMMAND2 = 'zpool status -x'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        try:
            ok_keyword = self.get_threshold_var('ok_keyword', default='all pools are healthy', value_type='str')        
            metrics = {}

            result = self._run_solaris_commands([
                {'command': CHECK_COMMAND1, 'timeout': 1},
                {'command': CHECK_COMMAND2, 'timeout': 1},
            ], become_required=True)

            result_check_command1 = result[-2]
            result_check_command2 = result[-1]
            
            rc = result_check_command1['rc']
            out = result_check_command1['stdout']
            err = result_check_command1['stderr']        
            metrics["zpool_status_output"] = out

            rc = result_check_command2['rc']
            out = result_check_command2['stdout']
            err = result_check_command2['stderr']          
            metrics["zpool_healthy_output"] = out

            is_pass = True if re.search(ok_keyword, out) else False
            metrics["is_pass"] = is_pass
            
            if is_pass:
                return self.ok(
                    metrics=metrics,
                    thresholds={'ok_keyword': ok_keyword},
                    reasons=f"디스크 이중화가 정상 입니다. {CHECK_COMMAND2} 결과에 {ok_keyword}가 발견되었습니다.",
                    message=f"디스크 이중화가 정상 입니다. {CHECK_COMMAND2} 결과에 {ok_keyword}가 발견되었습니다.",
                )
            else:
                return self.fail(
                    error=f"디스크 이중화가 비정상 입니다.",
                    metrics=metrics,
                    thresholds={'ok_keyword': ok_keyword},
                    reasons=f"디스크 이중화 점검이 필요합니다. {CHECK_COMMAND2} 결과에 {ok_keyword}가 발견되지 않았습니다.",
                    message=f"디스크 이중화 점검이 필요합니다. {CHECK_COMMAND2} 결과에 {ok_keyword}가 발견되지 않았습니다.",
                )
        except Exception as e:
            return self.fail(
                error=str(e),
                reasons=str(e),
                message=str(e),
            )

CHECK_CLASS = Check
