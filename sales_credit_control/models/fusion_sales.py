# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

from odoo.addons import decimal_precision as dp

from werkzeug.urls import url_encode

from datetime import date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Credit Control Page

    credit_payment_plan_id = fields.One2many('credit.payment.plan',
                                             'sale_order_id',
                                             string='Plan de Pagos',
                                             readonly=True,
                                             states={'draft': [('readonly', False)]})

    credit_payments_ids = fields.One2many('account.payment',
                                          'credit_sale_order_id',
                                          readonly=True,
                                          string='Pagos Realizados')

    credit_plan_total = fields.Float(string='Total Plan',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_credit_plan_total')

    credit_paid_total = fields.Float(string='Total Recibido',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_credit_paid_total')

    credit_open_total = fields.Float(string='Saldo Pendiente Total',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_credit_open_total')

    # Total por pagar
    @api.one
    @api.depends('credit_payment_plan_id.payment_amount')
    def _compute_credit_plan_total(self):
        self.credit_plan_total = sum(plan_line.payment_amount for plan_line in self.credit_payment_plan_id)

    # Total Pagado
    @api.one
    @api.depends('credit_payments_ids.amount')
    def _compute_credit_paid_total(self):
        self.credit_paid_total = sum(paid_line.amount for paid_line in self.credit_payments_ids)

    # Saldo por pagar
    @api.one
    @api.depends('credit_plan_total', 'credit_paid_total')
    def _compute_credit_open_total(self):
        self.credit_open_total = self.credit_plan_total - self.credit_paid_total


class account_payment(models.Model):
    _inherit = 'account.payment'

    credit_sale_order_id = fields.Many2one('sale.order',
                                    string='Orden de Venta',
                                    ondelete='restrict',
                                    index=True,
                                    track_visibility='onchange')


class CreditPaymentPlan(models.Model):
    _name = "credit.payment.plan"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Credits Payment Plan"

    partner_id = fields.Many2one('res.partner',
                                 string='Proveedor',
                                 change_default=True,
                                 required=True,
                                 track_visibility='onchange')

    payment_amount = fields.Float(string='Monto',
                                  required=True,
                                  digits=(16, 2),
                                  track_visibility='onchange')

    payment_type = fields.Selection([('terreno', 'Terreno'),('credit', 'Crédito Puente')], string='Tipo de Pago')

    sale_order_id = fields.Many2one('sale.order',
                                    string='Orden de Venta',
                                    ondelete='restrict',
                                    index=True,
                                    track_visibility='onchange')
