from odoo import api, models


class CleanField(models.TransientModel):

    """Initial Settings."""

    _name = "clean.field"

    # ToDo can be removed after field is deleted

    def init_remove_field(self):
        """Entry function remove Field (called with new API)."""
        return self._remove_field()

    @api.model
    def _remove_field(self):
        """Removes the Field sale_date from the database."""
        self.env.cr.execute("""SELECT 1 FROM ir_model_fields
        WHERE model = 'sale.order' AND name='sale_date';""")
        fields = self.env.cr.fetchall()
        if fields:
            self.env.cr.execute("""DELETE FROM ir_model_fields 
            WHERE model = 'sale.order'
            AND name='sale_date'; 
            ALTER TABLE sale.order DROP COLUMN sale_date;""")
            self.env.cr.commit()
        return True