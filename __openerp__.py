# -*- coding: utf-8 -*-
# © 2017 Igor V. Kartashov
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": 'SETIR sale',
    "version": "9.0.1.0",
    "summary": "particularización del módulo ventas para SETIR",
    "description": """
		i-vk
		v9.0.1.0
		sales specific data for SETIR: sale orders
	""",
    "author": "Igor V. Kartashov",
    "license": "AGPL-3",
    "website": "http://crm.setir.es",
    "category": "Sale",
    "depends": [
				'base',
				'sale',
				],
    "data": [
		"views/setirSaleOrderForm.xml",
    ],
    "installable": True,
    "application": True,
	"auto_install": False,
    "price": 0.00,
    "currency": "EUR"
}