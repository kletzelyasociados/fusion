# -*- coding: utf-8 -*-

from odoo import models, fields, api

from xml.dom import minidom

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
    def generate_record_name(self):
        # Ventana para seleccionar archivo XML
        #filename = askopenfilename()
        filename = self.x_xml_file.decode('utf-8')

        # Conversión de archivo a objeto manipulable de python
        mydoc = minidom.parse(self.x_xml_file.read())



        # Obtengo el nodo del emisor
        emisor_items = mydoc.getElementsByTagName("cfdi:Emisor")

        # Obtengo los datos necesarios
        NombreEmisor = emisor_items[0].attributes['Nombre'].value
        RfcEmisor = emisor_items[0].attributes['Rfc'].value
        RegimenEmisor = emisor_items[0].attributes['RegimenFiscal'].value

        self.write({'UUID':NombreEmisor})