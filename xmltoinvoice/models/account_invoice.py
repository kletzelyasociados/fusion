# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class my_module(models.Model):
#     _name = 'my_module.my_module'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    UUID = fields.Text(string='Folio Fiscal')

    @api.one
    def generate_record_name(self):
        self.write({'UUID': '23I85FH9756743'})