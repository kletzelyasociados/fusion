# -*- coding: utf-8 -*-
from xml.dom import minidom
import base64
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import re
from odoo import models, fields, api
from datetime import datetime


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def binary_to_xml(self):
        self.ensure_one()
        if not self.x_xml_file:
            raise ValidationError('No hay ningún archivo XML adjunto!')

        else:
            try:
                # If the XML is ok can be parsed into a document object model
                '''The file is stored in odoo encoded in base64 bytes column, in order to get the information in 
                the original way, It must have to be decoded in the same base.'''

                xml = minidom.parseString(base64.b64decode(self.x_xml_file))

            except:
                # If the XML has ilegal characters, it has to be decoded in base 64
                decoded = base64.b64decode(self.x_xml_file)

                # Conversion to string so it han be handled by sub() function
                string = str(decoded, "utf-8")

                # Definition of ilegal characters in XML files
                ilegal_characters = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')

                # Replacement of ilegal characters in the string
                fixed_xml = ilegal_characters.sub('', string)

                # Now the fixed string can be parsed into a document object model without error
                xml = minidom.parseString(fixed_xml)

            return xml

    def map_xml_to_odoo_fields(self):

        xml = self.binary_to_xml()

        # Obtengo el nodo del receptor
        receptor_items = xml.getElementsByTagName("cfdi:Receptor")

        # Obtengo nombre y RFC del receptor
        NombreReceptor = receptor_items[0].attributes['Nombre'].value

        RfcReceptor = receptor_items[0].attributes['Rfc'].value

        # Valido que la factura sea para la compañía actual
        if RfcReceptor == self.env.user.company_id.vat:

            # Obtengo el nodo del emisor
            emisor_items = xml.getElementsByTagName("cfdi:Emisor")

            # Obtengo los datos necesarios
            try:
                NombreEmisor = emisor_items[0].attributes['Nombre'].value

            except:
                NombreEmisor = "FACTURA TIMBRADA SIN NOMBRE DE PROVEEDOR"

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
                Folio = Folio[-5:]

            reference = Serie + " " + Folio

            x_invoice_date_sat = invoice_items[0].attributes['Fecha'].value
            amount_untaxed = invoice_items[0].attributes['SubTotal'].value

            try:
                discount = invoice_items[0].attributes['Descuento'].value

            except:
                discount = 0

            try:
                taxes = xml.getElementsByTagName("cfdi:Impuestos")[len(xml.getElementsByTagName("cfdi:Impuestos"))-1].attributes['TotalImpuestosTrasladados'].value
            except:
                taxes = 0

            amount_total = invoice_items[0].attributes['Total'].value

            # Obtengo los nodos con la información de las líneas de factura
            invoice_line_ids = xml.getElementsByTagName("cfdi:Concepto")

            # Busco al proveedor
            partner = self.env['res.partner'].search([["vat", "=", RfcEmisor]], limit=1)

            # Si no existe lo creo en odoo
            if not partner:
                partner = self.create_partner(RegimenEmisor=RegimenEmisor, NombreEmisor=NombreEmisor, RfcEmisor=RfcEmisor)

            xml_mapped = MappedXml(reference=reference,
                                   x_invoice_date_sat=x_invoice_date_sat,
                                   amount_untaxed=amount_untaxed,
                                   discount=discount,
                                   taxes=taxes,
                                   amount_total=amount_total,
                                   invoice_line_ids=invoice_line_ids,
                                   partner=partner)

            return xml_mapped

        # Si la factura no es de la compañia actual envío una alerta
        else:

            raise ValidationError('La factura no corresponde a ' + self.env.user.company_id.name
                                  + "\nLa factura está hecha a: " + NombreReceptor
                                  + " RFC: " + RfcReceptor)

    def import_xml_data(self):
        self.ensure_one()

        xml = self.map_xml_to_odoo_fields()

        if self.state == 'draft':

            # Asigno los datos al documento
            self.write({'partner_id': xml.partner.id,
                        'reference': xml.reference,
                        'x_invoice_date_sat': xml.x_invoice_date_sat})

            if self.search([('type', '=', self.type), ('reference', '=', self.reference),
                            ('company_id', '=', self.company_id.id),
                            ('commercial_partner_id', '=', self.commercial_partner_id.id),
                            ('id', '!=', self.id)]):

                raise ValidationError("Se ha detectado una referencia de " + xml.partner.name +
                                      " duplicada: " + self.reference +
                                      " timbrada el " + xml.x_invoice_date_sat +
                                      " en el SAT por un monto de " +
                                      "${:,.2f}".format(xml.amount_total))

            xml_line_items = xml.invoice_line_ids

            # Si tiene lineas de factura
            if self.invoice_line_ids:
                # Cuento las lineas de factura de odoo y del XML
                odoo_lines = 0

                for lines in self.invoice_line_ids:
                    odoo_lines = odoo_lines + 1

                xml_lines = len(xml_line_items)
                # Si son iguales solamente edito las de odoo
                if odoo_lines == xml_lines:

                    for idx, line in enumerate(self.invoice_line_ids):

                        self.overwrite_invoice_line(line, xml_line_items, idx)

                elif odoo_lines > xml_lines:

                    for idx, line in enumerate(self.invoice_line_ids):

                        try:

                            self.overwrite_invoice_line(line, xml_line_items, idx)

                        except:

                            line.unlink()

                elif xml_lines > odoo_lines:

                    for idx, line in enumerate(self.invoice_line_ids):

                        self.overwrite_invoice_line(line, xml_line_items, idx)

                    for idx, line in enumerate(xml_line_items):

                        if idx < odoo_lines:

                            continue

                        else:

                            self.create_invoice_line(line)

            # Sino tiene lineas de factura
            else:

                # Para cada concepto del XML creo una linea de factura en odoo
                for line in xml_line_items:

                    self.create_invoice_line(line)

            self.compute_taxes()

        elif self.state == 'approved_by_manager' or self.state == 'open' or self.state == 'paid':
            if self.match_xml(xml):
                self.write({'partner_id': xml.partner.id,
                            'reference': xml.reference,
                            'x_invoice_date_sat': xml.x_invoice_date_sat})

    def overwrite_invoice_line(self, odoo_line, xml_line, i):

        odoo_line.write({
            'name': xml_line[i].attributes['Descripcion'].value,
            'quantity': xml_line[i].attributes['Cantidad'].value,
            'uom_id': self.get_uom(xml_line[i]),
            'invoice_line_tax_ids': self.get_tax_id(odoo_line, xml_line[i]),
            'price_unit': self.get_discounted_unit_price(xml_line[i])
        })

        odoo_line._compute_price()

    def create_invoice_line(self, xml_line):

        # Creación de la línea de factura
        new_line = self.env['account.invoice.line'].create({
            'invoice_id': self.id,
            'product_id': 921,
            'name': xml_line.attributes['Descripcion'].value,
            'account_id': 1977,
            'quantity': xml_line.attributes['Cantidad'].value,
            'uom_id':  self.get_uom(xml_line),
            'price_unit': self.get_discounted_unit_price(xml_line),
            'type': "in_invoice"
        })

        new_line.invoice_line_tax_ids = self.get_tax_id(new_line, xml_line)

        new_line._compute_price()

    def match_xml(self, xml):

        if self.partner_id.id != xml.partner.id:

            raise ValidationError("No coincide el Proveedor de la Factura Odoo con el del CFDi!" +
                                  "\nProveedor en la Factura: " + self.partner_id.name +
                                  "\nProveedor en el CFDi: " + xml.partner.name)

        if self.search([('type', '=', self.type), ('reference', '=', self.reference),
                        ('company_id', '=', self.company_id.id),
                        ('commercial_partner_id', '=', self.commercial_partner_id.id),
                        ('id', '!=', self.id)]):

                raise ValidationError("Se ha detectado una referencia de " + xml.partner.name +
                                      " duplicada: " + self.reference +
                                      " timbrada el " + xml.x_invoice_date_sat +
                                      " en el SAT por un monto de " +
                                      "${:,.2f}".format(xml.amount_total))

        if self.x_invoice_date_sat != xml.x_invoice_date_sat:

            raise ValidationError("No coincide la fecha de timbrado de la Factura Odoo con el del CFDi!" +
                                  "\nFecha de facturación del SAT en la Factura Odoo: " + self.x_invoice_date_sat +
                                  "\nFecha de timbrado en el CFDi: " + xml.x_invoice_date_sat)

        difference = self.amount_total - xml.amount_total

        if not (-.10 <= difference <= .10):

            raise ValidationError("No coincide el monto de factura!" +
                                  "\nMonto total en la Factura Odoo: " + "${:,.2f}".format(self.amount_total) +
                                  "\nMonto total en el CFDi: " + "${:,.2f}".format(xml.amount_total) +
                                  "\nVariación: " + "${:,.2f}".format(difference))

    def create_partner(self, RegimenEmisor, NombreEmisor, RfcEmisor):
        if RegimenEmisor == 612:
            company_type = "person"
            fiscal_position = 10
        else:
            company_type = "company"
            fiscal_position = 1

        partner = self.env['res.partner'].create({
            'company_type': company_type,
            'name': NombreEmisor,
            'vat': RfcEmisor,
            'country_id': 156,
            'lang': "es_MX",
            'supplier': 1,
            'customer': 0,
            'property_account_position_id': fiscal_position,
            'l10n_mx_type_of_operation': "85",
            'type': 'contact'
        })

        return partner

    def get_product_id(self):
        pass

    def get_account_id(self):
        return self.account_id

    def get_tax_id(self, odoo_line, xml_line):

        try:

            rate = float(xml_line.getElementsByTagName("cfdi:Traslado")[0].attributes['TasaOCuota'].value)

            if rate == 0:
                tax_id = self.env['account.tax'].search([["type_tax_use", "=", "purchase"],
                                                         ["company_id", "=", self.company_id.id],
                                                         ["amount", "=", rate],
                                                         ["name", "like", "0%"]], limit=1)

                if tax_id:

                    return [(6, 0, [tax_id.id])]

                else:

                    return odoo_line.product_id.supplier_taxes_id
            else:

                return odoo_line.product_id.supplier_taxes_id

        except:

            product_id = self.env['product.product'].search([["purchase_ok", "=", True],
                                                             ["company_id", "=", self.company_id.id],
                                                             ["supplier_taxes_id.name", "like", "EXENTO"]], limit=1)

            if product_id:

                odoo_line.product_id = product_id

                return odoo_line.product_id.supplier_taxes_id

            else:

                return odoo_line.product_id.supplier_taxes_id


    def get_uom(self, xml_line):

        try:

            odoo_code = self.env['product.uom'].search([["l10n_mx_edi_code_sat_id.code", "=", xml_line.attributes['ClaveUnidad'].value]], limit=1)

            return odoo_code.id

        except:

            odoo_code = self.env['product.uom'].search([["l10n_mx_edi_code_sat_id.code", "=", "E48"]], limit=1)

            return odoo_code.id

    def get_discounted_unit_price(self, xml_line):

        price_unit = float(xml_line.attributes['ValorUnitario'].value)

        try:

            unitary_discount = float(xml_line.attributes['Descuento'].value) / float(
                xml_line.attributes['Cantidad'].value)

            price_unit = price_unit - unitary_discount

        except:

            price_unit = price_unit

        return price_unit


class MappedXml:

    def __init__(self, reference, x_invoice_date_sat, amount_untaxed, discount, taxes, amount_total, invoice_line_ids, partner):
        self.reference = reference
        self.x_invoice_date_sat = str(datetime.strptime(x_invoice_date_sat, '%Y-%m-%dT%H:%M:%S').date())
        self.amount_untaxed = float(amount_untaxed)
        self.discount = float(discount)
        self.taxes = float(taxes)
        self.amount_total = float(amount_total)
        self.invoice_line_ids = invoice_line_ids
        self.partner = partner
