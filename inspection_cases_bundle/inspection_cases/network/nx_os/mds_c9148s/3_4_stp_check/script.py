# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False

    def run(self):
        return self.ok(
            metrics={'applicable': False},
            thresholds={},
            reasons='해당 장비는 Ethernet STP 점검 대상이 아닙니다.',
            message='점검 대상이 아닙니다.',
        )


CHECK_CLASS = Check
