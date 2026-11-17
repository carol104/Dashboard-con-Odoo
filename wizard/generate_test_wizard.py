"""Asistente para crear datos sintéticos de práctica académica."""
import random
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class TechstoreQualityGenerateWizard(models.TransientModel):
    _name = 'techstore.quality.generate.wizard'
    _description = 'Generar registros de prueba TechStore'

    generation_mode = fields.Selection([
        ('random', 'Datos variados (aleatorios)'),
        ('sample', 'Seis ejemplos de la práctica'),
    ], string='Tipo de generación', required=True, default='random')
    quantity = fields.Integer(string='Cantidad de registros', required=True, default=30)
    random_seed = fields.Integer(string='Semilla reproducible', default=42,
                                 help='Usar la misma semilla permite repetir los valores simulados. Los códigos serán nuevos.')
    start_date = fields.Date(string='Fecha inicial', required=True,
                             default=fields.Date.context_today)

    def action_generate(self):
        self.ensure_one()
        if not self.env.user.has_group('practicaUnidad4.group_quality_analyst'):
            raise AccessError(_('No tiene permisos para generar datos de prueba.'))
        if self.generation_mode == 'random' and not 1 <= self.quantity <= 500:
            raise ValidationError(_('La cantidad debe estar entre 1 y 500.'))
        if not self.start_date:
            raise ValidationError(_('Seleccione una fecha inicial.'))

        Test = self.env['techstore.quality.test']
        Test.check_access_rights('create')
        date0 = fields.Date.to_date(self.start_date)
        modules = ['maintenance', 'customers', 'technicians', 'reports', 'inventory', 'dashboard']
        types = ['integration', 'functional', 'performance', 'usability', 'security', 'availability']
        vals_list = []

        if self.generation_mode == 'sample':
            # Datos individuales de la lámina TechStore; generan PRU nuevos por secuencia.
            sample = [
                ('maintenance', 'integration', 30, 22, 15, 1200, 92.5, 3.2),
                ('customers', 'functional', 25, 22, 5, 800, 95.5, 4.0),
                ('technicians', 'performance', 20, 18, 4, 950, 93.0, 3.8),
                ('reports', 'usability', 15, 13, 3, 700, 94.0, 3.6),
                ('inventory', 'security', 18, 17, 2, 600, 96.0, 4.2),
                ('dashboard', 'availability', 12, 11, 2, 580, 95.0, 4.1),
            ]
            for module, typ, executed, successful, errors, ms, avail, satisfaction in sample:
                vals_list.append({
                    'date': date0, 'module_name': module, 'test_type': typ,
                    'executed_tests': executed, 'successful_tests': successful,
                    'errors_found': errors, 'response_time': ms,
                    'availability': avail, 'satisfaction': satisfaction,
                    'responsible_id': self.env.uid, 'version': '1.0',
                    'notes': 'DATO SIMULADO - Ejemplo TechStore para prácticas.',
                })
        else:
            rng = random.Random(self.random_seed)
            for index in range(self.quantity):
                executed = rng.randint(10, 70)
                # Todos los estados son posibles y se generan resultados variados.
                rate = rng.uniform(0.62, 1.0)
                successful = min(executed, max(0, round(executed * rate)))
                failed = executed - successful
                vals_list.append({
                    'date': date0 + timedelta(days=rng.randint(0, 29)),
                    'module_name': rng.choice(modules),
                    'test_type': rng.choice(types),
                    'executed_tests': executed,
                    'successful_tests': successful,
                    'errors_found': rng.randint(failed, failed * 2 + 3),
                    'response_time': rng.randint(180, 1800),
                    'availability': round(rng.uniform(88.0, 100.0), 2),
                    'satisfaction': round(rng.uniform(2.5, 5.0), 1),
                    'responsible_id': self.env.uid,
                    'version': '1.0',
                    'notes': 'DATO SIMULADO - Generado para pruebas de Odoo y Power BI.',
                })

        records = Test.create(vals_list)
        if not records:
            raise UserError(_('No fue posible generar registros.'))
        # Abre solo los registros que acaba de crear este asistente.
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registros generados (%s)') % len(records),
            'res_model': 'techstore.quality.test',
            'view_mode': 'tree,form,graph,pivot',
            'target': 'current',
            'domain': [('id', 'in', records.ids)],
            'context': {'create': False},
        }
