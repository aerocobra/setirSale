# -*- coding: utf-8 -*-
# -*- setirSale.py
from openerp import tools
from openerp import models, fields, api
from pygments.lexer import _inherit

class setirSaleOrder ( models.Model):
	_inherit = "sale.order"

	x_datetimePO			= fields.Datetime	(	string			= "F PV",			help	= "fecha de Pedido de Venta")
	x_datetimePOcompleted	= fields.Datetime	(	string			= "F PV Realizado",	help	= "fecha de Pedio de Venta Realizado")
	x_idOperationUser		= fields.Many2one	(	comodel_name	= "res.users",		string	= "Responsable operación")

	@api.one
	def wfa_aprobar_por_operaciones (self):
		self.write ( {"x_datetimeApprovedByOperation" : fields.Datetime.now()})
		#self.message_post ( body = "responsable de operaciones: APROBADO")

	#self.send_mail_note( 'igor.kartashov@setir.es, astic@astic.net', data.get('company_name'), data.get('name'))
	def send_mail_note ( self, email_to, email_from, subject, msg):
		mail_pool = request.env['mail.mail']

		values={}
		values.update({'email_to': email_to})
		values.update({'email_from': email_from})
		values.update({'subject': subject})
		values.update({'body_html': msg})
		#values.update({'body': 'partner actualizado' })
		#values.update({'res_id': track_id}) #[optional] 'obj.id' here is the record id, where you want to post that email after sending
		#values.update({'model': 'res.partner'}) #[optional] here is the object(like 'project.project')  to whose record id you want to post that email after sending
		msg_id = mail_pool.create(values)
		# And then call send function of the mail.mail,
		if msg_id:
			mail_pool.send([msg_id])


class setirSaleOrderLine ( models.Model):
	_inherit = "sale.order.line"

	x_idsTarifa			= fields.Many2one	(
												comodel_name	= "product.pricelist",
												string			= "tarifa",
												required		= True,
												copy			= True
											)


	x_strTarifa		= fields.Char ( string = "Tarifa")
	x_eProvider		= fields.Selection (
											selection	= "get_providers",
											size		= 1,
											string		= "Proveedor",
											inverse		= "product_uom_change",
											required	= True,
											copy		= True
											)

	x_fPriceProvider	= fields.Float ( string = "PRVR")
	x_fPriceReseller	= fields.Float ( string = "SETIR")

	def get_providers (self):
		providers = []
		for partner in self.env['res.partner'].search([]):
			if partner.is_company == True and partner.supplier == True:
				providers.append ( ( partner.id, partner.name))

		return providers

	#se sibreescribe el metodo para que coja la tarida de cada  linea de pedido en vez de todo el pedido
	@api.onchange('product_uom', 'product_uom_qty', 'x_eProvider')
	def product_uom_change ( self):
		if not self.product_uom:
			self.price_unit = 0.0
			return

		idTarifa = 0
		rsTarifas	= self.env['product.pricelist'].search([('x_partner_id', '=', self.x_eProvider)])
		for tarifa in rsTarifas:
			if self.product_id == tarifa.items_ids[0].product_id:
				idTarifa			= tarifa.id
				self.x_strTarifa	= tarifa.name
				break

		if idTarifa and self.order_id.partner_id:
			product	= self.product_id.with_context	(
														lang			= self.order_id.partner_id.lang,
														partner			= self.order_id.partner_id.id,
														quantity		= self.product_uom_qty,
														date_order		= self.order_id.date_order,
														#pricelist		= self.order_id.pricelist_id.id,
														pricelist		= idTarifa,
														uom				= self.product_uom.id,
														fiscal_position	= self.env.context.get('fiscal_position')
													)

			self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)

			x_fPriceProvider	= -1.0
			x_fPriceReseller	= -1.0
			for item in tarifa.item_ids:
				if self.product_uom_qty > item.min_quantity:
					x_fPriceProvider	= item.x_fixed_price_provider
					x_fPriceReseller	= item.x_fixed_price_reseller

	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		if not self.product_id:
			return {'domain': {'product_uom': []}}

		vals = {}
		domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
		if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
			vals['product_uom'] = self.product_id.uom_id
			vals['product_uom_qty'] = 1.0

		product = self.product_id.with_context(
			lang=self.order_id.partner_id.lang,
			partner=self.order_id.partner_id.id,
			quantity=vals.get('product_uom_qty') or self.product_uom_qty,
			date=self.order_id.date_order,
			pricelist=self.x_idsTarifa.id,
			uom=self.product_uom.id
			)

		name = product.name_get()[0][1]
		if product.description_sale:
			name += '\n' + product.description_sale
		vals['name'] = name

		self._compute_tax_id()

		if self.order_id.pricelist_id and self.order_id.partner_id:
			vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
		self.update(vals)
		return {'domain': domain}

class setirProductPrecelist ( models.Model):
	_inherit = "product.pricelist"
											

	#el proveedor del acual depende la tarifa
	x_idPartner			= fields.Many2one(
											comodel_name	= "res.partner",
											string			= "Proveedor",
											inverse			= "partner_change",
										)
	x_partner_id		= fields.Integer()

	@api.onchange('x_idPartner')
	def partner_change ( self):
		self.x_partner_id = x_idPartner.id

class setirProductPrecelistItem ( models.Model):
	_inherit = "product.pricelist.item"

	x_fixed_price_provider	= fields.Float ( string = "Proveedor")
	x_fixed_price_reseller	= fields.Float ( string = "SETIR")
