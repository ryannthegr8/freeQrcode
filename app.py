from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import qrcode
import os
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/qr_codes'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    qr_codes = db.relationship('QRCode', backref='owner', lazy=True)

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    qr_file = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/generate', methods=['POST'])
@login_required
def generate_qr():
    text = request.form.get('text')
    if text:
        img = qrcode.make(text)
        filename = f'{text[:3]}_qr.png'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(file_path)

    # Store only the file name
    qr_code = QRCode(text=text, qr_file=filename, owner=current_user)
    db.session.add(qr_code)
    db.session.commit()


    # flash('QR Code generated successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    qr_codes = QRCode.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', qr_codes=qr_codes)

@app.route('/download/<int:qr_id>')
@login_required
def download(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    filepath = os.path.join(app.static_folder, 'qr_codes', qr_code.qr_file)
    return send_file(filepath, as_attachment=True)

@app.route('/edit/<int:qr_id>', methods=['GET', 'POST'])
@login_required
def edit(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    if request.method == 'POST':
        new_text = request.form.get('text')
        if new_text:
            img = qrcode.make(new_text)
            filename = f'{new_text[:10]}_qr.png'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img.save(file_path)

            qr_code.text = new_text
            qr_code.qr_file = filename  # Save only the file name
            db.session.commit()

            # flash('QR Code updated successfully!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('edit.html', qr_code=qr_code)


@app.route('/delete/<int:qr_id>')
@login_required
def delete(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    db.session.delete(qr_code)
    db.session.commit()

    # flash('QR Code deleted successfully!', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            # flash('Login successful!', 'success')
            return redirect(url_for('home'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'danger')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            # flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This creates all the database tables
    app.run(debug=True)

