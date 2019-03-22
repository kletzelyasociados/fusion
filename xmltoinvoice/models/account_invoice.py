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

    #UUID = fields.Text(string='Folio Fiscal')

    @api.multi
    def import_xml_data(self):

        if not self.x_xml_file:
            raise ValidationError('No hay ningún archivo XML adjunto!')

        else:
            # The file is stored in odoo encoded in base64 bytes column, in order to get the information in the original way
            # It must have to be decoded in the same base.

            xml = minidom.parseString(base64.b64decode(self.x_xml_file))

            # Obtengo el nodo del receptor
            receptor_items = xml.getElementsByTagName("cfdi:Receptor")

            # Obtengo nombre y RFC del receptor
            NombreReceptor = receptor_items[0].attributes['Nombre'].value
            RfcReceptor = receptor_items[0].attributes['Rfc'].value

            #Valido que la factura sea para la compañía actual
            if RfcReceptor == self.env.user.company_id.vat :

                # Obtengo el nodo del emisor
                emisor_items = xml.getElementsByTagName("cfdi:Emisor")

                # Obtengo los datos necesarios
                NombreEmisor = emisor_items[0].attributes['Nombre'].value
                RfcEmisor = emisor_items[0].attributes['Rfc'].value
                RegimenEmisor = emisor_items[0].attributes['RegimenFiscal'].value

                # Obtengo el nodo del comprobante
                invoice_items = xml.getElementsByTagName("cfdi:Comprobante")

                # Obtengo los datos principales de la factura
                try:
                    Serie = invoice_items[0].attributes['Serie'].value

                except:
                    Serie = ""

                try:
                    Folio = invoice_items[0].attributes['Folio'].value

                except:
                    Folio = xml.getElementsByTagName("tfd:TimbreFiscalDigital")[0].attributes['UUID'].value

                Fecha = invoice_items[0].attributes['Fecha'].value
                SubTotal = invoice_items[0].attributes['SubTotal'].value
                Moneda = invoice_items[0].attributes['Moneda'].value
                Total = invoice_items[0].attributes['Total'].value

                # Obtengo los nodos con la información de las líneas de factura
                invoice_line_items = xml.getElementsByTagName("cfdi:Concepto")

                #Busco al proveedor
                partner = self.env['res.partner'].search([["vat", "=", RfcEmisor]], limit=1)

                #Si no existe lo creo en odoo
                if not partner:

                    if RegimenEmisor == 612:
                        company_type = "person"
                    else:
                        company_type = "company"

                    fiscal_position = self.env['account.fiscal.position'].search(
                        [[("l10n_mx_edi_code", "=", RegimenEmisor)]], limit=1)

                    if not fiscal_position.id:
                        fiscal_position.id = 1

                    partner = self.env['res.partner'].create([{
                        "company_type": company_type, #person or company
                        "name": NombreEmisor,
                        "vat": RfcEmisor,
                        "country_id": 156, #México
                        "lang": "es_MX", #Español
                        "supplier": 1,
                        "customer": 0,
                        "property_account_position_id": fiscal_position.id,
                        "l10n_mx_type_of_operation": "85"
                    }])

                #Asigno los datos al documento
                self.write({'partner_id': partner.id,
                            'reference': Serie + " " + Folio,
                            'x_invoice_date_sat': Fecha})

                #Si tiene lineas de factura
                if self.invoice_line_ids:
                    #Cuento las lineas de factura de odoo y del XML
                    odoo_lines = 0

                    for lines in self.invoice_line_ids:
                        odoo_lines = odoo_lines + 1

                    xml_lines = len(invoice_line_items)
                    # Si son iguales solamente edito las de odoo
                    if odoo_lines == xml_lines:

                        for idx, line in enumerate(self.invoice_line_ids):

                            ValorUnitario = float(invoice_line_items[idx].attributes['ValorUnitario'].value)

                            try:
                                ValorUnitario = ValorUnitario - float(invoice_line_items[idx].attributes['Descuento'].value)
                            except:
                                ValorUnitario = ValorUnitario

                            line.write({
                                'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                'price_unit': ValorUnitario
                            })
                            line._set_taxes()

                    elif odoo_lines > xml_lines:

                        for idx, line in enumerate(self.invoice_line_ids):

                            try:

                                ValorUnitario = float(invoice_line_items[idx].attributes['ValorUnitario'].value)

                                try:
                                    ValorUnitario = ValorUnitario - float(invoice_line_items[idx].attributes['Descuento'].value)
                                except:
                                    ValorUnitario = ValorUnitario

                                line.write({
                                    'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                    'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                    'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                    'price_unit': ValorUnitario
                                })
                                line._set_taxes()

                            except:

                                line.unlink()

                    elif xml_lines > odoo_lines:

                        for idx, line in enumerate(self.invoice_line_ids):

                            ValorUnitario = float(invoice_line_items[idx].attributes['ValorUnitario'].value)

                            try:
                                ValorUnitario = ValorUnitario - float(
                                    invoice_line_items[idx].attributes['Descuento'].value)
                            except:
                                ValorUnitario = ValorUnitario

                            line.write({
                                'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                'price_unit': ValorUnitario
                            })
                            line._set_taxes()

                        for idx, line in enumerate(invoice_line_items):

                            if idx < odoo_lines:
                                continue

                            else:

                                ValorUnitario = float(line.attributes['ValorUnitario'].value)

                                try:
                                    ValorUnitario = ValorUnitario - float(line.attributes['Descuento'].value)
                                except:
                                    ValorUnitario = ValorUnitario

                                # Creación de la línea de factura
                                new_line = self.env['account.invoice.line'].create({
                                    'invoice_id': self.id,
                                    'product_id': 921,
                                    'name': line.attributes['Descripcion'].value,
                                    'account_id': 1977,
                                    'quantity': line.attributes['Cantidad'].value,
                                    'uom_id': self.getUOMID(line.attributes['ClaveUnidad'].value),
                                    'price_unit': ValorUnitario,
                                    'type': "in_invoice"
                                })

                                new_line._set_taxes()

                #Sino tiene lineas de factura
                else:
                    #Para cada concepto del XML creo una linea de factura en odoo
                    for line in invoice_line_items:

                        ValorUnitario = float(line.attributes['ValorUnitario'].value)

                        try:
                            ValorUnitario = ValorUnitario - float(line.attributes['Descuento'].value)
                        except:
                            ValorUnitario = ValorUnitario

                        #Creación de la línea de factura
                        new_line = self.env['account.invoice.line'].create({
                            'invoice_id': self.id,
                            'product_id': 921,
                            'name': line.attributes['Descripcion'].value,
                            'account_id': 1977,
                            'quantity': line.attributes['Cantidad'].value,
                            'uom_id': self.getUOMID(line.attributes['ClaveUnidad'].value),
                            'price_unit': ValorUnitario,
                            'type': "in_invoice"
                        })
                        new_line._set_taxes()

                    self.compute_taxes()

            #Si la factura no es de la compañia actual envío una alerta
            else:

                #Poner el valor en Null

                raise ValidationError('La factura no corresponde a ' + self.env.user.company_id.name
                                      + "\nLa factura está hecha a: " + NombreReceptor
                                      + " RFC: " + RfcReceptor)

    @api.multi
    def getUOMID(self, clave_unidad):

        try:
            # No funciona esta madre
            uom_sat = self.env['l10n_mx_edi.product.sat.code'].search(
                [[("code", "=", clave_unidad)]], limit=1)

            uom_odoo = self.env['product.uom'].search(
                [[("l10n_mx_edi_code_sat_id", "=", uom_sat.id)]], limit=1)

            return uom_odoo.id

        # Sino lo encuentra asigno la unida de medida "Servicio" con el id 31
        except:

            return 31
