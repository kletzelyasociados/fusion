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
                                              track_visibility='onchange',
                                              store=True)

    department_id = fields.Many2one('hr.department',
                                    string='Departamento',
                                    track_visibility='onchange',
                                    compute='_compute_department',
                                    store=True)

    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Cuenta Analítica',
                                          compute='_compute_analytic_account',
                                          store=True)

    analytic_tag_ids = fields.Many2many('account.analytic.tag',
                                        string='Etiquetas Analíticas',
                                        compute='_compute_analytic_tag',
                                        store=True)

    amount_authorized = fields.Monetary(string='Monto Autorizado de Pago',
                                        compute='_compute_authorized_amount',
                                        track_visibility='onchange',
                                        store=True)

    amount_paid_by_line = fields.Float(string='Pagado por linea',
                                       store=True,
                                       readonly=True,
                                       digits=(16, 2),
                                       compute='_compute_paid_by_line')

    @api.depends('residual')
    def _compute_paid_by_line(self):
        for invoice in self:
            if invoice.state == 'open':
                invoice.amount_paid_by_line = (invoice.amount_total - invoice.residual) / len(invoice.invoice_line_ids)
            else:
                invoice.amount_paid_by_line = 0

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
                if invoice.invoice_line_ids[0].analytic_tag_ids:
                    invoice.analytic_tag_ids = [(4, invoice.invoice_line_ids[0].analytic_tag_ids[0].id)]

    @api.multi
    def action_invoice_payment_request(self):

        self.verify_invoice_line_match_brute_force()

        if self.x_xml_file:
            xml = self.map_xml_to_odoo_fields()

            self.match_xml(xml)

            self.write({'payment_requested_by': self.env.uid, 'state': 'payment_request'})
            employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
            if employee:
                self.write({'department_id': employee[0].department_id.id})
            else:
                raise ValidationError(
                    'El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

        else:

            self.write({'payment_requested_by': self.env.uid, 'state': 'payment_request'})
            employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
            if employee:
                self.write({'department_id': employee[0].department_id.id})
            else:
                raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')


    @api.multi
    def action_invoice_approve(self):
        approver = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if approver:
            #Si el empleado es gerente de urbanización y la factura es de obra:
            if approver[0].job_id.name == 'Gerente de Urbanización' and approver[0].department_id == self.department_id:
                self.write({'state': 'approved_by_leader'})
            elif self.department_id.manager_id == approver[0]:
                self.write({'state': 'approved_by_manager'})
            else:
                raise ValidationError('No estás autorizado a aprobar solicitudes del departamento: ' + self.department_id.name)
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_invoice_reject(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
            if employee[0].job_id.name == 'Gerente de Urbanización' and employee[0].department_id == self.department_id:
                self.write({'state': 'payment_rejected'})
            elif self.department_id.manager_id == employee[0]:
                self.write({'state': 'payment_rejected'})
            else:
                raise ValidationError('No estás autorizado a rechazar solicitudes del departamento: ' + self.department_id.name)
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
            if employee[0].job_id.name == 'Coordinador de Administración' or employee[0].department_id.name == 'Administración y Finanzas' or employee[0].department_id.name == 'Tecnologías de la Información':
                to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
                if to_open_invoices.filtered(lambda inv: not inv.partner_id):
                    raise UserError("The field Vendor is required, please complete it to validate the Vendor Bill.")
                if to_open_invoices.filtered(lambda inv: inv.state not in ('draft', 'approved_by_manager')):
                    raise UserError("La factura tiene que estar en borrador o pago aprobado por el gerente para poder validarla.")
                if to_open_invoices.filtered(
                        lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
                    raise UserError("You cannot validate an invoice with a negative total amount. You should create a credit note instead.")
                if to_open_invoices.filtered(lambda inv: not inv.account_id):
                    raise UserError('No account was found to create the invoice, be sure you have installed a chart of account.')
                self.verify_invoice_line_match_brute_force()
                to_open_invoices.action_date_assign()
                to_open_invoices.action_move_create()
                return to_open_invoices.invoice_validate()
            else:
                raise ValidationError('No tienes los permisos necesarios para validar facturas' +
                                      '\nDepartamento: ' + employee[0].department_id.name +
                                      '\nPuesto: ' + employee[0].job_id.name)
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state not in ('cancel', 'payment_request', 'approved_by_leader', 'approved_by_manager', 'payment_rejected')):
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

    @api.multi
    def get_purchase_orders(self):

        if self.invoice_line_ids:
            purchase_order_line = self.env['purchase.order.line'].search([('id', '=', self.invoice_line_ids[0].purchase_line_id.id)])
            if purchase_order_line:
                purchase_order = self.env['purchase.order'].search([('id', '=', purchase_order_line.order_id.id)])
                if purchase_order:
                    return purchase_order

    @api.multi
    def get_purchase_contract(self, purchase_order):

        if purchase_order.requisition_id:
            purchase_requisition = self.env['purchase.requisition'].search([('id', '=', purchase_order.requisition_id.id)])
            if purchase_requisition:
                return purchase_requisition
            else:
                return 'no hay contrato'
        else:
            return 'no esta relacionada a algún contrato'

    '''
    @api.multi
    def verify_invoice_match_brute_force(self):
        purchase_order = self.get_purchase_orders()

        if purchase_order.id:

            inv_total_amount = 0
            inv_paid_amount = 0
            inv_residual_amount = 0

            for invoice in purchase_order.invoice_ids:
                if invoice.filtered(lambda inv: inv.state not in ('draft', 'cancel', 'payment_rejected')):
                    inv_total_amount = inv_total_amount + invoice.amount_total
                    inv_residual_amount = inv_residual_amount + invoice.residual
                inv_paid_amount = inv_total_amount - inv_residual_amount

            if inv_total_amount + self.amount_total > purchase_order.amount_total:
                raise ValidationError('Monto mayor al de la Orden de Compra!!!' +
                                      '\nTotal de Orden de Compra: ' + '${:,.2f}'.format(purchase_order.amount_total) +
                                      '\nTotal de Facturas: ' + '${:,.2f}'.format(inv_total_amount) +
                                      '\nTotal Pagado: ' + '${:,.2f}'.format(inv_paid_amount) +
                                      '\nExcedente con esta Factura: ' + '${:,.2f}'.format((purchase_order.amount_total - inv_total_amount - self.amount_total)*-1)
                                      )

            # contract = self.get_purchase_contract(purchase_order)
    '''


    @api.multi
    def verify_invoice_line_match_brute_force(self):

        # Si la factura tiene lineas
        if self.invoice_line_ids:
            # Para cada línea de la factura
            Error = []
            for i, invoice_line in enumerate(self.invoice_line_ids):
                # Si viene de una PO
                if invoice_line.purchase_line_id:
                    # Obtener la línea de la PO
                    purchase_line = invoice_line.purchase_line_id

                    if purchase_line.order_id.state == "purchase":

                        # Extraer el monto total
                        purchase_line_total_amount = purchase_line.price_total
                        # Obtener las líneas de factura
                        purchase_line_invoice_lines = purchase_line.invoice_lines

                        inv_total_amount = 0

                        # Para cada linea de factura
                        for linea_de_factura in purchase_line_invoice_lines:
                            # Filtrar donde el estado sea diferente de borrador, cancelado o pago rechazado
                            if linea_de_factura.invoice_id.state == 'payment_request' or linea_de_factura.invoice_id.state == 'approved_by_leader' or linea_de_factura.invoice_id.state == 'approved_by_manager' or linea_de_factura.invoice_id.state == 'open' or linea_de_factura.invoice_id.state == 'paid':
                                # Sumar el monto total
                                inv_total_amount = inv_total_amount + linea_de_factura.price_total

                        if self.state == 'approved_by_manager':
                            residual = purchase_line_total_amount - inv_total_amount

                        else:
                            residual = purchase_line_total_amount - inv_total_amount - invoice_line.price_total

                        # Comparar con el monto de la línea de orden de compra, si es mayor asignar error al arreglo
                        if not residual > -.10:
                            Error.append('\nError en Línea de Factura No. ' + str(i+1) +
                                         ':- Orden de Compra Origen: ' + purchase_line.order_id.name +
                                         '\n********Monto de Línea de Orden de Compra: ' + '${:,.2f}'.format(purchase_line_total_amount) +
                                         '\n********Monto de Lineas de Factura Registradas: ' + '${:,.2f}'.format(inv_total_amount) +
                                         '\n********Monto de Linea de Factura No. ' + str(i+1) + ': ' + '${:,.2f}'.format(invoice_line.price_total) +
                                         '\n********Excedente con esta Línea de Factura: ' + '${:,.2f}'.format(residual*-1) +
                                         '\n')

                    else:

                        Error.append('\nError en Línea de Factura No. ' + str(i + 1) +
                                     ':- Orden de Compra Origen: ' + purchase_line.order_id.name +
                                     '\n********La orden de compra está bloqueada, ya no se pueden realizar solicitudes de pagos')

                else:

                    employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
                    if employee:
                        if employee[0].department_id.name == "Construcción de Obra" or employee[0].department_id.name == "Compras" or employee[0].department_id.name == "Proyectos":
                            Error.append('\nError en Línea de Factura No. ' + str(i + 1) +
                                         ':- No tiene orden de compra de origen: ')

                    else:
                        Error.append('\nNo tienes los permisos necesarios para solicitar pagos de facturas')

            if Error:
                raise ValidationError(Error)

    @api.depends('residual')
    def _compute_authorized_amount(self):
        self.ensure_one()
        if self.residual > 0:
            self.amount_authorized = 0



class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line.invoice_lines.invoice_id.state', 'order_line.invoice_lines.invoice_id.amount_paid_by_line')
    def _compute_paid_total(self):

        for order in self:

            if order.order_line:

                amount_paid = 0

                for line in order.order_line:

                    for invoice_line in line.invoice_lines:

                        if invoice_line.invoice_id.state == 'paid':

                            amount_paid = amount_paid + invoice_line.price_total

                        elif invoice_line.invoice_id.state == 'open':

                            amount_paid = amount_paid + invoice_line.invoice_id.amount_paid_by_line

                order.paid_total = amount_paid

    @api.depends('paid_total')
    def _compute_residual(self):
        for order in self:
            if order.paid_total > 0:
                order.residual = order.amount_total - order.paid_total

    paid_total = fields.Float(string='Total Pagado',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_paid_total')

    residual = fields.Float(string='Saldo',
                              store=True,
                              readonly=True,
                              digits=(16, 2),
                              compute='_compute_residual')

    @api.multi
    def verify_req_or_contract(self):

        if self.x_studio_field_tpsA4 or self.requisition_id:
            return True

        else:
            employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
            if employee:
                if employee[0].department_id.name == "Construcción de Obra" or employee[0].department_id.name == "Compras" or employee[0].department_id.name == "Proyectos":
                    raise ValidationError('La Orden de Compra no proviene de Requisición o Contrato')

            else:
                raise ValidationError('No tienes los permisos necesarios para solicitar ordenes de compra')

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            order.verify_req_or_contract()

            if order.company_id.po_double_validation == 'one_step' or (order.company_id.po_double_validation == 'two_step' and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id)) or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True
