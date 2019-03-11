# -*- coding: utf-8 -*-

from odoo import models, fields, api

from xml.dom import minidom
import re

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

        print(filename)

        # Conversión de archivo a objeto manipulable de python
        #mydoc = minidom.parse(self.x_xml_file.decode('utf-8'))
        #mydoc = minidom.parseString(self.x_xml_file.decode('utf-8'))

        RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                         u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                         (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                          chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                          chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))
        x = re.sub(RE_XML_ILLEGAL, "", self.x_xml_file.decode('utf-8'))

        print(x)

        mydoc = minidom.parseString(x)

        print(mydoc)

        # Obtengo el nodo del emisor
        emisor_items = mydoc.getElementsByTagName("cfdi:Emisor")

        # Obtengo los datos necesarios
        NombreEmisor = emisor_items[0].attributes['Nombre'].value
        RfcEmisor = emisor_items[0].attributes['Rfc'].value
        RegimenEmisor = emisor_items[0].attributes['RegimenFiscal'].value

        self.write({'UUID':NombreEmisor})