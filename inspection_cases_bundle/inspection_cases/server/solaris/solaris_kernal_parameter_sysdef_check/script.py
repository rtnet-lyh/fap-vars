# -*- coding: utf-8 -*-

from .common._base import BaseCheck

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def run(self):
        return self.warn(
            '수동점검 대상',
            message='자동 점검이 어려운 항목입니다. 기준서에 따라 커널 파라미터를 수동 확인하세요.',
            reasons='점검 스크립트로 자동 판정이 어려워 수동 확인이 필요합니다.',
        )

CHECK_CLASS = Check
