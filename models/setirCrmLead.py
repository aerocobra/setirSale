# -*- coding: utf-8 -*-
# setirCrmLead.py
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models
from openerp import tools
from pygments.lexer import _inherit
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class riskProducts(models.Model):
	_name = "risk.product"
# eto dobavil ya na remote

	_rec_name = "x_strProduct"  # IMPORTANTE - por este campo se hace la selección por defecto en el formulario

	x_strProduct = fields.Char ( string = "Producto")

	x_idProduct = fields.Many2one(  comodel_name    =   "product.product",
									string          =   "Producto",
									inverse         =   "on_product_change")

#	_sql_constraints = [('risk_product_unique', 'unique(x_idProduct)', 'Solo un riesgo por producto')]

	x_eType     = fields.Selection (    selection=[
												('sum', 'Sumar'),
												('subtract', 'Restar')
												],
										default = 'sum',
										string  = "Tipo Aplicación",
										help    = "Sumar - se suma al total, Restar - se resta del total")

	x_bVolume	= fields.Boolean (	string	= "Aplicar Consumo",        default = True)
	x_bUntaxed	= fields.Boolean (	string	= "Aplicar Base Imponible", default = True)
	x_nPeriod	= fields.Integer (  string	= "Periodo consumo",
									default = 12,
									help	= "Se pone en meses: 12 - 1 año, 1 - 1 mes")
	x_fFactor	= fields.Float	(	string	= "Factor de correción",
									default = 1.2,
									help	= "Factor de correción: 1,2 corresponde a subida de 20%")


	@api.onchange ('x_idProduct')
	def on_product_change (self):
		self.x_strProduct = self.x_idProduct.name

class setirCrmLead ( models.Model):
	_inherit = ['crm.lead']

	x_fLeadRisk	= fields.Float	(
		# store	= True,
		compute	= '_compute_lead_risc',
		string	= 'Riesgo'
	)
	# se añade uno igual paar no tener problemas en la vista
	x_order_ids = fields.One2many('sale.order', 'opportunity_id', string='Ofertas')

	@api.one
	@api.depends ( 'x_order_ids')
	def _compute_lead_risc (self):
		self.x_fLeadRisk = fLeadRisk = 0.0
		if self.x_order_ids == False:
			return
		for order in self.x_order_ids:
			fLeadRisk += order.x_fOrderRisk

		self.x_fLeadRisk = fLeadRisk

	@api.one
	def set_stage (self, strStage):
		stg = self.env['crm.stage'].search([('name', '=', strStage)])
		if stg:
			self.opportunity_id.stage_id = stg[0].id
