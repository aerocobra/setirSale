# -*- coding: utf-8 -*-
# setirSale.py
from openerp import tools
from pygments.lexer import _inherit

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class setirSaleOrder ( models.Model):
	_inherit = "sale.order"

	x_dtPOconfirm		= fields.Datetime	(	string			= "F Pedido de Venta",	help	= "fecha de Pedido de Venta")
	x_dtPOformalize		= fields.Datetime	(	string			= "F Formalíazción",	help	= "fecha de Formalización de Pedido de Venta")
	x_dtPOdone			= fields.Datetime	(	string			= "F Realizado",		help	= "fecha de Pedio de Venta Realizado")

	x_idOperationUser	= fields.Many2one	(	comodel_name	= "res.users",
												string			= "Responsable operación"
												#default			= "_get_operation_user_default"
											)

	#NOTE: selection key must be 'str', if 'int' ODOO doesn't store the selected value
	#propagar a toas las lineas de pedido
	x_eProvider		= fields.Selection (
											string		= "Proveedor",
											selection 	= "get_providers",
											inverse		= "on_provider_change",
											required	= True
											)


	#_defaults = {
	#	'x_idOperationUser': "_get_operation_user_default"
	#}

	x_fRevenue			= fields.Float		(	string				= 'Beneficio SETIR',
												store				= True,
												compute				= '_amount_all',
												track_visibility	= 'always')

	@api.multi
	def print_sale_report_one(self):

		""" Print the invoice and mark it as sent, so that we can see more

		  easily the next step of the workflow

		 """

		#assert len(self) == 1, 'This option should only be used for a single id at a time.'
		
		#self.sent = True

		return self.env['report'].get_action(self, 'setirSale.setirSaleTimespanReport')

	def print_sale_report (self):
		attachment_obj = self.env['ir.attachment']
		for record in self.search([]):
			ir_actions_report = self.env['ir.actions.report.xml']
			matching_reports = ir_actions_report.search([('report_name','=','setirSale.setirSaleTimespanReport')])
			if matching_reports:
				report = matching_reports[0]
				report_service = 'report.' + report.report_name
				service = netsvc.LocalService(report_service)
				(result, format) = service.create([record.id], {'model': self._name}, context=context)
				eval_context = {'time': time, 'object': record}
				if not report.attachment or not eval(report.attachment, eval_context):
					# no auto-saving of report as attachment, need to do it manually
					result = base64.b64encode(result)
					file_name = re.sub(r'[^a-zA-Z0-9_-]', '_', 'tempoEXXXX')
					file_name += ".pdf"
					attachment_id = attachment_obj.create(cr, uid,
						{
							'name': file_name,
							'datas': result,
							'datas_fname': file_name,
							'res_model': self._name,
							'res_id': record.id,
							'type': 'binary'
						}, context=context)
		return True

	#se sibreescribe el metodo para que coja la tarifa de cada  linea de pedido en vez de todo el pedido
	@api.one
	@api.onchange('x_eProvider')
	def on_provider_change ( self):
		for orderLine in self.order_line:
			orderLine.x_eProvider = self.x_eProvider
			orderLine.product_uom_change()


	def get_providers (self):
		providers = []
		for partner in self.env['res.partner'].search([('is_company','=', True), ( 'supplier', '=', True)]):
			providers.append ( ( str(partner.id), partner.name))

		return providers

	@api.model
	def _get_operation_user_default ( self):
		idOperationsManager	= self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.user_id.id
		return self.env['res.users'].search([('id', '=', idOperationsManager)])[0].id

	@api.one
	def formalize ( self):
		if self.x_dtPOformalize != False or self.x_idOperationUser == False:
			return
		self.x_dtPOformalize	= fields.Datetime.now()

		#al responsable operaciones asignado
		strMailTo = self.x_idOperationUser.email
		#al comercial responsable
		strMailCc = self.user_id.email + ", " + self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.work_email
		
		strName		= self.name

		#strState	= str ( dict(self.fields_get(allfields=['state'])['state']['selection'])[order.state])
		strUser		= self.x_idOperationUser.name

		strNotification = "FT: [" + strName + u"]: asignado para su formalización a [" + str ( strUser) + "]"

		self.send_mail_note (
								strMailTo,
								strMailCc,
								"sistemas@setir.es",
								strNotification,
								strNotification
							)

		self.message_post ( strNotification)

	#sobreesctito para "sale.order.setir", NOTA: workflow no esta programado
	@api.model
	def create(self, vals):
		result = super (setirSaleOrder, self).create (vals)
		#self.notify_work_flow ( "Presupuesto (oferta) CREADO")
		return result

	#sobreesctito para "sale.order.setir", NOTA: workflow no esta programado
	@api.multi
	def action_confirm(self):
		for order in self:
			#codigo estandar
			order.state = 'sale'
			if self.env.context.get('send_email'):
				self.force_quotation_send()
			order.order_line._action_procurement_create()
			if not order.project_id:
				for line in order.order_line:
					if line.product_id.invoice_policy == 'cost':
						order._create_analytic_account()
						break
			#codigo setir *****************************************************
			#order.x_dtPOconfirmed	= fields.Datetime.now()
			order.write ( {'x_dtPOconfirm' : fields.Datetime.now()})
			order.notify_work_flow( "PEDIDO DE VENTA")
			#fin codigo setir *************************************************

		if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
			self.action_done()
		return True

	@api.multi
	def action_done(self):
		#self.write({'state': 'done'})
		super ( setirSaleOrder, self).action_done()

		self.write ( {'x_dtPOdone' : fields.Datetime.now()})

		self.notify_work_flow( "PEDIDO DE VENTA - REALIZADO")

	@api.multi
	def action_cancel(self):
		#self.write({'state': 'cancel'})
		super ( setirSaleOrder, self).action_cancel()

		self.write ( {'x_dtPOconfirm' : 0})
		self.write ( {'x_dtPOformalize' : 0})
		self.write ( {'x_dtPOdone' : 0})

		self.notify_work_flow( "CANCELADO")

	@api.multi
	def action_draft(self):
		super ( setirSaleOrder, self).action_draft()
		self.write ( {'x_dtPOconfirm' : 0})
		self.write ( {'x_dtPOformalize' : 0})
		self.write ( {'x_dtPOdone' : 0})

		self.notify_work_flow( "BORRADOR")

	#manada correo al comercial y al resposable del departameinto de "operaciones"
	#por lo que es necesario crear el departamiento "operaciones" y su responsabñle con el correo establecido
	def notify_work_flow ( self, strMsg):
		order = self
		#al comercial responsable
		strMailTo = order.user_id.email
		#al responsable del departamento operaciones
		strMailCc = self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.work_email
		
		strName		= order.name
		if order.name == False:
			strName = "NUEVO"

		#strState	= str ( dict(self.fields_get(allfields=['state'])['state']['selection'])[order.state])
		strUser		= order.user_id.name
		if order.user_id.name == False:
			strUser = "consultar"

		strNotification = "FT: [" + strName + "]: estado [" + strMsg + "] establecido por [" + strUser + "]"

		order.send_mail_note (
								strMailTo,
								strMailCc,
								"sistemas@setir.es",
								strNotification,
								strNotification
							)

		self.message_post ( strNotification)

	#self.send_mail_note( 'igor.kartashov@setir.es, astic@astic.net', data.get('company_name'), data.get('name'))
	def send_mail_note ( self, email_to, email_cc, email_from, subject, msg):
		mail_pool = self.env['mail.mail']

		values={}
		values.update({'email_to':		email_to})
		values.update({'email_cc':		email_cc})
		values.update({'email_from':	email_from})
		values.update({'subject':		subject})
		#values.update({'body':			'contenidos en html' })
		values.update({'body_html':		msg})
		#[optional] 'obj.id' here is the record id, where you want to post that email after sending
		#values.update({'res_id':		self.id})
		#[optional] here is the object(like 'project.project')  to whose record id you want to post that email after sending
		#values.update({'model':		'sale.order'})
		
		msg_id = mail_pool.create(values)
		# And then call send function of the mail.mail,
		if msg_id:
			mail_pool.send([msg_id])

	#sobreescrito para rRevenue
	@api.one
	@api.depends('order_line.price_total')
	def _amount_all(self):
		"""
		Compute the total amounts of the SO.
		"""
		for order in self:
			rRevenue = amount_untaxed = amount_tax = 0.0
			for line in order.order_line:
				amount_untaxed += line.price_subtotal
				rRevenue += self.fix_porcentage (line.x_fPriceMargin, line.product_uom) * line.product_uom_qty
				# FORWARDPORT UP TO 10.0
				if order.company_id.tax_calculation_rounding_method == 'round_globally':
					#price = self.fix_porcentage ( line.price_unit * (1 - (line.discount or 0.0) / 100.0), line.product_uom)
					price = self.fix_porcentage ( line.price_unit * (1 - (line.discount or 0.0) / 100.0), line.product_uom)
					taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
					amount_tax += self.fix_porcentage ( sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])), line.product_uom)
				else:
					amount_tax += self.fix_porcentage ( line.price_tax, line.product_uom)
			order.update({
				'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
				'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
				'amount_total': amount_untaxed + amount_tax,
				'x_fRevenue': self.pricelist_id.currency_id.round ( rRevenue)
			})

	#el precio los productos que tienen UOM de categoria "Porcentaje" se pone en porcientos
	#es necesario convertirlo a euros, aqui em _amount_all(): price, price_tax y rRevenue
	def fix_porcentage ( self, price, product_uom):
		if product_uom.category_id.name == "Porcentaje":
			price = price / 100.0
		return price

class setirSaleOrderLine ( models.Model):
	_inherit = "sale.order.line"

	x_fPriceProvider	= fields.Float (	string		= "COSTE",
											required	= True,
											inverse	= "on_price_provider_change"
										)

	x_fPriceMargin		= fields.Float (	string		= "MARG",
											compute		= "compute_price_margin",
											readonly = True
										)
	x_fMarginSubtotal	= fields.Float (	string		= "BENF",
											compute = "compute_margin_subtotal",
											readonly = True
											)

	x_strTarifa		= fields.Char ( string = "Tarifa", readonly = True)
	#NOTE: selection key must be 'str', if 'int' ODOO doesn't store the selected value
	x_eProvider		= fields.Selection (
											string		= "Proveedor",
											selection 	= "get_providers",
											inverse		= "product_uom_change"
											)


	#los campos compute por defecto se calculan al mostrar la vista y al salvar los cambios
	#para forzar la dependencia del cambio de otros campos
	@api.one
	@api.depends('price_unit', 'x_fPriceProvider')
	def compute_price_margin ( self):
		self.x_fPriceMargin = self.price_unit - self.x_fPriceProvider
	@api.one
	@api.depends('price_unit', 'x_fPriceProvider', 'product_uom_qty')
	def compute_margin_subtotal ( self):
		self.x_fMarginSubtotal	= self.fix_porcentage ( self.x_fPriceMargin, self.product_uom) * self.product_uom_qty

	def get_providers (self):
		providers = []
		for partner in self.env['res.partner'].search([('is_company','=', True), ( 'supplier', '=', True)]):
			providers.append ( ( str(partner.id), partner.name))
		return providers

	#el precio los productos que tienen UOM de categoria "Porcentaje" se pone en porcientos
	#es necesario convertirlo a euros, aqui en product_id_change() y en product_uom_change: price_subtotal
	def fix_porcentage ( self, price, product_uom):
		if price != False and product_uom.category_id.name == "Porcentaje":
			price = price / 100.0
		return price

	@api.one
	@api.onchange('x_fPriceProvider')
	def on_price_provider_change ( self):
		self.price_subtotal		= self.fix_porcentage ( self.price_unit, self.product_uom) * self.product_uom_qty

	#sobreescrito para 'price_unit'
	@api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
	def _compute_amount(self):
		super (setirSaleOrderLine, self)._compute_amount()
		for line in self:
			line.price_subtotal = line.fix_porcentage ( line.price_unit, line.product_uom) * line.product_uom_qty
			#line.x_fPriceMargin	= line.price_unit - line.x_fPriceProvider
			#line.x_fMarginSubtotal = line.fix_porcentage ( line.x_fPriceMargin, line.product_uom) * line.product_uom_qty


	#se sobreescribe el metodo para que coja la tarifa de cada  linea de pedido en vez de todo el pedido
	@api.one
	@api.onchange('product_uom', 'product_uom_qty', 'x_eProvider')
	def product_uom_change ( self):
		if not self.product_uom:
			self.price_unit = 0.0
			return

		#limpiar de los datos anteriores
		self.x_strTarifa		= "sin tarifa"
		self.x_fPriceProvider	= 0.0

		#obtener tarifa en función del proveedor y producto selecccionados
		rsTarifas				= self.env['product.pricelist'].search([('x_partner_id', '=', int(self.x_eProvider))])
		if not rsTarifas:
			self.price_unit = 0.0
			return
		for tarifa in rsTarifas:
			if self.product_id == tarifa.item_ids[0].product_id:
				self.x_strTarifa	= tarifa.name
				break

		if tarifa.id and self.order_id.partner_id:
			product	= self.product_id.with_context	(
														lang			= self.order_id.partner_id.lang,
														partner			= self.order_id.partner_id.id,
														quantity		= self.product_uom_qty,
														date_order		= self.order_id.date_order,
														#pricelist		= self.order_id.pricelist_id.id,
														#poner la tarifa de la linea de pedido en vez del todo pedido
														pricelist		= tarifa.id,
														uom				= self.product_uom.id,
														fiscal_position	= self.env.context.get('fiscal_position')
													)

			self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)

			for item in tarifa.item_ids.sorted ( key = lambda x: x.min_quantity, reverse = True):
				if self.product_uom_qty >= item.min_quantity:
					self.x_fPriceProvider	= item.x_fixed_price_provider
					break

	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		if not self.product_id:
			return {'domain': {'product_uom': []}}

		#limpiar de los datos anteriores
		self.x_strTarifa		= "siN tarifa"
		self.x_fPriceProvider	= 0.0

		#obtener tarifa en función del proveedor y producto selecccionados
		rsTarifas				= self.env['product.pricelist'].search([('x_partner_id', '=', int(self.x_eProvider))])
		if not rsTarifas:
			self.price_unit = 0.0
			return {'domain': {'product_uom': []}}

		for tarifa in rsTarifas:
			if self.product_id == tarifa.item_ids[0].product_id:
				self.x_strTarifa	= tarifa.name
				break

		vals = {}
		domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
		if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
			vals['product_uom'] = self.product_id.uom_id
			vals['product_uom_qty'] = 1.0

		product = self.product_id.with_context(
			lang		= self.order_id.partner_id.lang,
			partner		= self.order_id.partner_id.id,
			quantity	= vals.get('product_uom_qty') or self.product_uom_qty,
			date		= self.order_id.date_order,
			#pricelist=self.order_id.pricelist_id.id,
			#poner la tarifa de la linea de pedido en vez del todo pedido
			pricelist	= tarifa.id,
			uom			= self.product_uom.id
		)

		name = product.name_get()[0][1]
		if product.description_sale:
			name += '\n' + product.description_sale
		vals['name'] = name

		self._compute_tax_id()

		if self.order_id.pricelist_id and self.order_id.partner_id:
			vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
			for item in tarifa.item_ids.sorted ( key = lambda x: x.min_quantity, reverse = True):
				if self.product_uom_qty >= item.min_quantity:
					self.x_fPriceProvider	= item.x_fixed_price_provider
					break

		self.update(vals)
		return {'domain': domain}

class setirProductPricelist ( models.Model):
	_inherit = "product.pricelist"
										
	#el proveedor del acual depende la tarifa
	x_idPartner			= fields.Many2one(
											comodel_name	= "res.partner",
											string			= "Proveedor",
											inverse			= "partner_change",
											required		= True
										)
	x_partner_id		= fields.Integer()

	@api.onchange('x_idPartner')
	def partner_change ( self):
		self.x_partner_id = int ( self.x_idPartner.id)

class setirProductPricelistItem ( models.Model):
	_inherit = "product.pricelist.item"

	x_fixed_price_provider	= fields.Float ( string = "Coste")
