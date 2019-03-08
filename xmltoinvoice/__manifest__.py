# -*- coding: utf-8 -*-
{
    'name': "XMl to PO/Invoice",

    'summary': """
        Creation of Purchase Orders or Vendor Bill based on XML Data (Mexican CFDi)""",

    'description': """
        Creation of Purchase Orders or Vendor Bill based on XML Data (Mexican CFDi)
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Purchases',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase', 'account_accountant'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/purchase_views.xml',
        'views/account_invoice_view.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'application': True,
}