from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv
import os
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# 初始化数据库和JWT
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

@jwt.user_identity_loader
def user_identity_lookup(user_id):
    return str(user_id)

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(int(float(identity)))

# 用户模型
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username
        }

# 交易记录模型
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, unique=True, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.Integer, nullable=False)  # 0 for expense, 1 for income
    category_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'server_id': self.server_id,
            'amount': float(self.amount),
            'type': self.type,
            'category_id': self.category_id,
            'date': self.date,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 健康检查端点
@app.route('/')
def index():
    return jsonify({'message': 'Accounting App Backend is running'})

# 注册接口
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # 检查必需字段
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': '用户名和密码是必需的'}), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': '用户名已存在'}), 400
        
        # 创建新用户
        user = User(username=data['username'])
        user.set_password(data['password'])
        
        # 保存到数据库
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': '注册成功',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'注册失败: {str(e)}'}), 500

# 登录接口
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # 检查必需字段
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': '用户名和密码是必需的'}), 400
        
        # 查找用户
        user = User.query.filter_by(username=data['username']).first()
        
        # 验证用户和密码
        if not user or not user.check_password(data['password']):
            return jsonify({'message': '用户名或密码错误'}), 401
        
        # 创建访问令牌 (确保用户ID是字符串类型)
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'登录失败: {str(e)}'}), 500

# 获取当前用户信息
@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        current_user_id = get_jwt_identity()
        # 确保用户ID是正确的整数类型，即使它是浮点数格式
        user = User.query.get(int(float(current_user_id)))
        
        if not user:
            return jsonify({'message': '用户不存在'}), 404
            
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': f'获取用户信息失败: {str(e)}'}), 500

# 上传交易数据
@app.route('/api/transactions/upload', methods=['POST'])
@jwt_required()
def upload_transactions():
    try:
        current_user_id = get_jwt_identity()
        # 确保用户ID是正确的整数类型，即使它是浮点数格式
        user = User.query.get(int(float(current_user_id)))
        
        if not user:
            return jsonify({'message': '用户不存在'}), 404
            
        data = request.get_json()
        
        if not data or 'transactions' not in data:
            return jsonify({'message': '交易数据是必需的'}), 400
            
        transactions_data = data['transactions']
        
        # 处理每个交易记录
        uploaded_count = 0
        for transaction_data in transactions_data:
            try:
                # 检查是否已存在相同的server_id和user_id组合
                server_id = transaction_data.get('server_id')
                existing_transaction = Transaction.query.filter_by(server_id=server_id, user_id=int(current_user_id)).first()
                
                if existing_transaction:
                    # 更新现有记录
                    existing_transaction.amount = transaction_data.get('amount', existing_transaction.amount)
                    existing_transaction.type = transaction_data.get('type', existing_transaction.type)
                    existing_transaction.category_id = transaction_data.get('category_id', existing_transaction.category_id)
                    existing_transaction.date = transaction_data.get('date', existing_transaction.date)
                    existing_transaction.description = transaction_data.get('description', existing_transaction.description)
                    existing_transaction.updated_at = datetime.utcnow()
                    print(f"Updated existing transaction with server_id: {server_id}")
                else:
                    # 创建新记录
                    transaction = Transaction(
                        user_id=int(current_user_id),
                        server_id=server_id,
                        amount=transaction_data.get('amount'),
                        type=transaction_data.get('type'),
                        category_id=transaction_data.get('category_id'),
                        date=transaction_data.get('date'),
                        description=transaction_data.get('description')
                    )
                    db.session.add(transaction)
                    print(f"Created new transaction with server_id: {server_id}")
                
                uploaded_count += 1
            except Exception as e:
                print(f"处理交易记录时出错: {str(e)}")
                db.session.rollback()
                continue
        
        # 提交到数据库
        try:
            db.session.commit()
            print(f"Successfully committed {uploaded_count} transactions to database")
        except Exception as e:
            db.session.rollback()
            print(f"数据库提交失败: {str(e)}")
            return jsonify({'message': f'数据库提交失败: {str(e)}'}), 500
        
        return jsonify({
            'message': f'成功上传{uploaded_count}条交易记录',
            'uploaded_count': uploaded_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"上传交易数据失败: {str(e)}")
        return jsonify({'message': f'上传交易数据失败: {str(e)}'}), 500

# 下载交易数据
@app.route('/api/transactions/download', methods=['GET'])
@jwt_required()
def download_transactions():
    try:
        current_user_id = get_jwt_identity()
        # 确保用户ID是正确的整数类型，即使它是浮点数格式
        user = User.query.get(int(float(current_user_id)))
        
        if not user:
            return jsonify({'message': '用户不存在'}), 404
            
        # 获取用户的所有交易记录
        transactions = Transaction.query.filter_by(user_id=int(current_user_id)).all()
        
        # 转换为字典列表
        transactions_data = [transaction.to_dict() for transaction in transactions]
        
        return jsonify({
            'message': f'成功获取{len(transactions_data)}条交易记录',
            'transactions': transactions_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'下载交易数据失败: {str(e)}'}), 500

# 运行应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)