from dotenv import load_dotenv
import os

import urllib

load_dotenv()

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, cast, desc, func, literal_column
from sqlalchemy.orm import relationship, declarative_base, scoped_session, sessionmaker
from sqlalchemy import create_engine

sql = create_engine(f'mysql+pymysql://{os.environ.get('DB_UN')}:{os.environ.get('DB_PW')}@{os.environ.get('DB_SERVER')}/{os.environ.get('DB_NAME')}', connect_args={'ssl': {'ca': 'DigiCertGlobalRootCA.crt.pem'}})

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
    username = Column(String(64), unique=True, nullable=False)
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

class Downvote(Base):
    __tablename__ = 'downvotes'
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime, default=func.now())

class Bad_Words(Base):
    __tablename__ = 'bad_words'
    id = Column(Integer, primary_key=True)
    word = Column(String(128))

# Base.metadata.create_all(sql)

def gen_api_key():
    return os.urandom(128).hex()

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

@app.route('/api/status/db', methods=['TRACE'])
def api_status_db():
    """
    Endpoint to check the DB status.
    ---
    tags:
      - Status
    responses:
        200:
            description: DB is online
    """
    session = scoped_session(sessionFactory)
    session.execute('SELECT 1')
    return {'message': 'DB is online'}

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
                        - username
                        - password
                    properties:
                        username:
                            type: string
                            description: The user's username
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
                    email:
                        type: string
                        description: The user's email
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
    username, password = data['username'], data['password']
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        return {'message': 'User not found'}, 404
    if user.password != password:
        return {'message': 'Incorrect password'}, 401
    user.api_key = gen_api_key()
    profile_picture = session.query(Media).filter(Media.id == user.media_id).first()
    session.commit()
    return {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'dark_mode': user.dark_mode,
        'profanity_filter': user.profanity_filter,
        'ui_scale': user.ui_scale,
        'profile_picture': profile_picture.base64 if profile_picture is not None else None,
        'api_key': user.api_key
    }

@app.route('/api/change_password', methods=['PATCH'])
def api_change_password():
    """
    Endpoint to change a user's password.
    ---
    tags:
      - Authentication
    requestBody:
        content:
            application/json:
                schema:
                    required:
                        - username
                        - api_key
                        - password
                        - new_password
                    properties:
                        username:
                            type: string
                            description: The user's username
                        api_key: 
                            type: string
                            description: The user's API key
                        password: 
                            type: string
                            description: The user's current password
                        new_password:
                            type: string
                            description: The user's new password
    responses:
        200:
            description: Password changed
        401:
            description: User/API key not found
    """
    data = request.get_json()
    username, api_key, password, new_password = data['username'], data['api_key'], data['password'], data['new_password']
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == username).filter(User.api_key == api_key).filter(User.password == password).first()
    if user is None:
        return {'message': 'User/Password/API key not found'}, 401
    user.password = new_password
    session.commit()
    api_key = gen_api_key()
    return {'message': 'Password changed'}

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
                        - username
                        - api_key
                    properties:
                        username:
                            type: string
                            description: The user's username
                        api_key: 
                            type: string
                            description: The user's API key
    responses:
        200:
            description: User logged out
        401:
            description: User/API key not found
    """
    data = request.get_json()
    username, api_key = data['username'], data['api_key']
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == username).filter(User.api_key == api_key).first()
    if user is None:
        return {'message': 'User/API key not found'}, 401
    user.api_key = None
    session.commit()
    return {'message': 'User logged out'}

@app.route('/api/user', methods=['PUT'])
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
                        - username
                        - email
                        - password
                    properties:
                        first_name:
                            type: string
                            description: The user's first name
                        last_name:
                            type: string
                            description: The user's last name
                        username:
                            type: string
                            description: The user's username
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
            description: Username or email already exists
    """
    data = request.get_json(force=True)
    session = scoped_session(sessionFactory)
    try:
        existing_username = session.query(User).filter(User.username == data['username']).first()
        if existing_username:
            return {'message': 'Username already exists'}, 409
        existing_email = session.query(User).filter(User.email == data['email']).first()
        if existing_email:
            return {'message': 'Email already exists'}, 416
        session.add(User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            username=data['username'],
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
                        - username
                        - api_key
                    properties:
                        username:
                            type: string
                            description: The user's username
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
            description: User/API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User/API key not found'}, 401
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
                    username:
                        type: string
                        description: The user's username
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
            'username': user.username,
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
                    username:
                        type: string
                        description: The user's username
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
        'username': user.username,
        'profile_picture': profile_picture.base64 if profile_picture is not None else None
    }

@app.route('/api/post', methods=['PUT'])
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
                        - username
                        - api_key
                        - content
                    properties:
                        username:
                            type: string
                            description: The user's username
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
            description: User/API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User/API key not found'}, 401
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
          name: username
          type: string
          required: true
          description: The user's username
        - in: query
          name: api_key
          type: string
          required: true
          description: The user's API key
        - in: query
          name: offset
          type: integer
          required: false
          description: The number of posts to skip; defaults to 0
        - in: query
          name: limit
          type: integer
          required: false
          description: The number of posts to return; defaults to 10; max 20
        - in: query
          name: dislikes_only
          type: boolean
          required: false
          description: When provided, only posts that the user has downvoted will be returned.
        - in: query
          name: search
          type: string
          required: false
          description: When provided, only posts or users containing the search string will be returned; case insensitive
    responses:
        200:
            description: Post list
            schema:
                id: FullPost
                properties:
                    post_id:
                        type: integer
                        description: The post's id
                    content:
                        type: string
                        description: The post content
                    first_name:
                        type: string
                        description: The user's first name
                    last_name:
                        type: string
                        description: The user's last name
                    username:
                        type: string
                        description: The user's username
                    profile_picture:
                        type: string
                        description: The user's profile picture base64 string
                    downvotes:
                        type: integer
                        description: The number of downvotes
                    is_downvoted:
                        type: boolean
                        description: Whether the post is downvoted by the user
                    created_at:
                        type: string
                        description: The post creation date
                    updated_at:
                        type: string
                        description: The post last update date
        401:
            description: User/API key not found
        500:
            description: Internal server error likely due to invalid sort order.
    """
    data = request.args
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
    if user is None:
        return {'message': 'User/API key not found'}, 401
    profanity_filter = user.profanity_filter
    offset = int(data['offset']) if 'offset' in data else 0
    limit = max(min(int(data['limit']), 20), 1) if 'limit' in data else 10
    posts = session.query(
            Post,
            func.coalesce(
                literal_column("TIMESTAMPADD(DAY, -COUNT(downvotes.user_id), posts.created_at)"),
                Post.created_at
            ).label('penalized_created_at')
        ).outerjoin(Downvote, Downvote.post_id == Post.id).group_by(Post.id)
    if 'search' in data:
        posts = posts.filter(Post.content.ilike(f'%{data["search"]}%'))
    if 'dislikes_only' in data:
        posts = posts.filter(Downvote.user_id == user.id)
    posts = posts.order_by(desc('penalized_created_at')).offset(offset).limit(limit).all()
    bad_word_list = []
    if profanity_filter:
        bad_word_list = [bad.word for bad in session.query(Bad_Words).all()]
    return [{
        'post_id': post[0].id,
        'content': post[0].content if not profanity_filter else ' '.join(['***' if word.lower() in bad_word_list else word for word in post[0].content.split(' ')]),
        'first_name': post[0].author.first_name,
        'last_name': post[0].author.last_name,
        'username': post[0].author.username,
        'profile_picture': session.query(Media).filter(Media.id == post[0].author.media_id).first().base64 if post[0].author.media_id is not None else None,
        'media': session.query(Media).filter(Media.id == post[0].Media_id).first().base64 if post[0].Media_id is not None else None,
        'downvotes': session.query(Downvote).filter(Downvote.post_id == post[0].id).count(),
        'is_downvoted': session.query(Downvote).filter(Downvote.post_id == post[0].id).filter(Downvote.user_id == user.id).first() is not None,
        'created_at': post[0].created_at,
        'updated_at': post[0].updated_at
    } for post in posts]

@app.route('/api/post/downvote/<int:post_id>', methods=['PUT', 'DELETE'])
def create_downvote(post_id):
    """
    Endpoint to modify a post's downvote status
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
                        - username
                        - api_key
                    properties:
                        username:
                            type: string
                            description: The user's username
                        api_key: 
                            type: string
                            description: The user's API key
    responses:
        200:
            description: Downvote deleted
        201:
            description: Downvote created
        401:
            description: User/API key not found
        404:
            description: Post not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
    if user is None:
        return {'message': 'User/API key not found'}, 401
    post = session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return {'message': 'Post not found'}, 404
    exists = session.query(Downvote).filter(Downvote.post_id == post_id).filter(Downvote.user_id == user.id).first()
    if request.method == 'PUT':
        if exists is None:
            session.add(Downvote(
                post_id=post_id,
                user_id=user.id
            ))
            session.commit()
        return {'message': 'Downvote created'}, 201
    elif exists is not None and request.method == 'DELETE':
        session.delete(exists)
        session.commit()
        return {'message': 'Downvote deleted'}, 200
    
@app.route('/api/media', methods=['PUT'])
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
                        - username
                        - api_key
                        - base64
                    properties:
                        username:
                            type: string
                            description: The user's username
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
            description: User/API key not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    try:
        user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
        if user is None:
            return {'message': 'User/API key not found'}, 401
        exists = session.query(Media).filter(cast(Media.base64, String) == data['base64']).first()
        if not exists:
            session.add(Media(
                base64=data['base64'],
                author_id=user.id
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
                        - username
                        - api_key
                    properties:
                        username:
                            type: string
                            description: The user's username
                        api_key: 
                            type: string
                            description: The user's API key
    responses:
        200:
            description: Post deleted
        401:
            description: User/API key not found
        404:
            description: Post not found
    """
    data = request.get_json()
    session = scoped_session(sessionFactory)
    user = session.query(User).filter(User.username == data['username']).filter(User.api_key == data['api_key']).first()
    if user is None:
        return {'message': 'User/API key not found'}, 401
    post = session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return {'message': 'Post not found'}, 404
    session.delete(post)
    session.commit()
    return {'message': 'Post deleted'}




if __name__ == '__main__':
    app.run(host='0.0.0.0')
    # app.run(ssl_context=('cert.pem', 'key.pem'), host='0.0.0.0')
