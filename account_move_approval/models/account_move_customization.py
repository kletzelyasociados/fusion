# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection([('draft', 'Borrador'),
                              ('post_request','Solicitud de Posteo'),
                              ('cancel_request', 'Solicitud de Posteo'),
                              ('posted', 'Validado'),
                              ('rejected', 'Rechazado')],
                             string='Estado',
                             required=True,
                             readonly=True,
                             copy=False,
                             default='draft',
                             track_visibility='onchange',
                             help='All manually created new journal entries are usually in the status \'Unposted\', '
                                  'but you can set the option to skip that status on the related journal. '
                                  'In that case, they will behave as journal entries automatically created by the '
                                  'system on document validation (invoices, bank statements...) and will be created '
                                  'in \'Posted\' status.')

    @api.multi
    def action_post_request(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
            if employee[0].job_id.name == 'Coordinador Contable' and employee[0].department_id.name == 'Administración y Finanzas':
                self.write({'state': 'post_request'})
            elif employee[0].job_id.name == 'Coordinador de Tecnologías de la Información' and employee[0].department_id.name == 'Tecnologías de la Información':
                self.post()
            else:
                raise ValidationError('No estás autorizado para hacer pólizas manuales')
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_post_cancel(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])
        if employee:
            if employee[0].job_id.name == 'Coordinador Contable' and employee[0].department_id.name == 'Administración y Finanzas':
                self.write({'state': 'cancel_request'})
            elif employee[0].job_id.name == 'Coordinador de Tecnologías de la Información' and employee[0].department_id.name == 'Tecnologías de la Información':
                self.button_cancel()
            else:
                raise ValidationError('No estás autorizado para cancelar pólizas manuales')
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_approve(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])

        if employee:
            if employee[0].job_id.name == 'Gerente de Finanzas y Administración' and employee[0].department_id.name == 'Administración y Finanzas':
                if self.state == 'post_request':
                    self.post()
                elif self.state == 'cancel_request':
                    self.button_cancel()

            elif employee[0].job_id.name == 'Coordinador de Tecnologías de la Información' and employee[0].department_id.name == 'Tecnologías de la Información':
                if self.state == 'post_request':
                    self.post()
                elif self.state == 'cancel_request':
                    self.button_cancel()

            else:
                raise ValidationError('No tienes permisos para autorizar movimientos de pólizas manuales')
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')

    @api.multi
    def action_reject(self):
        employee = self.env['hr.employee'].search([('work_email', '=', self.env.user.email)])

        if employee:
            if employee[0].job_id.name == 'Gerente de Finanzas y Administración' and employee[0].department_id.name == 'Administración y Finanzas':
                if self.state == 'post_request':
                    self.write({'state': 'draft'})
                elif self.state == 'cancel_request':
                    self.write({'state': 'posted'})

            elif employee[0].job_id.name == 'Coordinador de Tecnologías de la Información' and employee[0].department_id.name == 'Tecnologías de la Información':
                if self.state == 'post_request':
                    self.write({'state': 'draft'})
                elif self.state == 'cancel_request':
                    self.write({'state': 'posted'})

            else:
                raise ValidationError('No tienes permisos para autorizar movimientos de pólizas manuales')
        else:
            raise ValidationError('El empleado no se encuentra dado de alta, o el correo electrónico en el empleado no es el mismo que el del usuario')
