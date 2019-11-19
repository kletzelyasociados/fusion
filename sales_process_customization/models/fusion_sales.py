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
        ('cancel', 'Cancelada'), # Autorización de Alejandro
    ], string='Estado',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        track_sequence=3,
        default='draft')

    hr_employee_id = fields.Many2one('hr.employee',
                                     string='Vendedor')

    deed_id = fields.Char(string='No. de Escritura')

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

    commissions_total = fields.Float(string='Total Comisiones',
                                     store=True,
                                     readonly=True,
                                     digits=(16, 2),
                                     compute='_compute_commissions_total')

    comm_paid_total = fields.Float(string='Total Pagado',
                                   store=True,
                                   readonly=True,
                                   digits=(16, 2),
                                   compute='_compute_comm_paid_total')

    comm_to_pay = fields.Float(string='Saldo Por Pagar',
                               store=True,
                               readonly=True,
                               digits=(16, 2),
                               compute='_compute_comm_to_pay')

    # Entitlement Page

    general_data = fields.Binary(string='Hoja de datos generales',
                            copy=False,
                            track_visibility='onchange')

    general_data_filename = fields.Char(string='Nombre del Archivo')

    credit_request = fields.Binary(string='Solicitud de crédito',
                            copy=False,
                            track_visibility='onchange')

    credit_request_expiration_date = fields.Date(string='Fecha de Expiración de Solicitud',
                                     copy=False,
                                     track_visibility='onchange')

    credit_request_filename = fields.Char(string='Nombre del Archivo')

    identification_id = fields.Binary(string='Identificación',
                            copy=False,
                            track_visibility='onchange')

    identification_id_filename = fields.Char(string='Nombre del Archivo')

    id_expiration_date = fields.Date(string='Fecha de Expiración',
                            copy=False,
                            track_visibility='onchange')

    fiscal_id = fields.Binary(string='Constancia de Situación Fiscal',
                            copy=False,
                            track_visibility='onchange')

    fiscal_id_expiration_date = fields.Date(string='Fecha de Expiración de Constancia',
                                                 copy=False,
                                                 track_visibility='onchange')

    fiscal_id_filename = fields.Char(string='Nombre del Archivo')

    curp = fields.Binary(string='CURP',
                            copy=False,
                            track_visibility='onchange')

    curp_filename = fields.Char(string='Nombre del Archivo')

    proof_of_address = fields.Binary(string='Comprobante de domicilio',
                            copy=False,
                            track_visibility='onchange')

    proof_of_address_expiration_date = fields.Date(string='Fecha de Expiración de Comprobante',
                                  copy=False,
                                  track_visibility='onchange')

    proof_of_address_filename = fields.Char(string='Nombre del Archivo')

    birth_certificate = fields.Binary(string='Acta de nacimiento',
                            copy=False,
                            track_visibility='onchange')

    birth_certificate_filename = fields.Char(string='Nombre del Archivo')

    marriage_certificate = fields.Binary(string='Acta de matrimonio',
                            copy=False,
                            track_visibility='onchange')

    marriage_certificate_filename = fields.Char(string='Nombre del Archivo')

    birth_certificate_2 = fields.Binary(string='Acta de nacimiento de conyugue',
                            copy=False,
                            track_visibility='onchange')

    birth_certificate_2_filename = fields.Char(string='Nombre del Archivo')

    sic = fields.Binary(string='Sociedad de Información Crediticia',
                            copy=False,
                            track_visibility='onchange')

    sic_filename = fields.Char(string='Nombre del Archivo')

    infonavit_conference = fields.Binary(string='Taller saber para decidir',
                            copy=False,
                            track_visibility='onchange')

    infonavit_conference_expiration_date = fields.Date(string='Fecha de Expiración de Taller',
                                                   copy=False,
                                                   track_visibility='onchange')

    infonavit_conference_filename = fields.Char(string='Nombre del Archivo')

    inst_certificate = fields.Binary(string='Carta de Instrucción Irrevocable',
                            copy=False,
                            track_visibility='onchange')

    inst_certificate_filename = fields.Char(string='Nombre del Archivo')

    pre_qualification_infonavit = fields.Binary(string='Precalificación de INFONAVIT',
                            copy=False,
                            track_visibility='onchange')

    pre_qualification_infonavit_filename = fields.Char(string='Nombre del Archivo')

    ecotechnics = fields.Binary(string='Ecotecnias',
                            copy=False,
                            track_visibility='onchange')

    ecotechnics_filename = fields.Char(string='Nombre del Archivo')

    infonavit_account = fields.Binary(string='Hoja mi cuenta INFONAVIT',
                            copy=False,
                            track_visibility='onchange')

    infonavit_account_filename = fields.Char(string='Nombre del Archivo')

    salary_receipt = fields.Binary(string='Último recibo de nómina',
                            copy=False,
                            track_visibility='onchange')

    salary_receipt_filename = fields.Char(string='Nombre del Archivo')

    afore_account = fields.Binary(string='Estado de cuenta AFORE',
                            copy=False,
                            track_visibility='onchange')

    afore_account_filename = fields.Char(string='Nombre del Archivo')

    credit_bureau_report = fields.Binary(string='Reporte buró de crédito',
                            copy=False,
                            track_visibility='onchange')

    credit_bureau_report_filename = fields.Char(string='Nombre del Archivo')

    appraisal = fields.Binary(string='Avalúo',
                            copy=False,
                            track_visibility='onchange')

    appraisal_expiration_date = fields.Date(string='Fecha de Expiración del Avalúo',
                                  copy=False,
                                  track_visibility='onchange')

    appraisal_filename = fields.Char(string='Nombre del Archivo')

    salary_receipts = fields.Binary(string='Recibos de nómina',
                            copy=False,
                            track_visibility='onchange')

    salary_receipts_expiration_date = fields.Date(string='Fecha de Recibos',
                                  copy=False,
                                  track_visibility='onchange')

    salary_receipts_filename = fields.Char(string='Nombre del Archivo')

    bank_acount_receipts = fields.Binary(string='Estados de cuenta bancarios',
                            copy=False,
                            track_visibility='onchange')

    bank_acount_receipts_expiration_date = fields.Date(string='Fecha de Expiración de Estados de Cuenta',
                                  copy=False,
                                  track_visibility='onchange')

    bank_acount_receipts_filename = fields.Char(string='Nombre del Archivo')

    tax_declaration = fields.Binary(string='Declaraciones de Impuestos',
                            copy=False,
                            track_visibility='onchange')

    tax_declaration_expiration_date = fields.Date(string='Fecha de Expiración de Declaraciones',
                                  copy=False,
                                  track_visibility='onchange')

    tax_declaration_filename = fields.Char(string='Nombre del Archivo')

    labor_voucher = fields.Binary(string='Carta Laboral',
                            copy=False,
                            track_visibility='onchange')

    labor_voucher_expiration_date = fields.Date(string='Fecha de Carta Laboral',
                                  copy=False,
                                  track_visibility='onchange')

    labor_voucher_filename = fields.Char(string='Nombre del Archivo')

    # Other Information Page

    sale_date = fields.Date(string='Fecha de Confirmación de Venta',
                                     copy=False,
                                     track_visibility='onchange')

    integration_date = fields.Date(string='Fecha de Comienzo de Integración',
                            copy=False,
                            track_visibility='onchange')

    entitlement_date = fields.Date(string='Fecha de Comienzo de Titulación',
                            copy=False,
                            track_visibility='onchange')

    house_finished_date = fields.Date(string='Fecha de Terminación de la Casa',
                            copy=False,
                            track_visibility='onchange')

    quality_check_date = fields.Date(string='Fecha de Recepción Postventa',
                            copy=False,
                            track_visibility='onchange')

    paid_date = fields.Date(string='Fecha de Pago Total',
                            copy=False,
                            track_visibility='onchange')

    deed_date = fields.Date(string='Fecha de Escrituración',
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

    @api.one
    @api.depends('commissions_ids.payment_amount')
    def _compute_commissions_total(self):
        self.commissions_total = sum(comm_line.payment_amount for comm_line in self.commissions_ids)

    @api.one
    @api.depends('commissions_ids.payment_amount')
    def _compute_comm_paid_total(self):
        self.comm_paid_total = sum(comm_line.payment_amount for comm_line in
                                   self.commissions_ids.filtered(lambda l: l.state == 'paid'))

    @api.one
    @api.depends('commissions_total', 'comm_paid_total')
    def _compute_comm_to_pay(self):
        self.comm_to_pay = self.commissions_total - self.comm_paid_total

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'leader_approved').with_context(tracking_disable=True).write({'state': 'sent'})
        return super(SaleOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    @api.multi
    def action_quotation_send(self):
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

    @api.multi
    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm()))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })

        return True

    @api.multi
    def action_authorize(self):
        if self.state == 'draft':
            self.write({'state': 'leader_approved'})
            self._action_confirm()
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

    voucher_filename = fields.Char(string='Nombre del Archivo del Comprobante')

    invoice_line_count = fields.Integer(string='No. de Líneas de Factura', compute='_get_invoiced', readonly=True)

    # @api.depends('state', 'order_line.invoice_status', 'order_line.invoice_lines')
    def _get_invoiced(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.

        # Ignore the status of the deposit product
        deposit_product_id = self.env['sale.advance.payment.inv']._default_product_id()
        line_invoice_status_all = [(d['order_id'][0], d['invoice_status']) for d in
                                   self.env['sale.order.line'].read_group(
                                       [('order_id', 'in', self.ids), ('product_id', '!=', deposit_product_id.id)],
                                       ['order_id', 'invoice_status'], ['order_id', 'invoice_status'], lazy=False)]
        for order in self:
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id').filtered(
                lambda r: r.type in ['out_invoice', 'out_refund'])
            # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
            # 'account.invoice.refund')
            # use like as origin may contains multiple references (e.g. 'SO01, SO02')
            refunds = invoice_ids.search([('origin', 'like', order.name), ('company_id', '=', order.company_id.id),
                                          ('type', 'in', ('out_invoice', 'out_refund'))])
            invoice_ids |= refunds.filtered(lambda r: order.name in [origin.strip() for origin in r.origin.split(',')])

            # Search for refunds as well
            domain_inv = expression.OR([
                ['&', ('origin', '=', inv.number), ('journal_id', '=', inv.journal_id.id)]
                for inv in invoice_ids if inv.number
            ])
            if domain_inv:
                refund_ids = self.env['account.invoice'].search(expression.AND([
                    ['&', ('type', '=', 'out_refund'), ('origin', '!=', False)],
                    domain_inv
                ]))
            else:
                refund_ids = self.env['account.invoice'].browse()

            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]

            if order.state not in ('sale', 'done'):
                invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                invoice_status = 'invoiced'
            elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
                invoice_status = 'upselling'
            else:
                invoice_status = 'no'

            order.update({
                'invoice_count': len(set(invoice_ids.ids + refund_ids.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids,
                'invoice_status': invoice_status
            })

        """

    @api.multi
    def action_draft(self):
        return True

    @api.multi
    def action_paid(self):
        return True

    @api.multi
    def action_cancel(self):
        return True

    @api.multi
    def action_view_invoice_line(self):
        return True
