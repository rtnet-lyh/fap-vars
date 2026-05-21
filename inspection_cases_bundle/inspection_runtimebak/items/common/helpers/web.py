# -*- coding: utf-8 -*-

import json
import ssl
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebHelper(object):
    def __init__(self, check):
        self.check = check

    def source_dicts(self):
        payload = self.check.ctx.get('item_payload') or {}
        app_cred = self.check.get_application_credential_data() or {}
        conn_cred = self.check.get_connection_credential_data() or {}
        return [payload, app_cred, conn_cred]

    def get_source_value(self, *keys, **kwargs):
        default = kwargs.get('default')
        for key in keys:
            value = self.check.get_threshold_var(key, default=None, value_type='raw')
            if value not in (None, ''):
                return value
        for source in self.source_dicts():
            for key in keys:
                value = source.get(key)
                if value not in (None, ''):
                    return value
        return default

    def get_list_value(self, *keys, **kwargs):
        default = kwargs.get('default')
        value = self.get_source_value(*keys, default=default)
        if value in (None, ''):
            return [] if default is None else list(default)
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        if text.startswith('[') and text.endswith(']'):
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    return [str(item).strip() for item in decoded if str(item).strip()]
            except Exception:
                pass
        text = text.replace('\r', '\n')
        parts = []
        for chunk in text.split('\n'):
            parts.extend(item.strip() for item in chunk.split(',') if item.strip())
        return parts

    def resolve_base_url(self):
        for key in ('target_url', 'service_url', 'url', 'base_url', 'endpoint'):
            value = self.get_source_value(key)
            if value:
                text = str(value).strip()
                if '://' in text:
                    return text.rstrip('/')
                return ('https://%s' % text).rstrip('/')

        host = str(self.get_source_value('domain', 'host', default=self.check.ctx.get('host') or '')).strip()
        if not host:
            return None
        scheme = str(self.get_source_value('scheme', default='https')).strip() or 'https'
        port = str(self.get_source_value('web_port', 'port', default='')).strip()
        if ':' in host or '/' in host:
            return host.rstrip('/') if '://' in host else ('%s://%s' % (scheme, host)).rstrip('/')
        if port and port not in ('80', '443'):
            return '%s://%s:%s' % (scheme, host, port)
        return '%s://%s' % (scheme, host)

    def build_url(self, path_or_url=None):
        base_url = self.resolve_base_url()
        if path_or_url in (None, ''):
            return base_url
        text = str(path_or_url).strip()
        if '://' in text:
            return text
        if not base_url:
            return None
        return urljoin(base_url.rstrip('/') + '/', text.lstrip('/'))

    def new_cookie_jar(self):
        return CookieJar()

    def request(self, path_or_url=None, method='GET', params=None, data=None, headers=None, follow_redirects=True, cookie_jar=None, timeout=5):
        url = self.build_url(path_or_url)
        if not url:
            return {'ok': False, 'error': '대상 URL 없음', 'status': None, 'headers': {}, 'set_cookies': [], 'body': '', 'url': ''}

        query = urlencode(params or {}, doseq=True)
        if query:
            delimiter = '&' if '?' in url else '?'
            url = '%s%s%s' % (url, delimiter, query)

        body_bytes = None
        if data is not None:
            if isinstance(data, (bytes, bytearray)):
                body_bytes = data
            else:
                body_bytes = urlencode(data, doseq=True).encode('utf-8')

        req_headers = {'User-Agent': 'FAP-VARS-WebCheck/1.0'}
        if headers:
            req_headers.update(headers)
        request = Request(url=url, data=body_bytes, headers=req_headers, method=method.upper())

        cookie_jar = cookie_jar or self.new_cookie_jar()
        handlers = [HTTPCookieProcessor(cookie_jar), HTTPSHandler(context=ssl._create_unverified_context())]
        if not follow_redirects:
            handlers.append(_NoRedirectHandler())
        opener = build_opener(*handlers)

        try:
            with opener.open(request, timeout=timeout) as resp:
                body = resp.read().decode('utf-8', errors='replace')
                headers_obj = resp.headers
                return {
                    'ok': True,
                    'error': '',
                    'status': resp.getcode(),
                    'headers': {key.lower(): value for key, value in headers_obj.items()},
                    'set_cookies': headers_obj.get_all('Set-Cookie') or [],
                    'body': body,
                    'url': resp.geturl(),
                    'cookie_jar': cookie_jar,
                }
        except HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace') if exc.fp else ''
            headers_obj = exc.headers
            return {
                'ok': False,
                'error': str(exc),
                'status': exc.code,
                'headers': {key.lower(): value for key, value in headers_obj.items()},
                'set_cookies': headers_obj.get_all('Set-Cookie') or [],
                'body': body,
                'url': exc.geturl(),
                'cookie_jar': cookie_jar,
            }
        except URLError as exc:
            return {'ok': False, 'error': str(exc.reason), 'status': None, 'headers': {}, 'set_cookies': [], 'body': '', 'url': url, 'cookie_jar': cookie_jar}
        except Exception as exc:
            return {'ok': False, 'error': str(exc), 'status': None, 'headers': {}, 'set_cookies': [], 'body': '', 'url': url, 'cookie_jar': cookie_jar}

    def find_markers(self, text, markers):
        lowered = (text or '').lower()
        return [marker for marker in (markers or []) if str(marker).lower() in lowered]

    def get_session_cookie_values(self, response=None, cookie_jar=None):
        values = []
        header_values = []
        if response:
            header_values.extend(response.get('set_cookies') or [])
        for item in header_values:
            values.append(item)
        jar = cookie_jar or (response or {}).get('cookie_jar')
        if jar:
            for cookie in jar:
                values.append('%s=%s' % (cookie.name, cookie.value))
        return values

    def extract_cookie_tokens(self, response=None, cookie_jar=None):
        tokens = []
        jar = cookie_jar or (response or {}).get('cookie_jar')
        if jar:
            for cookie in jar:
                tokens.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'secure': bool(cookie.secure),
                    'expires': cookie.expires,
                })
        if tokens:
            return tokens
        for header in (response or {}).get('set_cookies') or []:
            first = header.split(';', 1)[0].strip()
            if '=' not in first:
                continue
            name, value = first.split('=', 1)
            tokens.append({
                'name': name.strip(),
                'value': value.strip(),
                'secure': 'secure' in header.lower(),
                'expires': None,
            })
        return tokens

    def login(self, cookie_jar=None):
        login_path = self.get_source_value('login_url', 'login_path', 'auth_url')
        username = self.get_source_value(
            'login_username',
            'username',
            'user_id',
            default=self.check.get_application_credential_value('username'),
        )
        password = self.get_source_value(
            'login_password',
            'password',
            'user_password',
            default=self.check.get_application_credential_value('password'),
        )
        if not login_path or not username or not password:
            return {
                'ok': False,
                'error': '로그인 정보 없음',
                'status': None,
                'headers': {},
                'set_cookies': [],
                'body': '',
                'url': '',
                'cookie_jar': cookie_jar or self.new_cookie_jar(),
            }

        user_field = str(self.get_source_value('login_user_field', default='username')).strip() or 'username'
        password_field = str(self.get_source_value('login_password_field', default='password')).strip() or 'password'
        extra = self.get_source_value('login_extra_fields', default=None)
        form = {user_field: username, password_field: password}
        if extra:
            if isinstance(extra, dict):
                form.update(extra)
            else:
                try:
                    decoded = json.loads(str(extra))
                    if isinstance(decoded, dict):
                        form.update(decoded)
                except Exception:
                    pass
        return self.request(
            login_path,
            method='POST',
            data=form,
            cookie_jar=cookie_jar or self.new_cookie_jar(),
            follow_redirects=False,
        )

    def make_multipart(self, fields, file_field, filename, content, content_type='application/octet-stream'):
        boundary = '----FAPVARSBOUNDARY1234567890'
        lines = []
        for key, value in (fields or {}).items():
            lines.extend([
                '--%s' % boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                str(value),
            ])
        lines.extend([
            '--%s' % boundary,
            'Content-Disposition: form-data; name="%s"; filename="%s"' % (file_field, filename),
            'Content-Type: %s' % content_type,
            '',
            content,
            '--%s--' % boundary,
            '',
        ])
        body = '\r\n'.join(lines).encode('utf-8')
        return body, boundary
