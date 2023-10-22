from dotenv import load_dotenv
import os

import urllib

load_dotenv()

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, cast, desc, func
from sqlalchemy.orm import relationship, declarative_base, scoped_session, sessionmaker
from sqlalchemy import create_engine

sql = create_engine('mssql+pyodbc:///?autocommit=true&odbc_connect={}'.format(urllib.parse.quote_plus(f"""Driver={"{ODBC Driver 17 for SQL Server}"};Server=tcp:{os.environ.get('DB_SERVER')},1433;Database={os.environ.get('DB_NAME')};
Uid={os.environ.get('DB_UN')};Pwd={os.environ.get('DB_PW')};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=20;""")))
sessionFactory = scoped_session(sessionmaker(bind=sql))

from flask import Flask, redirect, request
app:Flask = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

from flasgger import Swagger
app.config['SWAGGER'] = {
    'title': 'Y App API',
    'uiversion': 3,
    "openapi": "3.0.3",
    "basePath": "/api",
    "auth_config": {}
}
swagger = Swagger(app, template={
  "info": {
    "title": "The Y App API Docs",
    "description": "The Y App API Docs. Please note that this is a work in progress and is subject to change. Please contact for more information.",
    "contact": {
      "responsibleOrganization": "DZ Apps",
      "responsibleDeveloper": "DZ Apps",
      "email": "dz.uofm@gmail.com",
    },
    "termsOfService": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    "version": "0.0.1"
  },
  "schemes": [
    "http",
    "https"
  ],
  "operationId": "getmyData"
})

Base = declarative_base()

class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True)
    base64 = Column(Text)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=func.now())

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey('media.id'), default=None, nullable=True)
    first_name = Column(String(64))
    last_name = Column(String(64))
    dark_mode = Column(Boolean, default=False)
    profanity_filter = Column(Boolean, default=False)
    ui_scale = Column(String(16), default='Normal')
    email = Column(String(128), unique=True)
    password = Column(String(128))
    api_key = Column(String(256))

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    content = Column(String(1024))
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    Media_id = Column(Integer, ForeignKey('media.id'), default=None, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    author = relationship('User', backref='posts')

# Base.metadata.create_all(sql)

@app.route('/', methods=['GET'])
def index():
    return redirect('/apidocs/')

@app.route('/api/status', methods=['GET'])
def api_status():
    """
    Endpoint to check the API status.
    ---
    tags:
      - Status
    responses:
        200:
            description: API is online
    """
    return {'message': 'API is online'}

@app.route('/api/login', methods=['POST'])
def api_login():
    """
    Endpoint to login.
    ---
    tags:
      - Authentication
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - password
                    properties:
                        email:
                            type: string
                            description: The user's email
                        password: 
                            type: string
                            description: The user's password
    responses:
        200:
            description: User logged in
            schema:
                id: Login
                properties:
                    first_name:
                        type: string
                        description: The user's first name
                    last_name:
                        type: string
                        description: The user's last name
                    profile_picture:
                        type: string
                        description: The user's profile picture base64 string
                    dark_mode:
                        type: boolean
                        description: Whether the user has dark mode enabled
                    profanity_filter:
                        type: boolean
                        description: Whether the user has the profanity filter enabled
                    ui_scale:
                        type: string
                        description: The user's UI scale
                    api_key:
                        type: string
                        description: The user's API key
        401:
            description: Incorrect password
        404:
            description: User not found
    """
    data = request.get_json()
    email, password = data['email'], data['password']
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.email == email).first()
    if user is None:
        return {'message': 'User not found'}, 404
    if user.password != password:
        return {'message': 'Incorrect password'}, 401
    user.api_key = os.urandom(128).hex()
    profile_picture = session.query(Media).filter(Media.id == user.media_id).first()
    session.commit()
    return {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'dark_mode': user.dark_mode,
        'profanity_filter': user.profanity_filter,
        'ui_scale': user.ui_scale,
        'profile_picture': profile_picture.base64 if profile_picture is not None else None,
        'api_key': user.api_key
    }

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """
    Endpoint to logout.
    ---
    tags:
      - Authentication
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - api_key
                    properties:
                        email:
                            type: string
                            description: The user's email
                        api_key: 
                            type: string
                            description: The user's API key
    responses:
        200:
            description: User logged out
        401:
            description: User API key not found
    """
    data = request.get_json()
    email, api_key = data['email'], data['api_key']
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.email == email).filter(User.api_key == api_key).first()
    if user is None:
        return {'message': 'User API key not found'}, 401
    user.api_key = None
    session.commit()
    return {'message': 'User logged out'}

@app.route('/api/user', methods=['POST'])
def create_user():
    """
    Endpoint to create a user
    ---
    tags:
      - User
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - first_name
                        - last_name
                        - email
                        - password
                    properties:
                        first_name:
                            type: string
                            description: The user's first name
                        last_name:
                            type: string
                            description: The user's last name
                        email:
                            type: string
                            description: The user's email
                        password: 
                            type: string
                            description: The user's password
    responses:
        201:
            description: User created
        400:
            description: Missing required fields
        416:
            description: User already exists
    """
    data = request.get_json(force=True)
    print(data)
    session = scoped_session(sessionFactory)
    try:
        existing_user = session.query(User).filter(User.email == data['email']).first()
        if existing_user is not None:
            return {'message': 'User already exists'}, 416
        session.add(User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            password=data['password']
        ))
        session.commit()
    except KeyError:
        return {'message': 'Missing required fields'}, 400
    return {'message': 'User created'}, 201

@app.route('/api/user', methods=['PATCH'])
def update_user():
    """
    Endpoint to update a user
    ---
    tags:
      - User
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - api_key
                    properties:
                        email:
                            type: string
                            description: The user's email
                        api_key: 
                            type: string
                            description: The user's API key
                        first_name:
                            type: string
                            description: The user's first name
                        last_name:
                            type: string
                            description: The user's last name
                        dark_mode:
                            type: boolean
                            description: Whether the user has dark mode enabled
                        profanity_filter:
                            type: boolean
                            description: Whether the user has the profanity filter enabled
                        ui_scale:
                            type: string
                            description: The user's UI scale
                        profile_picture_media_id:
                            type: integer
                            description: The user's profile picture media ID
    responses:
        200:
            description: User updated
        400:
            description: Missing required fields
        401:
            description: User API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.email == data['email']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User API key not found'}, 401
        user.first_name = data['first_name'] if 'first_name' in data else user.first_name
        user.last_name = data['last_name'] if 'last_name' in data else user.last_name
        user.dark_mode = data['dark_mode'] if 'dark_mode' in data else user.dark_mode
        user.profanity_filter = data['profanity_filter'] if 'profanity_filter' in data else user.profanity_filter
        user.ui_scale = data['ui_scale'] if 'ui_scale' in data else user.ui_scale
        user.media_id = data['profile_picture_media_id'] if 'profile_picture_media_id' in data else user.media_id
        session.commit()
    except KeyError:
        return {'message': 'Missing required fields'}, 400
    return {'message': 'User updated'}, 200

@app.route('/api/user', methods=['GET'])
def get_user():
    """
    Endpoint to get the users list. For Debugging!
    ---
    tags:
      - User
    responses:
        200:
            description: User list
            schema:
                id: FullUser
                properties:
                    first_name:
                        type: string
                        description: The user's first name
                    last_name:
                        type: string
                        description: The user's last name
                    email:
                        type: string
                        description: The user's email
                    dark_mode:
                        type: boolean
                        description: Whether the user has dark mode enabled
                    profanity_filter:
                        type: boolean
                        description: Whether the user has the profanity filter enabled
                    ui_scale:
                        type: string
                        description: The user's UI scale
                    password:
                        type: string
                        description: The user's password
                    api_key:
                        type: string
                        description: The user's API key
    """
    session = scoped_session(sessionFactory)
    users = session.query(User).all()
    return [{
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'dark_mode': user.dark_mode,
            'profanity_filter': user.profanity_filter,
            'ui_scale': user.ui_scale,
            'password': user.password,
            'api_key': user.api_key
        } for user in users]

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """
    Endpoint to get simple info about a user by ID
    ---
    tags:
      - User
    parameters:
        - in: path
          name: user_id
          type: integer
          required: true
          description: The user's ID
    responses:
        200:
            description: User found
            schema:
                id: FullUser
                properties:
                    first_name:
                        type: string
                        description: The user's first name
                    last_name:
                        type: string
                        description: The user's last name
                    profile_picture:
                        type: string
                        description: The user's profile picture base64 string
        404:
            description: User not found
    """
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        return {'message': 'User not found'}, 404
    profile_picture = session.query(Media).filter(Media.id == user.media_id).first()
    return {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_picture': profile_picture.base64 if profile_picture is not None else None
    }

@app.route('/api/post', methods=['POST'])
def create_post():
    """
    Endpoint to create a post
    ---
    tags:
      - Post
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - api_key
                        - content
                    properties:
                        email:
                            type: string
                            description: The user's email
                        api_key: 
                            type: string
                            description: The user's API key
                        content:
                            type: string
                            description: The post content
                        media_id:
                            type: integer
                            description: The post media ID
    responses:
        201:
            description: Post created
        400:
            description: Missing required fields
        401:
            description: User API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.email == data['email']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User API key not found'}, 401
        session.add(Post(
            content=data['content'],
            author_id=user.id,
            Media_id=data['media_id'] if 'media_id' in data else None
        ))
        session.commit()
        post_id = session.query(Post).filter(Post.content == data['content']).first().id
        return {'message': 'Post created', 'id': post_id}, 201
    except KeyError:
        return {'message': 'Missing required fields'}, 400
    
@app.route('/api/post', methods=['GET'])
def get_posts():
    """
    Endpoint to get the posts list.
    ---
    tags:
      - Post
    produces:
        - application/json
    parameters:
        - in: query
          name: email
          type: string
          required: true
          description: The user's email
        - in: query
          name: api_key
          type: string
          required: true
          description: The user's API key
    responses:
        200:
            description: Post list
            schema:
                id: FullPost
                properties:
                    content:
                        type: string
                        description: The post content
                    first_name:
                        type: string
                        description: The user's first name
                    last_name:
                        type: string
                        description: The user's last name
                    profile_picture:
                        type: string
                        description: The user's profile picture base64 string
                    created_at:
                        type: string
                        description: The post creation date
                    updated_at:
                        type: string
                        description: The post last update date
        401:
            description: User API key not found
        500:
            description: Internal server error likely due to invalid sort order.
    """
    data = request.args
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.email == data['email']).filter(User.api_key == data['api_key']).first()
    if user is None:
        return {'message': 'User API key not found'}, 401
    posts = session.query(Post).order_by(desc(Post.created_at)).all()
    print(posts[0].__str__() + ' ' + str(len(posts)))
    return [{
        'content': post.content,
        'first_name': post.author.first_name,
        'last_name': post.author.last_name,
        'profile_picture': session.query(Media).filter(Media.id == post.author.media_id).first().base64 if post.author.media_id is not None else None,
        'media': session.query(Media).filter(Media.id == post.Media_id).first().base64 if post.Media_id is not None else None,
        'created_at': post.created_at,
        'updated_at': post.updated_at
    } for post in posts]
    
@app.route('/api/media', methods=['POST'])
def create_media():
    """
    Endpoint to create a media
    ---
    tags:
      - Media
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - api_key
                        - base64
                    properties:
                        email:
                            type: string
                            description: The user's email
                        api_key: 
                            type: string
                            description: The user's API key
                        base64:
                            type: string
                            description: The media's base64 string
    responses:
        201:
            description: Media created
        400:
            description: Missing required fields
        401:
            description: User API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.email == data['email']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User API key not found'}, 401
        session.add(Media(
            base64=data['base64']
        ))
        session.commit()
        media_id = session.query(Media).filter(cast(Media.base64, String) == data['base64']).first().id
        return {'message': 'Media created', 'id': media_id}, 201
    except KeyError:
        return {'message': 'Missing required fields'}, 400

@app.route('/api/post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """
    Endpoint to delete a post
    ---
    tags:
      - Post
    parameters:
        - in: path
          name: post_id
          type: integer
          required: true
          description: The post's ID
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - email
                        - api_key
                    properties:
                        email:
                            type: string
                            description: The user's email
                        api_key: 
                            type: string
                            description: The user's API key
    responses:
        200:
            description: Post deleted
        401:
            description: User API key not found
        404:
            description: Post not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.email == data['email']).filter(User.api_key == data['api_key']).first()
    if user is None:
        return {'message': 'User API key not found'}, 401
    post = session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return {'message': 'Post not found'}, 404
    session.delete(post)
    session.commit()
    return {'message': 'Post deleted'}
