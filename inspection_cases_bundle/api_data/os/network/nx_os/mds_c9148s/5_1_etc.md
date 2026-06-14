# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

nx_os

# application

mds_c9148s

# inspection_code

NETWORK-NXOS-MDS-C9148S-ENVIRONMENT-01

# is_required

권고

# inspection_name

전원, FAN 등 점검

# inspection_content

장비의 물리적인 하드웨어(전원, FAN, 라우팅엔진, 라인카드 등) 상태 점검

# inspection_command

```bash
show environment
```

# inspection_output

```text
CITS-SAN1# show environment
Power Supply:
Voltage: 12 Volts
-----------------------------------------------------
PS  Model                Power       Power     Status
                         (Watts)     (Amp)
-----------------------------------------------------
1   DS-C48S-300AC         300.00     25.00     Ok
2   DS-C48S-300AC         300.00     25.00     Ok


Mod Model                Power     Power       Power     Power       Status
                         Requested Requested   Allocated Allocated
                         (Watts)   (Amp)       (Watts)   (Amp)
--- -------------------  -------   ----------  --------- ----------  ----------
1    DS-C9148S-K9-SUP     150.00    12.50      150.00    12.50       Powered-Up


Power Usage Summary:
--------------------
Power Supply redundancy mode:                 Redundant
Power Supply redundancy operational mode:     Redundant

Total Power Capacity                              300.00 W

Total Power Allocated (budget)                    150.00 W
                                                -------------
Total Power Available                             150.00 W
                                                -------------
Clock:
----------------------------------------------------------
Clock           Model                Hw         Status
----------------------------------------------------------
A               Clock Module         --         NotSupported/None


Fan:
------------------------------------------------------
Fan             Model                Hw         Status
------------------------------------------------------
ChassisFan1     FAN Module 1         --         Ok
ChassisFan2     FAN Module 2         --         Ok
ChassisFan3     FAN Module 3         --         Ok
ChassisFan4     FAN Module 4         --         Ok
Fan_in_PS1      --                   --         Ok
Fan_in_PS2      --                   --         Ok
Fan Air Filter : NotSupported


Temperature:
--------------------------------------------------------------------
Module   Sensor        MajorThresh   MinorThres   CurTemp     Status
                       (Celsius)     (Celsius)    (Celsius)
--------------------------------------------------------------------
1        Outlet1  (s1)   75              60          34         Ok
1        Outlet2  (s2)   75              60          32         Ok
1        Intake1  (s3)   75              60          32         Ok
1        Intake2  (s4)   75              60          32         Ok
1        FC-SOC1  (s5)   115             105         40         Ok
```

# description

- 명령어: 장비의 물리적인 하드웨어 상태를 확인하는 명령어.
- 각 status 값의 비정상 키워드를 변수로 설정 or 하드코딩

[참고]
- Power Supply: 장착된 전원 공급 장치
- Power Usage Summary: 전원과 전력상태 요약
- Clock:하드웨어 클럭 모듈 상태
- Fan: 내부 냉각 FAN 동작 상태
- Temperature: 내부 온도 센서 상태
- 비정상키워드 목록: fail|faulty|warning|critical|major|minor|down|unknown

- **양호**: 비정상 키워드 미 탐지
- **경고**: 비정상 키워드 탐지
- **확인 필요**: 명령어 실패 및 파싱 실패

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show environment'
BAD_STATUSES = {'fail', 'failed', 'faulty', 'warning', 'critical', 'major', 'minor', 'down', 'unknown'}


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if not lines:
            return self.fail('환경 상태 파싱 실패', message='show environment 출력이 비어 있습니다.', stdout=(out or '').strip())

        bad = [line for line in lines if line.split()[-1].lower() in BAD_STATUSES]
        metrics = {'abnormal_status_count': len(bad), 'abnormal_status_lines': bad}
        if bad:
            return self.warn(metrics=metrics, thresholds={'abnormal_statuses': sorted(BAD_STATUSES)}, reasons='환경 상태에서 비정상 status가 탐지되었습니다.', message=f'환경 상태 비정상 항목 {len(bad)}건.')
        return self.ok(metrics=metrics, thresholds={'abnormal_statuses': sorted(BAD_STATUSES)}, reasons='환경 상태에서 비정상 status가 탐지되지 않았습니다.', message='환경 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
