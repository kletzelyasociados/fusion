# -*- coding: utf-8 -*-
{
    'name': "invoice_payment_process",

    'summary': """
        This module helps to determine if the requested payment proceeds.""",

    'description': """
        This module adds a functionality to request invoice payments. 
        It does an extra validation to check if the requested payment is approved by the corresponding manager and if 
        it's amount is lower than the Purchase Order to which it is related.
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'account','account_3way_match'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}