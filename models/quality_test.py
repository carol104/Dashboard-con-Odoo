from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TechstoreQualityTest(models.Model):
    _name = 'techstore.quality.test'
    _description = 'Prueba de calidad de TechStore'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Código', required=True, readonly=True, copy=False,
                       default=lambda self: _('Nuevo'), index=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.context_today, index=True)
    module_name = fields.Selection([
        ('maintenance', 'Mantenimientos'),
        ('customers', 'Clientes'),
        ('technicians', 'Técnicos'),
        ('reports', 'Reportes'),
        ('inventory', 'Inventario'),
        ('dashboard', 'Dashboard'),
    ], string='Módulo evaluado', required=True, index=True)
    test_type = fields.Selection([
        ('integration', 'Integración'),
        ('functional', 'Funcional'),
        ('performance', 'Rendimiento'),
        ('usability', 'Usabilidad'),
        ('security', 'Seguridad'),
        ('availability', 'Disponibilidad'),
    ], string='Tipo de prueba', required=True)

    executed_tests = fields.Integer(string='Pruebas ejecutadas', required=True, default=0)
    successful_tests = fields.Integer(string='Pruebas exitosas', required=True, default=0)
    failed_tests = fields.Integer(string='Pruebas fallidas', compute='_compute_quality', store=True)
    errors_found = fields.Integer(string='Errores encontrados', required=True, default=0)
    success_rate = fields.Float(string='% éxito', compute='_compute_quality', store=True,
                                digits=(6, 2), group_operator='avg')
    response_time = fields.Float(string='Tiempo de respuesta (ms)', digits=(10, 2),
                                 group_operator='avg', required=True, default=0.0)
    availability = fields.Float(string='Disponibilidad (%)', digits=(6, 2),
                                group_operator='avg', required=True, default=100.0)
    satisfaction = fields.Float(string='Satisfacción (1-5)', digits=(3, 1),
                                group_operator='avg', required=True, default=3.0)
    quality_status = fields.Selection([
        ('critical', 'Crítico'),
        ('acceptable', 'Aceptable'),
        ('good', 'Bueno'),
        ('excellent', 'Excelente'),
    ], string='Estado de calidad', compute='_compute_quality', store=True, index=True)
    responsible_id = fields.Many2one('res.users', string='Responsable', required=True,
                                     default=lambda self: self.env.user, ondelete='restrict')
    version = fields.Char(string='Versión evaluada', default='1.0', required=True)
    notes = fields.Text(string='Observaciones')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('quality_code_unique', 'unique(name)', 'El código de la prueba debe ser único.'),
        ('quality_values_nonnegative',
         'CHECK(executed_tests >= 0 AND successful_tests >= 0 AND errors_found >= 0 AND response_time >= 0)',
         'Las cantidades y el tiempo de respuesta no pueden ser negativos.'),
        ('quality_success_le_executed',
         'CHECK(successful_tests <= executed_tests)',
         'Las pruebas exitosas no pueden superar las ejecutadas.'),
        ('quality_availability_range',
         'CHECK(availability >= 0 AND availability <= 100)',
         'La disponibilidad debe estar entre 0 y 100.'),
        ('quality_satisfaction_range',
         'CHECK(satisfaction >= 1 AND satisfaction <= 5)',
         'La satisfacción debe estar entre 1 y 5.'),
    ]

    @api.depends('executed_tests', 'successful_tests')
    def _compute_quality(self):
        for record in self:
            record.failed_tests = record.executed_tests - record.successful_tests
            rate = (100.0 * record.successful_tests / record.executed_tests
                    if record.executed_tests > 0 else 0.0)
            record.success_rate = rate
            if rate >= 95:
                record.quality_status = 'excellent'
            elif rate >= 90:
                record.quality_status = 'good'
            elif rate >= 80:
                record.quality_status = 'acceptable'
            else:
                record.quality_status = 'critical'

    @api.constrains('executed_tests', 'successful_tests', 'errors_found',
                    'response_time', 'availability', 'satisfaction')
    def _check_quality_values(self):
        for record in self:
            if record.executed_tests <= 0:
                raise ValidationError(_('Las pruebas ejecutadas deben ser mayores que cero.'))
            if not 0 <= record.successful_tests <= record.executed_tests:
                raise ValidationError(_('Las pruebas exitosas deben estar entre cero y las ejecutadas.'))
            if record.errors_found < 0 or record.response_time < 0:
                raise ValidationError(_('Los errores encontrados y el tiempo no pueden ser negativos.'))
            if not 0 <= record.availability <= 100:
                raise ValidationError(_('La disponibilidad debe estar entre 0 y 100%.'))
            if not 1 <= record.satisfaction <= 5:
                raise ValidationError(_('La satisfacción debe estar entre 1 y 5.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('techstore.quality.test') or _('Nuevo')
        return super().create(vals_list)

    @api.model
    def action_download_quality_pdf(self, domain=None, graph_image=None, graph_only=False):
        """Export the current search, using the caller's normal read permissions."""
        self.check_access_rights('read')
        report_id = ('practicaUnidad4.action_report_quality_graph' if graph_only
                     else 'practicaUnidad4.action_report_quality_analysis')
        return self.env.ref(report_id).report_action(
            self, data={'domain': domain or [], 'graph_image': graph_image, 'graph_only': bool(graph_only)},
        )
