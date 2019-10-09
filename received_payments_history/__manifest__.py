# -*- coding: utf-8 -*-
{
    'name': "Account Payment History",

    'summary': """
        Registration of payment history.""",

    'description': """
        
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_payment_history.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}