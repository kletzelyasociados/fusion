# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
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

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError("The field Vendor is required, please complete it to validate the Vendor Bill.")
        if to_open_invoices.filtered(lambda inv: inv.state not in ('draft','approved_by_manager')):
            raise UserError("Invoice must be in draft state or approved by manager in order to validate it.")
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
            raise UserError("Invoice must be cancelled or payment rejected in order to reset it to draft.")
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

    @api.multi
    def action_invoice_approve(self):
        self.write({'state': 'approved_by_manager'})


    @api.multi
    def action_invoice_reject(self):
        self.write({'state': 'payment_rejected'})


    @api.multi
    def action_invoice_payment_request(self):
        self.write({'state': 'payment_request'})
