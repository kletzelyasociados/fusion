# -*- coding: utf-8 -*-

from odoo import models, fields, api

from xml.dom import minidom
import base64
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


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
    def import_xml_data(self):

        if not self.x_xml_file:
            raise Warning('No hay ningún archivo XML adjunto!')

        else:
            # The file is stored in odoo encoded in base64 bytes column, in order to get the information in the original way
            # It must have to be decoded in the same base.
            xml = minidom.parseString(base64.b64decode(self.x_xml_file))

            # Obtengo el nodo del emisor
            emisor_items = xml.getElementsByTagName("cfdi:Emisor")

            # Obtengo los datos necesarios
            NombreEmisor = emisor_items[0].attributes['Nombre'].value
            RfcEmisor = emisor_items[0].attributes['Rfc'].value
            RegimenEmisor = emisor_items[0].attributes['RegimenFiscal'].value

            self.write({'UUID': xml.getElementsByTagName("tfd:TimbreFiscalDigital")[0].attributes['UUID'].value})
