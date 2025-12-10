# 记账应用后端服务

这是一个为记账应用提供后端服务的简单Python Flask应用。

## 功能特性

1. 用户注册（包含头像、用户名、密码）
2. 用户登录
3. JWT Token认证
4. 用户信息管理
5. 交易数据同步（上传/下载）

## 技术栈

- Python 3.x
- Flask
- MySQL (通过PyMySQL驱动)
- JWT for Authentication
- Flask-Migrate for 数据库迁移

## 安装和运行

1. 克隆或下载项目
2. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

3. 配置数据库
   
   在 `.env` 文件中配置MySQL数据库连接信息:
   ```
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=accounting_app
   ```

4. 创建数据库
   
   在MySQL中创建数据库:
   ```sql
   CREATE DATABASE accounting_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

5. 初始化数据库:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. 运行应用:
   ```
   python app.py
   ```

7. 服务将在 `http://localhost:5000` 上运行

## API 接口

### 1. 用户注册
- **URL**: `/api/register`
- **Method**: `POST`
- **Data Params**:
  ```
  {
    "username": "[用户名]",
    "password": "[密码]",
    "avatar": "[头像的base64编码数据，可选]"
  }
  ```
- **Success Response**:
  - Code: 201
  - Content: `{ "message": "注册成功", "user": { ... } }`

### 2. 用户登录
- **URL**: `/api/login`
- **Method**: `POST`
- **Data Params**:
  ```
  {
    "username": "[用户名]",
    "password": "[密码]"
  }
  ```
- **Success Response**:
  - Code: 200
  - Content: `{ "message": "登录成功", "access_token": "[JWT token]", "user": { ... } }`

### 3. 获取当前用户信息
- **URL**: `/api/user`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer [token]`
- **Success Response**:
  - Code: 200
  - Content: `{ "user": { ... } }`

### 4. 更新用户头像
- **URL**: `/api/user/avatar`
- **Method**: `PUT`
- **Headers**: `Authorization: Bearer [token]`
- **Data Params**:
  ```
  {
    "avatar": "[头像的base64编码数据]"
  }
  ```
- **Success Response**:
  - Code: 200
  - Content: `{ "message": "头像更新成功", "user": { ... } }`

### 5. 上传交易数据
- **URL**: `/api/transactions/upload`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer [token]`
- **Data Params**:
  ```
  {
    "transactions": [
      {
        "server_id": "[服务器ID]",
        "amount": "[金额]",
        "type": "[类型：0为支出，1为收入]",
        "category_id": "[分类ID]",
        "date": "[日期，格式：YYYY-MM-DD]",
        "description": "[描述]"
      },
      ...
    ]
  }
  ```
- **Success Response**:
  - Code: 200
  - Content: `{ "message": "成功上传X条交易记录", "uploaded_count": X }`

### 6. 下载交易数据
- **URL**: `/api/transactions/download`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer [token]`
- **Success Response**:
  - Code: 200
  - Content: 
    ```
    {
      "message": "成功获取X条交易记录",
      "transactions": [
        {
          "id": "[本地ID]",
          "user_id": "[用户ID]",
          "server_id": "[服务器ID]",
          "amount": "[金额]",
          "type": "[类型]",
          "category_id": "[分类ID]",
          "date": "[日期]",
          "description": "[描述]",
          "created_at": "[创建时间]",
          "updated_at": "[更新时间]"
        },
        ...
      ]
    }
    ```

## 注意事项

1. 在生产环境中，请务必更改 `SECRET_KEY` 和 `JWT_SECRET_KEY`
2. 当前使用MySQL数据库，可通过修改 `SQLALCHEMY_DATABASE_URI` 更改数据库
3. 头像文件存储在本地 `uploads` 目录中
4. 头像传输使用base64编码
5. 交易数据通过JWT Token进行身份验证
6. 上传时使用server_id来标识记录，避免重复上传