# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class account_payment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection([('draft', 'Borrador'),
                              ('posted', 'Validado'),
                              ('sent', 'Enviado'),
                              ('reconciled', 'Conciliado'),
                              ('cancelled', 'Cancelado'),
                              ('history', 'Histórico')],
                             readonly=True,
                             default='draft',
                             copy=False,
                             string="Estado")

    def action_history(self):
        self.write({'state': 'history'})
