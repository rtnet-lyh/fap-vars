# -*- coding: utf-8 -*-

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

    def _read_output_fixture_xml(self):
        password = self._source_value(
            'password',
            'login_password',
            default=self.check.get_application_credential_value('password'),
        )
        force_replay = self._threshold_value('force_replay', default=False, value_type='bool')
        if password and not force_replay:
            return ''

        inline_xml = self._source_value('replay_summary_xml', 'output_summary_xml', default='')
        if inline_xml:
            return str(inline_xml)

        rel_path = self._source_value('replay_summary_xml_file', 'output_summary_xml_file', default='')
        if not rel_path:
            return ''

        base_dir = self._source_value('replay_base_dir', 'output_base_dir', default='')
        candidates = []
        if base_dir:
            candidates.append(os.path.join(str(base_dir), str(rel_path)))
        candidates.append(str(rel_path))
        candidates.append(os.path.join(os.getcwd(), str(rel_path)))

        for path in candidates:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    return fh.read()
        raise RuntimeError('output summary XML 파일을 찾지 못했습니다: %s' % rel_path)

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
                'usage_percent': usage_percent,
            })
        return rows
