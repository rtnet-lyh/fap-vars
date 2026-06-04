# -*- coding: utf-8 -*-
from .common._base import BaseCheck
import traceback

COMMAND = ("show processes cpu")

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):        
        
        rc, out, err = self._ssh(COMMAND)
        
        return self.ok(
            metrics={},
            thresholds={},
            reasons="",
            message="",
        )        
            
CHECK_CLASS = Check