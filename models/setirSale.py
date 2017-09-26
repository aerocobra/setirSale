# -*- coding: utf-8 -*-
#setirSale.py
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models
from openerp import tools
from pygments.lexer import _inherit
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import exceptions

class setirSaleOrder ( models.Model):
	_inherit = "sale.order"

	#sobreescrito para cambiar readonly a False, es necesario para poder hacer actualizacioones desde CSV al importar este campo
	state = fields.Selection([
		('draft', 'Quotation'),
		('sent', 'Quotation Sent'),
		('sale', 'Sale Order'),
		('done', 'Done'),
		('cancel', 'Cancelled'),
		], string='Status', readonly=False, copy=False, index=True, track_visibility='onchange', default='draft')

	x_dtPOconfirm		= fields.Datetime	(	string			= "F Pedido de Venta",	help	= "fecha de Pedido de Venta")
	x_dtPOformalize		= fields.Datetime	(	string			= "F Formalíazción",	help	= "fecha de Formalización de Pedido de Venta")
	x_dtPOdone			= fields.Datetime	(	string			= "F Realizado",		help	= "fecha de Pedio de Venta Realizado")

	x_idOperationUser	= fields.Many2one	(	comodel_name	= "res.users",
												string			= "Responsable operación",
												default			= "_getOperationManager"
											)

	#NOTE: selection key must be 'str', if 'int' ODOO doesn't store the selected value
	#propagar a toas las lineas de pedido
	x_eProvider		= fields.Selection (
											string		= "Proveedor",
											selection 	= "get_providers",
											inverse		= "on_provider_change"
											#required	= True ...NOTA: activarlo al terminar los PV antiguos
											)



	x_fRevenue			= fields.Float		(	string				= 'Beneficio SETIR',
												store				= True,
												compute				= '_amount_all',
												track_visibility	= 'always')

	x_fOrderRisk	= fields.Float	(	string				= 'Riesgo',
										store				= True,
										compute				= '_amount_all',
										track_visibility	= 'always')


	#se utiliza para mandar el mail utilizado la platilla ya creada
	#1. muestra el dialogo de envio con la palntilla cargada
	#2. usuario puede editar el correo
	#2. usuario debe hacer clic en "enviar" para enviar el corrreo 
	@api.multi
	def sendMailTemplateDialog (self, strModule, strTempalteID):
		self.ensure_one()
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

	#envia el coprreo  automaticamente utilizando la plantilla previamente creada
	#el correo se manda automáticamente sin mostar el dialogo de correo  
	@api.multi
	def sendMailTemplate ( self, strModule, strTempalteID):
		# Find the e-mail template
		# template = self.env.ref('mail_template_demo.example_email_template')
		# You can also find the e-mail template like this:
		template = self.env['ir.model.data'].get_object ( strModule, strTempalteID)
 
		# Send out the e-mail template to the user
		self.env['mail.template'].browse(template.id).send_mail(self.id)

	#envia el correo automaticamente utilizando parámetros de entrada  
	@api.multi
	def sendMailNote ( self, email_to, email_cc, email_from, subject, msg):
		mail_pool = self.env['mail.mail']

		values={}
		values.update({'email_to':		email_to})
		values.update({'email_cc':		email_cc})
		values.update({'email_from':	email_from})
		values.update({'subject':		subject})
		#values.update({'body':			msg})
		values.update({'body_html':		msg})
		#[optional] 'obj.id' here is the record id, where you want to post that email after sending
		#values.update({'res_id':		self.id})
		#[optional] here is the object(like 'project.project')  to whose record id you want to post that email after sending
		#values.update({'model':		'sale.order'})
		
		msg_id = mail_pool.create(values)
		# And then call send function of the mail.mail,
		if msg_id:
			mail_pool.send([msg_id])

	#devueleve el nombre de usuario logeado
	def getUserName (self, uid):
		#user_obj = self.env['res.users'].search ( [('id','=', uid)])[0]
		#user_value = user_obj.browse(uid)[0]
		user_value = self.env['res.users'].search ( [('id','=', uid)])[0]
		return user_value.name or False

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

	#se sobreescribe el metodo para que coja la tarifa de cada  linea de pedido en vez de todo el pedido
	@api.one
	@api.onchange('x_eProvider')
	def on_provider_change ( self):
		for line in self.order_line:
			line.x_eProvider = self.x_eProvider
			line.product_uom_change()

	def get_providers (self):
		providers = []
		for partner in self.env['res.partner'].search([('is_company','=', True), ( 'supplier', '=', True)]):
			providers.append ( ( str(partner.id), partner.name))

		return providers

	@api.model
	def _getOperationManager ( self):
		idOperationsManager	= self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.user_id.id
		return self.env['res.users'].search([('id', '=', idOperationsManager)])[0]

	@api.model
	def create(self, vals):
		result = super (setirSaleOrder, self).create (vals)
		#self.notifyWorkFlow ( "Presupuesto (oferta) CREADO", False)
		return result

	#se sobreescribe para poner la oportubidad correspondiente al estado "Propuesta"
	@api.multi
	def action_quotation_send(self):
		result = super (setirSaleOrder, self).action_quotation_send()
		#por defecto en ODOO:
		#id_externo: crm.stage_lead3, id:3, name:  Propuesta
		#verificar en las etapas que hay solo una Propuesta
		for order in self:
			if order.opportunity_id:
				order.opportunity_id.set_stage ("Propuesta")

		return result

	@api.multi
	def action_cancel(self):
		#self.write({'state': 'cancel'})
		super ( setirSaleOrder, self).action_cancel()

		self.write ( {'x_dtPOconfirm' : 0})
		self.write ( {'x_dtPOformalize' : 0})
		self.write ( {'x_dtPOdone' : 0})

		self.notifyWorkFlow( "CANCELADO", False)

	@api.multi
	def action_draft(self):
		super ( setirSaleOrder, self).action_draft()
		self.write ( {'x_dtPOconfirm' : 0})
		self.write ( {'x_dtPOformalize' : 0})
		self.write ( {'x_dtPOdone' : 0})

		self.notifyWorkFlow( "OFERTA", False)

	#sobreesctito para "sale.order.setir", NOTA: workflow no esta programado
	@api.multi
	def action_confirm(self):
		for order in self:
			order.write ( {'x_dtPOconfirm' : fields.Datetime.now()})
			order.notifyWorkFlow( "PEDIDO DE VENTA - CREADO desde Ofera", True)
			if order.opportunity_id:
				order.opportunity_id.set_stage (u"Aprobación")

		return super ( setirSaleOrder, self).action_confirm()

	@api.one
	def formalize ( self):
		#return self.env['warning.dialog'].info(title='Export imformation', message="MESSAGE")
		if not self.x_idOperationUser:
			raise exceptions.ValidationError ( 'Es necesario indicar al responsable operaciones')
		
		self.x_dtPOformalize	= fields.Datetime.now()
		self.notifyWorkFlow( u"PEDIDO DE VENTA, FORMALIZACIÓN", True)
		self.message_post ( u"PEDIDO DE VENTA - FORMALIZACIÓN")

	#sobreesctito para "sale.order.setir", NOTA: workflow no esta programado

	@api.multi
	def action_done(self):
		#self.write({'state': 'done'})
		if not self.x_idOperationUser or not self.x_dtPOformalize:
			raise exceptions.ValidationError ( 'Es necesario indicar al responsable operaciones y/o formalizar')
		
		super ( setirSaleOrder, self).action_done()
		self.write ( {'x_dtPOdone' : fields.Datetime.now()})
		self.notifyWorkFlow( "PEDIDO DE VENTA - REALIZADO", True)
		fRevenue	= 0.0
		strOrders	= ""
		for order in self:
			if order.opportunity_id:
				if order.opportunity_id.order_ids.search([('opportunity_id', '=', order.opportunity_id.id),('state', 'in',['draft', 'sent', 'sale'])]):
					#existe por lo menos un pedido no realizado
					self.message_post ( u"existen ofertas/pedidos no realizados, oportunidad no ganada")
					return
				for doneOrder in order.opportunity_id.order_ids.search([('opportunity_id', '=', order.opportunity_id.id),('state', '=','done')]):
					fRevenue += doneOrder.x_fRevenue
					strOrders += doneOrder.name +", "
					
				order.opportunity_id.set_stage (u"Aprobación")
				
				order.opportunity_id.planned_revenue = fRevenue
				self.message_post ( u"todos los pedidos realizados, ingreso estimado actualizado en la oportunidad con el beneficio setir [{}]".format (fRevenue))
				order.opportunity_id.action_set_won()

				strMailTo = order.user_id.email
				strMailCc = self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.work_email

				strSalesman		= order.user_id.name
				if order.user_id.name == False:
					strSalesman = "comercial indefinido"
				strUser = self.getUserName ( self.env.user.id)

				self.sendMailNote (
										strMailTo,
										strMailCc,
										u"sistemas@setir.es",
										u"oportunidad [{}] ganada".format( order.opportunity_id.name),
										u"""
										<BODY LANG="es-ES" DIR="LTR">
										<P STYLE="margin-top: 0.1cm; margin-bottom: 0.2cm"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><U><B><SPAN LANG="en-US">ACCI&Oacute;N
										AUTOM&Aacute;TICA SOBRE LA OPORTUNIDAD</SPAN></B></U></FONT></FONT></P>
										<TABLE WIDTH=749 BORDER=1 BORDERCOLOR="#000000" CELLPADDING=5 CELLSPACING=0>
											<COL WIDTH=246>
											<COL WIDTH=481>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Oportunidad:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Cliente:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT COLOR="#0066cc"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Nuevo estado:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><FONT COLOR="#009900">Ganado</FONT>
													</B><SPAN STYLE="font-weight: normal">(probabilidad 100%)</SPAN></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Ingreso estimado
													actualizado*:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Pedidos de venta
													asociados:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Comercial
													asignado:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></P>
												</TD>
											</TR>
											<TR VALIGN=TOP>
												<TD WIDTH=246>
													<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Cambio realzaido
													por:</FONT></FONT></P>
												</TD>
												<TD WIDTH=481>
													<P LANG="en-US"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B>{}</B></FONT></FONT></P>
												</TD>
											</TR>
										</TABLE>
										<P STYLE="margin-bottom: 0cm"><BR>
										</P>
										<P STYLE="margin-bottom: 0cm"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>(*)
										- Ingreso estimado = <FONT FACE="Arial, sans-serif">&sum;</FONT>
										beneficios setir en los pedidos de venta asociados</FONT></FONT></P>
										</BODY>
										""".format ( order.opportunity_id.name, order.partner_id.name, fRevenue, strOrders, strSalesman, strUser)
									)

	#manada correo al comercial y al resposable del departameinto de "operaciones"
	#por lo que es necesario crear el departamiento "operaciones" y su responsabñle con el correo establecido
	def notifyWorkFlow ( self, strState, bNotifyOperations = True):
		order = self
		#al comercial responsable
		strMailTo = order.user_id.email
		#al responsable del departamento operaciones
		if bNotifyOperations:
			strMailCc = self.env['hr.department'].search([('name', '=', 'operaciones')])[0].manager_id.work_email
		else:
			strMailCc = ""
		
		strOrder	= order.name
		if order.name == False:
			strOrder = "oferta indefinida"

		#strState	= str ( dict(self.fields_get(allfields=['state'])['state']['selection'])[order.state])
		strSalesman		= order.user_id.name
		if order.user_id.name == False:
			strSalesman = "comercial indefinido"

		strUser = self.getUserName ( self.env.user.id)
		
		strNotification = u"""
							<BODY LANG="es-ES" DIR="LTR">
							<P STYLE="margin-top: 0.1cm; margin-bottom: 0.2cm; font-style: normal">
							<FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><U><B>DETALLE
							DE LA ACCI&Oacute;N <SPAN LANG="en-US">DE CAMBIO DE </SPAN><SPAN LANG="es-ES">ESTADO</SPAN></B></U></FONT></FONT></FONT></P>
							<TABLE WIDTH=783 BORDER=1 BORDERCOLOR="#000000" CELLPADDING=5 CELLSPACING=0>
								<COL WIDTH=188>
								<COL WIDTH=573>
								<TR VALIGN=TOP>
									<TD WIDTH=188>
										<P STYLE="margin-top: 0.1cm; font-style: normal"><FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Oferta/Pedido
										de Venta:</FONT></FONT></FONT></P>
									</TD>
									<TD WIDTH=573>
										<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><SPAN LANG="en-US">{}</SPAN></B></FONT></FONT></P>
									</TD>
								</TR>
								<TR VALIGN=TOP>
									<TD WIDTH=188>
										<P STYLE="margin-top: 0.1cm; font-style: normal; text-decoration: none">
										<FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Cliente:</FONT></FONT></FONT></P>
									</TD>
									<TD WIDTH=573>
										<P><FONT COLOR="#0066cc"><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><SPAN LANG="en-US">{}</SPAN></B></FONT></FONT></FONT></P>
									</TD>
								</TR>
								<TR VALIGN=TOP>
									<TD WIDTH=188>
										<P STYLE="margin-top: 0.1cm; font-style: normal; text-decoration: none">
										<FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Nuevo
										estado</FONT></FONT></FONT></P>
									</TD>
									<TD WIDTH=573>
										<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><SPAN LANG="en-US">{}</SPAN></B></FONT></FONT></P>
									</TD>
								</TR>
								<TR VALIGN=TOP>
									<TD WIDTH=188>
										<P STYLE="margin-top: 0.1cm; font-style: normal; text-decoration: none">
										<FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Comercial
										Asignado</FONT></FONT></FONT></P>
									</TD>
									<TD WIDTH=573>
										<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><SPAN LANG="en-US">{}</SPAN></B></FONT></FONT></P>
									</TD>
								</TR>
								<TR VALIGN=TOP>
									<TD WIDTH=188>
										<P STYLE="margin-top: 0.1cm; font-style: normal"><FONT COLOR="#000000"><FONT FACE="Arial, sans-serif"><FONT SIZE=2>Cambio
										realizado por</FONT></FONT></FONT></P>
									</TD>
									<TD WIDTH=573>
										<P><FONT FACE="Arial, sans-serif"><FONT SIZE=2><B><SPAN LANG="en-US">{}</SPAN></B></FONT></FONT></P>
									</TD>
								</TR>
							</TABLE>
							<P STYLE="margin-bottom: 0cm"><BR>
							</P>
							</BODY>
							 """.format ( strOrder, order.partner_id.name, strState, strSalesman, strUser)

		self.sendMailNote (
								strMailTo,
								strMailCc,
								u"sistemas@setir.es",
								u"cambio estado oferta/pedido [{}], nuevo estado [{}]".format ( strOrder, strState),
								strNotification
							)

	#sobreescrito para rRevenue
	#@api.one
	@api.depends('order_line.price_total')
	def _amount_all(self):
		"""
		Compute the total amounts of the SO.
		"""
		for order in self:
			rRevenue = amount_untaxed = amount_tax = 0.0
			fRiisk = 0.0
			for line in order.order_line:
				amount_untaxed += line.price_subtotal
				fRiisk += line.get_line_risk()
				rRevenue += self.fix_porcentage (line.x_fPriceMargin, line.product_uom) * line.product_uom_qty
				# FORWARDPORT UP TO 10.0
				if order.company_id.tax_calculation_rounding_method == 'round_globally':
					#price = self.fix_porcentage ( line.price_unit * (1 - (line.discount or 0.0) / 100.0), line.product_uom)
					price = self.fix_porcentage ( line.price_unit * (1 - (line.discount or 0.0) / 100.0), line.product_uom)
					taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
					amount_tax += self.fix_porcentage ( sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])), line.product_uom)
				else:
					amount_tax += self.fix_porcentage ( line.price_tax, line.product_uom)

			#order.x_fRevenue = rRevenue
			order.update({
				'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
				'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
				'amount_total': amount_untaxed + amount_tax,
				'x_fRevenue': order.pricelist_id.currency_id.round ( rRevenue),
				'x_fOrderRisk': order.pricelist_id.currency_id.round ( fRiisk)
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
											#required	= True, NOTA: el NOT NULL no es compatible con vinculacion ventas-projects
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

	def get_line_risk ( self):
		risk_amount		= 0.0
		line_product	= self.product_id
		risk_products	= self.env['risk.product'].search ([('x_idProduct', '=', line_product.id)])
		if risk_products:
			if risk_products[0].x_bVolume:
				risk_amount += self.product_uom_qty
			if risk_products[0].x_bUntaxed:
				risk_amount += self.price_subtotal

			risk_amount	= risk_amount / risk_products[0].x_nPeriod
			risk_amount = risk_amount * risk_products[0].x_fFactor
			risk_amount = risk_amount * risk_products[0].x_nMonth

		return risk_amount

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
			#si este for esta al final, no funciona bien la primera vez
			for item in tarifa.item_ids.sorted ( key = lambda x: x.min_quantity, reverse = True):
				if self.product_uom_qty >= item.min_quantity:
					self.x_fPriceProvider	= item.x_fixed_price_provider
					break

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
			for item in tarifa.item_ids.sorted ( key = lambda x: x.min_quantity, reverse = True):
				if self.product_uom_qty >= item.min_quantity:
					self.x_fPriceProvider	= item.x_fixed_price_provider
					break
			vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)

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
