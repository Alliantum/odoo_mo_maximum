from odoo import api, fields, models, _



class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    warning_message = fields.Html(compute="_compute_warning_message")

    @api.model
    def create(self, vals):
        # Checks if allow_exceed_max is checked and quantity is greater than allowed
        mo_id = self.env['mrp.production'].browse(vals.get('mo_id'))
        if not mo_id.allow_exceed_max and mo_id.product_id.max_production > 0:
            max_production = mo_id.product_id.max_production
            product_uom_qty = mo_id.product_uom_id._compute_quantity(vals.get('product_qty'), mo_id.product_id.uom_id)

            if product_uom_qty > max_production:
                vals['product_qty'] = max_production
                # Here is where the rest of the quantity gets converted into a new MO
                mo_id.copy(default={'product_qty': product_uom_qty - max_production})
        return super().create(vals)

    @api.onchange('product_qty')
    def onchange_product_qty_max(self):
        for wiz in self:
            mo = wiz.mo_id
            if not mo.allow_exceed_max and mo.product_id.max_production and mo.product_uom_id._compute_quantity(wiz.product_qty, mo.product_id.uom_id) > mo.product_id.max_production:
                return {
                    'warning': {
                        'title': _("Manufacturing Maximum Exceeded"),
                        'message': _(
                            "Producing %s %s exceeds the limit of %s %s for %s per a single Manufacturing Order.\n\n"
                            "If you really want to allow exceeding that maximum amount, please check the field 'Allow Exceed Max'."
                            " Otherwise a new Manufacturing Order will be created with the exceeded amounts.",
                            wiz.product_qty, mo.product_uom_id.name,
                            mo.product_id.max_production, mo.product_id.uom_id.name, mo.product_id.name,
                        )
                    }
                }

    @api.depends('product_qty')
    def _compute_warning_message(self):
        for wiz in self:
            mo = wiz.mo_id
            if not mo.allow_exceed_max and mo.product_id.max_production > 0:
                wiz.warning_message = _(
                    "<p>This product has a limit of %s %s to produce for a single Manufacturing Order",
                     mo.product_id.max_production, mo.product_id.uom_id.name
                )
            else:
                wiz.warning_message = False

