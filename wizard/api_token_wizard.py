"""Rotación controlada del token de lectura para la API de Power BI."""
import hashlib
import secrets

from odoo import _, fields, models
from odoo.exceptions import AccessError


class TechstoreQualityAPITokenWizard(models.TransientModel):
    _name = 'techstore.quality.api.token.wizard'
    _description = 'Token de acceso de lectura a TechStore Quality'

    token = fields.Char(string='Token generado', readonly=True, copy=False)
    warning = fields.Text(string='Instrucciones', readonly=True, default=(
        'Genere un token y cópielo antes de cerrar la ventana. '
        'El sistema almacena solamente su hash. Un token anterior dejará de funcionar.'
    ))

    def action_rotate_token(self):
        self.ensure_one()
        if not self.env.user.has_group('practicaUnidad4.group_quality_manager'):
            raise AccessError(_('Se requiere el rol Administrador de calidad.'))
        raw_token = secrets.token_urlsafe(36)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        self.env['ir.config_parameter'].sudo().set_param(
            'techstore_quality.api_token_hash', token_hash
        )
        self.write({'token': raw_token})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configuración API Power BI'),
            'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }
