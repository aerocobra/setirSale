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
from openerp import exceptions


class riskProducts(models.Model):
	
	#NUEVO COMMENTARIOOOO con Sr Guillermo 
	_name = "risk.product"

	_rec_name = "x_strProduct"  # IMPORTANTE - por este campo se hace la selección por defecto en el formulario

	x_strProduct = fields.Char ( string = "Producto")

	x_idProduct = fields.Many2one(  comodel_name    =   "product.product",
									string          =   "Producto",
									inverse         =   "on_product_change")

	_sql_constraints = [('risk_product_unique', 'unique(x_idProduct)', 'Solo un riesgo por producto')]

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
	x_nMonth	= fields.Integer (  string	= "Meses de cobertura",
									default = 2,
									help	= "Cantidad de meses a cubrir")
	x_fFactor	= fields.Float	(	string	= "Factor de correción",
									default = 1.2,
									help	= "Factor de correción: 1,2 corresponde a subida de 20%")



	@api.onchange ('x_idProduct')
	def on_product_change (self):
		self.x_strProduct = self.x_idProduct.name

class setirCrmLead ( models.Model):
	_inherit = "crm.lead"

	x_fLeadRiskRequest	= fields.Float	(
											string	= 'Solicitado',
											help	="Para calcular basandose en los datos de las ofertas utilizar el botón [recalcular]"
										)

	x_fLeadRiskApproved	= fields.Float	(
											string	= 'Aprobado',
											help	= "Responsable popne aquí el impoirte de la cobertura aprobada"
										)
	x_eLeadRiskResult		= fields.Selection (
											string		= "Resultado aprobación",
											selection 	= [('rechazado', 'Rechazado'),
															('total', 'Aprobado total'),
															('parcial', 'Aprobado parcial')],
											inverse		= "onSetRiskResult"
											)

	
	# se añade uno igual para no tener problemas en la vista
	x_order_ids				= fields.One2many	( comodel_name = 'sale.order', inverse_name = 'opportunity_id', string='Ofertas')

	x_strCurrentStage		= fields.Char		( compute	= "getCurrentStage")
	x_bOperationsDirector	= fields.Boolean	( compute	= "isOperationsDirector")


	@api.one
	def isOperationsDirector (self):
		idOperationsManager	= self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.user_id.id
		
		strSS = "={}={}=".format(idOperationsManager, self.env.user.id)
		#strSS = "=" + str(idOperationsManager) + "=" + str (self.env.user.id) + "="
		#self.message_post ( strSS)

		if int (idOperationsManager) == int (self.env.user.id):
			self.x_bOperationsDirector = True
		else:
			self.x_bOperationsDirector = False 

	@api.one
	def getCurrentStage (self):
		stg = self.env['crm.stage'].search([('id', '=', self.stage_id.id)])
		self.x_strCurrentStage	= "no defenido"
		if stg:
			self.x_strCurrentStage = stg[0].name

	@api.one
	@api.onchange ('x_eLeadRiskResult')
	def onSetRiskResult (self):
		if self.x_eLeadRiskResult == 'total':
			self.x_fLeadRiskApproved = self.x_fLeadRiskRequest
			return

		self.x_fLeadRiskApproved = 0.0
	
	@api.multi
	def send_risk_mail (self):
		self.ensure_one()
		ir_model_data = self.env['ir.model.data']
		try:
			template_id = ir_model_data.get_object_reference( "setirSale", "risk_email_template")[1]
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
			#'default_composition_mode': 'mass_mail',
			#'default_message_type': 'comment',
			'default_notify': False,
			'default_notification': False,
			'default_subtype_id': False,
		})
		
		self.set_stage ( "Riesgo")
	
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

	@api.one
	@api.depends ( 'x_order_ids')
	def risk_recalc (self):
		for record in self:
			record.x_fLeadRiskRequest = fLeadRiskRequest = 0.0
			if record.x_order_ids == False:
				return
			for order in record.x_order_ids:
				fLeadRiskRequest += order.x_fOrderRisk
	
			record.x_fLeadRiskRequest = fLeadRiskRequest

	@api.one
	def set_stage (self, strStage):
		stg = self.env['crm.stage'].search([('name', '=', strStage)])
		if stg:
			self.stage_id = stg[0].id

