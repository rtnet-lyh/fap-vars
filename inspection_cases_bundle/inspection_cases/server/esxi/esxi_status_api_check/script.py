# -*- coding: utf-8 -*-

import html
import os
import xml.etree.ElementTree as ET

from .common._base import BaseCheck


SOAP_PATH = '/sdk'


class Check(BaseCheck):
    USE_HOST_CONNECTION = False
    APPLICATION_TYPE = 'ESXI'

    def _thresholds(self):
        return {
            'max_cpu_usage_percent': self.get_threshold_var(
                'max_cpu_usage_percent',
                default=80.0,
                value_type='float',
            ),
            'max_memory_usage_percent': self.get_threshold_var(
                'max_memory_usage_percent',
                default=80.0,
                value_type='float',
            ),
            'expected_power_state': self.get_threshold_var(
                'expected_power_state',
                default='poweredOn',
                value_type='str',
            ),
            'expected_connection_state': self.get_threshold_var(
                'expected_connection_state',
                default='connected',
                value_type='str',
            ),
        }

    def _local_name(self, tag):
        return str(tag).rsplit('}', 1)[-1]

    def _find_child(self, parent, name):
        if parent is None:
            return None
        for child in list(parent):
            if self._local_name(child.tag) == name:
                return child
        return None

    def _find_text(self, parent, path, default=None):
        node = parent
        for name in path:
            node = self._find_child(node, name)
            if node is None:
                return default
        return (node.text or '').strip() if node.text is not None else default

    def _parse_xml(self, text, label):
        try:
            return ET.fromstring(text or '')
        except Exception as exc:
            raise ValueError('%s XML 파싱 실패: %s' % (label, exc))

    def _find_service_content(self, root):
        for elem in root.iter():
            if self._local_name(elem.tag) == 'returnval' and self._find_child(elem, 'about') is not None:
                return elem
        raise ValueError('RetrieveServiceContent 응답에서 returnval을 찾지 못했습니다.')

    def _find_host_summary(self, root):
        for elem in root.iter():
            if (
                self._find_child(elem, 'hardware') is not None and
                self._find_child(elem, 'runtime') is not None and
                self._find_child(elem, 'quickStats') is not None
            ):
                return elem
        raise ValueError('HostSystem summary 응답에서 HostListSummary를 찾지 못했습니다.')

    def _parse_int(self, value, field_name):
        try:
            return int(str(value).strip())
        except Exception:
            raise ValueError('%s 값을 정수로 해석할 수 없습니다: %s' % (field_name, value))

    def _request_timeout(self):
        return self.get_threshold_var('request_timeout_sec', default=15, value_type='int')

    def _soap_headers(self, api_version=None):
        soap_action = 'urn:vim25'
        if api_version:
            soap_action = '%s/%s' % (soap_action, api_version)
        return {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': soap_action,
        }

    def _soap_request(self, xml_text, cookie_jar, api_version=None, label='SOAP'):
        response = self._request(
            SOAP_PATH,
            method='POST',
            data=xml_text.encode('utf-8'),
            headers=self._soap_headers(api_version=api_version),
            cookie_jar=cookie_jar,
            timeout=self._request_timeout(),
        )
        status = response.get('status')
        body = response.get('body') or ''
        if not response.get('ok') or status != 200:
            message = '%s 요청 실패: HTTP status=%s, error=%s' % (
                label,
                status,
                response.get('error') or '',
            )
            raise RuntimeError(message)
        if '<Fault' in body or ':Fault' in body:
            raise RuntimeError('%s SOAP Fault 응답을 수신했습니다.' % label)
        return body

    def _retrieve_service_content_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Body>
    <RetrieveServiceContent xmlns="urn:vim25">
      <_this type="ServiceInstance" xsi:type="ManagedObjectReference">ServiceInstance</_this>
    </RetrieveServiceContent>
  </soapenv:Body>
</soapenv:Envelope>'''

    def _login_xml(self, session_manager_moid, username, password):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Body>
    <Login xmlns="urn:vim25">
      <_this type="SessionManager" xsi:type="ManagedObjectReference">{session_manager_moid}</_this>
      <userName>{username}</userName>
      <password>{password}</password>
      <locale>en_US</locale>
    </Login>
  </soapenv:Body>
</soapenv:Envelope>'''.format(
            session_manager_moid=html.escape(session_manager_moid or ''),
            username=html.escape(username or ''),
            password=html.escape(password or ''),
        )

    def _host_summary_xml(self, property_collector_moid, host_moid):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Body>
    <RetrievePropertiesEx xmlns="urn:vim25">
      <_this type="PropertyCollector" xsi:type="ManagedObjectReference">{property_collector_moid}</_this>
      <specSet>
        <propSet>
          <type>HostSystem</type>
          <pathSet>summary</pathSet>
        </propSet>
        <objectSet>
          <obj type="HostSystem" xsi:type="ManagedObjectReference">{host_moid}</obj>
        </objectSet>
      </specSet>
      <options/>
    </RetrievePropertiesEx>
  </soapenv:Body>
</soapenv:Envelope>'''.format(
            property_collector_moid=html.escape(property_collector_moid or ''),
            host_moid=html.escape(host_moid or ''),
        )

    def _read_replay_summary_xml(self):
        inline_xml = self._get_source_value('replay_summary_xml', default='')
        if inline_xml:
            return str(inline_xml)

        rel_path = self._get_source_value('replay_summary_xml_file', default='')
        if not rel_path:
            return ''

        base_dir = self._get_source_value('replay_base_dir', default='')
        candidates = []
        if base_dir:
            candidates.append(os.path.join(str(base_dir), str(rel_path)))
        candidates.append(str(rel_path))
        candidates.append(os.path.join(os.getcwd(), str(rel_path)))

        for path in candidates:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    return fh.read()
        raise RuntimeError('replay_summary_xml_file을 찾지 못했습니다: %s' % rel_path)

    def _load_summary_xml(self):
        replay_xml = self._read_replay_summary_xml()
        if replay_xml:
            return replay_xml, {
                'api_version': self._get_source_value('api_version', default='8.0.3.0'),
                'source': 'replay',
            }

        username = self._get_source_value(
            'username',
            'login_username',
            default=self.get_application_credential_value('username'),
        )
        password = self._get_source_value(
            'password',
            'login_password',
            default=self.get_application_credential_value('password'),
        )
        if not username or not password:
            raise RuntimeError('ESXi API 인증 정보가 없습니다.')

        cookie_jar = self._new_cookie_jar()
        service_xml = self._soap_request(
            self._retrieve_service_content_xml(),
            cookie_jar,
            label='RetrieveServiceContent',
        )
        service_content = self._find_service_content(self._parse_xml(service_xml, 'RetrieveServiceContent'))
        api_version = self._find_text(service_content, ['about', 'apiVersion'], default='')
        session_manager_moid = self._find_text(service_content, ['sessionManager'], default='')
        property_collector_moid = self._find_text(service_content, ['propertyCollector'], default='')

        if not api_version or not session_manager_moid or not property_collector_moid:
            raise RuntimeError('ESXi ServiceContent에서 필수 관리 객체 정보를 찾지 못했습니다.')

        self._soap_request(
            self._login_xml(session_manager_moid, username, password),
            cookie_jar,
            api_version=api_version,
            label='Login',
        )

        host_moid = self._get_source_value('host_moid', default='ha-host') or 'ha-host'
        summary_xml = self._soap_request(
            self._host_summary_xml(property_collector_moid, host_moid),
            cookie_jar,
            api_version=api_version,
            label='RetrievePropertiesEx',
        )
        return summary_xml, {
            'api_version': api_version,
            'host_moid': host_moid,
            'source': 'api',
        }

    def _metrics_from_summary_xml(self, summary_xml, metadata):
        summary = self._find_host_summary(self._parse_xml(summary_xml, 'HostSystem summary'))

        cpu_usage_mhz = self._parse_int(
            self._find_text(summary, ['quickStats', 'overallCpuUsage']),
            'quickStats.overallCpuUsage',
        )
        cpu_mhz = self._parse_int(
            self._find_text(summary, ['hardware', 'cpuMhz']),
            'hardware.cpuMhz',
        )
        num_cpu_cores = self._parse_int(
            self._find_text(summary, ['hardware', 'numCpuCores']),
            'hardware.numCpuCores',
        )
        memory_usage_mib = self._parse_int(
            self._find_text(summary, ['quickStats', 'overallMemoryUsage']),
            'quickStats.overallMemoryUsage',
        )
        memory_total_bytes = self._parse_int(
            self._find_text(summary, ['hardware', 'memorySize']),
            'hardware.memorySize',
        )

        cpu_capacity_mhz = cpu_mhz * num_cpu_cores
        memory_total_mib = int(round(memory_total_bytes / 1024.0 / 1024.0))
        if cpu_capacity_mhz <= 0:
            raise ValueError('CPU 전체 용량을 계산할 수 없습니다.')
        if memory_total_mib <= 0:
            raise ValueError('메모리 전체 용량을 계산할 수 없습니다.')

        return {
            'name': self._find_text(summary, ['config', 'name'], default=''),
            'full_name': self._find_text(summary, ['config', 'product', 'fullName'], default=''),
            'version': self._find_text(summary, ['config', 'product', 'version'], default=''),
            'build': self._find_text(summary, ['config', 'product', 'build'], default=''),
            'api_version': metadata.get('api_version') or self._find_text(summary, ['config', 'product', 'apiVersion'], default=''),
            'uuid': self._find_text(summary, ['hardware', 'uuid'], default=''),
            'vendor': self._find_text(summary, ['hardware', 'vendor'], default=''),
            'model': self._find_text(summary, ['hardware', 'model'], default=''),
            'cpu_model': self._find_text(summary, ['hardware', 'cpuModel'], default=''),
            'cpu_usage_mhz': cpu_usage_mhz,
            'cpu_capacity_mhz': cpu_capacity_mhz,
            'cpu_usage_percent': round((cpu_usage_mhz / float(cpu_capacity_mhz)) * 100.0, 2),
            'memory_usage_mib': memory_usage_mib,
            'memory_total_mib': memory_total_mib,
            'memory_usage_percent': round((memory_usage_mib / float(memory_total_mib)) * 100.0, 2),
            'power_state': self._find_text(summary, ['runtime', 'powerState'], default=''),
            'connection_state': self._find_text(summary, ['runtime', 'connectionState'], default=''),
            'overall_status': self._find_text(summary, ['overallStatus'], default=''),
            'source': metadata.get('source', ''),
        }

    def _raw_output(self, metrics):
        return (
            'ESXi HostSystem.summary API 조회 결과: '
            'name={name}, api_version={api_version}, '
            'cpu_usage_percent={cpu_usage_percent}%, '
            'memory_usage_percent={memory_usage_percent}%, '
            'power_state={power_state}, '
            'connection_state={connection_state}, '
            'overall_status={overall_status}'
        ).format(**metrics)

    def _policy_fail(self, message, metrics, thresholds, failed_items):
        result = self.fail(
            'ESXi 상태 기준 미충족',
            message=message,
            raw_output=self._raw_output(metrics),
        )
        result['metrics'] = metrics
        result['thresholds'] = thresholds
        result['reasons'] = ', '.join(failed_items)
        return result

    def run(self):
        thresholds = self._thresholds()

        try:
            summary_xml, metadata = self._load_summary_xml()
            metrics = self._metrics_from_summary_xml(summary_xml, metadata)
        except Exception as exc:
            return self.fail(
                'ESXi API 점검 실패',
                message=str(exc),
                raw_output='ESXi API 점검을 완료하지 못했습니다.',
            )

        failed_items = []
        if metrics['cpu_usage_percent'] > thresholds['max_cpu_usage_percent']:
            failed_items.append(
                'CPU Usage %.2f%% > %.2f%%' % (
                    metrics['cpu_usage_percent'],
                    thresholds['max_cpu_usage_percent'],
                )
            )
        if metrics['memory_usage_percent'] > thresholds['max_memory_usage_percent']:
            failed_items.append(
                'Memory Usage %.2f%% > %.2f%%' % (
                    metrics['memory_usage_percent'],
                    thresholds['max_memory_usage_percent'],
                )
            )
        if metrics['power_state'] != thresholds['expected_power_state']:
            failed_items.append(
                'Power State %s != %s' % (
                    metrics['power_state'],
                    thresholds['expected_power_state'],
                )
            )
        if metrics['connection_state'] != thresholds['expected_connection_state']:
            failed_items.append(
                'Connection State %s != %s' % (
                    metrics['connection_state'],
                    thresholds['expected_connection_state'],
                )
            )

        if failed_items:
            return self._policy_fail(
                'ESXi 상태 기준을 충족하지 못했습니다: %s' % ', '.join(failed_items),
                metrics,
                thresholds,
                failed_items,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                'CPU/Memory 사용률이 기준 이하이고 Power/Connection 상태가 정상입니다.'
            ),
            raw_output=self._raw_output(metrics),
            message=(
                'ESXi 상태 확인 점검이 정상 수행되었습니다. '
                'CPU Usage %.2f%%, Memory Usage %.2f%%, Power State %s, Connection State %s.'
                % (
                    metrics['cpu_usage_percent'],
                    metrics['memory_usage_percent'],
                    metrics['power_state'],
                    metrics['connection_state'],
                )
            ),
        )


CHECK_CLASS = Check
