# -*- coding: utf-8 -*-

import json
import os
import ssl
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


class VMwareHelper(object):
    """pyVmomi 기반 VMware API 헬퍼.

    ESXi 단독 호스트와 vCenter 모두 vSphere API 모델을 공유하므로 공통
    inventory 탐색과 summary 직렬화를 이곳에 모은다. pyVmomi는 선택
    의존성으로 두고, import 실패 시 호출자가 fallback을 결정한다.
    """

    def __init__(self, check):
        self.check = check

    def _source_value(self, *keys, **kwargs):
        return self.check._get_source_value(*keys, **kwargs)

    def _threshold_value(self, key, default=None, value_type=None):
        return self.check.get_threshold_var(key, default=default, value_type=value_type)

    def _load_sdk(self):
        try:
            from pyVim.connect import Disconnect, SmartConnect
            try:
                from pyVim.connect import SmartConnectNoSSL
            except Exception:
                SmartConnectNoSSL = None
            from pyVmomi import vim
        except Exception as exc:
            raise RuntimeError('pyVmomi를 사용할 수 없습니다: %s' % exc)
        return SmartConnect, SmartConnectNoSSL, Disconnect, vim

    def _parse_host_port(self, value, default_port):
        text = str(value or '').strip()
        if not text:
            return '', int(default_port or 443)

        parsed = urlparse(text if '://' in text else '//%s' % text)
        host = parsed.hostname or text.split('/')[0].split(':')[0]
        port = parsed.port or default_port or 443
        return host, int(port)

    def connection_params(self):
        endpoint = self._source_value('target_url', 'service_url', 'url', 'base_url', 'endpoint', default='')
        host_value = endpoint or self._source_value('hostname', 'domain', 'host', default=self.check.ctx.get('host') or '')
        default_port = self._source_value('web_port', 'port', default=self.check.ctx.get('port') or 443)
        host, port = self._parse_host_port(host_value, default_port)

        username = self._source_value(
            'username',
            'login_username',
            'user',
            default=self.check.get_application_credential_value('username'),
        )
        password = self._source_value(
            'password',
            'login_password',
            default=self.check.get_application_credential_value('password'),
        )

        return {
            'host': host,
            'port': int(port or 443),
            'username': username or '',
            'password': password or '',
            'disable_ssl_verification': self._source_value('disable_ssl_verification', default='true'),
        }

    def connect(self):
        SmartConnect, SmartConnectNoSSL, Disconnect, _vim = self._load_sdk()
        params = self.connection_params()
        if not params['host']:
            raise RuntimeError('VMware API 대상 host가 없습니다.')
        if not params['username'] or not params['password']:
            raise RuntimeError('VMware API 인증 정보가 없습니다.')

        disable_ssl = str(params.get('disable_ssl_verification', 'true')).strip().lower() in (
            '1',
            'true',
            'y',
            'yes',
            'on',
        )
        if disable_ssl and SmartConnectNoSSL is not None:
            service_instance = SmartConnectNoSSL(
                host=params['host'],
                user=params['username'],
                pwd=params['password'],
                port=params['port'],
            )
        elif disable_ssl:
            service_instance = SmartConnect(
                host=params['host'],
                user=params['username'],
                pwd=params['password'],
                port=params['port'],
                sslContext=ssl._create_unverified_context(),
            )
        else:
            service_instance = SmartConnect(
                host=params['host'],
                user=params['username'],
                pwd=params['password'],
                port=params['port'],
            )
        return service_instance, Disconnect

    def _container_view(self, service_instance, vim_type):
        content = service_instance.RetrieveContent()
        return content.viewManager.CreateContainerView(content.rootFolder, [vim_type], True)

    def iter_objects(self, service_instance, vim_type):
        view = self._container_view(service_instance, vim_type)
        try:
            for item in list(view.view):
                yield item
        finally:
            view.Destroy()

    def list_hosts(self, service_instance):
        _SmartConnect, _SmartConnectNoSSL, _Disconnect, vim = self._load_sdk()
        return list(self.iter_objects(service_instance, vim.HostSystem))

    def list_vms(self, service_instance):
        _SmartConnect, _SmartConnectNoSSL, _Disconnect, vim = self._load_sdk()
        return list(self.iter_objects(service_instance, vim.VirtualMachine))

    def list_datastores(self, service_instance):
        _SmartConnect, _SmartConnectNoSSL, _Disconnect, vim = self._load_sdk()
        return list(self.iter_objects(service_instance, vim.Datastore))

    def select_host(self, service_instance, host_moid=None, host_name=None):
        hosts = self.list_hosts(service_instance)
        if not hosts:
            raise RuntimeError('HostSystem 객체를 찾지 못했습니다.')

        host_moid = str(host_moid or '').strip()
        host_name = str(host_name or '').strip()

        if host_moid:
            for host in hosts:
                if str(getattr(host, '_moId', '') or '') == host_moid:
                    return host

        if host_name:
            for host in hosts:
                summary_config = getattr(getattr(host, 'summary', None), 'config', None)
                names = {
                    str(getattr(host, 'name', '') or ''),
                    str(getattr(summary_config, 'name', '') or ''),
                }
                if host_name in names:
                    return host

        if len(hosts) == 1:
            return hosts[0]

        raise RuntimeError('대상 HostSystem을 특정하지 못했습니다. host_moid 또는 host_name을 지정해야 합니다.')

    def _safe_text(self, value, default=''):
        if value is None:
            return default
        return str(value)

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def _safe_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in ('1', 'true', 'y', 'yes', 'on'):
            return True
        if text in ('0', 'false', 'n', 'no', 'off'):
            return False
        return default

    def _xml_local_name(self, tag):
        return str(tag).rsplit('}', 1)[-1]

    def _xml_child(self, parent, name):
        for child in list(parent or []):
            if self._xml_local_name(child.tag) == name:
                return child
        return None

    def _xml_text(self, parent, *path):
        node = parent
        for name in path:
            node = self._xml_child(node, name)
            if node is None:
                return ''
        return (node.text or '').strip()

    def _xml_int(self, parent, field_name, *path):
        value = self._xml_text(parent, *path)
        try:
            return int(str(value).strip())
        except Exception:
            raise ValueError('%s 값을 정수로 해석할 수 없습니다: %s' % (field_name, value))

    def _should_use_output_fixture(self):
        password = self._source_value(
            'password',
            'login_password',
            default=self.check.get_application_credential_value('password'),
        )
        force_replay = self._threshold_value('force_replay', default=False, value_type='bool')
        return (not password) or bool(force_replay)

    def _fixture_path_candidates(self, rel_path):
        base_dir = self._source_value('replay_base_dir', 'output_base_dir', default='')
        candidates = []
        if base_dir:
            candidates.append(os.path.join(str(base_dir), str(rel_path)))
        candidates.append(str(rel_path))
        candidates.append(os.path.join(os.getcwd(), str(rel_path)))
        return candidates

    def _read_fixture_file(self, rel_path, description):
        for path in self._fixture_path_candidates(rel_path):
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    return fh.read()
        raise RuntimeError('%s 파일을 찾지 못했습니다: %s' % (description, rel_path))

    def _read_output_fixture_xml(self):
        if not self._should_use_output_fixture():
            return ''

        inline_xml = self._source_value('replay_summary_xml', 'output_summary_xml', default='')
        if inline_xml:
            return str(inline_xml)

        rel_path = self._source_value('replay_summary_xml_file', 'output_summary_xml_file', default='')
        if not rel_path:
            return ''

        return self._read_fixture_file(rel_path, 'output summary XML')

    def _read_output_fixture_json(self, inline_keys=None, file_keys=None):
        if not self._should_use_output_fixture():
            return None

        inline_keys = list(inline_keys or []) + ['replay_json', 'output_json']
        file_keys = list(file_keys or []) + ['replay_json_file', 'output_json_file']

        for key in inline_keys:
            value = self._source_value(key, default='')
            if value in (None, ''):
                continue
            if isinstance(value, dict):
                return dict(value)
            try:
                decoded = json.loads(str(value))
            except Exception as exc:
                raise ValueError('output JSON 파싱 실패(%s): %s' % (key, exc))
            if not isinstance(decoded, dict):
                raise ValueError('output JSON은 object 형식이어야 합니다: %s' % key)
            return decoded

        for key in file_keys:
            rel_path = self._source_value(key, default='')
            if not rel_path:
                continue
            text = self._read_fixture_file(rel_path, 'output JSON')
            try:
                decoded = json.loads(text)
            except Exception as exc:
                raise ValueError('output JSON 파일 파싱 실패(%s): %s' % (rel_path, exc))
            if not isinstance(decoded, dict):
                raise ValueError('output JSON 파일은 object 형식이어야 합니다: %s' % rel_path)
            return decoded

        return None

    def _fixture_metrics(self, data, collection_key=None, count_key=None):
        copied = dict(data or {})
        copied['source'] = 'output'
        if collection_key and count_key and count_key not in copied:
            collection = copied.get(collection_key) or []
            copied[count_key] = len(collection) if isinstance(collection, list) else 0
        return copied

    def _summary_from_output_xml(self, text):
        try:
            root = ET.fromstring(text or '')
        except Exception as exc:
            raise ValueError('output HostSystem summary XML 파싱 실패: %s' % exc)

        for elem in root.iter():
            if self._xml_child(elem, 'hardware') is not None and self._xml_child(elem, 'quickStats') is not None:
                return elem
        raise ValueError('output XML에서 HostSystem summary를 찾지 못했습니다.')

    def host_summary_metrics_from_xml(self, text, source='output'):
        summary = self._summary_from_output_xml(text)
        cpu_usage_mhz = self._xml_int(summary, 'overallCpuUsage', 'quickStats', 'overallCpuUsage')
        cpu_mhz = self._xml_int(summary, 'cpuMhz', 'hardware', 'cpuMhz')
        cpu_cores = self._xml_int(summary, 'numCpuCores', 'hardware', 'numCpuCores')
        memory_usage_mib = self._xml_int(summary, 'overallMemoryUsage', 'quickStats', 'overallMemoryUsage')
        memory_size_bytes = self._xml_int(summary, 'memorySize', 'hardware', 'memorySize')

        cpu_capacity_mhz = cpu_mhz * cpu_cores
        memory_total_mib = int(round(memory_size_bytes / 1024.0 / 1024.0))
        if cpu_capacity_mhz <= 0:
            raise RuntimeError('CPU 전체 용량을 계산할 수 없습니다.')
        if memory_total_mib <= 0:
            raise RuntimeError('메모리 전체 용량을 계산할 수 없습니다.')

        return {
            'name': self._xml_text(summary, 'config', 'name'),
            'full_name': self._xml_text(summary, 'config', 'product', 'fullName'),
            'version': self._xml_text(summary, 'config', 'product', 'version'),
            'build': self._xml_text(summary, 'config', 'product', 'build'),
            'api_version': self._xml_text(summary, 'config', 'product', 'apiVersion') or self._source_value('api_version', default=''),
            'uuid': self._xml_text(summary, 'hardware', 'uuid'),
            'vendor': self._xml_text(summary, 'hardware', 'vendor'),
            'model': self._xml_text(summary, 'hardware', 'model'),
            'cpu_model': self._xml_text(summary, 'hardware', 'cpuModel'),
            'cpu_usage_mhz': cpu_usage_mhz,
            'cpu_capacity_mhz': cpu_capacity_mhz,
            'cpu_usage_percent': round((cpu_usage_mhz / float(cpu_capacity_mhz)) * 100.0, 2),
            'memory_usage_mib': memory_usage_mib,
            'memory_total_mib': memory_total_mib,
            'memory_usage_percent': round((memory_usage_mib / float(memory_total_mib)) * 100.0, 2),
            'power_state': self._xml_text(summary, 'runtime', 'powerState'),
            'connection_state': self._xml_text(summary, 'runtime', 'connectionState'),
            'overall_status': self._xml_text(summary, 'overallStatus'),
            'source': source,
        }

    def host_summary_metrics_from_context(self, default_host_moid='ha-host', source='pyvmomi'):
        fixture_xml = self._read_output_fixture_xml()
        if fixture_xml:
            return self.host_summary_metrics_from_xml(fixture_xml, source='output')

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            host_moid = self._source_value('host_moid', default=default_host_moid)
            host_name = self._source_value('host_name', 'hostname_filter', default='')
            return self.host_summary_metrics(
                service_instance,
                host_moid=host_moid,
                host_name=host_name,
                source=source,
            )
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def host_summary_metrics(self, service_instance, host=None, host_moid=None, host_name=None, source='pyvmomi'):
        if host is None:
            host = self.select_host(service_instance, host_moid=host_moid, host_name=host_name)

        content = service_instance.RetrieveContent()
        about = getattr(content, 'about', None)
        summary = getattr(host, 'summary', None)
        hardware = getattr(summary, 'hardware', None)
        runtime = getattr(summary, 'runtime', None)
        config = getattr(summary, 'config', None)
        product = getattr(config, 'product', None)
        quick_stats = getattr(summary, 'quickStats', None)

        cpu_usage_mhz = self._safe_int(getattr(quick_stats, 'overallCpuUsage', 0))
        cpu_mhz = self._safe_int(getattr(hardware, 'cpuMhz', 0))
        cpu_cores = self._safe_int(getattr(hardware, 'numCpuCores', 0))
        cpu_capacity_mhz = cpu_mhz * cpu_cores
        memory_usage_mib = self._safe_int(getattr(quick_stats, 'overallMemoryUsage', 0))
        memory_size_bytes = self._safe_int(getattr(hardware, 'memorySize', 0))
        memory_total_mib = int(round(memory_size_bytes / 1024.0 / 1024.0)) if memory_size_bytes else 0

        if cpu_capacity_mhz <= 0:
            raise RuntimeError('CPU 전체 용량을 계산할 수 없습니다.')
        if memory_total_mib <= 0:
            raise RuntimeError('메모리 전체 용량을 계산할 수 없습니다.')

        product_api_version = self._safe_text(getattr(product, 'apiVersion', ''), '')
        about_api_version = self._safe_text(getattr(about, 'apiVersion', ''), '')

        return {
            'name': self._safe_text(getattr(config, 'name', '') or getattr(host, 'name', '')),
            'full_name': self._safe_text(getattr(product, 'fullName', '') or getattr(about, 'fullName', '')),
            'version': self._safe_text(getattr(product, 'version', '') or getattr(about, 'version', '')),
            'build': self._safe_text(getattr(product, 'build', '') or getattr(about, 'build', '')),
            'api_version': product_api_version or about_api_version,
            'uuid': self._safe_text(getattr(hardware, 'uuid', '')),
            'vendor': self._safe_text(getattr(hardware, 'vendor', '')),
            'model': self._safe_text(getattr(hardware, 'model', '')),
            'cpu_model': self._safe_text(getattr(hardware, 'cpuModel', '')),
            'cpu_usage_mhz': cpu_usage_mhz,
            'cpu_capacity_mhz': cpu_capacity_mhz,
            'cpu_usage_percent': round((cpu_usage_mhz / float(cpu_capacity_mhz)) * 100.0, 2),
            'memory_usage_mib': memory_usage_mib,
            'memory_total_mib': memory_total_mib,
            'memory_usage_percent': round((memory_usage_mib / float(memory_total_mib)) * 100.0, 2),
            'power_state': self._safe_text(getattr(runtime, 'powerState', '')),
            'connection_state': self._safe_text(getattr(runtime, 'connectionState', '')),
            'overall_status': self._safe_text(getattr(summary, 'overallStatus', '')),
            'source': source,
        }

    def _host_display_name(self, host):
        summary = getattr(host, 'summary', None)
        config = getattr(summary, 'config', None)
        return self._safe_text(getattr(config, 'name', '') or getattr(host, 'name', ''))

    def _host_connection_state(self, host):
        summary = getattr(host, 'summary', None)
        runtime = getattr(summary, 'runtime', None)
        return self._safe_text(getattr(runtime, 'connectionState', ''))

    def _host_management_server_ip(self, host):
        summary = getattr(host, 'summary', None)
        return self._safe_text(getattr(summary, 'managementServerIp', ''))

    def _service_rows(self, host):
        config_manager = getattr(host, 'configManager', None)
        service_system = getattr(config_manager, 'serviceSystem', None)
        service_info = getattr(service_system, 'serviceInfo', None)
        services = getattr(service_info, 'service', None) or []

        rows = []
        for service in services:
            key = self._safe_text(getattr(service, 'key', ''))
            label = self._safe_text(getattr(service, 'label', '') or key)
            rows.append({
                'key': key,
                'label': label,
                'running': self._safe_bool(getattr(service, 'running', False)),
                'policy': self._safe_text(getattr(service, 'policy', '')),
            })
        if not any(str(row.get('key') or '').lower() == 'hostd' for row in rows):
            # vSphere API 세션 자체가 hostd를 통해 성립하므로 목록 미노출 시 보정한다.
            rows.append({
                'key': 'hostd',
                'label': 'hostd (vSphere API session)',
                'running': True,
                'policy': 'api-session',
            })
        rows.sort(key=lambda row: (row.get('key') or row.get('label') or '').lower())
        return rows

    def agent_services(self, service_instance, host=None, host_moid=None, host_name=None, source='pyvmomi'):
        if host is None:
            host = self.select_host(service_instance, host_moid=host_moid, host_name=host_name)

        management_server_ip = self._host_management_server_ip(host)
        return {
            'host_name': self._host_display_name(host),
            'managed_by_vcenter': bool(management_server_ip),
            'management_server_ip': management_server_ip,
            'connection_state': self._host_connection_state(host),
            'services': self._service_rows(host),
            'source': source,
        }

    def agent_services_from_context(self, default_host_moid='ha-host', source='pyvmomi'):
        fixture_json = self._read_output_fixture_json(
            inline_keys=('replay_agent_services_json', 'output_agent_services_json'),
            file_keys=('replay_agent_services_json_file', 'output_agent_services_json_file'),
        )
        if fixture_json is not None:
            return self._fixture_metrics(fixture_json, collection_key='services', count_key='service_count')

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            host_moid = self._source_value('host_moid', default=default_host_moid)
            host_name = self._source_value('host_name', 'hostname_filter', default='')
            return self.agent_services(
                service_instance,
                host_moid=host_moid,
                host_name=host_name,
                source=source,
            )
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def vcenter_agent_status(self, service_instance, host=None, host_moid=None, host_name=None, source='pyvmomi'):
        metrics = self.agent_services(
            service_instance,
            host=host,
            host_moid=host_moid,
            host_name=host_name,
            source=source,
        )
        services = metrics.get('services') or []
        vpxa = None
        for service in services:
            if str(service.get('key') or '').lower() == 'vpxa':
                vpxa = service
                break

        metrics['vpxa'] = {
            'exists': vpxa is not None,
            'running': bool(vpxa and vpxa.get('running')),
            'policy': self._safe_text((vpxa or {}).get('policy', '')),
        }
        return metrics

    def vcenter_agent_status_from_context(self, default_host_moid='ha-host', source='pyvmomi'):
        fixture_json = self._read_output_fixture_json(
            inline_keys=('replay_vcenter_agent_json', 'output_vcenter_agent_json'),
            file_keys=('replay_vcenter_agent_json_file', 'output_vcenter_agent_json_file'),
        )
        if fixture_json is not None:
            return self._fixture_metrics(fixture_json)

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            host_moid = self._source_value('host_moid', default=default_host_moid)
            host_name = self._source_value('host_name', 'hostname_filter', default='')
            return self.vcenter_agent_status(
                service_instance,
                host_moid=host_moid,
                host_name=host_name,
                source=source,
            )
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def _status_text(self, value):
        for attr in ('key', 'label', 'summary', 'value'):
            attr_value = getattr(value, attr, None)
            if attr_value not in (None, ''):
                return self._safe_text(attr_value)
        return self._safe_text(value)

    def _sensor_category(self, sensor):
        sensor_type = self._safe_text(getattr(sensor, 'sensorType', ''))
        name = self._safe_text(getattr(sensor, 'name', ''))
        text = ('%s %s' % (sensor_type, name)).lower()
        if 'power' in text or 'psu' in text:
            return 'power_supply'
        if 'fan' in text:
            return 'fan'
        if 'temp' in text or 'thermal' in text:
            return 'temperature'
        if 'volt' in text:
            return 'voltage'
        if 'battery' in text:
            return 'battery'
        return sensor_type.lower().replace(' ', '_') or 'other'

    def _sensor_status_rank(self, status):
        text = str(status or '').strip().lower()
        if text in ('red', 'critical', 'failure', 'failed', 'alert'):
            return 4
        if text in ('yellow', 'warning', 'degraded'):
            return 3
        if text in ('unknown', 'gray', 'grey'):
            return 2
        if text in ('green', 'normal', 'ok'):
            return 1
        return 2

    def _hardware_sensor_rows(self, host):
        runtime = getattr(host, 'runtime', None)
        health_runtime = getattr(runtime, 'healthSystemRuntime', None)
        health_info = getattr(health_runtime, 'systemHealthInfo', None)
        sensors = []
        if health_info is not None:
            sensors.extend(getattr(health_info, 'numericSensorInfo', None) or [])
            sensors.extend(getattr(health_info, 'sensorInfo', None) or [])

        rows = []
        for sensor in sensors:
            name = self._safe_text(getattr(sensor, 'name', ''))
            sensor_type = self._safe_text(getattr(sensor, 'sensorType', ''))
            status = self._status_text(getattr(sensor, 'healthState', ''))
            rows.append({
                'name': name,
                'type': sensor_type,
                'category': self._sensor_category(sensor),
                'status': status,
            })
        rows.sort(key=lambda row: (row.get('category') or '', row.get('name') or ''))
        return rows

    def hardware_health(self, service_instance, host=None, host_moid=None, host_name=None, source='pyvmomi'):
        if host is None:
            host = self.select_host(service_instance, host_moid=host_moid, host_name=host_name)

        summary = getattr(host, 'summary', None)
        sensors = self._hardware_sensor_rows(host)
        hardware_health = {}
        for sensor in sensors:
            category = sensor.get('category') or 'other'
            current = hardware_health.get(category)
            status = sensor.get('status') or 'unknown'
            if current is None or self._sensor_status_rank(status) > self._sensor_status_rank(current):
                hardware_health[category] = status

        failed_sensors = [
            sensor for sensor in sensors
            if self._sensor_status_rank(sensor.get('status')) >= 4
        ]
        warning_sensors = [
            sensor for sensor in sensors
            if self._sensor_status_rank(sensor.get('status')) in (2, 3)
        ]

        return {
            'host_name': self._host_display_name(host),
            'overall_status': self._safe_text(getattr(summary, 'overallStatus', '')),
            'hardware_health': hardware_health,
            'sensors': sensors,
            'warning_sensors': warning_sensors,
            'failed_sensors': failed_sensors,
            'source': source,
        }

    def hardware_health_from_context(self, default_host_moid='ha-host', source='pyvmomi'):
        fixture_json = self._read_output_fixture_json(
            inline_keys=('replay_hardware_health_json', 'output_hardware_health_json'),
            file_keys=('replay_hardware_health_json_file', 'output_hardware_health_json_file'),
        )
        if fixture_json is not None:
            return self._fixture_metrics(fixture_json)

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            host_moid = self._source_value('host_moid', default=default_host_moid)
            host_name = self._source_value('host_name', 'hostname_filter', default='')
            return self.hardware_health(
                service_instance,
                host_moid=host_moid,
                host_name=host_name,
                source=source,
            )
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def vm_summaries_from_context(self, source='pyvmomi'):
        fixture_json = self._read_output_fixture_json(
            inline_keys=('replay_vm_list_json', 'output_vm_list_json'),
            file_keys=('replay_vm_list_json_file', 'output_vm_list_json_file'),
        )
        if fixture_json is not None:
            return self._fixture_metrics(fixture_json, collection_key='virtual_machines', count_key='vm_count')

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            rows = self.vm_summaries(service_instance)
            return {
                'vm_count': len(rows),
                'virtual_machines': rows,
                'source': source,
            }
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def datastore_summaries_from_context(self, source='pyvmomi'):
        fixture_json = self._read_output_fixture_json(
            inline_keys=('replay_datastore_json', 'output_datastore_json'),
            file_keys=('replay_datastore_json_file', 'output_datastore_json_file'),
        )
        if fixture_json is not None:
            return self._fixture_metrics(fixture_json, collection_key='datastores', count_key='datastore_count')

        service_instance = None
        disconnect = None
        try:
            service_instance, disconnect = self.connect()
            rows = self.datastore_summaries(service_instance)
            return {
                'datastore_count': len(rows),
                'datastores': rows,
                'source': source,
            }
        finally:
            if service_instance is not None and disconnect is not None:
                try:
                    disconnect(service_instance)
                except Exception:
                    pass

    def vm_summaries(self, service_instance):
        rows = []
        for vm in self.list_vms(service_instance):
            summary = getattr(vm, 'summary', None)
            runtime = getattr(summary, 'runtime', None)
            config = getattr(summary, 'config', None)
            rows.append({
                'name': self._safe_text(getattr(config, 'name', '') or getattr(vm, 'name', '')),
                'uuid': self._safe_text(getattr(config, 'uuid', '')),
                'power_state': self._safe_text(getattr(runtime, 'powerState', '')),
            })
        return rows

    def datastore_summaries(self, service_instance):
        rows = []
        for datastore in self.list_datastores(service_instance):
            summary = getattr(datastore, 'summary', None)
            capacity = self._safe_int(getattr(summary, 'capacity', 0))
            free_space = self._safe_int(getattr(summary, 'freeSpace', 0))
            used = max(capacity - free_space, 0)
            usage_percent = round((used / float(capacity)) * 100.0, 2) if capacity else 0.0
            rows.append({
                'name': self._safe_text(getattr(summary, 'name', '') or getattr(datastore, 'name', '')),
                'type': self._safe_text(getattr(summary, 'type', '')),
                'url': self._safe_text(getattr(summary, 'url', '')),
                'accessible': bool(getattr(summary, 'accessible', False)),
                'capacity_bytes': capacity,
                'free_space_bytes': free_space,
                'capacity_gib': round(capacity / 1024.0 / 1024.0 / 1024.0, 2) if capacity else 0.0,
                'free_space_gib': round(free_space / 1024.0 / 1024.0 / 1024.0, 2) if free_space else 0.0,
                'usage_percent': usage_percent,
            })
        return rows
