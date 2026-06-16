# -*- coding: utf-8 -*-
from .common._base import BaseCheck

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    
    def parse_output(self, output):
        # TO DO: CPU_사용률 추출
        return {
            "CPU_사용률": 90
        }

    def evaluate(self, metrics, threshold):
        CPU_사용률 = metrics["CPU_사용률"]
        # support return value: ok(정상), warn(경고), fail(불량), excluded(제외)
        if CPU_사용률 >= threshold:
            return "fail"
        elif CPU_사용률 >= threshold-10:
            return "warn"
        elif CPU_사용률 < threshold-10:
            return "ok"
        else:
            return "fail"
        
    def build_result(self, metrics, threshold, status):
        CPU_사용률 = metrics["CPU_사용률"]

        result = {}
        result["message"] = None 
        result["results"] = f"CPU 사용률 {CPU_사용률}"                    
        result["criteria"] = f"정상: {threshold-10}% 미만 / 불량: {threshold}% 이상 / 경고: {threshold-10}% 이상"
        
        if status == "ok":
            result["message"] = "CPU 사용률 정상"
        elif status == "warn":
            result["message"] = "CPU 사용률 경고"            
        elif status == "fail":
            result["message"] = "CPU 사용률 불량"
        
        return result

    def run(self):     
        최대_CPU_사용률 = self.get_threshold_var("최대_CPU_사용률", default=80, value_type='int')   

        results = self._run_paramiko_commands('whoami', become=True)
        output = results[-1]['stdout']

        metrics = self.parse_output(output)
        status = self.evaluate(metrics, 최대_CPU_사용률)
        result = self.build_result(metrics, 최대_CPU_사용률, status)

        return self.result(
            status=status,
            message=result["message"],
            metrics=metrics,
            results=result["results"],
            criteria=result["criteria"],
        )

CHECK_CLASS = Check
