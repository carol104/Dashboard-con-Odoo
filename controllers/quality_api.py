
import hashlib
import hmac
from collections import Counter, defaultdict

from odoo import fields, http
from odoo.http import request


MODULE_NAMES = {
    'maintenance': 'Mantenimientos', 'customers': 'Clientes',
    'technicians': 'Técnicos', 'reports': 'Reportes',
    'inventory': 'Inventario', 'dashboard': 'Dashboard',
}
STATUS_NAMES = {
    'critical': 'Crítico', 'acceptable': 'Aceptable',
    'good': 'Bueno', 'excellent': 'Excelente',
}
TEST_NAMES = {
    'integration': 'Integración', 'functional': 'Funcional',
    'performance': 'Rendimiento', 'usability': 'Usabilidad',
    'security': 'Seguridad', 'availability': 'Disponibilidad',
}


class TechstoreQualityAPI(http.Controller):
    @staticmethod
    def _json(payload, status=200):
        return request.make_json_response(
            payload, status=status,
            headers=[('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')],
        )

    def _authorize(self):
        configured_hash = request.env['ir.config_parameter'].sudo().get_param(
            'techstore_quality.api_token_hash', default=''
        )
        header = request.httprequest.headers.get('Authorization', '')
        prefix = 'Bearer '
        token = header[len(prefix):].strip() if header.lower().startswith(prefix.lower()) else ''
        if not configured_hash or not token:
            return False
        candidate_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        return hmac.compare_digest(candidate_hash, configured_hash)

    def _filter_domain(self, params):
        domain = [('active', '=', True)]
        module = params.get('module')
        if module:
            if module not in MODULE_NAMES:
                raise ValueError('Módulo no válido. Use: ' + ', '.join(MODULE_NAMES))
            domain.append(('module_name', '=', module))
        for arg, op in [('date_from', '>='), ('date_to', '<=')]:
            if params.get(arg):
                try:
                    date = fields.Date.to_date(params[arg])
                    if not date or date.isoformat() != params[arg]:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise ValueError('Fecha no válida en %s. Use AAAA-MM-DD.' % arg)
                domain.append(('date', op, date))
        return domain

    @staticmethod
    def _record_dict(rec):
        return {
            'id': rec.id, 'code': rec.name,
            'date': fields.Date.to_string(rec.date) if rec.date else None,
            'module': rec.module_name,
            'module_name': MODULE_NAMES.get(rec.module_name, rec.module_name),
            'test_type': rec.test_type,
            'test_type_name': TEST_NAMES.get(rec.test_type, rec.test_type),
            'executed_tests': rec.executed_tests,
            'successful_tests': rec.successful_tests,
            'failed_tests': rec.failed_tests,
            'errors_found': rec.errors_found,
            'success_rate': round(rec.success_rate, 2),
            'response_time_ms': round(rec.response_time, 2),
            'availability_pct': round(rec.availability, 2),
            'satisfaction': round(rec.satisfaction, 1),
            'quality_status': rec.quality_status,
            'quality_status_name': STATUS_NAMES.get(rec.quality_status, rec.quality_status),
            'responsible': rec.responsible_id.name,
            'version': rec.version,
            'notes': rec.notes or '',
        }

    def _validated_request(self, params):
        if not self._authorize():
            return None, self._json({'error': 'No autorizado: token ausente o inválido.'}, 401)
        try:
            domain = self._filter_domain(params)
        except ValueError as exc:
            return None, self._json({'error': str(exc)}, 400)
        return domain, None

    @http.route('/api/techstore/quality/tests', type='http', auth='public',
                methods=['GET'], csrf=False, sitemap=False)
    def tests(self, **params):
        domain, error = self._validated_request(params)
        if error is not None:
            return error
        try:
            limit = int(params.get('limit', '100'))
            offset = int(params.get('offset', '0'))
        except (ValueError, TypeError):
            return self._json({'error': 'limit y offset deben ser enteros.'}, 400)
        if not 1 <= limit <= 3000 or not 0 <= offset <= 1000000:
            return self._json({'error': 'limit: 1..3000; offset: 0..1000000.'}, 400)
        records = request.env['techstore.quality.test'].sudo()
        total = records.search_count(domain)
        page = records.search(domain, limit=limit, offset=offset, order='date desc, id desc')
        return self._json({
            'count': len(page), 'total': total, 'limit': limit, 'offset': offset,
            'has_more': offset + len(page) < total,
            'data': [self._record_dict(rec) for rec in page],
        })

    @http.route('/api/techstore/quality/tests/<int:test_id>', type='http', auth='public',
                methods=['GET'], csrf=False, sitemap=False)
    def test_detail(self, test_id, **params):
        domain, error = self._validated_request(params)
        if error is not None:
            return error
        record = request.env['techstore.quality.test'].sudo().search(
            domain + [('id', '=', test_id)], limit=1
        )
        if not record:
            return self._json({'error': 'Registro no encontrado.'}, 404)
        return self._json({'data': self._record_dict(record)})

    @staticmethod
    def _aggregate(records):
        count = len(records)
        total_executed = sum(r.executed_tests for r in records)
        total_successful = sum(r.successful_tests for r in records)
        statuses = Counter(r.quality_status for r in records)
        return {
            'total_records': count,
            'total_tests': total_executed,
            'successful_tests': total_successful,
            'failed_tests': total_executed - total_successful,
            'total_errors': sum(r.errors_found for r in records),
            'success_rate': round(100 * total_successful / total_executed, 2) if total_executed else 0,
            'average_availability': round(sum(r.availability for r in records) / count, 2) if count else 0,
            'average_response_time': round(sum(r.response_time for r in records) / count, 2) if count else 0,
            'average_satisfaction': round(sum(r.satisfaction for r in records) / count, 2) if count else 0,
            'critical': statuses['critical'], 'acceptable': statuses['acceptable'],
            'good': statuses['good'], 'excellent': statuses['excellent'],
        }

    @http.route('/api/techstore/quality/metrics', type='http', auth='public',
                methods=['GET'], csrf=False, sitemap=False)
    def metrics(self, **params):
        domain, error = self._validated_request(params)
        if error is not None:
            return error
        records = request.env['techstore.quality.test'].sudo().search(domain)
        return self._json(self._aggregate(records))

    @http.route('/api/techstore/quality/modules', type='http', auth='public',
                methods=['GET'], csrf=False, sitemap=False)
    def modules(self, **params):
        domain, error = self._validated_request(params)
        if error is not None:
            return error
        records = request.env['techstore.quality.test'].sudo().search(domain)
        groups = defaultdict(list)
        for rec in records:
            groups[rec.module_name].append(rec)
        data = []
        for code, label in MODULE_NAMES.items():
            if code in groups:
                data.append({'module': code, 'module_name': label,
                             **self._aggregate(groups[code])})
        return self._json({'count': len(data), 'data': data})
