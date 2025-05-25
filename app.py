import os
from flask import Flask, request, render_template, redirect, url_for, session, flash, abort
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import RequestEntityTooLarge


# Konfigurasi dasar
app = Flask(__name__)
app.secret_key = 'Xfv$X$tevhh&$heu;hfuhf-uhnUx+Xyvy5g&]j=u6g@d4a'

UPLOAD_FOLDER = 'static/uploads'
ADMIN_PASSWORD = 'admin123'
ADMIN_USERNAME = 'useradmin'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xXtcdX6f.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024  # 80 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Daftar ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {
    # Dokumen
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'odt', 'ods',
    # Gambar
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
    # Video
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv',
    # Presentasi
    'ppt', 'pptx', 'key',
    # Grafis
    'eps', 'ai', 'psd',
    # Audio
    'mp3', 'wav', 'ogg', 'm4a', 'flac'
}

# Fungsi cek ekstensi file
def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

# Inisialisasi ekstensi Flask
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])
limiter.init_app(app)

# Model database
class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(15), nullable=False)
    pesan = db.Column(db.Text, nullable=False)
    file = db.Column(db.String(255))
    waktu = db.Column(db.String(50))
    pinned = db.Column(db.Boolean, default=False)
    bahaya = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)
    pp = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))  # Menyimpan alamat IP
    user_agent = db.Column(db.String(255))  # Menyimpan user agent

# Form upload
class UploadForm(FlaskForm):
    nama = StringField('Nama', validators=[DataRequired(), Length(max=15)])
    pesan = TextAreaField('Pesan', validators=[DataRequired()])

# Fungsi sanitasi pesan
def sanitize_message(message):
    return message.replace('"', '\\"').replace(":", "&#58;")

# Inisialisasi database saat pertama dijalankan
with app.app_context():
    db.create_all()

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return render_template('error.html', code=413, message="File terlalu besar. Maksimal ukuran file adalah 80 MB."), 413

@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        nama = form.nama.data
        pesan = form.pesan.data
        file = request.files.get('file')

        filename = ''
        if file and file.filename:
            if not allowed_file(file.filename):
                flash(" ")
                abort(415)

            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

        waktu = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ip_address = request.remote_addr  # Mengambil alamat IP
        user_agent = request.user_agent.string  # Mengambil user agent

        new_entry = Upload(
            nama=nama,
            pesan=pesan,
            file=filename,
            waktu=waktu,
            pinned=True,
            ip_address=ip_address,  # Menyimpan alamat IP
            user_agent=user_agent   # Menyimpan user agent
        )
        db.session.add(new_entry)
        db.session.commit()

        session['message_sent'] = True
        return redirect(url_for('success'))

    return render_template('index.html', form=form)
    
@app.route('/admin2')
def admin2():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    uploads = Upload.query.order_by(Upload.pinned.asc(), Upload.id.desc()).all()
    return render_template('admin2.html', uploads=uploads)

@app.route('/success')
def success():
    if not session.get('message_sent'):
        return redirect(url_for('index'))  # atau halaman lain jika perlu
    session.pop('message_sent', None)  # hapus agar tidak bisa diakses ulang
    return render_template('success.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))  # Langsung ke admin jika sudah login

    if 'login_attempts' not in session:
        session['login_attempts'] = 0

    now = datetime.now()
    error_message = None

    blocked_until = session.get('blocked_until')
    if blocked_until:
        blocked_time = datetime.fromisoformat(blocked_until)
        if now < blocked_time:
            waktu_sisa = (blocked_time - now).seconds
            error_message = f"Akses diblokir. Coba lagi dalam {waktu_sisa // 60} menit {waktu_sisa % 60} detik."
            return render_template('login.html', attempts=session['login_attempts'], error_message=error_message)
        else:
            session['login_attempts'] = 0
            session.pop('blocked_until', None)

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['login_attempts'] = 0
            session.pop('blocked_until', None)
            return redirect(url_for('admin'))
        else:
            session['login_attempts'] += 1
            flash('Username atau password salah!')

            if session['login_attempts'] >= 2:
                session['blocked_until'] = (now + timedelta(minutes=10)).isoformat()
                error_message = " "
                return render_template('login.html', attempts=session['login_attempts'], error_message=error_message)

    return render_template('login.html', attempts=session['login_attempts'], error_message=error_message)
    
@app.route('/mxbjnlo')
def logout():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    uploads = Upload.query.order_by(Upload.pinned.asc(), Upload.id.desc()).all()
    return render_template('admin.html', uploads=uploads)

@app.route('/hapus/<int:id>', methods=['POST'])
def hapus_data(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    entry = Upload.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/pin/<int:id>', methods=['POST'])
def pin_data(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    entry = Upload.query.get_or_404(id)
    entry.pinned = not entry.pinned
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/bahaya/<int:id>', methods=['POST'])
def toggle_bahaya(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    entry = Upload.query.get_or_404(id)
    entry.bahaya = not entry.bahaya
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_data(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    entry = Upload.query.get_or_404(id)

    if request.method == 'POST':
        entry.pesan = request.form.get('pesan', '')

        pp = request.files.get('pp')
        if pp and pp.filename:
            if not allowed_file(pp.filename):
                flash(" ")
                abort(415)

            pp_filename = f"profile_{datetime.now().timestamp()}_{pp.filename}"
            pp_path = os.path.join(UPLOAD_FOLDER, pp_filename)
            pp.save(pp_path)
            entry.pp = pp_filename

        db.session.commit()
        return redirect(url_for('admin'))

    return render_template('edit.html', entry=entry)

@app.route('/dashboard')
def dashboard():
    uploads = Upload.query.order_by(Upload.pinned.asc(), Upload.id.desc()).all()
    return render_template("dashboard.html", uploads=uploads)

@app.route('/upload', methods=['POST'])
def upload_data():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    nama = request.form.get('nama')
    pesan = request.form.get('pesan')
    file = request.files.get('file')
    pp = request.files.get('pp')

    filename = None
    pp_filename = None

    if file and file.filename:
        if not allowed_file(file.filename):
            flash(" ")
            abort(415)

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

    if pp and pp.filename:
        if not allowed_file(pp.filename):
            flash(" ")
            abort(415)

        pp_filename = f"profile_{datetime.now().timestamp()}_{pp.filename}"
        pp_path = os.path.join(UPLOAD_FOLDER, pp_filename)
        pp.save(pp_path)

    new_entry = Upload(
        nama=nama,
        pesan=pesan,
        file=filename,
        admin=True,
        pp=pp_filename,
        waktu=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        pinned=True,
        bahaya=False
    )

    db.session.add(new_entry)
    db.session.commit()

    return redirect(url_for('admin'))
    
@app.route('/lama')
def lama():
    return redirect(url_for('not_found_302'))

@app.route('/not-found')
def not_found_302():
    return render_template('error.html', code=302), 302

# Error handler khusus
@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html', code=400), 400

@app.errorhandler(401)
def unauthorized(e):
    return render_template('error.html', code=401), 401

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', code=404), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('error.html', code=405), 405

@app.errorhandler(408)
def request_timeout(e):
    return render_template('error.html', code=408), 408

@app.errorhandler(429)
def too_many_requests(e):
    return render_template('error.html', code=429), 429

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', code=500), 500

@app.errorhandler(415)
def unsupported_media_type(e):
    return render_template('dont.html', code=415), 415

@app.errorhandler(503)
def service_unavailable(e):
    return render_template('error.html', code=503), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)