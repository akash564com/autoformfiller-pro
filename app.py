from flask import Flask, render_template, request, send_file, redirect, url_for, session
from fpdf import FPDF
from datetime import datetime
import os, uuid, json
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)
new_user = {
    "email": request.form['email'],
    "password": generate_password_hash(request.form['password']),
    "name": request.form['name'],
    "dob": request.form['dob'],
    "address": request.form['address'],
    "pdfs": []
}

app = Flask(__name__)
import os, secrets
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
  # session support

UPLOAD_FOLDER = 'uploads'
PDF_FOLDER = 'static/generated_pdfs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

USER_DB = 'database/users.json'

# 🔹 Load exam form data
with open('exams.json') as f:
    exam_data = json.load(f)

# 🔹 User helpers
def load_users():
    with open(USER_DB) as f:
        return json.load(f)["users"]

def save_user(new_user):
    users = load_users()
    users.append(new_user)
    with open(USER_DB, "w") as f:
        json.dump({"users": users}, f, indent=2)

# --------------------
# ✅ ROUTES
# --------------------

@app.route('/')
def index():
    return render_template('index.html', exams=exam_data)

@app.route('/form/<exam_id>')
def exam_form(exam_id):
    if 'user' not in session:
        return redirect('/login')
    if exam_id not in exam_data:
        return "Form not found", 404
    return render_template('dynamic_exam_form.html', config=exam_data[exam_id], exam_id=exam_id, user=session['user'])

@app.route('/generate', methods=['POST'])
email = request.form['email']
password = request.form['password']
for user in load_users():
    if user["email"] == email and check_password_hash(user["password"], password):
        session['user'] = user
        return redirect('/')
def generate():
    if 'user' not in session:
        return redirect('/login')

    exam_id = request.args.get('exam_id', 'general')
    config = exam_data.get(exam_id, {})
    form_type = config.get("title", "General Application")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, form_type, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)

    user = session['user']

    for field in config.get('fields', []):
        name = field['name']
        label = field['label']
        if field['type'] == 'file':
            file = request.files[name]
            filepath = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
            file.save(filepath)
            if name == 'photo':
                pdf.image(filepath, x=160, y=20, w=30, h=30)
                pdf.ln(30)
            elif name == 'signature':
                pdf.image(filepath, x=150, y=pdf.get_y(), w=40, h=15)
                pdf.set_y(pdf.get_y() + 20)
                pdf.cell(0, 10, "Signature", align='R')
        else:
            value = request.form.get(name, '')
            pdf.cell(60, 10, f"{label}", border=1)
            pdf.cell(130, 10, value, border=1, ln=True)

    date_today = datetime.today().strftime("%d-%m-%Y")
    serial_no = str(uuid.uuid4())[:8]
    pdf.ln(10)
    pdf.cell(0, 10, f"Date: {date_today}   Serial No: {serial_no}", ln=True, align='C')

    username = session['user']['username']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_name = f"{username}_{exam_id}_{timestamp}.pdf"
    output_path = os.path.join(PDF_FOLDER, pdf_name)
    pdf.output(output_path)

    users = load_users()
    for u in users:
        if u['username'] == username:
            u.setdefault('pdfs', []).append(pdf_name)
            session['user']['pdfs'] = u['pdfs']
    with open(USER_DB, 'w') as f:
        json.dump({'users': users}, f, indent=2)

    return send_file(output_path, as_attachment=True)

@app.route('/upload_files', methods=['POST'])
def upload_files():
    if 'user' not in session:
        return redirect('/login')

    user = session['user']
    users = load_users()

    photo_file = request.files.get('photo')
    signature_file = request.files.get('signature')
    updated = False

    if photo_file and photo_file.filename:
        photo_name = f"{uuid.uuid4()}_{photo_file.filename}"
        photo_path = os.path.join('static/uploads', photo_name)
        photo_file.save(photo_path)
        user['photo'] = photo_name
        updated = True

    if signature_file and signature_file.filename:
        sign_name = f"{uuid.uuid4()}_{signature_file.filename}"
        sign_path = os.path.join('static/uploads', sign_name)
        signature_file.save(sign_path)
        user['signature'] = sign_name
        updated = True

    if updated:
        for u in users:
            if u['username'] == user['username']:
                u.update(user)
        with open(USER_DB, 'w') as f:
            json.dump({'users': users}, f, indent=2)
        session['user'] = user

    return redirect('/dashboard')

# --------------------
# ✅ AUTH SYSTEM
# --------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        new_user = {
            "username": request.form['username'],
            "password": request.form['password'],
            "name": request.form['name'],
            "dob": request.form['dob'],
            "address": request.form['address'],
            "pdfs": []
        }
        save_user(new_user)
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                session['user'] = user
                return redirect('/')
        return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', user=session['user'])

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        username = request.form['username']
        users = load_users()
        for user in users:
            if user['username'] == username:
                session['reset_user'] = username
                return redirect('/reset')
        return "User not found"
    return render_template('forgot.html')

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if 'reset_user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        new_pass = request.form['password']
        users = load_users()
        for user in users:
            if user['username'] == session['reset_user']:
                user['password'] = new_pass
        with open(USER_DB, 'w') as f:
            json.dump({'users': users}, f, indent=2)
        session.pop('reset_user', None)
        return "Password reset successful. <a href='/login'>Login</a>"

    return '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Reset Password</title>
      <style>
        body { background: #0f2027; color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
        form { background: rgba(255,255,255,0.1); padding: 30px; border-radius: 12px; backdrop-filter: blur(6px); }
        input { display: block; margin-bottom: 10px; padding: 10px; border-radius: 6px; border: none; width: 250px; background: rgba(255,255,255,0.2); color: white; }
        button { padding: 10px 20px; background: #00e6e6; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
      </style>
    </head>
    <body>
      <form method="POST">
        <h2>Reset Password</h2>
        <input type="password" name="password" placeholder="New Password" required>
        <button type="submit">Reset</button>
      </form>
    </body>
    </html>
    '''

# --------------------
@app.route('/promote_user/<username>', methods=['POST'])
def promote_user(username):
    if 'user' not in session or session['user'].get('role') != 'admin':
        return "Unauthorized", 403
    users = load_users()
    for u in users:
        if u['username'] == username:
            u['role'] = 'admin'
    with open(USER_DB, 'w') as f:
        json.dump({'users': users}, f, indent=2)
    return redirect('/admin')

@app.route('/export_users')
def export_users():
    if 'user' not in session or session['user'].get('role') != 'admin':
        return "Unauthorized", 403
    return send_file(USER_DB, as_attachment=True)

@app.route('/admin')
def admin():
    if 'user' not in session or session['user'].get('role') != 'admin':
        return "Access Denied", 403
    users = load_users()
    return render_template('admin_dashboard.html', users=users)



@app.route('/edit_user/<username>', methods=['GET', 'POST'])
def edit_user(username):
    if 'user' not in session or session['user'].get('role') != 'admin':
        return "Unauthorized", 403
    users = load_users()
    user_data = next((u for u in users if u['username'] == username), None)
    if not user_data:
        return "User not found", 404

    if request.method == 'POST':
        user_data['name'] = request.form['name']
        user_data['dob'] = request.form['dob']
        user_data['address'] = request.form['address']
        with open(USER_DB, 'w') as f:
            json.dump({'users': users}, f, indent=2)
        return redirect('/admin')

    return render_template('edit_user.html', user=user_data)

@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if 'user' not in session or session['user'].get('role') != 'admin':
        return "Unauthorized", 403
    users = load_users()
    users = [u for u in users if u['username'] != username]
    with open(USER_DB, 'w') as f:
        json.dump({'users': users}, f, indent=2)
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
