from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import extract, event

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///waste2cash.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Predefined South African provinces
PROVINCES = [
    'Eastern Cape', 'Free State', 'Gauteng', 
    'KwaZulu-Natal', 'Limpopo', 'Mpumalanga',
    'Northern Cape', 'North West', 'Western Cape'
]

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    collections = db.relationship('CollectionTransaction', backref='user', lazy=True)

class WasteCollectionCenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    province = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    operating_hours = db.Column(db.String(100), nullable=False)
    collections = db.relationship('CollectionTransaction', backref='center', lazy=True)

class CollectionTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    center_id = db.Column(db.Integer, db.ForeignKey('waste_collection_center.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    collection_date = db.Column(db.DateTime, nullable=False)
    date_submitted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Scheduled')

class EcoStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    co2_per_kg = db.Column(db.Float, default=0.5)
    trees_per_kg = db.Column(db.Float, default=0.0017)
    energy_per_kg = db.Column(db.Float, default=4.1)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def initialize_centers():
    centers = [
        {'name': 'EcoGreen Eastern Cape', 'location': 'Port Elizabeth', 'province': 'Eastern Cape', 
         'capacity': 5000, 'contact': '041 123 4567', 'operating_hours': 'Mon-Fri: 8am-5pm'},
        {'name': 'Bloem Recycling Hub', 'location': 'Bloemfontein', 'province': 'Free State', 
         'capacity': 3500, 'contact': '051 234 5678', 'operating_hours': 'Mon-Sat: 7am-4pm'},
        {'name': 'Joburg Waste Solutions', 'location': 'Johannesburg', 'province': 'Gauteng', 
         'capacity': 8000, 'contact': '011 345 6789', 'operating_hours': 'Mon-Sun: 6am-6pm'},
        {'name': 'Durban Eco Center', 'location': 'Durban', 'province': 'KwaZulu-Natal', 
         'capacity': 6000, 'contact': '031 456 7890', 'operating_hours': 'Mon-Fri: 8am-5pm'},
        {'name': 'Polokwane Recycling', 'location': 'Polokwane', 'province': 'Limpopo', 
         'capacity': 3000, 'contact': '015 567 8901', 'operating_hours': 'Mon-Fri: 8am-4pm'},
        {'name': 'Nelspruit Eco Depot', 'location': 'Nelspruit', 'province': 'Mpumalanga', 
         'capacity': 4000, 'contact': '013 678 9012', 'operating_hours': 'Mon-Sat: 7am-5pm'},
        {'name': 'Kimberley Waste Center', 'location': 'Kimberley', 'province': 'Northern Cape', 
         'capacity': 2500, 'contact': '053 789 0123', 'operating_hours': 'Mon-Fri: 8am-4pm'},
        {'name': 'Rustenburg Recycling', 'location': 'Rustenburg', 'province': 'North West', 
         'capacity': 3500, 'contact': '014 890 1234', 'operating_hours': 'Mon-Fri: 7:30am-4:30pm'},
        {'name': 'Cape Town Eco Station', 'location': 'Cape Town', 'province': 'Western Cape', 
         'capacity': 7000, 'contact': '021 901 2345', 'operating_hours': 'Mon-Sun: 7am-7pm'}
    ]
    
    for center_data in centers:
        if not WasteCollectionCenter.query.filter_by(name=center_data['name']).first():
            center = WasteCollectionCenter(**center_data)
            db.session.add(center)
    db.session.commit()

def calculate_eco_impact(user_id, custom_amount=None):
    stats = EcoStats.query.first()
    if not stats:
        stats = EcoStats()
        db.session.add(stats)
        db.session.commit()
    
    if user_id:
        total_kg = db.session.query(db.func.sum(CollectionTransaction.amount))\
                   .filter_by(user_id=user_id).scalar() or 0
    else:
        total_kg = custom_amount
    
    return {
        'kg': total_kg,
        'trees': total_kg * stats.trees_per_kg,
        'co2': total_kg * stats.co2_per_kg,
        'energy': total_kg * stats.energy_per_kg
    }

@app.template_filter('month_name')
def month_name(month_num):
    return datetime(2020, month_num, 1).strftime('%b')

@app.route('/')
@login_required
def dashboard():
    # Upcoming collections
    upcoming = CollectionTransaction.query.filter(
        CollectionTransaction.user_id == current_user.id,
        CollectionTransaction.collection_date >= datetime.now()
    ).order_by(CollectionTransaction.collection_date).limit(5).all()
    
    # Total collected
    total_collected = db.session.query(db.func.sum(CollectionTransaction.amount))\
                   .filter_by(user_id=current_user.id).scalar() or 0
    
    # Eco impact
    eco_stats = calculate_eco_impact(current_user.id)
    
    # Personal stats
    total_collections = CollectionTransaction.query.filter_by(user_id=current_user.id).count()
    
    # Monthly data
    monthly_data = db.session.query(
        extract('month', CollectionTransaction.collection_date).label('month'),
        db.func.sum(CollectionTransaction.amount).label('total')
    ).filter_by(user_id=current_user.id).group_by('month').all()
    
    monthly_totals = {row.month: row.total for row in monthly_data}
    
    # Weekly comparison
    week_ago = datetime.now() - timedelta(days=7)
    weekly_total = db.session.query(db.func.sum(CollectionTransaction.amount)).filter(
        CollectionTransaction.user_id == current_user.id,
        CollectionTransaction.collection_date >= week_ago
    ).scalar() or 0
    
    # Achievements
    achievements = []
    if total_collected >= 1000:
        achievements.append('Recycling Master')
    if total_collections >= 10:
        achievements.append('Frequent Recycler')
    if weekly_total >= 100:
        achievements.append('Weekly Champion')
    
    # Chart data
    months = [datetime(2020, m, 1).strftime('%b') for m in range(1, 13)]
    monthly_values = [monthly_totals.get(m, 0) for m in range(1, 13)]
    
    return render_template('dashboard.html', 
                         upcoming=upcoming,
                         total_collected=total_collected,
                         eco_stats=eco_stats,
                         total_collections=total_collections,
                         monthly_totals=monthly_totals,
                         weekly_total=weekly_total,
                         achievements=achievements,
                         months=months,
                         monthly_values=monthly_values)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/centers')
@login_required
def centers():
    centers = WasteCollectionCenter.query.order_by(WasteCollectionCenter.province).all()
    return render_template('centers.html', centers=centers, provinces=PROVINCES)

@app.route('/add-collection', methods=['GET', 'POST'])
@login_required
def add_collection():
    centers = WasteCollectionCenter.query.order_by(WasteCollectionCenter.name).all()
    
    if request.method == 'POST':
        try:
            center_id = int(request.form.get('center_id'))
            amount = float(request.form.get('amount'))
            collection_date = datetime.strptime(
                request.form.get('collection_date'), 
                '%Y-%m-%dT%H:%M'
            )
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('add-collection.html', centers=centers)
                
            if collection_date < datetime.now():
                flash('Collection date cannot be in the past', 'danger')
                return render_template('add-collection.html', centers=centers)
                
            center = WasteCollectionCenter.query.get(center_id)
            if not center:
                flash('Invalid collection center selected', 'danger')
                return render_template('add-collection.html', centers=centers)
                
            new_collection = CollectionTransaction(
                user_id=current_user.id,
                center_id=center_id,
                amount=amount,
                collection_date=collection_date
            )
            db.session.add(new_collection)
            db.session.commit()
            
            flash(
                f'Successfully scheduled {amount}kg collection at {center.name} for {collection_date.strftime("%d %b %Y at %H:%M")}!', 
                'success'
            )
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash('Please enter valid information: ' + str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred: ' + str(e), 'danger')
            
    return render_template('add-collection.html', centers=centers)

@app.route('/eco-calculator', methods=['GET', 'POST'])
@login_required
def eco_calculator():
    total_stats = calculate_eco_impact(current_user.id)
    hypothetical_impact = None
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            hypothetical_impact = calculate_eco_impact(None, amount)
        except ValueError:
            flash('Please enter a valid number', 'danger')
            
    return render_template('eco-calculator.html', 
                         total_stats=total_stats,
                         hypothetical=hypothetical_impact)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@event.listens_for(EcoStats.__table__, 'after_create')
def initialize_eco_stats(*args, **kwargs):
    with app.app_context():
        if not EcoStats.query.first():
            default_stats = EcoStats()
            db.session.add(default_stats)
            db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_centers()
    app.run(debug=True)