# -*- coding: utf-8 -*-

from .common._base import BaseCheck


CHECK_BASE_COMMAND = 'ndd -get /dev/tcp'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _judge(self, value, operator, threshold):
        if operator == ">":
            return value > threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "<":
            return value < threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "!=":
            return value != threshold
        else:
            raise ValueError(f"지원하지 않는 operator: {operator}")

    def run(self):
        metrics = {}
        threshold_list_map = self.get_threshold_list_map()

        if not threshold_list_map:
            threshold_list_map["tcp_time_wait_interval"] = "<=,60000"
            threshold_list_map["tcp_conn_req_max_q"] = ">=,128"
            threshold_list_map["tcp_conn_req_max_q0"] = ">=,1024"
            threshold_list_map["tcp_keepalive_interval"] = "<=,7200000"
            threshold_list_map["tcp_fin_wait_2_flush_interval"] = "<=,67500"
            threshold_list_map["tcp_smallest_anon_port"] = ">=,32768"
            threshold_list_map["tcp_largest_anon_port"] = ">=,65535"

        parameters = []
        for value, condition in threshold_list_map.items():
            operator, threshold = condition.split(",")
            threshold = int(threshold)
            parameters.append({
                "command": f"{CHECK_BASE_COMMAND} {value}",
                "operator": operator,
                "threshold": threshold,
                "timeout": 1
            })

        results = self._run_solaris_commands(
            parameters, 
            become_required=True)

        merged = [
            {**parameter, **result}
            for parameter, result in zip(parameters, results)
        ]

        merged_results = []
        for item in merged:
            ndd_result = {}
            command = item["command"]
            value = int(item["stdout"])
            operator = item["operator"]
            threshold = item["threshold"]

            ndd_result["command"] = command 
            ndd_result["value"] = value
            ndd_result["operator"] = operator
            ndd_result["threshold"] = threshold
            ndd_result["is_pass"] = self._judge(value, operator, threshold)

            merged_results.append(ndd_result)

        ok_items = [item for item in merged_results if item.get("is_pass")]
        fail_items = [item for item in merged_results if not item.get("is_pass")]
        
        is_pass = True if ok_items and not fail_items else False
        
        metrics["ok_items"] = ok_items
        metrics["fail_items"] = fail_items
        metrics["is_pass"] = is_pass
        metrics["thresholds"] = threshold_list_map

        if is_pass:
            return self.ok(
                metrics=metrics,
                thresholds=threshold_list_map,
                reasons=f"주요 커널파라미터가 임계치 기준을 통과 하였습니다.",
                message=f"주요 커널파라미터가 임계치 기준을 통과 하였습니다.",
            )
        
        else:
            return self.fail(
                error="커널파라미터 점검실패",
                metrics=metrics,
                thresholds=threshold_list_map,
                reasons=f"주요 커널파라미터가 임계치 값을 충족하지 못했습니다. fail_items: {fail_items}",
                message=f"주요 커널파라미터가 임계치 값을 충족하지 못했습니다. fail_items: {fail_items}",
            )

CHECK_CLASS = Check
