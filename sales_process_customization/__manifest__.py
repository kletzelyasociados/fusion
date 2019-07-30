# -*- coding: utf-8 -*-
{
    'name': "Sales Process Customization",

    'summary': """
        In this module we add the needed functionality for the sales process.""",

    'description': """
        Sale states.
        Sale approval by manager.
        New fields to add files that we ask to the customers.
        Payment plan of customers.
        Commission calculation of sales team.
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_form_customization.xml'
        'views/account_payment_form_customization.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}