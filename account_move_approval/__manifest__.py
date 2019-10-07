# -*- coding: utf-8 -*-
{
    'name': "Account Move Approval",

    'summary': """
        In this module we do an implementation of approval process to avoid stupid movements.""",

    'description': """
        We detected a lot of manual movements that should not have been done, we create a point of revision with this module
    """,

    'author': "Manuel Fabela",
    'website': "https://www.linkedin.com/in/josemanuelvilchis/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_cancel'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_view_customization.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}