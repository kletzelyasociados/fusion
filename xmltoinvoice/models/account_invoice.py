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
    _inherit = ["account.invoice"]

    UUID = fields.Text(string='Folio Fiscal')

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
            if RfcReceptor == self.env.user.company_id.vat:

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
                        [[("l10n_mx_edi_code", "=", RegimenEmisor),
                          ("company_id", "=", self.env.user.company_id)]], limit=1)

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

                    odoo_lines = 0

                    for lines in self.invoice_line_ids:
                        odoo_lines = odoo_lines + 1

                    xml_lines = len(invoice_line_items)

                    if odoo_lines == xml_lines:

                        for idx, line in enumerate(self.invoice_line_ids):

                            line.write({
                                'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                'price_unit': float(invoice_line_items[idx].attributes['ValorUnitario'].value)
                            })
                            line._set_taxes()

                    elif odoo_lines > xml_lines:

                        for idx, line in enumerate(self.invoice_line_ids):

                            try:
                                line.write({
                                    'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                    'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                    'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                    'price_unit': float(invoice_line_items[idx].attributes['ValorUnitario'].value)
                                })
                                line._set_taxes()

                            except:

                                line.unlink()

                    elif xml_lines > odoo_lines:

                        difference = xml_lines-odoo_lines

                        for idx, line in enumerate(self.invoice_line_ids):

                            line.write({
                                'name': invoice_line_items[idx].attributes['Descripcion'].value,
                                'quantity': invoice_line_items[idx].attributes['Cantidad'].value,
                                'uom_id': self.getUOMID(invoice_line_items[idx].attributes['ClaveUnidad'].value),
                                'price_unit': float(invoice_line_items[idx].attributes['ValorUnitario'].value)
                            })
                            line._set_taxes()

                        for line in range(invoice_line_items-difference, invoice_line_items):
                            # Obtengo el id de la unidad de medida de odoo correspondiente al que trae el XML
                            try:

                                uom_sat = self.env['l10n_mx_edi.product.sat.code'].search(
                                    [[("code", "=", line.attributes['ClaveUnidad'].value)]], limit=1)

                                uom_odoo = self.env['product.uom'].search(
                                    [[("l10n_mx_edi_code_sat_id", "=", uom_sat.id)]], limit=1)
                            # Sino lo encuentra asigno la unida de medida "Servicio" con el id 31
                            except:

                                uom_odoo.id = 31

                            # Creación de la línea de factura
                            self.env['account.invoice.line'].create({
                                'invoice_id': self.id,
                                'product_id': 921,
                                'name': line.attributes['Descripcion'].value,
                                'account_id': 1977,
                                'quantity': line.attributes['Cantidad'].value,
                                'uom_id': uom_odoo.id,
                                'price_unit': float(line.attributes['ValorUnitario'].value),
                                'type': "in_invoice"
                            })

                            line._set_taxes()

                #Sino tiene lineas de factura
                else:
                    #Para cada concepto del XML creo una linea de factura en odoo
                    for line in invoice_line_items:

                        #Creación de la línea de factura
                        self.env['account.invoice.line'].create({
                            'invoice_id': self.id,
                            'product_id': 921,
                            'name': line.attributes['Descripcion'].value,
                            'account_id': 1977,
                            'quantity': line.attributes['Cantidad'].value,
                            'uom_id': self.getUOMID(line.attributes['ClaveUnidad'].value),
                            'price_unit': float(line.attributes['ValorUnitario'].value),
                            'type': "in_invoice"
                        })

                    self.compute_taxes()

            #Si la factura no es de la compañia actual envío una alerta
            else:

                #Poner el valor en Null

                raise ValidationError('La factura no corresponde a ' + self.env.user.company_id.name
                                      + "\nLa factura está hecha a: " + NombreReceptor
                                      + " RFC: " + RfcReceptor)

    @api.multi
    def getUOMID(self, clave_unidad):

        #try:

        #uom_sat = self.env['l10n_mx_edi.product.sat.code'].search(
        #    [[("code", "=", "XBJ")]])

        #uom_odoo = self.env['product.uom'].search(
        #    [[("l10n_mx_edi_code_sat_id", "=", uom_sat[0].id)]])

        uom_odoo = self.env['account.invoice.line.product.uom'].search(
            [[("l10n_mx_edi_code_sat_id", "=", 53525)]])

        return uom_odoo.id

        # Sino lo encuentra asigno la unida de medida "Servicio" con el id 31
        #except:

        #return 31


class OrderLine():

    def __init__(self, product_id, name, date_planned, product_qty, product_uom, price_unit):

        self.order_line_dictionary = {
            "product_id": product_id,
            "name": name,
            "date_planned": date_planned,
            "product_qty": product_qty,
            "product_uom": product_uom,
            "price_unit": price_unit,

            #Automation in odoo to calculate taxes
            #for order_line in records:
                #order_line._compute_tax_id()
        }

        self.order_tuple = tuple((0, 1, self.order_line_dictionary))


    #FInd taxes Id desptite I am not allowed to set it by this method.


class PurchaseOrder():

    def __init__(self, state, partner_id, partner_ref, date_order, order_lines):
        self.purchase_order_dictionary = {
            "state": state,
            "partner_id": partner_id,
            "partner_ref": partner_ref,
            "date_order": date_order,
            "order_line": order_lines
        }

        self.purchase_orders_list = []

    def addPurchaseOrder(self):
        self.purchase_orders_list.append(self.purchase_order_dictionary)

    def createPurchaseOrder(self, connection):
        connection.ODOO_OBJECT.execute_kw(
            connection.DATA
            , connection.UID
            , connection.PASS
            , "purchase.order"
            , 'create'
            , self.purchase_orders_list)
        messagebox.showinfo(title="PO Creation", message="PO Created successfully!")

    """
       def _compute_tax_id(self):
           for line in self:
               fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
               # If company_id is set, always filter taxes by the company
               taxes = line.product_id.supplier_taxes_id.filtered(
                   lambda r: not line.company_id or r.company_id == line.company_id)
               line.taxes_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_id) if fpos else taxes

       def map_tax(self, taxes):
           result = taxes.browse()
           result = set()
           for tax in taxes:
               found = False
               for t in self.tax_ids:
                   if t.tax_src_id == tax:
                       result |= t.tax_dest_id
                       found = True
               if not found:
                   if t.tax_dest_id:
                       result |= t.tax_dest_id
                   break
               else:
                   result |= tax
           return result

       def onchange_product_id(self):
           result = {}
           if not self.product_id:
               return result

           # Reset date, price and quantity since _onchange_quantity will provide default values
           self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
           self.price_unit = self.product_qty = 0.0
           self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
           result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

           product_lang = self.product_id.with_context(
               lang=self.partner_id.lang,
               partner_id=self.partner_id.id,
           )
           self.name = product_lang.display_name
           if product_lang.description_purchase:
               self.name += '\n' + product_lang.description_purchase

           fpos = self.order_id.fiscal_position_id
           if self.env.uid == SUPERUSER_ID:
               company_id = self.env.user.company_id.id
               self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
           else:
               self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

           self._suggest_quantity()
           self._onchange_quantity()

           return result

   """  # Métodos de odoo para asignación de impuestos a lineas de PO


class InvoiceLine():

    def __init__(self, product_id, name, account_id, quantity, uom_id, price_unit):

        self.invoice_line_dictionary = {
            "product_id": product_id,
            "name": name,
            "account_id": account_id,
            "quantity": quantity,
            "uom_id": uom_id,
            "price_unit": price_unit,
            "type": "in_invoice"

        }

        self.invoice_tuple = tuple((0, 0, self.invoice_line_dictionary))


    #FInd taxes Id desptite I am not allowed to set it by this method.


class Invoice():

    def __init__(self, partner_id, reference, x_invoice_date_sat, invoice_line_ids):
        self.invoice_dictionary = {
            "partner_id": partner_id,
            "reference": reference,
            "x_invoice_date_sat": x_invoice_date_sat,
            "invoice_line_ids": invoice_line_ids,
            "type": "in_invoice"
        }

        self.invoice = []

    def addInvoice(self):
        self.invoice.append(self.invoice_dictionary)

    def createInvoice(self, connection):
        connection.ODOO_OBJECT.execute_kw(
            connection.DATA
            , connection.UID
            , connection.PASS
            , 'account.invoice'
            , 'create'
            , self.invoice)
        messagebox.showinfo(title="Invoice Creation", message="Invoice Created successfully!")


class Getters():


    @api.multi
    def getTaxes(self, TasaoCuota, product_id):  # Falta de adaptar
        try:

            print("Getting SAT Unit of Measure Id")
            odoo_filter = [[("amount", "=", int(TasaoCuota * 10)), ("type_tax_use", "=", "Compras")]]
            tax_id = self.connection.ODOO_OBJECT.execute_kw(
                self.connection.DATA
                , self.connection.UID
                , self.connection.PASS
                , 'account.tax'
                , 'search'
                , odoo_filter)

            return tax_id

        except:

            return product_id.supplier_taxes_id

    @api.multi
    def getAccount(self, code):  # Falta de adaptar

        print("Getting Account Id")
        odoo_filter = [[("code", "=", code), ("company_id", "=", 1)]]
        account_id = self.connection.ODOO_OBJECT.execute_kw(
            self.connection.DATA
            , self.connection.UID
            , self.connection.PASS
            , 'account.account'
            , 'search'
            , odoo_filter)

        return account_id[0]