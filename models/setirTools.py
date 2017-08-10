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

class localMailMail(models.Model):

	_inherit = 'mail.mail'
	
	def _get_partner_access_link(self, cr, uid, mail, partner=None, context=None):
		# Do not append access link
		return None

class MailNotification(models.Model):
	_inherit = 'mail.notification'

	def get_signature_footer(self, cr, uid, user_id, res_model=None, res_id=None, context=None, user_signature=True):
		""" Format a standard footer for notification emails (such as pushed messages notification or invite emails).
			Format:
				<p>--<br />
					Administrator
				</p>
				<div>
					<small>Sent from <a ...>Your Company</a>
						   using <a ...>OpenERP</a>.</small>
				</div>
		"""
		footer = ""
		if not user_id:
			return footer

		# Only add user signature
		user = self.pool.get("res.users").browse(cr, SUPERUSER_ID, [user_id],context=context)[0]
		if user_signature:
			if user.signature:
				signature = user.signature
			else:
				signature = "--<br />%s" % user.name
			footer = tools.append_content_to_html(footer, signature, plaintext=False)

		return footer