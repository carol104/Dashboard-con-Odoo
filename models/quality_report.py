import base64
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class QualityAnalysisReport(models.AbstractModel):
    _name = 'report.techstore.quality.analysis'
    _description = 'PDF del análisis de calidad'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        tests = self.env['techstore.quality.test']
        tests.check_access_rights('read')
        # Search enforces ACLs and record rules. Never elevate report access.
        domain = data.get('domain', [])
        if docids:
            domain = ['&', ('id', 'in', docids)] + domain
        docs = tests.search(domain, order='module_name, date desc, id desc')
        graph_image = data.get('graph_image') or False
        graph_only = bool(data.get('graph_only'))
        if graph_only and not graph_image:
            raise ValidationError('Abra la vista de gráfico para descargarlo en PDF.')
        if graph_image:
            prefix = 'data:image/png;base64,'
            if not isinstance(graph_image, str) or not graph_image.startswith(prefix) or len(graph_image) > 4000000:
                raise ValidationError('La imagen del gráfico no es válida o es demasiado grande.')
            try:
                raw = base64.b64decode(graph_image[len(prefix):], validate=True)
                if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError()
            except (ValueError, base64.binascii.Error):
                raise ValidationError('La imagen del gráfico no es un PNG válido.')

        def totals(records):
            executed = sum(r.executed_tests for r in records)
            successful = sum(r.successful_tests for r in records)
            return {
                'count': len(records), 'executed': executed, 'successful': successful,
                'failed': executed - successful,
                'errors': sum(r.errors_found for r in records),
                'rate': 100 * successful / executed if executed else 0,
            }

        grouped = defaultdict(list)
        for record in docs:
            grouped[record.module_name].append(record)
        labels = dict(tests._fields['module_name']._description_selection(self.env))
        return {
            'doc_ids': docs.ids, 'doc_model': tests._name, 'docs': docs,
            'generated_at': fields.Datetime.now(), 'graph_image': graph_image,
            'graph_only': graph_only,
            'summary': totals(docs),
            'modules': [dict(totals(records), label=labels.get(code, code))
                        for code, records in sorted(grouped.items(), key=lambda item: labels.get(item[0], item[0]))],
        }
