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
                                    compute='_compute_department',
                                    store=True,
                                    )

    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Cuenta Analítica',
                                          compute='_compute_analytic_account')

    analytic_tag_ids = fields.Many2many('account.analytic.tag',
                                        string='Etiquetas Analíticas',
                                        compute='_compute_analytic_tag')

    @api.depends('payment_requested_by_id')
    def _compute_department(self):
        for invoice in self:
            if not invoice.payment_requested_by_id:
                employee = self.env['hr.employee'].search([('user_id', '=', invoice.create_uid.id)])
                if employee:
                    invoice.department_id = employee[0].department_id.id
                else:
                    invoice.department_id = None

    @api.depends('invoice_line_ids')
    def _compute_analytic_account(self):
        for invoice in self:
            if invoice.invoice_line_ids:
                invoice.account_analytic_id = invoice.invoice_line_ids[0].account_analytic_id.id

    @api.depends('invoice_line_ids')
    def _compute_analytic_tag(self):
        for invoice in self:
            if invoice.invoice_line_ids:
                invoice.analytic_tag_ids = [(4, invoice.invoice_line_ids[0].analytic_tag_ids.id)]

    @api.multi
    def action_invoice_payment_request(self):
        self.write({'payment_requested_by': self.env.uid, 'state': 'payment_request'})
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
            self.write({'department_id': employee[0].department_id.id})
        else:
            raise ValidationError('El empleado no se encuentra dado de alta')

    @api.multi
    def action_invoice_approve(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
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
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
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
        current_user = self.env['res.users'].browse(self.env.uid)
        if current_user.has_group('account.invoice accountant') or current_user.has_group('account.invoice'):
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
        else:
            raise ValidationError('No tienes los permisos necesarios para validar facturas')

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

