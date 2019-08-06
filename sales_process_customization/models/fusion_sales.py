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

    state = fields.Selection([
        ('draft', 'Cotización'),
        ('leader_approved', 'Autorización del Lider'),
        ('sent', 'Cotización Enviada'), # Verificación de Monto
        ('sale_request', 'Solicitud de Venta'),
        ('sale', 'Venta'), # Autorización de Alejandro
        ('folder_integration', 'Integración'), # Verificación de Pablo
        ('entitlement', 'Titulación'), # Verificación de Manuel Belman
        ('house_finished', 'Casa Terminada'), # Autorización de Luis Antonio
        ('quality_check', 'Recibida Post-venta'),  # Verificación Postventa
        ('house_paid', 'Casa Pagada'), # Verificación de Fernando
        ('deed', 'Escrituración'), # Autorización de Liliana
        ('done', 'Entregada'), # Verificación de Pablo Guerrero
        ('cancel_request', 'Solicitud de Cancelación'), # Autorización de Alejandro
        ('cancel', 'Cancelled'), # Autorización de Alejandro
    ], string='Estado',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        track_sequence=3,
        default='draft')

    # Payments Page
    payment_plan_id = fields.One2many('payment.plan', 'sale_order_id', string='Plan de Pagos',
        readonly=True, states={'draft': [('readonly', False)]})

    payments_ids = fields.One2many('account.payment', 'sale_order_id', readonly=True, string='Pagos Recibidos')

    plan_total = fields.Float(string='Total Plan',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_plan_total')

    plan_difference = fields.Float(string='Diferencia con Monto de Venta',
                                   store=True,
                                   readonly=True,
                                   digits=(16, 2),
                                   compute='_compute_sale_vs_plan')

    paid_total = fields.Float(string='Total Recibido',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_paid_total')

    open_total = fields.Float(string='Saldo Pendiente Total',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_open_total')

    open_total_by_date = fields.Float(string='Saldo Pendiente por Fecha',
                                      store=True,
                                      readonly=True,
                                      digits=(16, 2),
                                      compute='_compute_open_total_by_date')

    # Commissions Page

    commissions_ids = fields.One2many('sale.commissions', 'sale_order_id', readonly=True, string='Comisiones')

    # Entitlement Page

    general_data = fields.Binary(string='Hoja de datos generales',
                            copy=False,
                            track_visibility='onchange')

    credit_request = fields.Binary(string='Solicitud de crédito',
                            copy=False,
                            track_visibility='onchange')

    identification_id = fields.Binary(string='Identificación',
                            copy=False,
                            track_visibility='onchange')

    id_expiration_date = fields.Date(string='Fecha de Expiración',
                            copy=False,
                            track_visibility='onchange')

    fiscal_id = fields.Binary(string='Fiscal',
                            copy=False,
                            track_visibility='onchange')

    curp = fields.Binary(string='CURP',
                            copy=False,
                            track_visibility='onchange')

    proof_of_address = fields.Binary(string='Comprobante de domicilio',
                            copy=False,
                            track_visibility='onchange')

    birth_certificate = fields.Binary(string='Acta de nacimiento',
                            copy=False,
                            track_visibility='onchange')

    marriage_certificate = fields.Binary(string='Acta de matrimonio',
                            copy=False,
                            track_visibility='onchange')

    birth_certificate_2 = fields.Binary(string='Acta de nacimiento de conyugue',
                            copy=False,
                            track_visibility='onchange')

    sic = fields.Binary(string='Sociedad de información crediticia',
                            copy=False,
                            track_visibility='onchange')

    infonavit_conference = fields.Binary(string='Taller saber para decidir',
                            copy=False,
                            track_visibility='onchange')

    inst_certificate = fields.Binary(string='Carta de instrucción irrevocable',
                            copy=False,
                            track_visibility='onchange')

    pre_qualification_infonavit = fields.Binary(string='Precalificación de INFONAVIT',
                            copy=False,
                            track_visibility='onchange')

    ecotechnics = fields.Binary(string='Ecotecnias',
                            copy=False,
                            track_visibility='onchange')

    infonavit_account = fields.Binary(string='Hoja mi cuenta INFONAVIT',
                            copy=False,
                            track_visibility='onchange')

    salary_receipt = fields.Binary(string='Último recibo de nómina',
                            copy=False,
                            track_visibility='onchange')

    afore_account = fields.Binary(string='Estado de cuenta AFORE',
                            copy=False,
                            track_visibility='onchange')

    credit_bureau_report = fields.Binary(string='Reporte buró de crédito',
                            copy=False,
                            track_visibility='onchange')

    appraisal = fields.Binary(string='Avalúo',
                            copy=False,
                            track_visibility='onchange')

    salary_receipts = fields.Binary(string='Recibos de nómina',
                            copy=False,
                            track_visibility='onchange')

    bank_acount_receipts = fields.Binary(string='Estados de cuenta bancarios',
                            copy=False,
                            track_visibility='onchange')

    tax_declaration = fields.Binary(string='Declaraciones de Impuestos',
                            copy=False,
                            track_visibility='onchange')

    labor_voucher = fields.Binary(string='Carta Laboral',
                            copy=False,
                            track_visibility='onchange')

    @api.one
    @api.depends('payment_plan_id.payment_amount')
    def _compute_plan_total(self):
        self.plan_total = sum(plan_line.payment_amount for plan_line in self.payment_plan_id)

    @api.one
    @api.depends('amount_total', 'plan_total')
    def _compute_sale_vs_plan(self):
        self.plan_difference = self.amount_total - self.plan_total

    @api.one
    @api.depends('payments_ids.amount')
    def _compute_paid_total(self):
        self.paid_total = sum(paid_line.amount for paid_line in self.payments_ids)

    @api.one
    @api.depends('plan_total', 'plan_difference', 'paid_total')
    def _compute_open_total(self):
        if self.plan_difference == 0 and self.amount_total > 0:
            self.open_total = self.plan_total - self.paid_total
        else:
            self.open_total = 0

    @api.one
    @api.depends('plan_total', 'plan_difference', 'paid_total')
    def _compute_open_total_by_date(self):
        if self.plan_difference == 0 and self.amount_total > 0:

            plan_total_by_date = sum(plan_line.payment_amount for plan_line in
                                     self.payment_plan_id.filtered(lambda l: l.payment_date <= str(date.today())))

            paid_total_by_date = sum(paid_line.amount for paid_line
                                     in self.payments_ids.filtered(lambda l: l.payment_date <= str(date.today())))

            self.open_total_by_date = plan_total_by_date - paid_total_by_date
        else:

            self.open_total_by_date = 0

    """
    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})

        return self.env.ref('sale.action_report_saleorder') \
            .with_context({'discard_logo_check': True}).report_action(self)

    @api.multi
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        invoices_origin = {}
        invoices_name = {}

        # Keep track of the sequences of the lines
        # To keep lines under their section
        inv_line_sequence = 0
        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)

            # We only want to create sections that have at least one invoiceable line
            pending_section = None

            # Create lines in batch to avoid performance problems
            line_vals_list = []
            # sequence is the natural order of order_lines
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                    invoices_origin[group_key] = [invoice.origin]
                    invoices_name[group_key] = [invoice.name]
                elif group_key in invoices:
                    if order.name not in invoices_origin[group_key]:
                        invoices_origin[group_key].append(order.name)
                    if order.client_order_ref and order.client_order_ref not in invoices_name[group_key]:
                        invoices_name[group_key].append(order.client_order_ref)

                if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final):
                    if pending_section:
                        section_invoice = pending_section.invoice_line_create_vals(
                            invoices[group_key].id,
                            pending_section.qty_to_invoice
                        )
                        inv_line_sequence += 1
                        section_invoice[0]['sequence'] = inv_line_sequence
                        line_vals_list.extend(section_invoice)
                        pending_section = None

                    inv_line_sequence += 1
                    inv_line = line.invoice_line_create_vals(
                        invoices[group_key].id, line.qty_to_invoice
                    )
                    inv_line[0]['sequence'] = inv_line_sequence
                    line_vals_list.extend(inv_line)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoices[group_key]] |= order

            self.env['account.invoice.line'].create(line_vals_list)

        for group_key in invoices:
            invoices[group_key].write({'name': ', '.join(invoices_name[group_key]),
                                       'origin': ', '.join(invoices_origin[group_key])})
            sale_orders = references[invoices[group_key]]
            if len(sale_orders) == 1:
                invoices[group_key].reference = sale_orders.reference

        if not invoices:
            raise UserError(_(
                'There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))

        for invoice in invoices.values():
            invoice.compute_taxes()
            if not invoice.invoice_line_ids:
                raise UserError(_(
                    'There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_total < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            # Idem for partner
            so_payment_term_id = invoice.payment_term_id.id
            fp_invoice = invoice.fiscal_position_id
            invoice._onchange_partner_id()
            invoice.fiscal_position_id = fp_invoice
            # To keep the payment terms set on the SO
            invoice.payment_term_id = so_payment_term_id
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice, 'origin': references[invoice]},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices.values()]

    @api.multi
    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        return orders.write({
            'state': 'draft',
            'signature': False,
            'signed_by': False,
        })

    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})
    
    """

    @api.multi
    def action_quotation_send(self):

        if self.state == "leader_approved":
            self.write({'state': 'sent'})

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    """
    @api.multi
    def action_done(self):
        for order in self:
            tx = order.sudo().transaction_ids.get_last_transaction()
            if tx and tx.state == 'pending' and tx.acquirer_id.provider == 'transfer':
                tx._set_transaction_done()
                tx.write({'is_processed': True})
        return self.write({'state': 'done'})

    @api.multi
    def action_unlock(self):
        self.write({'state': 'sale'})
    """

    @api.multi
    def action_authorize(self):
        if self.state == 'draft':
            self.action_draft()
        elif self.state == 'sale_request':
            self.action_confirm()
        elif self.state == 'cancel_request':
            self.write({'state': 'cancel'})

    @api.multi
    def action_reject(self):
        if self.state == 'leader_approved':
            self.write({'state': 'draft'})
        elif self.state == 'sale_request':
            self.write({'state': 'draft'})
        elif self.state == 'sale':
            self.write({'state': 'draft'})
        elif self.state == 'folder_integration':
            self.write({'state': 'sale'})
        elif self.state == 'entitlement':
            self.write({'state': 'folder_integration'})
        elif self.state == 'house_finished':
            self.write({'state': 'entitlement'})
        elif self.state == 'quality_check':
            self.write({'state': 'house_finished'})
        elif self.state == 'deed' or self.state == 'house_paid':
            self.write({'state': 'quality_check'})
        else:
            return

    @api.multi
    def action_cancel_request(self):
        self.write({'state': 'cancel_request'})

    @api.multi
    def action_sale_request(self):
        self.write({'state': 'sale_request'})

    @api.multi
    def action_integration(self):
        self.write({'state': 'folder_integration'})

    @api.multi
    def action_entitlement(self):
        self.write({'state': 'entitlement'})

    @api.multi
    def action_finished_home(self):
        self.write({'state': 'house_finished'})

    @api.multi
    def action_quality_check(self):
        self.write({'state': 'quality_check'})

    @api.multi
    def action_paid(self):
        self.write({'state': 'house_paid'})

    @api.multi
    def action_deed(self):
        self.write({'state': 'deed'})

    @api.multi
    def action_update_commissions(self):
        return


class PaymentPlan(models.Model):
    _name = "payment.plan"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Customer Payment Plan"

    payment_date = fields.Date(string='Fecha de Pago',
                               required=True,
                               index=True,
                               copy=False,
                               track_visibility='onchange')

    payment_amount = fields.Float(string='Monto',
                                  required=True,
                                  digits=(16, 2),
                                  track_visibility='onchange')

    note = fields.Char(string='Nota',
                       copy=False,
                       track_visibility='onchange')

    sale_order_id = fields.Many2one('sale.order',
                                    string='Orden de Venta',
                                    ondelete='restrict',
                                    index=True,
                                    track_visibility='onchange')


class account_payment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order',
                                    string='Orden de Venta',
                                    ondelete='restrict',
                                    index=True,
                                    track_visibility='onchange')


class Employee(models.Model):
    _inherit = 'hr.employee'

    commission_rate = fields.Float(string='Tarifa de Comisión',
                                   store=True,
                                   digits=(1, 3))

    commissions_ids = fields.One2many('sale.commissions', 'employee_id', readonly=True, string='Comisiones')


class Commissions(models.Model):
    _name = "sale.commissions"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Comisiones de Ventas"

    sale_order_id = fields.Many2one('sale.order',
                                    string='Orden de Venta',
                                    ondelete='restrict',
                                    index=True,
                                    track_visibility='onchange')

    employee_id = fields.Many2one('hr.employee',
                                  string='Empleado',
                                  ondelete='restrict',
                                  index=True,
                                  track_visibility='onchange')

    payment_date = fields.Date(string='Fecha de Pago',
                               required=True,
                               index=True,
                               copy=False,
                               track_visibility='onchange')

    payment_amount = fields.Float(string='Monto',
                                  required=True,
                                  digits=(16, 2),
                                  track_visibility='onchange')

    note = fields.Char(string='Nota',
                       copy=False,
                       track_visibility='onchange')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('paid', 'Pagado'),
        ('cancel', 'Cancelled'),
    ], string='Estado',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        default='draft')

    voucher = fields.Binary(string='Comprobante',
                            copy=False,
                            track_visibility='onchange')
