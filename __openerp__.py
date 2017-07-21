# -*- coding: utf-8 -*-
# © 2017 Igor V. Kartashov
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": 'SETIR sale',
    "version": "9.0.1.0",
    "summary": "módulo ventas para SETIR",
    "description": """
		i-vk
		v9.0.1.0
		ofertas para SETIR:
		las tarifas con el precio fijo incluyen el precio proveedor ademas del precio de venta (precio por defecto).
		las ofertas muestran además del precio de venta (precio unidad):
			a) precio proveedor
			b) margen setir (calculable = precio venta - precio proveedor)
			c) beneficio setir (calculable = margen setir * cantidad pedida)

		NOTA:
					1) al cambiar el precio venta o el precio proveedor se recalculan el margen y el beneficio setir
					2) al cambiar la cantidad pedida se aplica el precio tarif ade acuerdo con la cantidad
					3) al cambiar el proveedor se cambia la tarifa 
					4) el informe "Oferta" no mostrará los impuestos y totales

		IMPORTANTE:
					realizar las siguinetes operaciones:
					1) después de instalar el módulo es necesario asociar
						la unidad de medida creada para peajes "€-%" a la categoria creada "Porcentaje"
						(sin esto las tarifas de peaje no se van a asociarse correctamente)
					2) cada tarifa creada debe ser asociada al proveedor correspondiente
					3) es necesario estrablecer el resposnsable del dpto de operaciones,
						ya que es el quien tien permisos para gestionar los pedidos de venta
		CONFIGURACION OFERTA:
		1)	plantilla nombre oferta: oferta_${object.name}_${object.partner_id.name}
		2)	mail_from: ${(object.user_id.email and '%s <%s>' % (object.user_id.name, object.user_id.email) or '')|safe}
			mail_to: ${object.partner_id.email}
			mail_cc: ${object.user_id.email}, sistemas@setir.es
			responder: ${object.user_id.email}
		3)	poner el ID de la plantilla mail en "ID de registro" en Configuracion-Technical-Sequences & Identifieres-External identifiers-
			[id= "sale.email_template_edi_sale", model name=mail.template]
	""",
    "author": "Igor V. Kartashov",
    "license": "AGPL-3",
    "website": "http://crm.setir.es",
    "category": "Sale",
    "depends": [
				'base',
				'sale',
				'website_quote',
				],
    "data": [
		"views/setirSaleOrderForm.xml",
		"data/data.xml",
		"reports/setirOfertaReport.xml",
		"reports/setirSaleTimespanReport.xml",
    ],
    "installable": True,
    "application": True,
	"auto_install": False,
    "price": 0.00,
    "currency": "EUR"
}