from datetime import date, datetime, timedelta
from collections import defaultdict
from odoo import api, _, fields, models
from odoo.tools import date_utils
from odoo.osv import expression


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'
    _description = 'HR Work Entry Type'

    input_line_ids = fields.One2many(
        'work.entry.input', 'work_entry_id', string='Work Entry Inputs', store=True,
        readonly=False, states={'validated': [('readonly', True)], 'cancelled': [('readonly', True)], 'conflict': [('readonly', True)]})



class HrWorkEntryInput(models.Model):
    _name = 'work.entry.input'
    _description = 'work Entry Input'
    _order = 'work_entry_id, sequence'

    name = fields.Char(string="Description")
    work_entry_id = fields.Many2one('hr.work.entry', string='Work Entry', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Type', required=True, domain="['|', ('id', 'in', _allowed_input_type_ids), ('struct_ids', '=', False)]")
    _allowed_input_type_ids = fields.Many2many('hr.payslip.input.type', related='work_entry_id.employee_id.contract_id.structure_type_id.default_struct_id.input_line_type_ids')
    code = fields.Char(related='input_type_id.code', required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(
        string="Count")
    # there is no error message in work entry the window won't save if the contractor is out of contract
    contract_id = fields.Many2one( 'hr.contract',
        related='work_entry_id.contract_id', string='Contract',
        help="The contract for which apply this input")
    date_start = fields.Datetime(required=True, string='From, ')
    date_start = fields.Datetime(required=True, string='From', related='work_entry_id.date_start')
    date_stop = fields.Datetime( store=True, readonly=False, string='To', related='work_entry_id.date_stop')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('conflict', 'Conflict'),
        ('cancelled', 'Cancelled')
    ], default='draft', related='work_entry_id.state')
    
    
class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    
    def _get_work_input_ammount(self, date_from, date_to, domain=None):

        date_from = datetime.combine(date_from, datetime.min.time())
        date_to = datetime.combine(date_to, datetime.max.time()) + timedelta(days=1)
        work_data = defaultdict(int)

        # First, found work entry that didn't exceed interval.
        work_entries = self.env['work.entry.input'].read_group(
            self._get_work_hours_domain(date_from, date_to, domain=domain, inside=True),
            ['amount:sum(amount)'],
            ['input_type_id']
        )
        work_data.update({data['input_type_id'][0] if data['input_type_id'] else False: data['amount'] for data in work_entries})
        return work_data
    
    
    
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def _get_worked_entry_input_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        
        work_instant = self.contract_id._get_work_input_ammount(self.date_from, self.date_to, domain=domain)
        work_instant_ordered = sorted(work_instant.items(), key=lambda x: x[1])
        
        
        for input_type_id, instant in work_instant_ordered:
            work_entry_input_type = self.env['hr.payslip.input.type'].browse(input_type_id)
            attendance_line = {
                'input_type_id': input_type_id,
                'amount': instant,
            }
            res.append(attendance_line)
        return [(5, 0, 0)] + [(0, 0, vals) for vals in res]

    
        
    
    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        if self.env.context.get('salary_simulation'):
            return
        valid_slips = self.filtered(lambda p: p.employee_id and p.date_from and p.date_to and p.contract_id and p.struct_id)
        # Make sure to reset invalid payslip's worked days line
        invalid_slips = self - valid_slips
        invalid_slips.worked_days_line_ids = [(5, False, False)]
        # Ensure work entries are generated for all contracts
        generate_from = min(p.date_from for p in self)
        current_month_end = date_utils.end_of(fields.Date.today(), 'month')
        generate_to = max(min(fields.Date.to_date(p.date_to), current_month_end) for p in self)
        self.mapped('contract_id')._generate_work_entries(generate_from, generate_to)

        for slip in valid_slips:
            slip.write({'worked_days_line_ids': slip._get_new_worked_days_lines()})
            slip.write({'input_line_ids': slip._get_worked_entry_input_lines_values()})