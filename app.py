import os
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, send_file, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'bp_logger_secret_key' # Required for session storage

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class BPEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100))
    dob = db.Column(db.String(20))
    comment = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    systolic1 = db.Column(db.Integer)
    diastolic1 = db.Column(db.Integer)
    systolic2 = db.Column(db.Integer)
    diastolic2 = db.Column(db.Integer)

# Create tables on startup
with app.app_context():
    db.create_all()

# --- Helper Logic for 7-Day Blocks ---
def calculate_blocks(entries):
    if not entries:
        return []
    
    # Sort chronologically to calculate blocks correctly
    sorted_entries = sorted(entries, key=lambda x: x.timestamp)
    blocks = []
    current_block = {'entries': [], 'days_seen': set()}
    
    for entry in sorted_entries:
        entry_date = entry.timestamp.strftime('%d/%m/%Y')
        
        # If we have 7 days and this is a new 8th day, start a new block
        if len(current_block['days_seen']) == 7 and entry_date not in current_block['days_seen']:
            blocks.append(process_block_totals(current_block))
            current_block = {'entries': [], 'days_seen': set()}
        
        current_block['entries'].append(entry)
        current_block['days_seen'].add(entry_date)
        
    if current_block['entries']:
        blocks.append(process_block_totals(current_block))
        
    return list(reversed(blocks)) # Show newest blocks at the top

def process_block_totals(block_data):
    entries = block_data['entries']
    # Identify the first chronological day in this block
    days_sorted = sorted(list(block_data['days_seen']), key=lambda d: datetime.strptime(d, '%d/%m/%Y'))
    
    totals = None
    first_day = days_sorted[0] if days_sorted else None
    
    if len(days_sorted) == 7:
        totals = {'sys1': 0, 'dia1': 0, 'sys2': 0, 'dia2': 0}
        for e in entries:
            # Exclude the first day's entries from the total
            if e.timestamp.strftime('%d/%m/%Y') != first_day:
                totals['sys1'] += e.systolic1
                totals['dia1'] += e.diastolic1
                totals['sys2'] += e.systolic2
                totals['dia2'] += e.diastolic2
                
    return {
        'entries': reversed(entries), # Show newest entries in block first
        'totals': totals,
        'is_complete': len(days_sorted) == 7,
        'first_day_excluded': first_day
    }

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Use session if form fields are hidden, otherwise use form
        name = session.get('user_name') or request.form.get('name')
        dob = session.get('user_dob') or request.form.get('dob')
        comment = session.get('user_comment') or request.form.get('comment', '')

        session['user_name'] = name
        session['user_dob'] = dob
        session['user_comment'] = comment

        if not name or not dob:
            return "Error: Name and DOB required", 400

        new_entry = BPEntry(
            user_name=name, dob=dob, comment=comment,
            systolic1=int(request.form['sys1']),
            diastolic1=int(request.form['dia1']),
            systolic2=int(request.form['sys2']),
            diastolic2=int(request.form['dia2'])
        )
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('index'))

    all_data = BPEntry.query.all()
    blocks = calculate_blocks(all_data)
    return render_template('index.html', blocks=blocks)

@app.route('/edit/<int:id>', methods=['POST'])
def edit_entry(id):
    entry = BPEntry.query.get_or_404(id)
    entry.systolic1 = int(request.form.get('sys1'))
    entry.diastolic1 = int(request.form.get('dia1'))
    entry.systolic2 = int(request.form.get('sys2'))
    entry.diastolic2 = int(request.form.get('dia2'))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    entry = BPEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/reset_user')
def reset_user():
    session.clear()
    return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
def download():
    mode = request.form.get('mode')
    query = BPEntry.query
    if mode == 'range':
        start = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end = datetime.strptime(request.form['end_date'], '%Y-%m-%d').replace(hour=23, minute=59)
        query = query.filter(BPEntry.timestamp >= start, BPEntry.timestamp <= end)
    
    entries = query.order_by(BPEntry.timestamp.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date/Time', 'Name', 'DOB', 'Comment', 'Sys1', 'Dia1', 'Sys2', 'Dia2'])
    for e in entries:
        writer.writerow([e.timestamp.strftime('%d/%m/%Y %H:%M'), e.user_name, e.dob, e.comment, e.systolic1, e.diastolic1, e.systolic2, e.diastolic2])
    
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='bp_log.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
