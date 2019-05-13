# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    state = fields.Selection([
            ('draft', 'Draft'),
            ('payment_request', 'Solicitud de Pago'),
            ('approved_by_leader', 'Aprobado por el Lider'),
            ('approved_by_manager', 'Aprobado por el Gerente'),
            ('payment_rejected', 'Pago Rechazado'),
            ('open', 'Open'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
            ], string='Status', index=True, readonly=True, default='draft',
                track_visibility='onchange', copy=False,
                help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
                     " * The 'Payment Request' status is used when a user wants to request to that invoice to be paid.\n"
                     " * The 'Approved by Leader' status is used when the Leader of the Payment Requester Approves the payment.\n"
                     " * The 'Approved by Manager' status is used when the Manager of the Payment Requester Approves the payment.\n"
                     " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
                     " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
                     " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
                     " * The 'Cancelled' status is used when user cancel invoice.")

    payment_requested_by_id = fields.Many2one('res.users',
                                              string='Pago solicitado por',
                                              track_visibility='onchange')

    department_id = fields.Many2one('hr.department',
                                    string='Departamento',
                                    track_visibility='onchange',
                                    default='_compute_department',
                                    store=True)

    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Cuenta Analítica',
                                          compute='_compute_analytic_account')

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Etiquetas Analíticas')

    @api.multi
    def _compute_department(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.created_by.email)])
        if len(employee) > 0:
            self.write({'department_id': employee[0].department_id.id})
        else:
            self.write({'department_id': None})

    @api.multi
    def _compute_analytic_account(self):
        if self.invoice_line_ids:
            self.write({'account_analytic_id': self.invoice_line_ids[0].account_analytic_id})

    @api.multi
    def _compute_analytic_tag(self):
        if self.invoice_line_ids:
            self.write({'analytic_tag_ids': self.invoice_line_ids[0].analytic_tag_ids})

    @api.multi
    def action_invoice_payment_request(self):
        self.write({'payment_requested_by': self.env.uid, 'state': 'payment_request'})
        employee = self.env['hr.employee'].search([('work_email', '=', self.payment_requested_by_id.email)])
        if len(employee) > 0:
            self.write({'department_id': employee[0].department_id.id})
        else:
            raise ValidationError('El empleado no se encuentra dado de alta')

    @api.multi
    def action_invoice_approve(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.uid.email)])
        if len(employee) > 0:
            if employee[0].job_id.name == 'Gerente de Urbanización':
                if employee[0].department_id == self.department_id:
                    self.write({'state': 'approved_by_leader'})
                else:
                    raise ValidationError('No estás autorizado a aprobar solicitudes del departamento: ' + self.department_id.name)
            elif employee[0].department_id.manager_id == employee[0]:
                if employee[0].department_id == self.department_id:
                    self.write({'state': 'approved_by_manager'})
                else:
                    raise ValidationError('No estás autorizado a aprobar solicitudes del departamento: ' + self.department_id.name)
            else:
                raise ValidationError('No estás autorizado para aprobar solicitudes de pago')

    @api.multi
    def action_invoice_reject(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.uid.email)])
        if len(employee) > 0:
            if employee[0].job_id.name == 'Gerente de Urbanización':
                if employee[0].department_id == self.department_id:
                    self.write({'state': 'payment_rejected'})
                else:
                    raise ValidationError('No estás autorizado a rechazar solicitudes del departamento: ' + self.department_id.name)
            elif employee[0].department_id.manager_id == employee[0]:
                if employee[0].department_id == self.department_id:
                    self.write({'state': 'payment_rejected'})
                else:
                    raise ValidationError(
                        'No estás autorizado a rechazar solicitudes del departamento: ' + self.department_id.name)
            else:
                raise ValidationError('No estás autorizado para rechazar solicitudes de pago')

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError("The field Vendor is required, please complete it to validate the Vendor Bill.")
        if to_open_invoices.filtered(lambda inv: inv.state not in ('draft','approved_by_manager')):
            raise UserError("La factura tiene que estar en borrador o pago aprobado por el gerente para poder validarla.")
        if to_open_invoices.filtered(
                lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
            raise UserError("You cannot validate an invoice with a negative total amount. You should create a credit note instead.")
        if to_open_invoices.filtered(lambda inv: not inv.account_id):
            raise UserError('No account was found to create the invoice, be sure you have installed a chart of account.')
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate()

    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state not in ('cancel','payment_rejected')):
            raise UserError("La factura tiene que estar cancelada o el pago rechazado para poder cambiar a borrador.")
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['ir.actions.report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.number, invoice.state = invoice.move_name, 'open'
                    attachment = self.env.ref('account.account_invoices').retrieve_attachment(invoice)
                if attachment:
                    attachment.unlink()
        return True

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('purchase_line_id.total')
    def _can_be_paid(self):
        """ Computes the 'release to pay' status of an invoice line, depending on
        the invoicing policy of the product linked to it, by calling the dedicated
        subfunctions. This function also ensures the line is linked to a purchase
        order (otherwise, can_be_paid will be set as 'exception'), and the price
        between this order and the invoice did not change (otherwise, again,
        the line is put in exception).
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        """
        po_total_amount = 0
        inv_total_amount = 0

        po_line_size = 0
        inv_line_size = 0

        for invoice_line in self:
            inv_line_size = inv_line_size + 1
            inv_total_amount = inv_total_amount + invoice_line.price_total
            if invoice_line.purchase_line_id:
                po_line_size = po_line_size + 1
                po_total_amount = po_total_amount + invoice_line.purchase_line_id.price_total

        if po_line_size > inv_line_size:
            if

        if po_line_size < inv_line_size:


        if po_line_size == inv_line_size:

        """

        for invoice_line in self:
            po_line = invoice_line.purchase_line_id

            if po_line:
                #po_total = po_total + po_line.price_total
                invoiced_qty = po_line.qty_invoiced
                received_qty = po_line.qty_received
                ordered_qty = po_line.product_qty

                # A price difference between the original order and the invoice results in an exception
                invoice_currency = invoice_line.currency_id
                order_currency = po_line.currency_id
                invoice_converted_price = invoice_currency.compute(invoice_line.price_unit, order_currency)
                if order_currency.compare_amounts(po_line.price_unit, invoice_converted_price) != 0:
                    invoice_line.can_be_paid = 'exception'
                    continue

                if po_line.product_id.purchase_method == 'purchase': # 'on ordered quantities'
                    invoice_line._can_be_paid_ordered_qty(invoiced_qty, received_qty, ordered_qty, precision)
                else: # 'on received quantities'
                    invoice_line._can_be_paid_received_qty(invoiced_qty, received_qty, ordered_qty, precision)

            else: # Serves as default if the line is not linked to any Purchase.
                invoice_line.can_be_paid = 'exception'

    def _can_be_paid_ordered_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        """
        Gives the release_to_pay status of an invoice line for 'on ordered
        quantity' billing policy, if this line's invoice is related to a purchase order.

        This function sets can_be_paid field to one of the following:
        'yes': the content of the line has been ordered and can be invoiced
        'no' : the content of the line hasn't been ordered at all, and cannot be invoiced
        'exception' : only part of the invoice has been ordered
        """
        if float_compare(invoiced_qty - self.quantity, ordered_qty, precision_digits=precision) >= 0:
            self.can_be_paid = 'no'
        elif float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        else:
            self.can_be_paid = 'exception'


    def _can_be_paid_received_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        """
        Gives the release_to_pay status of an invoice line for 'on received
        quantity' billing policy, if this line's invoice is related to a purchase order.

        This function sets can_be_paid field to one of the following:
        'yes': the content of the line has been received and can be invoiced
        'no' : the content of the line hasn't been received at all, and cannot be invoiced
        'exception' : ordered and received quantities differ
        """
        if float_compare(invoiced_qty, received_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        elif received_qty == 0 and float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0: # "and" part to ensure a too high billed quantity results in an exception:
            self.can_be_paid = 'no'
        else:
            self.can_be_paid = 'exception'

    can_be_paid = fields.Selection(
        _release_to_pay_status_list,
        compute='_can_be_paid',
        copy=False,
        store=True,
        string='Release to Pay')
