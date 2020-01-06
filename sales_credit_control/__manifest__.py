# -*- coding: utf-8 -*-
{
    'name': "Credit Control",

    'summary': """
        In this module we will control the payments that we do for the requested financial credits""",

    'description': """
        In this module we will control the payments that we do for the requested financial credits
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '3.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_management', 'hr', 'sale_order_dates', 'sale_stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_form_customization.xml',
        'views/account_payment_form_customization.xml',
        'views/hr_employee_form_customization.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}