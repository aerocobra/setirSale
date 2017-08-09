# -*- coding: utf-8 -*-
# setirTools.py
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models
from openerp import tools
from pygments.lexer import _inherit
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class setirTools ( models.Model):
    _name = "setir.tools"

    @api.one
    def sendMailTemplate (self, strModule, strTempalteID):
        # Find the e-mail template
        #template = self.env.ref('mail_template_demo.example_email_template')
        #  template = self.env.ref('setirSale.risk_email_template')
        
        # You can also find the e-mail template like this:
        #template = self.env['ir.model.data'].get_object('crm.lead', 'send risk')

        # Send out the e-mail template to the user
        #  self.env['mail.template'].browse(template.id).send_mail(self.id)

        #self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference( strModule, strTempalteID)[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'crm.lead',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
